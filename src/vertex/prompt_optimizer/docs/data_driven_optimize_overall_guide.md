# Guide to Data-Driven Optimize (Prompt Optimizer)

## 1. Introduction to Data-Driven Optimize

Data-Driven Optimize (Prompt Optimizer), also known as Auto Prompt Optimization,
is a powerful Vertex AI feature designed to enhance the performance of your
Large Language Models (LLMs). Manually iterating on prompts to find the one
that performs best can be time-consuming and inefficient. Data-Driven Optimize
automates this process using a data-driven approach.

### What problem does it solve?

Data-Driven Optimize addresses the challenge of prompt engineering. Instead of
relying on intuition to create the perfect prompt, you can use Data-Driven
Optimize to systematically test and discover prompts that yield the best
results for your specific task, based on your own data.

### How does it work?

The process is straightforward:
1.  **You provide a starting point:** This includes a base prompt (or just a
    task description), a dataset with examples, and a metric to measure
    success.
2.  **The Optimizer takes over:** It runs a sophisticated tuning job that
    generates many new prompt variations.
3.  **Evaluation and Ranking:** Each new prompt is tested against your dataset,
    and its performance is scored based on the evaluation metric you chose.
4.  **You get the best prompt:** The service returns a ranked list of the
    best-performing prompts, which you can then integrate into your
    application.

This document serves as a detailed guide to configuring the parameters for a
Data-Driven Optimize job to ensure a successful and effective optimization run.

## 2. Configuration Parameters

A Data-Driven Optimize job is configured using a flat JSON file. The parameters
are detailed below.

### 2.1. Job Configuration

This section covers settings related to the execution and output of your job.

*   **`project`**: (Required) Your Google Cloud project ID.
*   **`output_path`**: (Required) The Cloud Storage URI
    (e.g., `gs://your-bucket/folder/`) where the optimization job will save its
    results. This path **must** be a GCS location.
    *   **Suggestion:** It is highly recommended to create a unique folder for
        each optimization job's output. This helps in keeping results organized
        and avoids potential conflicts. Note that while the job requires a GCS
        path, the analysis tools can read the output files from GCS or a local
        copy.

### 2.2. Model and Prompt Configuration

This section deals with the models, prompts, and instructions that form the
core of the optimization.

*   **`prompt_optimizer_method`**: (Required) The method for prompt optimization. 
    Supported values:
    - `VAPO`: Standard prompt optimization.
    - `OPTIMIZATION_TARGET_GEMINI_NANO`: Specialized target for Gemini Nano.
*   **`target_model`**: (Required) The model you are optimizing the prompt for
    (e.g., "gemini-2.5-flash", "gemini-nano").
*   **`target_model_location`**: (Optional) The Google Cloud location for the
    target model (e.g., `us-central1`).
*   **`target_model_qps`**: (Optional) The maximum queries per second for the
    target model. Defaults to a sensible value like 5.
*   **`optimizer_model`**: (Optional) The powerful model used to generate mutant
    prompt variations (e.g., "gemini-2.5-pro"). If not specified, a default
    high-performing model is used.
*   **`optimizer_model_location`**: (Optional) The Google Cloud location for the
    optimizer model.
*   **`optimizer_model_qps`**: (Optional) QPS limit for the optimizer model.
*   **`eval_model`**: The model used for model-based evaluation. If not
    specified, it defaults to the `target_model`.
*   **`eval_model_location`**: (Optional) The Google Cloud location for the
    evaluation model.
*   **`eval_model_qps`**: (Optional) QPS limit for the evaluation model.
*   **`prompt_template`**: (Required) The prompt template, which defines the
    structure of the prompt. It often includes placeholders for input
    variables (e.g., `Input: {{ query }}`).
*   **`demo_and_query_template`**: (Optional) A template used to format few-shot
    examples (demos) and the query itself during optimization.
    *   **Note:** If omitted, the agent will automatically generate a default
        template using your `data_vars` and `label_variable`.
*   **`target_model_endpoint_url`**: (Required for Gemini Nano) The base URL of a
    custom endpoint for the target model.

