#!/bin/bash
# Resource monitoring for agent system tests

LOG_FILE="/home/claude/claude-agent-system/logs/resource_monitor.log"

echo "=== Resource Monitor Started at $(date) ===" >> $LOG_FILE

while true; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

    # Memory stats
    MEM_INFO=$(free -m | grep Mem | awk '{printf "Total:%sMB Used:%sMB Free:%sMB Available:%sMB", $2, $3, $4, $7}')

    # CPU stats
    CPU_LOAD=$(uptime | awk -F'load average:' '{print $2}')

    # Process count
    CLAUDE_PROCS=$(ps aux | grep -c "claude --print")
    ORCH_PROCS=$(ps aux | grep -c "orchestrator.py")

    # Disk usage
    DISK_USAGE=$(df -h /home/claude | tail -1 | awk '{print $5}')

    # Memory usage percentage
    MEM_PERCENT=$(free | grep Mem | awk '{printf "%.1f", ($3/$2) * 100.0}')

    echo "$TIMESTAMP | $MEM_INFO | CPU:$CPU_LOAD | Disk:$DISK_USAGE | MemUsed:${MEM_PERCENT}% | ClaudeProcs:$CLAUDE_PROCS | OrchProcs:$ORCH_PROCS" >> $LOG_FILE

    # Alert if memory usage > 90%
    if (( $(echo "$MEM_PERCENT > 90" | bc -l) )); then
        echo "$TIMESTAMP | ⚠️ WARNING: Memory usage critical at ${MEM_PERCENT}%" >> $LOG_FILE
    fi

    sleep 30
done
