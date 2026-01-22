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
from .circuit_breaker import create_circuit_breaker
from .claude_cli import CLISession
from .models import ExecutionMode, ExecutionResult
from .prompt import resolve_prompt

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
    goal: str | None = None,
    goal_file: str | Path | None = None,
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
        goal: Task goal/description (string)
        goal_file: Path to goal file (PROMPT.md style)
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

    # Resolve prompt (validates that we have a valid prompt source)
    prompt = resolve_prompt(
        goal=goal,
        goal_file=goal_file,
        project_dir=project_dir,
        edit=False,  # Can't do interactive edit when starting tmux session
    )

    # Create log directory
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"{session_name}_{timestamp}.log"

    # Write the resolved prompt to a temp file for the tmux session to read
    prompt_file = STATE_DIR / f"{session_name}_prompt.md"
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    prompt_file.write_text(prompt.render())

    # Build the command to run inside tmux
    mode_arg = f"--mode {mode.value}" if mode else ""
    max_iter_arg = f"--max-iterations {max_iterations}" if max_iterations else ""
    context_arg = f'--context "{context}"' if context else ""

    # Use the fireteam CLI entry point with --goal-file
    fireteam_cmd = (
        f"python -m fireteam.runner run "
        f'--project-dir "{project_dir}" '
        f'--goal-file "{prompt_file}" '
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

    # Save session info (use truncated prompt.goal for display)
    goal_summary = prompt.goal[:200] + "..." if len(prompt.goal) > 200 else prompt.goal
    info = SessionInfo(
        session_name=session_name,
        project_dir=str(project_dir),
        goal=goal_summary,
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
    goal: str | None = None,
    goal_file: str | Path | None = None,
    mode: ExecutionMode | None = None,
    context: str = "",
    max_iterations: int | None = None,
    edit: bool = False,
) -> ExecutionResult:
    """
    Run Fireteam autonomously until completion.

    This is the main entry point for autonomous execution.
    Called from within a tmux session.

    Args:
        project_dir: Project directory to work in
        goal: Task goal/description (string)
        goal_file: Path to goal file (PROMPT.md style)
        mode: Execution mode (auto-detect if None)
        context: Additional context
        max_iterations: Max loop iterations (None = infinite)
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

    # Resolve the prompt
    prompt = resolve_prompt(
        goal=goal,
        goal_file=goal_file,
        project_dir=project_dir,
        edit=edit,
    )
    goal_text = prompt.render()

    log.info("=" * 60)
    log.info("FIRETEAM AUTONOMOUS EXECUTION")
    log.info("=" * 60)
    log.info(f"Project: {project_dir}")
    log.info(f"Goal: {goal_text[:200]}{'...' if len(goal_text) > 200 else ''}")
    if prompt.included_files:
        log.info(f"Included files: {len(prompt.included_files)}")
    log.info(f"Mode: {mode.value if mode else 'auto-detect'}")
    log.info(f"Max iterations: {max_iterations or 'unlimited'}")
    log.info("=" * 60)

    session = CLISession()
    circuit_breaker = create_circuit_breaker()

    try:
        result = await execute(
            project_dir=project_dir,
            goal=goal_text,
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


def main() -> None:
    """CLI entry point for the tmux runner."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Fireteam - autonomous task execution with Claude",
        prog="fireteam",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Start command
    start_parser = subparsers.add_parser(
        "start",
        help="Start a background session in tmux",
        description="""Start autonomous task execution in a detached tmux session.

Creates a PROMPT.md file in your project directory with your task, then run
this command. Fireteam will execute until complete. Use 'fireteam attach' to
watch progress or 'fireteam logs' to check output.""",
    )
    start_parser.add_argument("--project-dir", "-p", default=".", help="Project directory (default: current)")
    start_parser.add_argument("--goal", "-g", help="Task goal as a string")
    start_parser.add_argument("--goal-file", "-f", help="Path to goal file (default: auto-detect PROMPT.md)")
    start_parser.add_argument("--mode", "-m", choices=["single_turn", "moderate", "full"], help="Execution mode (default: auto-detect from complexity)")
    start_parser.add_argument("--context", "-c", default="", help="Additional context to include")
    start_parser.add_argument("--max-iterations", type=int, help="Maximum iterations before stopping (default: unlimited)")
    start_parser.add_argument("--session-name", "-s", help="Custom tmux session name (default: fireteam-<project>)")

    # Run command
    run_parser = subparsers.add_parser(
        "run",
        help="Run in foreground (blocking)",
        description="""Run autonomous task execution in the foreground.

Like 'start' but blocks until complete. Useful for short tasks or debugging.
Output streams directly to your terminal. Use --edit to open an editor for
writing your goal interactively.""",
    )
    run_parser.add_argument("--project-dir", "-p", default=".", help="Project directory (default: current)")
    run_parser.add_argument("--goal", "-g", help="Task goal as a string")
    run_parser.add_argument("--goal-file", "-f", help="Path to goal file (default: auto-detect PROMPT.md)")
    run_parser.add_argument("--edit", "-e", action="store_true", help="Open $EDITOR to write goal interactively")
    run_parser.add_argument("--mode", "-m", choices=["single_turn", "moderate", "full"], help="Execution mode (default: auto-detect from complexity)")
    run_parser.add_argument("--context", "-c", default="", help="Additional context to include")
    run_parser.add_argument("--max-iterations", type=int, help="Maximum iterations before stopping (default: unlimited)")

    # List command
    subparsers.add_parser(
        "list",
        help="List running sessions",
        description="Show all active Fireteam tmux sessions with their status, project directory, and goal.",
    )

    # Attach command
    attach_parser = subparsers.add_parser(
        "attach",
        help="Attach to a session",
        description="Attach to a running tmux session to watch execution in real-time. Detach with Ctrl+B D.",
    )
    attach_parser.add_argument("session_name", help="Session name (e.g., fireteam-myproject)")

    # Kill command
    kill_parser = subparsers.add_parser(
        "kill",
        help="Terminate a session",
        description="Stop a running Fireteam session and clean up its state files.",
    )
    kill_parser.add_argument("session_name", help="Session name to terminate")

    # Logs command
    logs_parser = subparsers.add_parser(
        "logs",
        help="View session logs",
        description="Display recent log output from a Fireteam session. Logs are stored in ~/.fireteam/logs/.",
    )
    logs_parser.add_argument("session_name", help="Session name to view logs for")
    logs_parser.add_argument("--lines", "-n", type=int, default=50, help="Number of lines to show (default: 50)")

    args = parser.parse_args()

    if args.command == "start":
        mode = ExecutionMode(args.mode) if args.mode else None
        try:
            info = start_session(
                project_dir=Path(args.project_dir),
                goal=args.goal,
                goal_file=args.goal_file,
                mode=mode,
                context=args.context,
                max_iterations=args.max_iterations,
                session_name=args.session_name,
            )
            print(f"Started session: {info.session_name}")
            print(f"Log file: {info.log_file}")
            print(f"\nTo attach: fireteam attach {info.session_name}")
            print(f"To view logs: fireteam logs {info.session_name}")
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)

    elif args.command == "run":
        mode = ExecutionMode(args.mode) if args.mode else None
        try:
            asyncio.run(run_autonomous(
                project_dir=Path(args.project_dir),
                goal=args.goal,
                goal_file=args.goal_file,
                mode=mode,
                context=args.context,
                max_iterations=args.max_iterations,
                edit=args.edit,
            ))
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)

    elif args.command == "list":
        sessions = list_sessions()
        if not sessions:
            print("No active Fireteam sessions.")
        else:
            print("Active Fireteam sessions:")
            for s in sessions:
                print(f"  {s.session_name}")
                print(f"    Project: {s.project_dir}")
                goal_display = s.goal or "(from file)"
                print(f"    Goal: {goal_display[:50]}..." if len(goal_display) > 50 else f"    Goal: {goal_display}")
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
