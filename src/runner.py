"""
Tmux-based runner for autonomous Fireteam execution.

Provides a lean, efficient way to run Fireteam as an autonomous agent
that continues until project completion. Uses tmux for:
- Detached background execution
- Live monitoring capability
- Session persistence across terminal disconnects
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from .api import execute
from .models import ExecutionMode, ExecutionResult
from .claude_cli import CLISession
from .circuit_breaker import create_circuit_breaker
from .rate_limiter import get_rate_limiter


# Session state file location
STATE_DIR = Path.home() / ".fireteam"
LOG_DIR = STATE_DIR / "logs"


@dataclass
class SessionInfo:
    """Information about a running Fireteam session."""
    session_name: str
    project_dir: str
    goal: str
    started_at: str
    pid: int | None = None
    log_file: str | None = None
    status: Literal["running", "completed", "failed", "unknown"] = "unknown"


def ensure_tmux() -> bool:
    """Check if tmux is available."""
    return shutil.which("tmux") is not None


def get_session_name(project_dir: Path) -> str:
    """Generate a session name from project directory."""
    return f"fireteam-{project_dir.name}"


def session_exists(session_name: str) -> bool:
    """Check if a tmux session exists."""
    result = subprocess.run(
        ["tmux", "has-session", "-t", session_name],
        capture_output=True,
    )
    return result.returncode == 0


def list_sessions() -> list[SessionInfo]:
    """List all Fireteam tmux sessions."""
    result = subprocess.run(
        ["tmux", "list-sessions", "-F", "#{session_name}"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return []

    sessions = []
    for name in result.stdout.strip().split("\n"):
        if name.startswith("fireteam-"):
            # Try to load session info
            info = load_session_info(name)
            if info:
                sessions.append(info)
            else:
                sessions.append(SessionInfo(
                    session_name=name,
                    project_dir="unknown",
                    goal="unknown",
                    started_at="unknown",
                ))

    return sessions


def save_session_info(info: SessionInfo) -> None:
    """Save session info to state file."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state_file = STATE_DIR / f"{info.session_name}.json"
    state_file.write_text(json.dumps({
        "session_name": info.session_name,
        "project_dir": info.project_dir,
        "goal": info.goal,
        "started_at": info.started_at,
        "pid": info.pid,
        "log_file": info.log_file,
        "status": info.status,
    }))


def load_session_info(session_name: str) -> SessionInfo | None:
    """Load session info from state file."""
    state_file = STATE_DIR / f"{session_name}.json"
    if not state_file.exists():
        return None

    try:
        data = json.loads(state_file.read_text())
        return SessionInfo(**data)
    except (json.JSONDecodeError, TypeError):
        return None


def clear_session_info(session_name: str) -> None:
    """Remove session info file."""
    state_file = STATE_DIR / f"{session_name}.json"
    if state_file.exists():
        state_file.unlink()


def start_session(
    project_dir: Path,
    goal: str,
    mode: ExecutionMode | None = None,
    context: str = "",
    max_iterations: int | None = None,
    session_name: str | None = None,
) -> SessionInfo:
    """
    Start a new Fireteam session in tmux.

    Creates a detached tmux session running the Fireteam autonomous loop.

    Args:
        project_dir: Project directory to work in
        goal: Task goal/description
        mode: Execution mode (auto-detect if None)
        context: Additional context
        max_iterations: Max loop iterations (None = infinite)
        session_name: Custom session name (auto-generated if None)

    Returns:
        SessionInfo with session details

    Raises:
        RuntimeError: If tmux is not available or session already exists
    """
    if not ensure_tmux():
        raise RuntimeError("tmux is not installed. Please install tmux first.")

    project_dir = Path(project_dir).resolve()
    session_name = session_name or get_session_name(project_dir)

    if session_exists(session_name):
        raise RuntimeError(f"Session '{session_name}' already exists. Use 'attach' or 'kill' first.")

    # Create log directory
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"{session_name}_{timestamp}.log"

    # Build the command to run inside tmux
    mode_arg = f"--mode {mode.value}" if mode else ""
    max_iter_arg = f"--max-iterations {max_iterations}" if max_iterations else ""
    context_arg = f'--context "{context}"' if context else ""

    # Use the fireteam CLI entry point
    fireteam_cmd = (
        f"python -m fireteam.runner run "
        f'--project-dir "{project_dir}" '
        f'--goal "{goal}" '
        f"{mode_arg} {max_iter_arg} {context_arg} "
        f'2>&1 | tee "{log_file}"'
    )

    # Create tmux session
    subprocess.run(
        ["tmux", "new-session", "-d", "-s", session_name, "-c", str(project_dir)],
        check=True,
    )

    # Send the command to the session
    subprocess.run(
        ["tmux", "send-keys", "-t", session_name, fireteam_cmd, "Enter"],
        check=True,
    )

    # Save session info
    info = SessionInfo(
        session_name=session_name,
        project_dir=str(project_dir),
        goal=goal,
        started_at=datetime.now().isoformat(),
        log_file=str(log_file),
        status="running",
    )
    save_session_info(info)

    return info


def attach_session(session_name: str) -> None:
    """Attach to a running Fireteam session."""
    if not session_exists(session_name):
        raise RuntimeError(f"Session '{session_name}' does not exist.")

    # This will replace the current process
    os.execvp("tmux", ["tmux", "attach-session", "-t", session_name])


def kill_session(session_name: str) -> None:
    """Kill a Fireteam session."""
    if not session_exists(session_name):
        raise RuntimeError(f"Session '{session_name}' does not exist.")

    subprocess.run(["tmux", "kill-session", "-t", session_name], check=True)
    clear_session_info(session_name)


