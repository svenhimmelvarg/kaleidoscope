#!/bin/bash
# Test for workflow:get command
set -e

WORKFLOW_ID="1e11af0abd47a164eb008b4caeab57af7a8f064151c6f24f82cfd290da6f6d09"

echo "Testing op workflow:get with a known workflow ID..."
uv run op workflow:get "$WORKFLOW_ID" > workflow_output.json

if [ -s workflow_output.json ]; then
    echo "Successfully retrieved workflow and saved to workflow_output.json"
    cat workflow_output.json | jq .
else
    echo "Failed to retrieve workflow"
    exit 1
fi

echo ""
echo "Testing op workflow:get with an unknown workflow ID..."
if uv run op workflow:get "invalid_workflow_123" 2> error_output.txt; then
    echo "Expected failure, but command succeeded."
    exit 1
else
    echo "Command correctly failed."
    cat error_output.txt
fi

rm workflow_output.json error_output.txt
echo "Tests passed."