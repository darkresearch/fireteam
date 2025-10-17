#!/bin/bash
# Batch test runner - runs all tests sequentially with auto-progression
# Runs in background, survives session disconnections

SYSTEM_DIR="/home/claude/fireteam"
LOG_FILE="$SYSTEM_DIR/logs/batch_test_runner.log"
COMPLETION_THRESHOLD=90  # Stop test when it reaches this percentage

# Test definitions: "project_dir|prompt"
declare -a TESTS=(
    "/home/claude/csv-analyzer-v2|Build a Python CLI tool that analyzes CSV files and generates statistics. Requirements: Read CSV files using pandas or csv module, calculate statistics (mean, median, standard deviation, min, max) for numeric columns, generate a summary report in both terminal output and JSON format, handle missing data gracefully, include a sample CSV file with test data, support filtering by column, and make it production-ready with proper error handling and documentation."

    "/home/claude/json-log-parser|Build a Python CLI tool that parses JSON-formatted application logs and extracts insights. Requirements: Parse JSON log files line-by-line, filter by log level (ERROR, WARN, INFO, DEBUG), count occurrences by type, generate summary statistics (total logs, errors per hour/day, top error messages), support date range filtering, create sample log file with realistic data, export results to JSON/CSV, and make it production-ready with proper error handling."

    "/home/claude/web-scraper|Build a Python web scraper that extracts top headlines from Hacker News front page. Requirements: Use requests + BeautifulSoup, extract titles/scores/authors, handle pagination (top 10 stories), export to JSON/CSV, respect robots.txt, implement rate limiting, handle network errors gracefully, and make it production-ready with proper error handling."

    "/home/claude/task-manager-cli|Build a Task Manager CLI with SQLite persistence. Requirements: SQLite database for storage, CRUD operations (Create, Read, Update, Delete tasks), task properties (id, title, description, status, due_date), commands (add, list, complete, delete), filter by status (pending/completed), and make it production-ready with proper error handling and documentation."

    "/home/claude/rest-api-server|Build a REST API server for a note-taking application using Flask or FastAPI. Requirements: Endpoints for GET, POST, PUT, DELETE notes, SQLite or in-memory storage, JSON request/response, input validation, error handling (404, 400, 500), API documentation (Swagger for FastAPI), basic tests using pytest, and make it production-ready."

    "/home/claude/github-analyzer|Build a CLI tool that analyzes GitHub repositories using GitHub API. Requirements: Fetch repo info (stars, forks, languages, contributors), analyze commit history (last 30 days), generate markdown report, handle API rate limits, pretty terminal output with colors, and make it production-ready with proper error handling."
)

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

get_completion_percentage() {
    local state_file="$SYSTEM_DIR/state/current.json"
    if [ -f "$state_file" ]; then
        python3 -c "import json; f=open('$state_file'); data=json.load(f); print(data.get('completion_percentage', 0))" 2>/dev/null || echo "0"
    else
        echo "0"
    fi
}

wait_for_completion() {
    local project_name="$1"
    local max_wait_minutes=90  # Max 90 minutes per test
    local check_interval=60    # Check every minute
    local elapsed=0

    log_message "Waiting for $project_name to reach $COMPLETION_THRESHOLD%..."

    while [ $elapsed -lt $((max_wait_minutes * 60)) ]; do
        sleep $check_interval
        elapsed=$((elapsed + check_interval))

        completion=$(get_completion_percentage)
        log_message "$project_name: ${completion}% complete (${elapsed}s elapsed)"

        # Check if threshold reached
        if [ "$completion" -ge "$COMPLETION_THRESHOLD" ]; then
            log_message "$project_name: Reached $completion% - SUCCESS!"
            return 0
        fi

        # Check if process still running
        if ! pgrep -f "orchestrator.py" > /dev/null; then
            log_message "$project_name: Process died unexpectedly"
            return 1
        fi
    done

    log_message "$project_name: Timeout after $max_wait_minutes minutes"
    return 2
}

run_test() {
    local test_def="$1"
    local project_dir=$(echo "$test_def" | cut -d'|' -f1)
    local prompt=$(echo "$test_def" | cut -d'|' -f2-)
    local project_name=$(basename "$project_dir")

    log_message "========================================"
    log_message "Starting Test: $project_name"
    log_message "Project Dir: $project_dir"
    log_message "========================================"

    # Start the test
    $SYSTEM_DIR/cli/start-agent --project-dir "$project_dir" --prompt "$prompt"

    if [ $? -ne 0 ]; then
        log_message "ERROR: Failed to start $project_name"
        return 1
    fi

    # Wait for completion or threshold
    wait_for_completion "$project_name"
    local result=$?

    # Stop the agent
    $SYSTEM_DIR/cli/stop-agent

    # Record result
    if [ $result -eq 0 ]; then
        log_message "$project_name: COMPLETED SUCCESSFULLY"
        echo "$project_name" >> "$SYSTEM_DIR/logs/completed_tests.txt"
    elif [ $result -eq 1 ]; then
        log_message "$project_name: FAILED (process died)"
        echo "$project_name" >> "$SYSTEM_DIR/logs/failed_tests.txt"
    else
        log_message "$project_name: TIMEOUT"
        echo "$project_name" >> "$SYSTEM_DIR/logs/timeout_tests.txt"
    fi

    # Brief pause between tests
    sleep 10

    return $result
}

# Main execution
main() {
    log_message "=========================================="
    log_message "Batch Test Runner Started"
    log_message "Tests to run: ${#TESTS[@]}"
    log_message "Completion threshold: $COMPLETION_THRESHOLD%"
    log_message "=========================================="

    # Clean up old result files
    rm -f "$SYSTEM_DIR/logs/completed_tests.txt"
    rm -f "$SYSTEM_DIR/logs/failed_tests.txt"
    rm -f "$SYSTEM_DIR/logs/timeout_tests.txt"

    local test_num=1
    local total_tests=${#TESTS[@]}

    for test_def in "${TESTS[@]}"; do
        log_message "Running test $test_num of $total_tests"
        run_test "$test_def"
        test_num=$((test_num + 1))
    done

    log_message "=========================================="
    log_message "Batch Test Runner Completed"
    log_message "=========================================="

    # Summary
    local completed=$(wc -l < "$SYSTEM_DIR/logs/completed_tests.txt" 2>/dev/null || echo "0")
    local failed=$(wc -l < "$SYSTEM_DIR/logs/failed_tests.txt" 2>/dev/null || echo "0")
    local timeout=$(wc -l < "$SYSTEM_DIR/logs/timeout_tests.txt" 2>/dev/null || echo "0")

    log_message "Results:"
    log_message "  Completed: $completed"
    log_message "  Failed: $failed"
    log_message "  Timeout: $timeout"
}

# Run in background if --background flag provided
if [ "$1" == "--background" ]; then
    nohup bash "$0" >> "$LOG_FILE" 2>&1 &
    echo "Batch test runner started in background (PID: $!)"
    echo "Monitor progress: tail -f $LOG_FILE"
    exit 0
fi

# Run normally
main