### 2.3. Data and Evaluation Configuration

This section covers the data used for training and testing, and the metric for
evaluation.

*   **`train_input_data_path`**: (Required) The Cloud Storage URI of the JSONL or
    CSV file containing the training data. This path **must** be a GCS location.
*   **`test_input_data_path`**: (Required) The Cloud Storage URI of the JSONL or
    CSV file containing the testing/evaluation data.
*   **`data_vars`**: (Required) A list of variable names corresponding to the
    columns in your data files that should be used in the templates.
    *   **Note:** These are typically inferred automatically by the agent from
        your dataset headers.
*   **`label_variable`**: (Required) The name of the variable/column containing
    the ground truth labels.
    *   **Note:** This is typically inferred automatically by the agent from
        your dataset headers.
*   **`batch_size`**: (Optional) The number of data points used to evaluate a
    candidate prompt in each mini step. 
    Note: If `prompt_optimizer_method` is `VAPO`, `batch_size` is supported. 
    However, if it's currently not supported in the SDK for your specific 
    version, it will be automatically removed from the config file.
*   **`eval_metrics_types`**: (Required) A list of standard evaluation metrics to
    optimize your prompts for (e.g., `["exact_match"]`, `["ROUGE_L"]`).
*   **`eval_metrics_weights`**: (Optional) A list of weights corresponding to the
    metrics in `eval_metrics_types`. Defaults to `[1.0]` if a single metric is
    used.
*   **`eval_qps`**: (Optional) Overall QPS limit for evaluation.

### 2.4. Optimization Strategy

*   **`num_steps`**: (Required) The total number of optimization steps to run.
*   **`population_size`**: (Optional) The number of candidate prompts to
    maintain in the population.
*   **`num_mutants_per_candidate`**: (Optional) The number of new mutant
    prompts to generate from each survivor.

### 2.5. Example JSON Configuration

```json
{
  "project": "your-gcp-project-id",
  "output_path": "gs://your-bucket/data-driven-optimize-output/run-1/",
  "target_model": "gemini-2.5-flash",
  "target_model_location": "us-central1",
  "target_model_qps": 5,
  "optimizer_model": "gemini-2.5-pro",
  "optimizer_model_location": "us-central1",
  "optimizer_model_qps": 3,
  "eval_model": "gemini-2.5-flash",
  "eval_model_location": "us-central1",
  "eval_model_qps": 5,
  "prompt_template": "Classify the following text into one of the following categories: Business, Sci/Tech, World, Sports. Output the category name only.",
  "demo_and_query_template": "text:\n{{input}}\n\nanswer:\n{{output}}",
  "train_input_data_path": "gs://your-bucket/data/training-data.csv",
  "test_input_data_path": "gs://your-bucket/data/test-data.csv",
  "data_vars": ["input", "output"],
  "label_variable": "output",
  "eval_metrics_types": ["exact_match"],
  "eval_metrics_weights": [1.0],
  "num_steps": 10,
  "batch_size": 20,
  "population_size": 10,
  "num_mutants_per_candidate": 2
}
```

### 2.6. Understanding the Optimization Process

The core of the optimization process uses an evolutionary algorithm to discover
high-performing prompts. Here's a brief overview:

1.  **Initialization:** Start with an initial pool of candidate prompts.
2.  **Selection Loop (within an iteration):** For a number of steps
    (`num_ucb_steps`), the algorithm selects promising candidates and
    evaluates them on new mini-batches of data to refine performance estimates.
3.  **Survival Selection:** After the selection steps, the top candidates
    (based on `population_size`) are preserved for the next generation.
4.  **Mutation:** New candidate prompts are generated by mutating the
    survivors. Each survivor produces multiple variants
    (`num_mutants_per_candidate`).
5.  **New Pool:** These new mutants form the candidate pool for the next major
    iteration.

This iterative process continues for a specified number of training steps,
balancing the discovery of new prompt ideas with the refinement of established
good ones.

## 3. Further Reading

*   [Data-Driven Optimize Official Documentation](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/prompts/data-driven-optimizer)
