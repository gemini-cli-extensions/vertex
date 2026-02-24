# Guide to Tuning Data-Driven Optimize Jobs

## 1. Introduction

After reviewing the initial results from a Data-Driven Optimize job, the next
step is to decide how to improve them in the next run. This guide provides a
framework for interpreting the results to diagnose common issues and suggests
concrete changes to your configuration for the next iteration.

## 2. Core Diagnostic Questions

The analysis of a Data-Driven Optimize run can be distilled into few key
questions.

### Question 0: What do we see about the data?

It's crucial to understand the data presented in the
`analyze_data_driven_optimize_results` tool output. This tool processes the raw
output files and provides a structured JSON object containing all the necessary
information for analysis.

1.  **Examine the Analysis Output:** Inspect the JSON object returned by
    `analyze_data_driven_optimize_results`. Key top-level keys include:
    -   `config`: The configuration used for the Data-Driven Optimize job
        (summarized if saving to file).
    -   `best_prompt`: The prompt with the highest score based on the
        `metric_source` (present in the metadata file).
    -   `comparison`: Metrics comparing the initial prompt and the best prompt
        on the training batches and full test set (if available).
    -   `all_metrics_ranked`: A list of all candidates and their scores across
        different evaluations. **Note: Full prompt text is excluded from this
        list to save space and is stored separately. When saving to a file,
        this list is omitted from the chat summary to avoid payload limits.**
        This list contains the data needed to analyze learning curves and is
        available in the `*_metrics.json` file.
    -   `metric_name`: The name of the metric being optimized.
    -   `metric_source`: Indicates the data source used for ranking in
        `all_metrics_ranked`.

2.  **Identify Available Datasets and Metrics:** The `all_metrics_ranked` list
    is the most important part for this. Each element in this list is a
    dictionary representing a prompt candidate, and contains scores from *all*
    available evaluation configurations. The presence of certain keys within
    these dictionaries indicates which datasets were evaluated:
    -   **`score_ucb_train`**: Always present. Represents the score on the
        training mini-batches.
    -   **`score_full_train`**: Present if `eval_all_candidates_on_full_train`
        was true in the config.
    -   **`score_full_test`**: Present if `eval_all_candidates_on_full_test`
        was true in the config.

    The `comparison` object will also reflect metrics for the initial and best
    prompts, typically on the test set data if configured. Understanding the
    distinctions between these datasets is vital for diagnosing issues like
    overfitting or noisy evaluations.

3.  **Assess Data Noise:** To analyze trends and noise, you need to process the
    `all_metrics_ranked` list to extract scores for each `step`. For example,
    examine the variance or trends of `score_ucb_train`, `score_full_train`, and
    `score_full_test`.
    -   **Noisy Data:** Significant fluctuations (e.g., large ups and downs) in
        training scores across steps suggest noise in the evaluations.
    -   **Stable Data:** Relatively smooth trends in scores suggest more
        reliable evaluations.

### Question 1: Is the optimization process actually learning?

First, we need to determine if the optimizer is successfully finding better
prompts on the **training data**. To do this, analyze the training score values
within the `all_metrics_ranked` list. You should look at the trend of the
maximum training score at each step.

-   **What to look for:** A generally upward trend in the training score across
    the optimization steps.
-   **Good sign:** The score is increasing from one step to the next. This
    means the algorithm is generating better prompts and successfully
    identifying them.
-   **Bad sign:** The training score is flat, erratic, or decreasing. This
    suggests a problem with the optimization process itself or noise in the
    metric.

### Question 2: Is the learning generalizing to unseen data?

If the model is learning on the training data, we then need to see if that
learning translates to better performance on the **full test data**. This tells
us if we are overfitting.

-   **What to look for:** Compare the trend of the training score with the test
    score at each step within the `all_metrics_ranked` data. This requires test
    scores to be available.
-   **Good sign:** Both the train score and the test score are increasing. This
    is the ideal scenario, indicating that the prompts are getting better and
    the improvements are generalizing.
-   **Bad sign (Overfitting):** The training score is increasing, but the test
    score is flat or decreasing. This is a classic sign of overfitting. The
    optimizer is finding prompts that are too specific to your training
    examples and do not perform well on new, unseen examples.
-   **Other Gaps:** Also, pay attention to the gap between mini-batch training
    scores and full training scores (if available). A large or inconsistent gap
    here might suggest that the mini-batches are not representative of the full
    training set, potentially due to a small `batch_size`.

### Question 3: Is the starting metric too high and already saturated?

## 3. Tunable Parameters

**Important**: The parameters listed in this section are the primary and
**only** tuning knobs that should be modified for Data-Driven Optimize jobs.
Other parameters are not intended for user modification and can lead to
unexpected results.

The following parameters are the knobs that can be adjusted to tune the
Data-Driven Optimize optimization process:
-   `num_steps`
-   `batch_size`
-   `population_size`
-   `num_mutants_per_candidate`
-   `num_ucb_steps`

### Impact of Tuning Knobs

-   **`num_steps`**: The total number of optimization steps to run. More steps
    allow for more exploration but increase runtime.
-   **`batch_size`**: The number of data points used to evaluate a candidate
    prompt in each mini step. Larger batches provide more stable score
    estimates but increase the computational cost of each step. A common batch
    size is between 20-50.
-   **`population_size`**: Controls the number of elite candidates preserved at
    each iteration. A larger size maintains more diversity, potentially
    avoiding local optima but slowing down convergence.
