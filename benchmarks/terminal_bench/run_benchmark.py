#!/usr/bin/env python3
"""
Fireteam Terminal Bench Orchestrator

This script orchestrates Terminal Bench runs for Fireteam, supporting:
- Quick testing on 1-2 sample tasks
- Full benchmark runs on all 80 tasks
- 48-hour task timeout (Fireteam's long-horizon advantage)
- Progressive reporting during execution
- Configuration via config.yaml

Usage:
    # Test on 2 sample tasks
    python run_benchmark.py --test

    # Test on specific task
    python run_benchmark.py --task-id task_001

    # Run full benchmark (80 tasks, ~2-3 weeks)
    python run_benchmark.py --full

    # Run with custom config
    python run_benchmark.py --config custom_config.yaml
"""

import argparse
import json
import subprocess
import sys
import yaml
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()


class FireteamBenchmarkRunner:
    """Orchestrates Terminal Bench runs for Fireteam."""

    def __init__(self, config_path: Path = Path("config.yaml")):
        """Initialize the benchmark runner.

        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.reports_dir = Path("reports")
        self.in_progress_dir = self.reports_dir / "in_progress"

        # Ensure directories exist
        self.reports_dir.mkdir(exist_ok=True)
        self.in_progress_dir.mkdir(exist_ok=True)
        (self.in_progress_dir / "task_logs").mkdir(exist_ok=True)

    def _load_config(self) -> dict:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path) as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            console.print(f"[red]Error: Config file not found: {self.config_path}[/red]")
            sys.exit(1)
        except yaml.YAMLError as e:
            console.print(f"[red]Error parsing config: {e}[/red]")
            sys.exit(1)

    def _get_run_id(self) -> str:
        """Generate unique run ID with timestamp and version."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        version = self.config.get("fireteam", {}).get("version", "main")
        return f"{timestamp}_v{version}"

    def _build_tb_command(
        self,
        task_ids: Optional[list[str]] = None,
        n_tasks: Optional[int] = None,
        test_mode: bool = False,
    ) -> list[str]:
        """Build the Terminal Bench command with all parameters.

        Args:
            task_ids: Specific task IDs to run
            n_tasks: Number of tasks to run
            test_mode: If True, run in test mode with quick settings

        Returns:
            Command as list of strings
        """
        tb_config = self.config.get("terminal_bench", {})
        fireteam_config = self.config.get("fireteam", {})
        reporting_config = self.config.get("reporting", {})

        # Base command
        cmd = ["tb", "run"]

        # Dataset
        dataset = tb_config.get("dataset", "terminal-bench-core")
        version = tb_config.get("version", "0.1.1")
        cmd.extend(["--dataset", f"{dataset}=={version}"])

        # Custom agent via import path
        cmd.extend([
            "--agent-import-path",
            "fireteam_agent:FireteamAgent",
        ])

        # Timeout configuration
        if test_mode:
            # For testing: use shorter timeout (10 minutes)
            console.print("[yellow]Test mode: Using 10-minute timeout[/yellow]")
            cmd.extend(["--global-agent-timeout-sec", "600"])
        else:
            # Production: 48-hour timeout
            timeout_sec = fireteam_config.get("timeout_seconds", 172800)
            cmd.extend(["--global-agent-timeout-sec", str(timeout_sec)])

        # Task selection
        if task_ids:
            for task_id in task_ids:
                cmd.extend(["--task-id", task_id])
        elif n_tasks:
            cmd.extend(["--n-tasks", str(n_tasks)])

        # Concurrency
        concurrency = 1 if test_mode else tb_config.get("concurrency", 1)
        cmd.extend(["--n-concurrent", str(concurrency)])

        # Output configuration
        run_id = self._get_run_id()
        output_path = self.in_progress_dir if not test_mode else Path("reports/test_runs")
        output_path.mkdir(parents=True, exist_ok=True)
        cmd.extend([
            "--output-path", str(output_path),
            "--run-id", run_id,
        ])

        # Logging
        cmd.extend([
            "--log-level", "info",
            "--livestream",  # Enable live output
        ])

        # Upload results (only if configured)
        if reporting_config.get("upload_to_leaderboard", False):
            cmd.append("--upload-results")
        else:
            cmd.append("--no-upload-results")

        # Docker management
        cmd.extend([
            "--rebuild",  # Always rebuild to get latest Fireteam
            "--cleanup",  # Clean up containers after
        ])

        return cmd

    def run_test(self, n_tasks: int = 2, task_ids: Optional[list[str]] = None):
        """Run a quick test on a few tasks.

        Args:
            n_tasks: Number of random tasks to test (if task_ids not specified)
            task_ids: Specific task IDs to test
        """
        console.print(Panel.fit(
            f"[bold cyan]Fireteam Terminal Bench - Test Mode[/bold cyan]\n\n"
            f"Tasks: {', '.join(task_ids) if task_ids else f'{n_tasks} random tasks'}\n"
            f"Timeout: 10 minutes per task\n"
            f"Purpose: Verify Fireteam integration works",
            border_style="cyan",
        ))

        cmd = self._build_tb_command(
            task_ids=task_ids,
            n_tasks=n_tasks if not task_ids else None,
            test_mode=True,
        )

        self._run_command(cmd, test_mode=True)

    def run_full(self):
        """Run the full Terminal Bench benchmark (80 tasks, ~2-3 weeks)."""
        # Show warning and get confirmation
        console.print(Panel.fit(
            f"[bold yellow]Fireteam Terminal Bench - FULL RUN[/bold yellow]\n\n"
            f"[bold]Configuration:[/bold]\n"
            f"• Dataset: {self.config['terminal_bench']['dataset']}\n"
            f"• Tasks: 80 tasks\n"
            f"• Timeout: 48 hours per task\n"
            f"• Concurrency: {self.config['terminal_bench']['concurrency']}\n"
            f"• Estimated time: 2-3 weeks\n\n"
            f"[bold red]WARNING:[/bold red] This is a long-running, expensive benchmark.\n"
            f"Make sure you have:\n"
            f"  1. ANTHROPIC_API_KEY set correctly\n"
            f"  2. Sufficient API credits (expect $$$)\n"
            f"  3. Stable machine (will run for weeks)\n"
            f"  4. Docker configured and working\n\n"
            f"Results will be saved to: {self.in_progress_dir}\n"
            f"Monitor progress with: python monitor_progress.py --watch",
            border_style="yellow",
        ))

        response = console.input("\n[bold]Continue with full benchmark? (yes/no): [/bold]")
        if response.lower() not in ["yes", "y"]:
            console.print("[yellow]Benchmark cancelled.[/yellow]")
            return

        cmd = self._build_tb_command(test_mode=False)
        self._run_command(cmd, test_mode=False)

    def _run_command(self, cmd: list[str], test_mode: bool):
        """Execute the Terminal Bench command.

        Args:
            cmd: Command to execute
            test_mode: Whether this is a test run
        """
        console.print("\n[bold]Executing command:[/bold]")
        console.print(f"[dim]{' '.join(cmd)}[/dim]\n")

        # Save command to log
        log_file = self.in_progress_dir / "command.log"
        with open(log_file, "a") as f:
            f.write(f"\n[{datetime.now().isoformat()}]\n")
            f.write(" ".join(cmd) + "\n\n")

        try:
            # Run Terminal Bench with live output
            with console.status("[bold green]Running Terminal Bench...", spinner="dots"):
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )

                # Stream output
                for line in process.stdout:
                    console.print(line.rstrip())

                process.wait()

            if process.returncode == 0:
                console.print(f"\n[bold green]✓ Benchmark completed successfully![/bold green]")
                if not test_mode:
                    console.print(f"\nResults saved to: {self.in_progress_dir}")
                    console.print("Monitor progress: python monitor_progress.py --summary")
            else:
                console.print(f"\n[bold red]✗ Benchmark failed with code {process.returncode}[/bold red]")
                sys.exit(process.returncode)

        except KeyboardInterrupt:
            console.print("\n[yellow]Benchmark interrupted by user.[/yellow]")
            console.print("Note: Terminal Bench containers may still be running.")
            console.print("Check with: docker ps")
            sys.exit(130)
        except Exception as e:
            console.print(f"\n[bold red]Error running benchmark: {e}[/bold red]")
            sys.exit(1)


