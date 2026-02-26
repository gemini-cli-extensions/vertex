# Vertex AI Gemini CLI Extension

This extension provides tools to manage prompts and work with data-driven prompt optimizer in Vertex AI directly from the Gemini CLI. It allows you to create, read, update, list, and delete prompts, making it easier to integrate prompt management into your development workflow.

## Features

### Prompt Management
*   **Create Prompt**: Save new prompts with specified content, system instructions, model, and display name.
*   **Read Prompt**: Retrieve existing prompts by their ID.
*   **Update Prompt**: Modify the content, system instructions, or model of an existing prompt.
*   **Delete Prompt**: Remove prompts using their ID.
*   **List Prompts**: Search and list prompts, useful for finding prompt IDs based on display names.

### Data-Driven Prompt Optimizer
*   **Configuration Generation**: Create the input configurations required to run data-driven prompt optimizer.
*   **Job Execution**: Run large-scale prompt optimization jobs directly on Vertex AI.
*   **Results Analysis**: Perform deep-dive analysis of optimization results, including learning curves and candidate comparisons.
*   **Automated Reporting**: Generate comprehensive HTML reports with tuning suggestions for subsequent runs.

### Few-Shot Prompt Optimizer
*  **Prompt Optimization**: tunes the given prompt by utilizing small set of user-provided examples using few-shot prompt optimization. For more details about the algorithm, please refer to this [documentation](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/prompts/few-shot-optimizer) or this [guide](@./src/vertex/prompt_optimizer/docs/few_shot_prompt_optimization_guide.md).


## Prerequisites

*   You have the [Gemini CLI](https://github.com/google-gemini/gemini-cli) installed.
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

### Prompt Management Examples

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

### Data-Driven Prompt Optimizer Examples

*   **Analyze optimization results**:
    ```bash
    gemini "analyze my data drive prompt optimizer results at gs://your-bucket/optimization-run-1/"
    ```

*   **Configure a new optimization job**:
    ```bash
    gemini "help me configure a new optimization job based on my existing config at gs://your-bucket/config.json"
    ```

*   **Run optimization job**:
    ```bash
    gemini "start a data driven prompt optimizer job using my config at gs://your-bucket/config-new.json"
    ```

For more detailed information on all available commands and workflows, please refer to the `GEMINI.md` file in this repository.

### Few-Shot Prompt Optimization Examples
*   **Few-shot optimization with target response**:
When user examples consit of `(question, model_response, target_response)`, few-shot optimization should be run with "target response" method.
    ```bash
    gemini "Apply few-shot prompt optimization using target response with data from gs://your_bucket/your_examples.csv. Here is the prompt: '...'"

*   **Few-shot optimization with rubrics and evaluations**:
When user examples consit of `(question, model_response, rubrics, rubrics_evaluations)`, few-shot optimization should be run with "rubrics" method.
    ```bash
    gemini "Apply few-shot prompt optimization using rubrics with data from gs://your_bucket/your_examples.csv. Here is the prompt: '...'"

## Development

### Local Development Setup

To set up your development environment, first make the setup script executable, then run it:

```bash
sh ./dev-setup.sh
```

After running the script, activate your virtual environment:

```bash
source .venv/bin/activate
```


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

### Testing

To run the unit tests locally:

```bash
uv run python3 -m unittest discover
```

### Pre-commit Hooks

This project uses `pre-commit` to enforce code quality checks automatically before commits and pushes. The `dev-setup.sh` script automatically installs these hooks for you.

*   **On `git commit`**: `ruff` (linting and formatting) and `pyright` (static type checking) will run.
*   **On `git push`**: `pytest` will run to execute the test suite.

### Continuous Integration

This project uses GitHub Actions for CI. The workflow in `.github/workflows/ci.yml` automatically runs linting and type checking on every push and pull request.
