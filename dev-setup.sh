#!/bin/bash
set -e

echo "--- Setting up development environment ---"

# Check if uv is installed
if ! command -v uv &> /dev/null
then
    echo "uv could not be found. Please install it first:"
    echo "pip install uv"
    exit 1
fi

# Create virtual environment
echo "--- Creating virtual environment ---"
uv venv

# Install dependencies
echo "--- Installing dependencies ---"
uv pip install -e ".[dev]"

# Install pre-commit hooks
echo "--- Installing pre-commit hooks ---"
uv run pre-commit install -t pre-commit -t pre-push

# Link the extension for local testing
echo "--- Linking local extension to Gemini CLI ---"
if command -v gemini &> /dev/null
then
    gemini extension link .
    echo "Extension linked successfully."
else
    echo "Gemini CLI not found. Skipping extension link."
    echo "Please install it and run 'gemini extension link .' manually."
fi

echo ""
echo "--- Development setup complete! ---"
echo "To activate the virtual environment, run:"
echo "source .venv/bin/activate"