def main():
    """Main entry point for the benchmark orchestrator."""
    parser = argparse.ArgumentParser(
        description="Fireteam Terminal Bench Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick test on 2 random tasks
  python run_benchmark.py --test

  # Test on specific task
  python run_benchmark.py --task-id task_001

  # Test on multiple specific tasks
  python run_benchmark.py --task-id task_001 --task-id task_002

  # Run full benchmark (takes ~2-3 weeks)
  python run_benchmark.py --full

For more information, see: benchmarks/TERMINAL_BENCH_PLAN.md
        """,
    )

    # Mode selection (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--test",
        action="store_true",
        help="Test mode: Run on 2 random tasks with 10-min timeout",
    )
    mode_group.add_argument(
        "--full",
        action="store_true",
        help="Full mode: Run all 80 tasks with 48-hour timeout",
    )
    mode_group.add_argument(
        "--task-id",
        action="append",
        metavar="ID",
        help="Run specific task(s) in test mode. Can be used multiple times.",
    )

    # Optional arguments
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.yaml"),
        help="Path to config file (default: config.yaml)",
    )
    parser.add_argument(
        "--n-tasks",
        type=int,
        help="Number of tasks to run in test mode (default: 2)",
    )

    args = parser.parse_args()

    # Initialize runner
    runner = FireteamBenchmarkRunner(config_path=args.config)

    # Execute based on mode
    if args.full:
        runner.run_full()
    elif args.test:
        n_tasks = args.n_tasks or 2
        runner.run_test(n_tasks=n_tasks)
    elif args.task_id:
        runner.run_test(task_ids=args.task_id)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
