#!/usr/bin/env python3
"""Analyze all test results from the Claude Agent System."""

import json
import os
import glob
import re
from datetime import datetime
from pathlib import Path

def parse_log_file(log_path):
    """Extract key information from an orchestrator log file."""
    with open(log_path, 'r') as f:
        content = f.read()

    data = {
        'log_file': os.path.basename(log_path),
        'project_name': None,
        'project_dir': None,
        'goal': None,
        'start_time': None,
        'end_time': None,
        'total_cycles': 0,
        'final_completion': None,
        'final_status': None,
        'total_duration': None,
        'cycles': []
    }

    # Extract project directory
    match = re.search(r"Project: (.+?)(?:\n|$)", content)
    if match:
        data['project_dir'] = match.group(1).strip()
        data['project_name'] = os.path.basename(data['project_dir'])

    # Extract goal
    match = re.search(r"Goal: (.+?)(?:\n|$)", content)
    if match:
        data['goal'] = match.group(1).strip()

    # Extract start time
    match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*Claude Agent System Starting", content)
    if match:
        data['start_time'] = match.group(1)

    # Extract cycles
    cycle_pattern = r"Review completed - Completion: (\d+)%"
    cycle_num = 0
    for match in re.finditer(cycle_pattern, content):
        completion = int(match.group(1))
        data['cycles'].append({'cycle': cycle_num, 'completion': completion})
        cycle_num += 1
        data['total_cycles'] = cycle_num

    # Extract final state
    match = re.search(r"Final state saved.*completion_percentage['\"]:\s*(\d+)", content)
    if match:
        data['final_completion'] = int(match.group(1))
    elif data['cycles']:
        data['final_completion'] = data['cycles'][-1]['completion']

    # Extract final status
    match = re.search(r"status['\"]:\s*['\"]([^'\"]+)['\"]", content)
    if match:
        data['final_status'] = match.group(1)

    # Extract duration
    match = re.search(r"Total duration: (.+?)(?:\n|$)", content)
    if match:
        data['total_duration'] = match.group(1).strip()

    return data

def analyze_all_tests():
    """Analyze all test projects."""
    logs_dir = "/home/claude/claude-agent-system/logs"
    log_files = sorted(glob.glob(f"{logs_dir}/orchestrator_*.log"))

    print(f"Found {len(log_files)} orchestrator log files\n")

    all_tests = []

    for log_file in log_files:
        try:
            data = parse_log_file(log_file)
            if data['project_name']:
                all_tests.append(data)
                print(f"✓ Parsed: {data['project_name']}")
        except Exception as e:
            print(f"✗ Error parsing {os.path.basename(log_file)}: {e}")

    print(f"\n{'='*80}")
    print(f"COMPREHENSIVE TEST ANALYSIS - ALL 11 PROJECTS")
    print(f"{'='*80}\n")

    # Group tests by project
    projects = {}
    for test in all_tests:
        pname = test['project_name']
        if pname not in projects:
            projects[pname] = []
        projects[pname].append(test)

    print(f"Total unique projects: {len(projects)}\n")

    # Detailed analysis for each project
    project_summaries = []

    for idx, (project_name, runs) in enumerate(sorted(projects.items()), 1):
        # Use the most recent run (last in list after sorting)
        latest_run = runs[-1]

        print(f"{'='*80}")
        print(f"TEST #{idx}: {project_name}")
        print(f"{'='*80}")
        print(f"Log File: {latest_run['log_file']}")
        print(f"Project Dir: {latest_run['project_dir']}")
        print(f"Goal: {latest_run['goal'][:100]}..." if latest_run['goal'] and len(latest_run['goal']) > 100 else f"Goal: {latest_run['goal']}")
        print(f"")
        print(f"RESULTS:")
        print(f"  Total Cycles: {latest_run['total_cycles']}")
        print(f"  Final Completion: {latest_run['final_completion']}%")
        print(f"  Final Status: {latest_run['final_status']}")
        print(f"  Duration: {latest_run['total_duration']}")
        print(f"")

        if latest_run['cycles']:
            print(f"Cycle Progress:")
            for cycle_data in latest_run['cycles'][:10]:  # Show first 10 cycles
                print(f"  Cycle {cycle_data['cycle']}: {cycle_data['completion']}%")
            if len(latest_run['cycles']) > 10:
                print(f"  ... ({len(latest_run['cycles']) - 10} more cycles)")

        print("")

        project_summaries.append({
            'name': project_name,
            'completion': latest_run['final_completion'] or 0,
            'cycles': latest_run['total_cycles'],
            'status': latest_run['final_status'] or 'unknown',
            'duration': latest_run['total_duration'] or 'unknown'
        })

    # Summary table
    print(f"\n{'='*80}")
    print(f"SUMMARY TABLE")
    print(f"{'='*80}\n")
    print(f"{'Project':<30} {'Completion':>12} {'Cycles':>8} {'Status':>15}")
    print(f"{'-'*30} {'-'*12} {'-'*8} {'-'*15}")

    for summary in project_summaries:
        print(f"{summary['name']:<30} {summary['completion']:>11}% {summary['cycles']:>8} {summary['status']:>15}")

    # Calculate averages
    completions = [s['completion'] for s in project_summaries if s['completion']]
    cycles_list = [s['cycles'] for s in project_summaries if s['cycles']]

    if completions:
        avg_completion = sum(completions) / len(completions)
        max_completion = max(completions)
        min_completion = min(completions)

        print(f"\n{'='*80}")
        print(f"STATISTICS")
        print(f"{'='*80}")
        print(f"Total Projects Tested: {len(project_summaries)}")
        print(f"Average Completion: {avg_completion:.1f}%")
        print(f"Max Completion: {max_completion}%")
        print(f"Min Completion: {min_completion}%")
        print(f"Average Cycles: {sum(cycles_list) / len(cycles_list):.1f}")
        print(f"Total Cycles Across All Tests: {sum(cycles_list)}")
        print(f"")

        # Success metrics
        success_count = sum(1 for c in completions if c >= 90)
        print(f"Tests >= 90% Complete: {success_count}/{len(completions)} ({success_count/len(completions)*100:.1f}%)")

    print(f"\n{'='*80}\n")

    return project_summaries

if __name__ == "__main__":
    analyze_all_tests()
