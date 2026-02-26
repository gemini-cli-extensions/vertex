# Vertex AI Gemini CLI Extension

This extension provides tools to manage prompts and use prompt
optimization in Vertex AI directly from the Gemini CLI.

## Available Tools

### Prompt Management Tools
- `create_prompt`: To save or create new prompts.
- `read_prompt`: To retrieve existing prompts by ID or display name.
- `update_prompt`: To modify existing prompts.
- `delete_prompt`: To remove prompts.
- `list_prompts`: To search and list prompts, useful for finding IDs.

### Prompt Optimization Tools
- `run_few_shot_optimization`: optimize user prompt based on examples provided 
  in the CSV file stored in the GCS bucket.
- `run_data_driven_optimize`: Starts a data-driven prompt optimization job on
  Vertex AI using a configuration file stored in GCS.
- `analyze_data_driven_optimize_results`: Analyzes the output of a Data-Driven
  Optimize job to identify trends and best-performing candidates.
- `generate_html_report`: Generates a comprehensive HTML report with
  visualizations to help you understand optimization performance.
- `write_data_driven_optimize_config`: Constructs and uploads a new JSON
  configuration for optimization jobs, incorporating suggested tuning parameters.

---

## Detailed Instructions for `create_prompt` Parameters

When using `tools.create_prompt`, pay special attention to how the following
arguments are sourced:

