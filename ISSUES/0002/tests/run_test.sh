#!/bin/bash
# Test script for ISSUES/0002 - Support Image Uploads for op workflow:invoke

WORKFLOW_ID="6470a1021d44f31603b2a0ffdea7e6f724e4f48d8d5221f9c6218585ef7a7887"
PAYLOAD_FILE="./test_invoke.json"

echo "Invoking workflow with local image payload..."
echo "Payload file: $PAYLOAD_FILE"
echo "Workflow ID: $WORKFLOW_ID"

# Change directory to ensure relative paths work correctly
cd "$(dirname "$0")"

# We run python -m op from the project root
cd ../../../
python -m op workflow:invoke "$WORKFLOW_ID" "ISSUES/0002/tests/test_invoke.json"
