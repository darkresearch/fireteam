"""Test helpers for Fireteam tests."""

import subprocess
import sys
import os
import re
import time
import threading
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class TestResult:
    """Result from running a Fireteam test."""
    success: bool
    returncode: int
    project_dir: Path
    logs: str
    duration: float
    git_commits: int
    files_created: List[str]
    cycle_count: int
    final_completion: int
    
    def __str__(self):
        """Human-readable summary."""
        status = "✅ SUCCESS" if self.success else "❌ FAILED"
        return (
            f"{status}\n"
            f"  Duration: {self.duration:.1f}s\n"
            f"  Cycles: {self.cycle_count}\n"
            f"  Completion: {self.final_completion}%\n"
            f"  Commits: {self.git_commits}\n"
            f"  Files: {len(self.files_created)}"
        )


class LogParser:
    """Parse Fireteam logs to extract metrics."""
    
    @staticmethod
    def extract_cycle_count(logs: str) -> int:
        """Extract final cycle count from logs."""
        cycles = re.findall(r'CYCLE (\d+)', logs)
        return max(map(int, cycles)) if cycles else 0
    
    @staticmethod
    def extract_final_completion(logs: str) -> int:
        """Extract final completion percentage from logs."""
        completions = re.findall(r'(?:Completion|completion):\s*(\d+)%', logs)
        return int(completions[-1]) if completions else 0


class StreamingOutputHandler:
    """Handle real-time output streaming with progress updates."""
    
    def __init__(self, process: subprocess.Popen, show_progress: bool = True):
        self.process = process
        self.show_progress = show_progress
        self.stdout_lines = []
        self.stderr_lines = []
    
    def collect_output(self) -> tuple[str, str]:
        """Collect output while showing progress."""
        stdout_thread = threading.Thread(
            target=self._stream_output,
            args=(self.process.stdout, self.stdout_lines, True)
        )
        stderr_thread = threading.Thread(
            target=self._stream_output,
            args=(self.process.stderr, self.stderr_lines, False)
        )
        
        stdout_thread.start()
        stderr_thread.start()
        stdout_thread.join()
        stderr_thread.join()
        
        return '\n'.join(self.stdout_lines), '\n'.join(self.stderr_lines)
    
    def _stream_output(self, pipe, lines: List[str], is_stdout: bool):
        """Stream output from pipe, showing progress."""
        for line in iter(pipe.readline, ''):
            if not line:
                break
            line = line.rstrip()
            lines.append(line)
            
            if is_stdout and self.show_progress:
                # Update progress indicator
                if 'CYCLE' in line:
                    cycle = re.search(r'CYCLE (\d+)', line)
                    if cycle:
                        print(f"\r🔄 Cycle {cycle.group(1)}                    ", end='', flush=True)
                elif 'PHASE' in line:
                    phase = re.search(r'PHASE \d+: (\w+)', line)
                    if phase:
                        print(f"\r   → {phase.group(1)}...", end='', flush=True)
                elif 'Completion:' in line:
                    completion = re.search(r'(\d+)%', line)
                    if completion:
                        print(f"\r   ✓ {completion.group(1)}%", flush=True)
        pipe.close()


