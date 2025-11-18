# Vertex AI Gemini CLI Extension

This extension provides tools to manage prompts in Vertex AI directly from the Gemini CLI. It allows you to create, read, update, list, and delete prompts, making it easier to integrate prompt management into your development workflow.

## Features

*   **Create Prompt**: Save new prompts with specified content, system instructions, model, and display name.
*   **Read Prompt**: Retrieve existing prompts by their ID.
*   **Update Prompt**: Modify the content, system instructions, or model of an existing prompt.
*   **Delete Prompt**: Remove prompts using their ID.
*   **List Prompts**: Search and list prompts, useful for finding prompt IDs based on display names.

## Prerequisites

*   You have the [Gemini CLI](https://github.com/google/gemini-cli) installed.
*   You have a Google Cloud project with the Vertex AI API enabled.
*   You have authenticated with Google Cloud (e.g., by running `gcloud auth application-default login`).

## Installation

Install the extension using the Gemini CLI:

```bash
gemini extensions install https://github.com/gemini-cli-extensions/vertex
```

After installation, set your Google Cloud Project ID and location. The extension requires these to function.

```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"
```

## Usage

Once installed and configured, you can use the Vertex AI prompt management tools by passing natural language commands to the Gemini CLI.

Here are a few examples:

*   **Create a prompt**:
    ```bash
    gemini "create a prompt with content 'Hello World' and display name 'My First Prompt'"
    ```

*   **List existing prompts**:
    ```bash
    gemini "list prompts"
    ```

*   **Read a specific prompt by ID**:
    ```bash
    gemini "read prompt <your-prompt-id>"
    ```

For more detailed information on all available commands and their parameters, please refer to the `extension/commands` files.

## Development

### Local Development Setup

1.  **Clone the repository**:
    ```bash
    git clone git@github.com:gemini-cli-extensions/vertex.git
    cd vertex
    ```

2.  **Install `uv`** (a fast Python package installer):
    ```bash
    pip install uv
    ```

3.  **Create a virtual environment and install dependencies**:
    ```bash
    uv venv
    source .venv/bin/activate
    uv pip install -e ".[dev]"
    ```

4.  **Link your local version for testing**:
    Use the `gemini extension link` command to symlink your local `extension` directory to the Gemini CLI's extensions folder. This allows you to test your changes live.
    ```bash
    gemini extension link .
    ```
    You may need to restart the Gemini CLI for the changes to take effect.

### Code Quality

This project uses:

*   **Ruff**: For linting and formatting.
*   **Pyright**: For static type checking.

To run the checks:

```bash
uv run ruff check .
uv run pyright
```

To automatically fix formatting issues:

```bash
uv run ruff format .
```

### Continuous Integration

This project uses GitHub Actions for CI. The workflow in `.github/workflows/ci.yml` automatically runs linting and type checking on every push and pull request.
