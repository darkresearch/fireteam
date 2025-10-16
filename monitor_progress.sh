#!/bin/bash

# Progress Monitor - Human-readable updates every 5 minutes
# Logs to: /home/claude/fireteam/logs/progress_monitor.log

SYSTEM_DIR="/home/claude/fireteam"
LOG_FILE="$SYSTEM_DIR/logs/progress_monitor.log"
STATE_FILE="$SYSTEM_DIR/state/current.json"
CHECK_INTERVAL=300  # 5 minutes in seconds

# Create log file if it doesn't exist
touch "$LOG_FILE"

log_update() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $1" | tee -a "$LOG_FILE"
}

format_time() {
    local seconds=$1
    local hours=$((seconds / 3600))
    local minutes=$(((seconds % 3600) / 60))
    local secs=$((seconds % 60))

    if [ $hours -gt 0 ]; then
        printf "%dh %dm %ds" $hours $minutes $secs
    elif [ $minutes -gt 0 ]; then
        printf "%dm %ds" $minutes $secs
    else
        printf "%ds" $secs
    fi
}

get_project_name() {
    local project_dir="$1"
    basename "$project_dir"
}

get_phase_name() {
    local status="$1"
    case "$status" in
        "planning") echo "Planning" ;;
        "executing") echo "Executing" ;;
        "reviewing") echo "Reviewing" ;;
        *) echo "$status" ;;
    esac
}

log_update "=========================================="
log_update "Progress Monitor Started"
log_update "Updates every 5 minutes"
log_update "=========================================="

last_completion=""
last_cycle=""
last_project=""
start_time=$(date +%s)

while true; do
    if [ -f "$STATE_FILE" ]; then
        # Parse JSON state file
        project_dir=$(python3 -c "import json; f=open('$STATE_FILE'); data=json.load(f); print(data.get('project_dir', 'unknown'))" 2>/dev/null)
        completion=$(python3 -c "import json; f=open('$STATE_FILE'); data=json.load(f); print(data.get('completion_percentage', 0))" 2>/dev/null)
        cycle=$(python3 -c "import json; f=open('$STATE_FILE'); data=json.load(f); print(data.get('cycle_number', 0))" 2>/dev/null)
        status=$(python3 -c "import json; f=open('$STATE_FILE'); data=json.load(f); print(data.get('status', 'unknown'))" 2>/dev/null)
        started_at=$(python3 -c "import json; f=open('$STATE_FILE'); data=json.load(f); print(data.get('started_at', ''))" 2>/dev/null)

        project_name=$(get_project_name "$project_dir")
        phase_name=$(get_phase_name "$status")

        # Calculate elapsed time since project start
        if [ -n "$started_at" ]; then
            project_start_epoch=$(python3 -c "from datetime import datetime; dt=datetime.fromisoformat('$started_at'); print(int(dt.timestamp()))" 2>/dev/null || echo "0")
            current_epoch=$(date +%s)
            elapsed=$((current_epoch - project_start_epoch))
            elapsed_formatted=$(format_time $elapsed)
        else
            elapsed_formatted="unknown"
        fi

        # Check if anything changed
        current_state="${project_name}_${completion}_${cycle}"

        if [ "$current_state" != "${last_project}_${last_completion}_${last_cycle}" ]; then
            # Something changed, log an update
            log_update ""
            log_update "╔════════════════════════════════════════════════════════════╗"
            log_update "║ Test: $project_name"
            log_update "║ Progress: ${completion}% complete"
            log_update "║ Cycle: $cycle | Phase: $phase_name"
            log_update "║ Elapsed: $elapsed_formatted"
            log_update "╚════════════════════════════════════════════════════════════╝"

            # Track progress changes
            if [ "$project_name" != "$last_project" ] && [ -n "$last_project" ]; then
                log_update "🎉 New test started: $project_name"
            elif [ "$completion" != "$last_completion" ] && [ -n "$last_completion" ]; then
                if [ "$completion" -gt "$last_completion" ]; then
                    log_update "📈 Progress increased: ${last_completion}% → ${completion}%"
                elif [ "$completion" -lt "$last_completion" ]; then
                    log_update "📉 Progress adjusted: ${last_completion}% → ${completion}%"
                fi
            fi

            if [ "$cycle" != "$last_cycle" ] && [ -n "$last_cycle" ]; then
                log_update "🔄 New cycle started: Cycle $cycle"
            fi

            last_completion="$completion"
            last_cycle="$cycle"
            last_project="$project_name"
        else
            # No change, just log a heartbeat
            log_update "⏱️  $project_name: ${completion}% (Cycle $cycle, $phase_name) - $elapsed_formatted elapsed"
        fi
    else
        log_update "⚠️  State file not found - waiting..."
    fi

    sleep $CHECK_INTERVAL
done
