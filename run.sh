#!/bin/bash
set -e

# Change to the directory containing this script.
# Exit if the directory change fails.
cd "$(dirname "${BASH_SOURCE[0]}")" || { echo "ERROR: Could not change to script directory." >&2; exit 1; }

# Check if python3 is available
if ! command -v python3 &> /dev/null
then
    echo "python3 could not be found, please install it."
    exit 1
fi

# Check for uv and install if not present using the official installer
if ! command -v uv &> /dev/null
then
    echo "'uv' is not found. Attempting to install it using the official installer..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Add the default installation directory to the PATH for this script's execution
    export PATH="$HOME/.local/bin:$PATH"
fi

# Final check for uv
if ! command -v uv &> /dev/null
then
    echo "Failed to install or find 'uv'. Please install it manually from https://astral.sh/uv/install.sh and ensure it is in your PATH."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment with uv..."
    uv venv
fi

# Install dependencies
echo "Installing dependencies with uv..."
uv pip install .

# Start the server
echo "Starting Vertex AI server..."
./.venv/bin/python3 -m vertex.server
