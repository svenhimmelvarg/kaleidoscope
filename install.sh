#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "Starting Kaleidoscope installation..."

# Check prerequisites
if ! command -v git &> /dev/null; then
    echo "Error: git is not installed."
    exit 1
fi

if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed. Please install it from https://github.com/astral-sh/uv"
    exit 1
fi

echo "Creating virtual environment using uv..."
uv venv

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing package and dependencies..."
uv pip install -e .

echo "Initializing configuration..."
op init

echo "Please enter the absolute or relative path to your ComfyUI instance."
echo "Press Enter to use the current directory ('.'):"
read -p "> " comfy_path

if [ -z "$comfy_path" ]; then
    comfy_path="."
fi

echo "Setting required configuration paths..."
op config set COMFYUI_INSTANCE_BASE_PATH "$comfy_path"

echo "Current configuration:"
op config show

echo "Validating configuration:"
op config validate

echo ""
echo "Installation and configuration complete!"
echo "To start the application, run:"
echo "  source .venv/bin/activate"
echo "  op start"
