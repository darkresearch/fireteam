#!/usr/bin/env python3
"""
Main orchestrator for the Claude agent system.
Manages infinite cycles of planning → execution → review.
"""

import os
import sys
import logging
import subprocess
import signal
from datetime import datetime
from pathlib import Path

# Add system directory to path
sys.path.insert(0, '/home/claude/claude-agent-system')

import config
from state.manager import StateManager
from agents import PlannerAgent, ExecutorAgent, ReviewerAgent


class Orchestrator:
    """Main orchestrator managing the agent system lifecycle."""

    def __init__(self, project_dir: str, goal: str):
        self.project_dir = os.path.abspath(project_dir)
        self.goal = goal
        self.state_manager = StateManager()

        # Set up logging
        self.setup_logging()

        # Initialize agents
        self.planner = PlannerAgent(self.logger)
        self.executor = ExecutorAgent(self.logger)
        self.reviewer = ReviewerAgent(self.logger)

        # Signal handling for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self.running = True

    def setup_logging(self):
        """Set up logging to file and console."""
        log_file = os.path.join(
            config.LOGS_DIR,
            f"orchestrator_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )

        logging.basicConfig(
            level=getattr(logging, config.LOG_LEVEL),
            format=config.LOG_FORMAT,
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )

        self.logger = logging.getLogger("orchestrator")
        self.logger.info("=" * 80)
        self.logger.info("Claude Agent System Starting")
        self.logger.info(f"Project: {self.project_dir}")
        self.logger.info(f"Goal: {self.goal}")
        self.logger.info("=" * 80)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    def initialize_git_repo(self) -> str:
        """
        Initialize git repo if needed and create a new branch.
        Returns the branch name.
        """
        try:
            # Ensure project directory exists
            os.makedirs(self.project_dir, exist_ok=True)

            # Check if .git exists
            git_dir = os.path.join(self.project_dir, ".git")
            if not os.path.exists(git_dir):
                self.logger.info("Initializing new git repository")
                subprocess.run(
                    ["git", "init"],
                    cwd=self.project_dir,
                    check=True,
                    capture_output=True
                )

                # Set git config
                subprocess.run(
                    ["git", "config", "user.name", config.GIT_USER_NAME],
                    cwd=self.project_dir,
                    check=True,
                    capture_output=True
                )
                subprocess.run(
                    ["git", "config", "user.email", config.GIT_USER_EMAIL],
                    cwd=self.project_dir,
                    check=True,
                    capture_output=True
                )

                # Create initial commit if no commits exist
                subprocess.run(
                    ["git", "add", "."],
                    cwd=self.project_dir,
                    check=True,
                    capture_output=True
                )
                subprocess.run(
                    ["git", "commit", "-m", "Initial commit", "--allow-empty"],
                    cwd=self.project_dir,
                    check=True,
                    capture_output=True
                )

            # Create new branch with timestamp
            branch_name = f"agent-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            self.logger.info(f"Creating branch: {branch_name}")

            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=self.project_dir,
                check=True,
                capture_output=True
            )

            return branch_name

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Git initialization error: {e}")
            raise

    def commit_changes(self, cycle_number: int, message_suffix: str = ""):
        """Commit changes after each cycle."""
        try:
            # Check if there are changes to commit
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=True
            )

            if not result.stdout.strip():
                self.logger.info("No changes to commit")
                return

            # Add all changes
            subprocess.run(
                ["git", "add", "."],
                cwd=self.project_dir,
                check=True,
                capture_output=True
            )

            # Commit with descriptive message
            commit_msg = f"Cycle {cycle_number}: {message_suffix}"
            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=self.project_dir,
                check=True,
                capture_output=True
            )

            self.logger.info(f"Committed changes: {commit_msg}")

            # Push to remote if it exists
            self.push_to_remote()

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Git commit error: {e}")
            # Don't raise - continue even if commit fails

    def push_to_remote(self):
        """Push to remote origin if it exists."""
        try:
            # Check if remote exists
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=self.project_dir,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                self.logger.info("Pushing to remote origin")
                subprocess.run(
                    ["git", "push", "-u", "origin", "HEAD"],
                    cwd=self.project_dir,
                    check=True,
                    capture_output=True
                )
                self.logger.info("Successfully pushed to remote")

        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Could not push to remote: {e}")
            # Don't raise - pushing is optional

    def run_cycle(self, state: dict) -> dict:
        """
        Run a single plan → execute → review cycle.
        Returns updated state.
        """
        cycle_num = state.get("cycle_number", 0)
        self.logger.info(f"\n{'=' * 80}")
        self.logger.info(f"CYCLE {cycle_num} - Starting")
        self.logger.info(f"{'=' * 80}\n")

        # Goal alignment check every 3 cycles
        if cycle_num > 0 and cycle_num % 3 == 0:
            self.logger.info(f"{'='*60}")
            self.logger.info(f"GOAL ALIGNMENT CHECK (Cycle {cycle_num})")
            self.logger.info(f"{'='*60}")
            self.logger.info(f"Original Goal: {self.goal}")
            self.logger.info(f"\n⚠️  Reminder: Ensure all work aligns with original goal!")
            self.logger.info(f"{'='*60}\n")

        # PHASE 1: Planning
        self.logger.info("PHASE 1: Planning")
        self.state_manager.update_state({"status": "planning"})

        planner_result = self.planner.execute(
            project_dir=self.project_dir,
            goal=self.goal,
            cycle_number=cycle_num,
            previous_plan=state.get("current_plan"),
            last_execution_result=state.get("last_execution_result"),
            last_review=state.get("last_review")
        )

        if not planner_result["success"]:
            self.logger.error(f"Planning failed: {planner_result.get('error')}")
            return state

        current_plan = planner_result["plan"]
        self.logger.info("Planning completed")

        # PHASE 2: Execution
        self.logger.info("\nPHASE 2: Execution")
        self.state_manager.update_state({
            "status": "executing",
            "current_plan": current_plan
        })

        executor_result = self.executor.execute(
            project_dir=self.project_dir,
            goal=self.goal,
            plan=current_plan,
            cycle_number=cycle_num
        )

        if not executor_result["success"]:
            self.logger.error(f"Execution failed: {executor_result.get('error')}")
            return state

        execution_result = executor_result["execution_result"]
        self.logger.info("Execution completed")

        # PHASE 3: Review
        self.logger.info("\nPHASE 3: Review")
        self.state_manager.update_state({
            "status": "reviewing",
            "last_execution_result": execution_result
        })

        is_validation = state.get("completion_percentage", 0) >= config.COMPLETION_THRESHOLD

        reviewer_result = self.reviewer.execute(
            project_dir=self.project_dir,
            goal=self.goal,
            plan=current_plan,
            execution_result=execution_result,
            cycle_number=cycle_num,
            is_validation=is_validation
        )

        if not reviewer_result["success"]:
            self.logger.error(f"Review failed: {reviewer_result.get('error')}")
            return state

        review = reviewer_result["review"]
        parsed_completion = reviewer_result["completion_percentage"]

        # Use StateManager's parse failure handling
        completion_pct = self.state_manager.update_completion_percentage(
            parsed_completion,
            logger=self.logger
        )

        self.logger.info(f"Review completed - Completion: {completion_pct}%")

        # Update state (completion_percentage already set by update_completion_percentage)
        updated_state = self.state_manager.update_state({
            "current_plan": current_plan,
            "last_execution_result": execution_result,
            "last_review": review
        })

        # Commit changes
        self.commit_changes(cycle_num, f"{completion_pct}% complete")

        # Increment cycle counter
        self.state_manager.increment_cycle()

        return updated_state

    def check_completion(self, state: dict) -> bool:
        """
        Check if project is complete based on validation logic.
        Requires 3 consecutive reviews with >95% completion.
        """
        completion_pct = state.get("completion_percentage", 0)
        validation_checks = state.get("validation_checks", 0)

        if completion_pct >= config.COMPLETION_THRESHOLD:
            validation_checks += 1
            self.state_manager.update_state({"validation_checks": validation_checks})

            self.logger.info(f"Validation check {validation_checks}/{config.VALIDATION_CHECKS_REQUIRED}")

            if validation_checks >= config.VALIDATION_CHECKS_REQUIRED:
                self.logger.info("Project completed! All validation checks passed.")
                return True
        else:
            # Reset validation checks if percentage drops
            if validation_checks > 0:
                self.logger.info("Completion percentage dropped, resetting validation checks")
                self.state_manager.update_state({"validation_checks": 0})

        return False

    def run(self):
        """Main execution loop."""
        try:
            # Initialize state
            state = self.state_manager.initialize_project(self.project_dir, self.goal)

            # Initialize git
            branch_name = self.initialize_git_repo()
            self.state_manager.update_state({"git_branch": branch_name})

            # Infinite loop until completion
            while self.running:
                state = self.run_cycle(state)

                if self.check_completion(state):
                    self.state_manager.mark_completed()
                    self.logger.info("\n" + "=" * 80)
                    self.logger.info("PROJECT COMPLETED SUCCESSFULLY")
                    self.logger.info("=" * 80)
                    break

            return 0

        except Exception as e:
            self.logger.error(f"Orchestrator error: {e}", exc_info=True)
            return 1


def main():
    """Entry point for orchestrator."""
    import argparse

    parser = argparse.ArgumentParser(description="Claude Agent System Orchestrator")
    parser.add_argument("--project-dir", required=True, help="Project directory")
    parser.add_argument("--goal", required=True, help="Project goal/prompt")

    args = parser.parse_args()

    orchestrator = Orchestrator(args.project_dir, args.goal)
    sys.exit(orchestrator.run())


if __name__ == "__main__":
    main()
