"""
State management for Fireteam.
Handles persistence and isolation of project state to prevent cross-project contamination.
"""

import json
import os
import fcntl
from datetime import datetime
from typing import Any
from pathlib import Path


class StateManager:
    """Manages agent system state with project isolation."""

    def __init__(self, state_dir: str = "/home/claude/fireteam/state"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / "current.json"
        self.lock_file = self.state_dir / "state.lock"

    def _acquire_lock(self):
        """Acquire exclusive lock on state file."""
        self.lock_fd = open(self.lock_file, 'w')
        fcntl.flock(self.lock_fd, fcntl.LOCK_EX)

    def _release_lock(self):
        """Release lock on state file."""
        if hasattr(self, 'lock_fd'):
            fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
            self.lock_fd.close()

    def initialize_project(self, project_dir: str, goal: str) -> dict[str, Any]:
        """
        Initialize fresh state for a new project.
        CRITICAL: Completely clears previous state to avoid cross-project contamination.
        """
        self._acquire_lock()
        try:
            state = {
                "project_dir": os.path.abspath(project_dir),
                "goal": goal,
                "status": "planning",
                "cycle_number": 0,
                "completion_percentage": 0,
                "last_known_completion": 0,  # For parse failure fallback
                "consecutive_parse_failures": 0,  # Safety counter
                "validation_checks": 0,
                "git_branch": None,
                "current_plan": None,
                "last_execution_result": None,
                "last_review": None,
                "started_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "completed": False
            }

            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)

            return state
        finally:
            self._release_lock()

    def load_state(self) -> dict[str, Any] | None:
        """Load current state from disk."""
        self._acquire_lock()
        try:
            if not self.state_file.exists():
                return None

            with open(self.state_file, 'r') as f:
                return json.load(f)
        finally:
            self._release_lock()

    def update_state(self, updates: dict[str, Any]) -> dict[str, Any]:
        """
        Update state with new values.
        Always updates the 'updated_at' timestamp.
        """
        self._acquire_lock()
        try:
            # Load state without nested locking
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
            else:
                state = {}

            state.update(updates)
            state['updated_at'] = datetime.now().isoformat()

            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)

            return state
        finally:
            self._release_lock()

    def get_status(self) -> dict[str, Any]:
        """Get current status for CLI display."""
        state = self.load_state()
        if not state:
            return {
                "status": "idle",
                "message": "No active project"
            }

        return {
            "status": state.get("status", "unknown"),
            "project_dir": state.get("project_dir"),
            "goal": state.get("goal"),
            "cycle_number": state.get("cycle_number", 0),
            "completion_percentage": state.get("completion_percentage", 0),
            "last_updated": state.get("updated_at"),
            "completed": state.get("completed", False)
        }

    def mark_completed(self):
        """Mark current project as completed."""
        self.update_state({
            "status": "completed",
            "completed": True,
            "completed_at": datetime.now().isoformat()
        })

    def clear_state(self):
        """Completely clear state - used when project finishes."""
        self._acquire_lock()
        try:
            if self.state_file.exists():
                self.state_file.unlink()
        finally:
            self._release_lock()

    def increment_cycle(self):
        """Increment the cycle counter."""
        self._acquire_lock()
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    state = json.load(f)

                state["cycle_number"] = state.get("cycle_number", 0) + 1
                state['updated_at'] = datetime.now().isoformat()

                with open(self.state_file, 'w') as f:
                    json.dump(state, f, indent=2)
        finally:
            self._release_lock()

    def update_completion_percentage(self, parsed_percentage: int | None, logger=None) -> int:
        """
        Update completion percentage with fallback to last known value on parse failure.

        Args:
            parsed_percentage: Result from parser (may be None if parsing failed)
            logger: Optional logger for warnings

        Returns:
            int: Completion percentage to use
        """
        self._acquire_lock()
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
            else:
                state = {}

            if parsed_percentage is not None:
                # Successful parse - reset failure counter
                state["consecutive_parse_failures"] = 0
                state["last_known_completion"] = parsed_percentage
                state["completion_percentage"] = parsed_percentage
                if logger:
                    logger.info(f"Completion: {parsed_percentage}%")
                result = parsed_percentage
            else:
                # Parse failure - use last known value
                state["consecutive_parse_failures"] = state.get("consecutive_parse_failures", 0) + 1
                last_known = state.get("last_known_completion", 0)

                if logger:
                    logger.warning(
                        f"Could not parse completion percentage "
                        f"(failure #{state['consecutive_parse_failures']}). "
                        f"Using last known: {last_known}%"
                    )

                # Safety valve: stop after 3 consecutive failures
                if state["consecutive_parse_failures"] >= 3:
                    if logger:
                        logger.error(
                            "3 consecutive parse failures - parser may be broken. "
                            "Defaulting to 0% to force investigation."
                        )
                    state["completion_percentage"] = 0
                    result = 0
                else:
                    state["completion_percentage"] = last_known
                    result = last_known

            state['updated_at'] = datetime.now().isoformat()

            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)

            return result
        finally:
            self._release_lock()