class FireteamTestRunner:
    """Helper for spawning and testing Fireteam processes."""
    
    def __init__(self, project_dir: Path, system_dir: Path):
        self.project_dir = project_dir
        self.system_dir = system_dir
        self.process = None
        self.start_time = None
    
    def run(self, goal: str, timeout: int = 300, keep_memory: bool = False, 
            show_progress: bool = True) -> TestResult:
        """Spawn Fireteam and wait for completion with real-time output."""
        self.start_time = time.time()
        
        print(f"\n{'='*60}")
        print(f"🚀 Starting Fireteam")
        print(f"{'='*60}")
        print(f"Goal: {goal}")
        print(f"Timeout: {timeout}s\n")
        
        self._ensure_git_repo()
        
        env = os.environ.copy()
        env['FIRETEAM_DIR'] = str(self.system_dir)
        env['PYTHONUNBUFFERED'] = '1'
        
        cmd = [
            sys.executable, 'src/orchestrator.py',
            '--project-dir', str(self.project_dir),
            '--goal', goal
        ]
        if keep_memory:
            cmd.append('--keep-memory')
        
        try:
            self.process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, bufsize=1, env=env
            )
        except FileNotFoundError as e:
            raise RuntimeError(f"Failed to start Fireteam: {e}")
        
        handler = StreamingOutputHandler(self.process, show_progress)
        
        try:
            stdout, stderr = handler.collect_output()
            self.process.wait(timeout=timeout)
            duration = time.time() - self.start_time
            
            print(f"\n{'='*60}")
            print(f"⏱️  Completed in {duration:.1f}s")
            print(f"{'='*60}\n")
            
            cycle_count = LogParser.extract_cycle_count(stdout)
            final_completion = LogParser.extract_final_completion(stdout)
            
            return TestResult(
                success=(self.process.returncode == 0),
                returncode=self.process.returncode,
                project_dir=self.project_dir,
                logs=stdout + "\n" + stderr,
                duration=duration,
                git_commits=self._count_commits(),
                files_created=self._list_files(),
                cycle_count=cycle_count,
                final_completion=final_completion
            )
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
            duration = time.time() - self.start_time
            raise TimeoutError(
                f"⏱️  Fireteam timed out after {timeout}s (ran for {duration:.1f}s)"
            )
    
    def _ensure_git_repo(self):
        """Ensure project directory is a git repo."""
        git_dir = self.project_dir / ".git"
        if not git_dir.exists():
            subprocess.run(['git', 'init'], cwd=self.project_dir, check=True, capture_output=True)
            subprocess.run(['git', 'config', 'user.name', 'Fireteam Test'], 
                         cwd=self.project_dir, check=True, capture_output=True)
            subprocess.run(['git', 'config', 'user.email', 'test@fireteam.ai'],
                         cwd=self.project_dir, check=True, capture_output=True)
    
    def _count_commits(self) -> int:
        """Count git commits in project."""
        try:
            result = subprocess.run(['git', 'rev-list', '--count', 'HEAD'],
                                  cwd=self.project_dir, capture_output=True, 
                                  text=True, check=True)
            return int(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError):
            return 0
    
    def _list_files(self) -> List[str]:
        """List non-git files in project directory."""
        files = []
        for item in self.project_dir.rglob('*'):
            if '.git' in item.parts or not item.is_file():
                continue
            files.append(item.relative_to(self.project_dir).as_posix())
        return sorted(files)


@dataclass
class TerminalBenchResult:
    """Parsed result from terminal-bench run."""
    task_id: str
    success: bool
    passed: bool
    accuracy: float
    duration: Optional[float]
    error: Optional[str]
    
    def __str__(self):
        """Human-readable summary."""
        status = "✅ PASSED" if self.passed else "❌ FAILED"
        lines = [
            f"\n{'='*60}",
            f"Terminal-bench Result: {status}",
            f"{'='*60}",
            f"Task: {self.task_id}",
            f"Success: {'Yes' if self.success else 'No'}",
            f"Accuracy: {self.accuracy * 100:.1f}%",
        ]
        if self.duration:
            lines.append(f"Duration: {self.duration:.1f}s")
        if self.error:
            lines.append(f"Error: {self.error}")
        lines.append(f"{'='*60}\n")
        return '\n'.join(lines)


class TerminalBenchParser:
    """Parse terminal-bench stdout output."""
    
    @staticmethod
    def parse_output(stdout: str, task_id: str) -> TerminalBenchResult:
        """Parse terminal-bench stdout for task results."""
        # Look for success/failure indicators
        success_found = any(keyword in stdout.lower() for keyword in [
            'passed', 'success', '✓', '✅'
        ])
        
        failure_found = any(keyword in stdout.lower() for keyword in [
            'failed', 'error', '✗', '❌'
        ])
        
        # Extract accuracy/score
        accuracy = 0.0
        accuracy_patterns = [
            r'accuracy[:\s]+(\d+\.?\d*)',
            r'score[:\s]+(\d+\.?\d*)',
            r'(\d+)%\s+correct',
        ]
        
        for pattern in accuracy_patterns:
            match = re.search(pattern, stdout.lower())
            if match:
                val = float(match.group(1))
                accuracy = val if val <= 1.0 else val / 100.0
                break
        
        passed = success_found and not failure_found
        
        # Extract duration if available
        duration = None
        duration_match = re.search(
            r'(?:took|duration|time)[:\s]+(\d+\.?\d*)\s*(?:s|sec|seconds)', 
            stdout.lower()
        )
        if duration_match:
            duration = float(duration_match.group(1))
        
        # Extract error message if failed
        error = None
        if not passed:
            error_match = re.search(r'error[:\s]+(.+?)(?:\n|$)', stdout, re.IGNORECASE)
            if error_match:
                error = error_match.group(1).strip()
        
        return TerminalBenchResult(
            task_id=task_id,
            success=success_found,
            passed=passed,
            accuracy=accuracy,
            duration=duration,
            error=error
        )