def tail_log(session_name: str, lines: int = 50) -> str:
    """Get recent log output from a session."""
    info = load_session_info(session_name)
    if not info or not info.log_file:
        return "No log file found for session."

    log_path = Path(info.log_file)
    if not log_path.exists():
        return "Log file does not exist."

    result = subprocess.run(
        ["tail", "-n", str(lines), str(log_path)],
        capture_output=True,
        text=True,
    )
    return result.stdout


async def run_autonomous(
    project_dir: Path,
    goal: str,
    mode: ExecutionMode | None = None,
    context: str = "",
    max_iterations: int | None = None,
) -> ExecutionResult:
    """
    Run Fireteam autonomously until completion.

    This is the main entry point for autonomous execution.
    Called from within a tmux session.
    """
    log = logging.getLogger("fireteam")
    log.setLevel(logging.INFO)

    # Add console handler with formatting
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    ))
    log.addHandler(handler)

    log.info("=" * 60)
    log.info("FIRETEAM AUTONOMOUS EXECUTION")
    log.info("=" * 60)
    log.info(f"Project: {project_dir}")
    log.info(f"Goal: {goal}")
    log.info(f"Mode: {mode.value if mode else 'auto-detect'}")
    log.info(f"Max iterations: {max_iterations or 'unlimited'}")
    log.info("=" * 60)

    session = CLISession()
    circuit_breaker = create_circuit_breaker()
    rate_limiter = get_rate_limiter()

    try:
        result = await execute(
            project_dir=project_dir,
            goal=goal,
            mode=mode,
            context=context,
            max_iterations=max_iterations,
            session=session,
            circuit_breaker=circuit_breaker,
            logger=log,
        )

        log.info("=" * 60)
        if result.success:
            log.info("EXECUTION COMPLETE - SUCCESS")
            log.info(f"Completion: {result.completion_percentage}%")
        else:
            log.info("EXECUTION COMPLETE - FAILED")
            log.info(f"Error: {result.error}")
        log.info(f"Iterations: {result.iterations}")
        log.info("=" * 60)

        return result

    except KeyboardInterrupt:
        log.warning("Execution interrupted by user")
        raise
    except Exception as e:
        log.error(f"Execution failed: {e}")
        raise


def main():
    """CLI entry point for the tmux runner."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Fireteam autonomous execution runner",
        prog="python -m fireteam.runner",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Start command
    start_parser = subparsers.add_parser("start", help="Start a new autonomous session")
    start_parser.add_argument("--project-dir", "-p", required=True, help="Project directory")
    start_parser.add_argument("--goal", "-g", required=True, help="Task goal")
    start_parser.add_argument("--mode", "-m", choices=["single_turn", "moderate", "full"], help="Execution mode")
    start_parser.add_argument("--context", "-c", default="", help="Additional context")
    start_parser.add_argument("--max-iterations", type=int, help="Max iterations")
    start_parser.add_argument("--session-name", "-s", help="Custom session name")

    # Run command (called from within tmux)
    run_parser = subparsers.add_parser("run", help="Run autonomous execution (called from tmux)")
    run_parser.add_argument("--project-dir", "-p", required=True, help="Project directory")
    run_parser.add_argument("--goal", "-g", required=True, help="Task goal")
    run_parser.add_argument("--mode", "-m", choices=["single_turn", "moderate", "full"], help="Execution mode")
    run_parser.add_argument("--context", "-c", default="", help="Additional context")
    run_parser.add_argument("--max-iterations", type=int, help="Max iterations")

    # List command
    subparsers.add_parser("list", help="List running sessions")

    # Attach command
    attach_parser = subparsers.add_parser("attach", help="Attach to a session")
    attach_parser.add_argument("session_name", help="Session name")

    # Kill command
    kill_parser = subparsers.add_parser("kill", help="Kill a session")
    kill_parser.add_argument("session_name", help="Session name")

    # Logs command
    logs_parser = subparsers.add_parser("logs", help="View session logs")
    logs_parser.add_argument("session_name", help="Session name")
    logs_parser.add_argument("--lines", "-n", type=int, default=50, help="Number of lines")

    args = parser.parse_args()

    if args.command == "start":
        mode = ExecutionMode(args.mode) if args.mode else None
        info = start_session(
            project_dir=Path(args.project_dir),
            goal=args.goal,
            mode=mode,
            context=args.context,
            max_iterations=args.max_iterations,
            session_name=args.session_name,
        )
        print(f"Started session: {info.session_name}")
        print(f"Log file: {info.log_file}")
        print(f"\nTo attach: python -m fireteam.runner attach {info.session_name}")
        print(f"To view logs: python -m fireteam.runner logs {info.session_name}")

    elif args.command == "run":
        mode = ExecutionMode(args.mode) if args.mode else None
        asyncio.run(run_autonomous(
            project_dir=Path(args.project_dir),
            goal=args.goal,
            mode=mode,
            context=args.context,
            max_iterations=args.max_iterations,
        ))

    elif args.command == "list":
        sessions = list_sessions()
        if not sessions:
            print("No active Fireteam sessions.")
        else:
            print("Active Fireteam sessions:")
            for s in sessions:
                print(f"  {s.session_name}")
                print(f"    Project: {s.project_dir}")
                print(f"    Goal: {s.goal[:50]}..." if len(s.goal) > 50 else f"    Goal: {s.goal}")
                print(f"    Started: {s.started_at}")
                print()

    elif args.command == "attach":
        attach_session(args.session_name)

    elif args.command == "kill":
        kill_session(args.session_name)
        print(f"Killed session: {args.session_name}")

    elif args.command == "logs":
        output = tail_log(args.session_name, args.lines)
        print(output)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
