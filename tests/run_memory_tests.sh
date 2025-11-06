#!/bin/bash
# Run memory system tests

set -e

cd "$(dirname "$0")/.."

echo "=================================="
echo "Running Memory System Tests"
echo "=================================="
echo ""

# Run memory-specific tests
echo "1. Testing MemoryManager..."
python -m pytest tests/test_memory_manager.py -v

echo ""
echo "2. Testing BaseAgent Memory Integration..."
python -m pytest tests/test_base_agent_memory.py -v

echo ""
echo "3. Testing Memory Integration..."
python -m pytest tests/test_memory_integration.py -v

echo ""
echo "4. Testing Project Isolation..."
python -m pytest tests/test_memory_isolation.py -v

echo ""
echo "=================================="
echo "All Memory Tests Complete!"
echo "=================================="