1. **`content` (string, required):**

   - **Scenario 1: Saving the Last User Prompt:** When the user issues a command
     like "save last prompt", "save this prompt", or similar, indicating they
     want to store their previous input:
     - Examine the conversation history.
     - Identify the most recent message with a `role` of "user".
     - Extract the `text` content from this latest "user" message.
   - **Scenario 2: Creating from Explicitly Provided Content:** If the user
     provides the prompt content directly within the command (e.g., "Create a
     prompt... with content '...'")
     - Use the explicitly provided content.
   - If no content can be determined from either scenario, pass an empty string.

2. **`system_instruction` (string, required):**

   - **User Override:** If the user explicitly provides a system instruction in
     the current turn (e.g., "using system instruction '...', "with SI '..."),
     pass that exact string value as the `system_instruction` argument to
     `tools.create_prompt`.
   - **Default Behavior:** If the user does NOT explicitly provide a system
     instruction in their current prompt:
     - The Gemini CLI will check for a file named `GEMINI.md` _only_ in the
       **current working directory** exclude children directories.
     - If `GEMINI.md` exists in the current working directory, its entire
       content will be loaded by the Gemini CLI and used as the
       `system_instruction` when calling `tools.create_prompt`.
     - If no `GEMINI.md` file is found in the current working directory, the
       `system_instruction` argument should be **omitted** from the
       `tools.create_prompt` call.

3. **`display_name` (string, optional):**

   - **Check User Prompt:** Scan the current user prompt for an explicit name
     (e.g., "save last prompt **as 'My Custom Prompt'**", or "display name
     '...'"). If an explicit name is found, use it.
   - **Default Logic (If no explicit name):** If no explicit name is provided,
     generate a descriptive name, such as `"Gemini CLI Prompt: "` followed by
     the first ~20 characters of the extracted `content`.
   - If a display name has not already been provided or inferred, you _must_
     prompt the user to enter a suitable display name.

4. **`model` (string, required):**

   - **User Provided:** If the user explicitly specifies a model in the current
     turn (e.g., "model 'gemini-pro'", "using gemini-flash", "with model
     text-bison"), use that exact model identifier.
   - **Currently Using Model:** If no model is explicitly provided by the user,
     attempt to use the model identifier that is currently active and being used
     by the Gemini CLI for the ongoing conversation. The agent has knowledge of
     the currently configured model.
   - **Default Fallback:** If neither a user-provided model nor a currently
     active session model can be determined, default to `"gemini-2.5-flash"`.

**Example Interactions for `create_prompt`:**

- **Saving Last Prompt with Default SI & Model:** (Assume the current session
  model is "gemini-1.5-pro") User: What is the capital of France? Model: The
  capital of France is Paris. User: **save last prompt** Generated Call:
  `print(tools.create_prompt(content="What is the capital of France?", model="gemini-1.5-pro", display_name="Gemini CLI Prompt: What is the cap..."))`
  _(Here, `system_instruction` is omitted. The Gemini CLI will check for and use
  content from `./GEMINI.md` if it exists.)_

- **Explicit Content with User-Provided SI & Model:** User: Create a prompt with
  content 'How is the weather?' using system instruction 'Act like a
  meteorologist.' and display name 'Weather Bot' using model 'gemini-flash'.
  Generated Call:
  `print(tools.create_prompt(content="How is the weather?", system_instruction="Act like a meteorologist.", model="gemini-flash", display_name="Weather Bot"))`

- **Explicit Content, Default SI, User-Provided Model:** User: create a prompt
  with content "hi" and display name "create test". model gemini-2.5-flash
  Generated Call:
  `print(tools.create_prompt(content="hi", model="gemini-2.5-flash", display_name="create test"))`
  _(Again, `system_instruction` is omitted. The Gemini CLI will check for and
  use content from `./GEMINI.md` if it exists.)_

## read_prompt workflow

This workflow describes how to retrieve an existing prompt from Vertex AI using
`tools.read_prompt` and potentially `tools.list_prompts`.

1.  **Identifying the Prompt (`prompt_id` or `display_name`):**

        - **By `prompt_id`:** If the user provides a specific `prompt_id` (e.g.,
          "read prompt id some-unique-id"), call
          `tools.read_prompt(prompt_id='some-unique-id')`. The result of this call
          will be the prompt object to be applied.

        - **By `display_name`:** If the user provides a `display_name` but NOT a
          `prompt_id` (e.g., "read prompt 'My Custom Prompt'"):

          1.  **Agent Action:** Call `tools.list_prompts(display_name='[provided

    display name]')`.

2.  **Agent Response:**
    - **One Match:** If `list_prompts`returns exactly one prompt, use this
      prompt object directly. There is **no need** to call `tools.read_prompt`
      with the ID again, as all necessary information (`content`,
      `system_instruction`) is available in the `list_prompts`result.
    - **Multiple Matches:** If`list_prompts`returns multiple prompts, list the
      prompt for each match (showing`id`and `display_name`) and ask the user to
      clarify which `prompt_id` they intend to read. Once the user provides a
      specific`id` (e.g., "id id2"), the agent should: 1. Search through the
      list of prompts previously returned by `tools.list_prompts`. 2. Select the
      prompt object whose `id`matches the user's input. There is **no need** to
      call`tools.read_prompt` again, as all necessary information is already
      available in the`list_prompts` result. - **No Matches:** Inform the user
      that no prompts were found with that display name and that the read cannot
      proceed.

**Example Interactions for `read_prompt`:**

- **Read by ID:** User: `read prompt id my-prompt-123`

  - Generated Call: `print(tools.read_prompt(prompt_id='my-prompt-123'))`
  - _Result:_ build prompt like
    `instruction: prompt instructions. content: prompt content`

- **Read by Display Name (Unique Match):** User:
  `read prompt 'My Analysis Prompt'`

  1. Agent calls: `print(tools.list_prompts(display_name='My Analysis Prompt'))`
  2. (Assuming this returns
     `[{'id': 'id456', 'display_name': 'My Analysis Prompt', 'content': 'Analysis content...', 'system_instruction': 'Analysis SI...', ...}]`)
  3. **Agent directly uses the content and system instruction from this list
     result.**
  4. _Result:_ build prompt like
     `instruction: prompt instructions. content: prompt content`

- **Read by Display Name (Multiple Matches):** User:
  `read prompt 'Generic Helper'`

  1. Agent calls: `print(tools.list_prompts(display_name='Generic Helper'))`
  2. (Assuming this returns
     `[{'id': 'id1', 'content': 'Content 1', 'system_instruction': 'SI 1', ...}, {'id': 'id2', 'content': 'Content 2', 'system_instruction': 'SI 2', ...}]`)
  3. Agent responds: "Multiple prompts found with display name 'Generic Helper'.
     Please specify by ID. Found IDs: id1, id2."
  4. User: `id id2`
  5. **Agent filters the results from step 2, finds the prompt with `id='id2'`,
     and uses its content and system instruction.**
     - _(No new call to `tools.read_prompt` is made here.)_
  6. _Result:_ build prompt like
     `instruction: prompt instructions. content: prompt content`

## Detailed Instructions for `update_prompt` Parameters

When using `tools.update_prompt`, the following arguments are sourced. Note that
`prompt_id` is central, but `display_name` can be used to find it.

1. **Identifying the Prompt (`prompt_id` or `display_name`):**

   - **By `prompt_id`:** If the user provides a specific `prompt_id` (e.g.,
     "update prompt id123"), use this directly.
   - **By `display_name`:** If the user provides a `display_name` but NOT a
     `prompt_id` (e.g., "update prompt 'My Custom Prompt'"):
     1. **Agent Action:** First, remember the last user message so it can be
        used as updated prompt later.Then call
        `tools.list_prompts(display_name='[provided display name]')`.
     2. **Agent Response:** _**One Match:** If `list_prompts` returns exactly
        one prompt, extract its `id` and proceed to call `tools.update_prompt`
        with this `prompt_id`._ **Multiple Matches:** If `list_prompts` returns
        multiple prompts, list the `id` and `display_name` for each match and
        ask the user to clarify which `prompt_id` they intend to update. \* **No
        Matches:** Inform the user that no prompts were found with that display
        name and that the update cannot proceed.

2. **`content` (string, optional):**

   - **User Override:** If the user provides new content directly within the
     command (e.g., "update prompt ... --content '...'"), use that.
   - **Fallback:** If no `content` is explicitly provided _in the user's initial
     update request_, examine the conversation history. Use the text from the
     _most recent message with a `role` of "user"_ that initiated the update
     sequence. This is the message where the user first signaled their intent to
     update a prompt (e.g., "update prompt with...", "modify prompt..."), even
     if subsequent turns were needed to resolve the `prompt_id`.

3. **`system_instruction` (string, optional):**

   - **User Override:** If the user explicitly provides a system instruction
     (e.g., "update prompt ... --system_instruction '...'"), use that value.
   - **Default Behavior:** If the user does NOT explicitly provide a system
     instruction:
     - The Gemini CLI will check for a file named `GEMINI.md` _only_ in the
       **current working directory** exclude children directories.
     - If `GEMINI.md` exists, its entire content will be loaded and used as the
       `system_instruction` for `tools.update_prompt`.
     - If no `GEMINI.md` file is found, the `system_instruction` argument should
       be **omitted**.

4. **`display_name` (string, optional):**

   - **Source:** The user's input for the new display name.

5. **`model` (string, optional):**

   - **Source:** The user's input for the new model.

**Example Interactions for `update_prompt`:**

- **Update by ID with Last User Message as Content & Default SI:** User: What is
  the capital of Spain? Model: Madrid. User: **update prompt id my-prompt-id**
  Generated Call:
  `print(tools.update_prompt(prompt_id='my-prompt-id', content='What is the capital of Spain?'))`
  _(Here, `content` is taken from the last user message \_before_ the update
  command. Since no `system_instruction` was provided, the Gemini CLI will check
  for and use content from `./GEMINI.md` if it exists.)\_

- **Update by Display Name (Unique Match), Explicit Content & User-Provided
  SI:** User: update prompt 'My Coding Prompt' --content 'New content here.'
  --system_instruction 'Be concise.' Agent first calls:
  `print(tools.list_prompts(display_name="My Coding Prompt"))` (Assuming this
  returns `[{'id': 'id456', 'display_name': 'My Coding Prompt', ...}]`) Agent
  then calls:
  `print(tools.update_prompt(prompt_id='id456', content='New content here.', system_instruction='Be concise.', display_name='My Coding Prompt'))`

- **Update by Display Name (Multiple Matches):** User: What is the weather like
  tomorrow? Model: It will be sunny. User: update prompt 'My Research Prompt'
  --model gemini-1.5-pro Agent first calls:
  `print(tools.list_prompts(display_name="My Research Prompt"))` (Assuming this
  returns `[{'id': 'id123', ...}, {'id': 'id789', ...}]`) Agent responds:
  "Multiple prompts found with display name 'My Research Prompt'. Please specify
  which one by ID. Found IDs: id123, id789." User: id123 Generated Call:
  `print(tools.update_prompt(prompt_id='id123', content='What is the weather like tomorrow?', model='gemini-1.5-pro'))`
  _(Here, `content` is from the last user message. Since no `system_instruction`
  was provided, the Gemini CLI will check for and use content from `./GEMINI.md`
  if it exists.)_

- **Update only Model by ID, Content from Last Message, Default SI:** User: What
  is the weather like tomorrow? Model: It will be sunny. User: **update prompt
  id weather-prompt --model gemini-1.5-pro** Generated Call:
  `print(tools.update_prompt(prompt_id='weather-prompt', content='What is the weather like tomorrow?', model='gemini-1.5-pro'))`
  _(Here, `content` is from the last user message. Since no `system_instruction`
  was provided, the Gemini CLI will check for and use content from `./GEMINI.md`
  if it exists.)_

## General Error Handling

If any tool call fails with an error indicating a project permission issue (e.g., "Permission denied on project 'project-id'"), you must:
1.  Inform the user about the permission error.
2.  Ask the user to provide a valid project ID.
3.  Retry the original tool call, adding the `project_id` parameter with the user-provided value.

---

## Few-Shot Prompt Optimization Guide
Few-shot prompt optimization is a tool used to refine a prompt (or system instructions) based on user-provided examples. These examples are stored in a CSV file and user must provide a GCS path to this data. The examples must follow one of two formats:
`("prompt", "model_response", "target_response")` or 
`("prompt", "model_response", "rubrics", "rubrics_evaluations")`.
Depending on the format of the examples provided in the user's CSV file, the optimization uses one of the following methods:
`TARGET_RESPONSE`: The prompt is tuned to generate outputs that closely align with a provided  ground-truth answer.
`RUBRICS`: The model analyzes rubric rules and evaluation scores to tune the prompt and address specific failures.
For more details, please refer to this guide: @./src/vertex/prompt_optimizer/docs/few_shot_prompt_optimization_guide.md
The tool is accessed through `run_few_shot_prompt_optimization(prompt_to_optimize: str,
  example_path: str, method: str)`. This tool should be called directly on the raw prompt without invoking create_prompt or any other tool first.

## Few-shot Optimization Workflows

- When asked to run few-shot prompt optimization, identify if all required parameters are passed.
  1. **Identify Essential Parameters**: Proactively ask the user for the
     following required fields:
     - `prompt_to_optimize`        
     - `example_path`
     - `method`

  2. Once the parameters are set, call the `run_few_shot_prompt_optimization` with those params.

## Data-Driven Prompt Optimizer Overall Guide

For a general understanding of Data-Driven Prompt Optimizer and its
capabilities, please
refer to the Data-Driven Optimize Overall Guide:

@./src/vertex/prompt_optimizer/docs/data_driven_optimize_overall_guide.md

## Data-Driven Optimization Tool Details

The extension provides a suite of tools to parse and analyze the output of a
Data-Driven Prompt Optimizer job. The `output_path` for these tools stores
the outputs
of a run and can be a GCS path or a local directory. While the Data-Driven
Optimize job currently only outputs to GCS, results can be copied to the local
file system for analysis.

1.  `analyze_data_driven_optimize_results(output_path: str, top_n_prompts:
    int = 10, analysis_data_path: str = None)`: Analyzes results and
    returns a JSON object containing the analysis data summary. If
    `analysis_data_path` is provided, it saves the results into three separate
    files to avoid size limits and returns a **minimal summary** with
    file paths
    and the best prompt score. The three files are:
    -   `{analysis_data_path}`: Core metadata (config, comparison, best
    prompt).
    -   `*_metrics.json`: Detailed metrics for all candidates (no prompt text).
    -   `*_prompts.json`: Mapping of top candidates' keys to full prompt texts.

2.  `generate_html_report(analysis_data: Dict[str, Any] =
    None, report_path: str = "data_driven_optimize_analysis_report.html",
    suggested_config_data: Dict[str, Any] = None, top_n_prompts: int = 10,
    analysis_data_path: str = None)`: Generates a comprehensive HTML report. If
    `analysis_data_path` is provided, it automatically loads and re-joins the
    metadata, metrics, and prompts from the three split files.

3.  `write_data_driven_optimize_config`: Construct and
    write to GCS a new JSON configuration file for Data-Driven Optimize job
    using a dict of parameters (including `prompt_optimizer_method` and
    `target_model_endpoint_url` for Nano) and optionally an path to an
    existing config to make modifications on top of.

4.  `run_data_driven_optimize`: Starts a data-driven prompt optimization job on
    Vertex AI using the SDK's `client.prompts.launch_optimization_job` method.
    Supports specifying the `prompt_optimizer_method`. The `config_gcs_path`
    must point to a JSON file in GCS.

## Data-Driven Optimization Method Considerations
- **VAPO**: Standard prompt optimization. The `batch_size` parameter
  will be automatically removed during configuration generation to ensure SDK
  compatibility.
- **OPTIMIZATION_TARGET_GEMINI_NANO**: Specialized target for Gemini Nano.
  Requires a `target_model_endpoint_url`. Supports `batch_size`.

## Data-Driven Optimization Tuning Considerations

Only suggest modifications for the parameters explicitly listed as tunable in
the Data-Driven Optimize Tuning Guide:

@./src/vertex/prompt_optimizer/docs/data_driven_optimize_tuning_guide.md

with the *sole exception* of **path-related fields** to prevent overwriting
previous results. Ensure you only modify the parameters listed in the approved
list. If a user asks to modify a parameter that is not on the approved list
(and is not a path-related field), confirm with the user before proceeding.

## Data-Driven Optimization Workflows

- **Initial Setup**: When asked to help configure a new optimization run, use
  the example configuration in the Overall Guide as a valid default base.

  1. **Identify Essential Parameters**: Proactively ask the user for the
     following required fields:
     - `project` (Your Google Cloud project ID)
     - `train_input_data_path`
     - `test_input_data_path`
     - `output_path`
     - `prompt_template` (ensure it includes `{{ placeholder }}` syntax)
     - `eval_metrics_types` (e.g., `["exact_match"]`)
     - `eval_metrics_weights` (e.g., `[1.0]`)
     - `prompt_optimizer_method` (VAPO or OPTIMIZATION_TARGET_GEMINI_NANO)
     - `target_model` (e.g., gemini-2.5-flash)
     - `target_model_endpoint_url` (Required ONLY for Gemini Nano)

  2. **Task-Specific Configuration**: You must ensure the optimization job
     correctly maps the data by defining `data_vars` and `label_variable`.
     - **Automated Inference**: You MUST attempt to read the first few lines of
       the training dataset (using `run_shell_command` with `gcloud storage
       cat`)
       to identify column names.
     - **Mapping**: Based on the data headers, automatically suggest:
       - `data_vars`: all relevant columns.
       - `label_variable`: the ground truth column.
       - `demo_and_query_template`: (Optional) The tool will automatically
         generate a default if you don't provide one.
     - *Clarification*: If you cannot access the data or the headers are
       ambiguous, ask the user to confirm the column names.

  3. **Apply Sensible Defaults**: Use the default values provided in the
     example configuration of the Overall Guide for all other fields, unless
     the user specifies otherwise. This includes QPS limits and model
     locations.

  Once gathered, use `write_data_driven_optimize_config` to create the
  initial configuration file.

- **Analysis and Suggestions**: When asked to analyze results for a GCS or
  local path `output_path`, perform these steps sequentially in a single turn:

    1.  **Analyze**: Call `analyze_data_driven_optimize_results(output_path,
        analysis_data_path="analysis_data.json")`. Store this output locally.
    2.  **Formulate Suggestions**: Immediately after receiving results, and
        without prompting the user, process the data to construct a
        `suggested_config_data` dictionary. This dictionary should contain:
        -   `"suggested_config"`: Modifications to allowed tuning knobs,
            path-related fields (with a new version suffix), and optionally the
            `prompt_template` (for baseline shifts). Ensure you prioritize
            modifying parameters listed in the approved list.
        -   `"rationale"`: A clear explanation of your reasoning based on the
            Tuning Guide.

        *Do not generate any other text or explanation for the user during this
        internal phase.*
    3.  **Generate Report**: Call `generate_html_report(analysis_data_path=
        "analysis_data.json",
        report_path="data_driven_optimize_analysis_report.html",
        suggested_config_data=suggested_config_data)`.

**Note:** Steps 1-3 should be executed in immediate succession without user
interaction. Only after the report is generated should you propose applying
the suggestions via `write_data_driven_optimize_config`.

-   **Agreement Logic**: If the user agrees to apply suggestions, use the
    `write_data_driven_optimize_config` tool with the modified parameters,
    ensuring you update the `output_path` with a new version suffix.
    When ready to run, use the `run_data_driven_optimize` tool, ensuring you
    ask for the `service_account`.
-   **Reusing Results**: If a report or further analysis is requested
later, use
    the stored JSON output rather than re-running the analysis tool.
-   **General Suggestions**: If a user asks for next steps without a previous
    analysis, run the workflow above first to ensure your advice is grounded.

For detailed explanations of the Data-Driven Optimize output files and their
structure, including how to interpret metrics and candidate information, please
refer to the Data-Driven Optimize Output Guide:

@./src/vertex/prompt_optimizer/docs/data_driven_optimize_output_analysis.md