-   **`num_mutants_per_candidate`**: Determines the exploration breadth around
    each elite candidate. More mutants increase the chances of finding
    improvements but require more evaluations.
-   **`num_ucb_steps`**: Controls how many times candidates are selected and
    evaluated *within* an iteration. More steps lead to more accurate
    estimates of each candidate's performance before selection, but increases
    the computational cost per iteration.

## 4. Common Scenarios and Next Steps

**General Guidance:**

-   **Prioritize Addressing Noise:** If the metrics appear noisy, address this
    first by increasing `batch_size` and/or `num_ucb_steps`. It is difficult to
    diagnose other issues like overfitting if the underlying metrics are not
    stable.
-   If the training score is not improving, increasing `num_ucb_steps` or
    `batch_size` can help get more stable estimates for candidate selection.
-   To increase exploration, you can increase `population_size` or
    `num_mutants_per_candidate`.
-   **Resource Consideration:** The total number of model inference calls per
    iteration is determined by a combination of the number of candidates in the
    pool, the number of selection steps (`num_ucb_steps`), and the `batch_size`.
    Balancing these parameters is crucial to achieve the best quality with
    highest efficiency. When suggesting changes, always consider the trade-off
    between potential quality gains and the increased computational cost.

Based on the answers to the questions above, here are some common scenarios and
suggested actions. It's best to first check for and address noisy metrics
before diving into other potential issues.

### Scenario 1: Metrics are Noisy or Train Score is Flat/Erratic

**Diagnosis:** Scores fluctuate significantly across steps, or the training
score is flat or erratic. This makes it difficult to determine if changes in
scores are due to better prompts or random chance.

**Suggestions:**
-   **Increase `batch_size`:** This is often the most effective way to reduce
    noise, as it provides a more stable estimate of prompt performance on a
    larger sample of data.
-   **Increase `num_ucb_steps`:** More selection steps allow for more
    evaluations of each candidate, which can help in getting more reliable
    score estimates before the next generation.
-   **Improve Data Quality:** Examine the data for inconsistencies or errors. A
    cleaner dataset leads to a more stable metric.
-   **Run on the full dataset (for small datasets):** If your training dataset
    is relatively small, the noise from sampling can be high. Consider
    configuring the job to evaluate on the full training dataset at each step.

### Scenario 2: Both Train and Test scores are improving.

**Diagnosis:** This is the ideal outcome. The process is working as expected.

**Suggestion:**
-   You can stop if you are satisfied with the performance.
-   To potentially achieve even better results, you can try another run using
    the best prompt from this job as the new starting point.

### Scenario 3: Train score improves, but Test score is flat or decreasing.

**Diagnosis:** Overfitting. The prompts are becoming too tailored to the
training data.

**Suggestions:**
-   **Add more data:** The most effective way to combat overfitting is to
    increase the number of diverse, high-quality examples in your training set.
-   **Enable full test evaluation:** For a more granular view of overfitting,
    you can evaluate every candidate prompt on the full test set. This allows
    for a detailed analysis of how each candidate generalizes.
-   **Enable full training evaluation:** For a detailed comparison between
    training and test performance, you can evaluate all candidate prompts
    against the full training set. This identifies performance gaps between
    seen and unseen data.

## 5. Advanced Tuning Lessons

This section provides a more structured approach to tuning, based on the
`analyze_data_driven_optimize_results` output.

### I. Key Signals to Examine

Before making changes, diagnose the current state of optimization by looking at
these specific signal combinations:

1.  **The "Best" Step Location**
    -   **What to look for:** At what step do the highest scores occur?
    -   **Why:** This indicates if the process is "undertrained" (peaked at the
        end) or "saturated" (peaked early).
2.  **Metric Stability**
    -   **What to look for:** How much do training scores fluctuate?
    -   **Why:** High volatility usually indicates that the sample size is too
        small to get a stable estimate of prompt quality.
3.  **Generalization Gaps**
    -   **What to look for:** How do the trends of training and test scores
        compare?
    -   **Why:** This separates healthy learning from overfitting.

### II. Tuning Guidelines & Heuristics

1.  **The Hierarchy of Levers**
    When results are unstable or stalling, apply fixes in this order:
    -   **Increase `batch_size` (Primary):** This is the most effective lever
        for stabilizing metrics and providing a smoother optimization gradient.
    -   **Increase `num_ucb_steps` (Secondary):** Use this to further refine
        candidate selection.
    -   **Adjust `num_steps` (Tertiary):** Change this only after the metric is
        stable.

### III. Budget and Resource Management

Tuning parameters have a direct impact on the number of model inference calls,
and thus the overall cost and time required for optimization.

1.  **Resource-Neutral Tuning**
    If you have a fixed budget, you must trade off one parameter for another:
    -   **To increase exploration without increasing cost:** If you increase
        the number of mutant variants, you should decrease the population size
        or batch size proportionally.
    -   **To increase stability without increasing cost:** If you increase the
        batch size, you must decrease the number of tracked candidates or
        selection steps.

2.  **Cost Efficiency Heuristic**
    -   **Increasing the number of steps** is the most direct way to spend
        more budget. It doesn't change the complexity of each step, just the
        duration.
    -   **Increasing the population size** is the most expensive way to spend
        budget, as it increases the number of candidates that must be tracked
        and evaluated in every subsequent step.

## 6. New suggested config

Name the new config file base on the original config name. Add a suffix index
and a name to indicate the change. Only modify the Tuning Knobs and Inherit the
rest of the parameters from the original config.
