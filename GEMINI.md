# Vertex Prompt Management Extension

This extension provides tools to manage prompts in Vertex AI.

Whenever anyone wants to read or write vertex prompts, you must use the vertex
management tools.

The available tools are:

- `create_prompt`: To save or create new prompts.
- `read_prompt`: To retrieve existing prompts by ID or display name.
- `update_prompt`: To modify existing prompts.
- `delete_prompt`: To remove prompts.
- `list_prompts`: To search and list prompts, useful for finding IDs.

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