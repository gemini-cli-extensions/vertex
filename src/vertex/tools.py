"""Module for defining tools for Vertex AI Prompt management."""

import itertools
import os

import pydantic
from google.api_core import exceptions
from google.genai import _common
from google.genai import types as genai_types
from vertexai import types as vertexai_types
from vertexai._genai import Client

_DEFAULT_LOCATION = "us-central1"
_MAX_PREVIEW_LENGTH = 100  # Define the maximum length for preview


class PromptDetails(_common.BaseModel):
    """Class for holding prompt details."""

    prompt_id: str = pydantic.Field(..., description="The ID of the prompt.")
    display_name: str = pydantic.Field(
        ..., description="The display name of the prompt."
    )
    system_instruction: str = pydantic.Field(
        ..., description="The system instruction for the prompt."
    )
    contents: str = pydantic.Field(
        ..., description="The combined contents of the prompt."
    )


def _build_content(text: str, role: str) -> genai_types.Content:
    """Build the content data for the prompt."""
    part = genai_types.Part(text=text)
    content = genai_types.Content(role=role, parts=[part])
    return content


def _build_contents(text: str, role: str) -> list[genai_types.Content]:
    return [_build_content(text, role)]


def _truncate_text(text: str, max_length: int) -> str:
    """Truncates text to max_length and appends an ellipsis if truncated."""
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text


def _build_prompt_details(
    prompt: vertexai_types.Prompt, truncate_texts: bool = False
) -> PromptDetails:
    """Helper function to format a single Prompt object into a dictionary."""
    if not prompt:
        raise ValueError("Prompt is None. Cannot format to PromptDetails.")

    prompt_data = getattr(prompt, "prompt_data", None)
    display_name = prompt.dataset.display_name or "N/A"

    system_instruction_text = ""
    if prompt_data and prompt_data.system_instruction:
        si_parts = getattr(prompt_data.system_instruction, "parts", None)
        if si_parts is not None:
            system_instruction_text = "".join(
                part.text
                for part in si_parts
                if hasattr(part, "text") and part.text is not None
            )
    if truncate_texts:
        system_instruction_text = _truncate_text(
            system_instruction_text, _MAX_PREVIEW_LENGTH
        )

    contents_combined = ""
    if prompt_data and prompt_data.contents:
        all_content_texts = []
        for content in prompt_data.contents:
            if content:
                content_parts = getattr(content, "parts", None)
                if content_parts is not None:
                    part_texts = [
                        part.text
                        for part in content_parts
                        if hasattr(part, "text") and part.text is not None
                    ]
                    if part_texts:
                        all_content_texts.append("".join(part_texts))

        contents_combined = "".join(all_content_texts)
    if truncate_texts:
        contents_combined = _truncate_text(
            contents_combined, _MAX_PREVIEW_LENGTH
        )

    return PromptDetails(
        prompt_id=prompt.prompt_id,
        display_name=display_name,
        system_instruction=system_instruction_text,
        contents=contents_combined,
    )


class VertexPromptManager:
    """Class for managing Vertex AI prompts."""

    def __init__(self):
        self._project_id = None
        self._location_id = None
        pass

    def _get_client(
        self,
        project_id: str | None = None,
        location_id: str | None = None,
    ) -> Client:
        """Helper to get a Vertex AI client, with env var fallback and prompting."""
        final_project_id = (
            project_id
            or self._project_id
            or os.environ.get("GOOGLE_CLOUD_PROJECT")
        )

        if not final_project_id:
            raise ValueError(
                "Error: Google Cloud Project ID is required. Please set the "
                "GOOGLE_CLOUD_PROJECT environment variable or provide 'project_id' "
                "in your Gemini CLI command."
            )
        final_location_id = (
            location_id
            or self._location_id
            or os.environ.get("GOOGLE_CLOUD_LOCATION", _DEFAULT_LOCATION)
        )
        self._project_id = final_project_id
        self._location_id = final_location_id
        print(
            f"Using Project: {final_project_id}, Location: {final_location_id}"
        )
        return Client(project=final_project_id, location=final_location_id)

    def read_prompt(
        self,
        prompt_id: str,
        project_id: str | None = None,
        location_id: str | None = None,
    ) -> PromptDetails:
        """Get the prompt content with given prompt id."""
        prompt = self._get_prompt(prompt_id, project_id, location_id)
        return _build_prompt_details(prompt)

    def create_prompt(
        self,
        content: str,
        system_instruction: str,
        model: str,
        display_name: str,
        project_id: str | None = None,
        location_id: str | None = None,
    ) -> PromptDetails:
        """Create a prompt with given content, system instruction, model and display name."""
        client = self._get_client(project_id, location_id)
        contents = _build_contents(content, "user")

        si = None
        if system_instruction:
            if isinstance(system_instruction, str):
                # If a plain string is provided, create genai_types.Content
                si = _build_content(system_instruction, "system")
            elif isinstance(system_instruction, list):
                # If it's a list, extract the single genai_types.Content
                if len(system_instruction) == 1 and isinstance(
                    system_instruction[0], genai_types.Content
                ):
                    si = system_instruction[0]
                else:
                    raise TypeError(
                        "If system_instruction is a list, it must contain exactly one"
                        " genai_types.Content object."
                    )
            else:
                raise TypeError(
                    "system_instruction must be str, list[genai_types.Content], or"
                    f" None, but got {type(system_instruction).__name__}"
                )

        # Convert si to a dictionary using .dict() if it exists,
        # as the PromptData likely expects a dictionary for system_instruction.
        si_dict = si.dict() if si else None

        prompt_data = vertexai_types.PromptData(
            model=model,
            contents=contents,
            system_instruction=si_dict,
            generation_config=genai_types.GenerationConfig(
                temperature=0.1,
                top_p=0.95,
                top_k=20,
                candidate_count=1,
                max_output_tokens=100,
            ),
        )

        prompt = vertexai_types.Prompt(prompt_data=prompt_data)

        create_config = vertexai_types.CreatePromptConfig(
            prompt_display_name=display_name
        )

        return _build_prompt_details(
            client.prompts.create(prompt=prompt, config=create_config)
        )

    # TODO(b/455906163): Add support for updating display name of a prompt.
    def update_prompt(
        self,
        prompt_id: str,
        project_id: str | None = None,
        location_id: str | None = None,
        content: str | None = None,
        system_instruction: str | None = None,
        model: str | None = None,
    ) -> PromptDetails:
        """Update a prompt with given prompt_id and new content, system instruction, model."""
        client = self._get_client(project_id, location_id)
        prompt = self._get_prompt(
            prompt_id, project_id, location_id
        )  # Pass project_id/location_id

        if content is not None:
            prompt.prompt_data.contents = _build_contents(content, "user")
        if system_instruction is not None:
            prompt.prompt_data.system_instruction = _build_content(
                system_instruction, "system"
            )
        if model is not None:
            prompt.prompt_data.model = model

        try:
            return _build_prompt_details(
                client.prompts.create_version(
                    prompt=prompt, prompt_id=prompt_id
                )
            )
        except Exception as e:
            raise ValueError(f"Failed to update prompt {prompt_id}.") from e

    def delete_prompt(
        self,
        prompt_id: str,
        project_id: str | None = None,
        location_id: str | None = None,
    ) -> None:
        """Delete a prompt with given prompt_id."""
        client = self._get_client(project_id, location_id)
        try:
            client.prompts.delete(prompt_id=prompt_id)  # Use local client
        except exceptions.NotFound as e:
            raise ValueError(f"Prompt {prompt_id} not found.") from e
        except Exception as e:
            raise ValueError(f"Failed to delete prompt {prompt_id}.") from e

    def list_prompts(
        self,
        display_name: str | None = None,
        page_size: int | None = 10,
        project_id: str | None = None,
        location_id: str | None = None,
    ) -> list[PromptDetails]:
        """Lists Vertex prompts matching a given display name."""
        client = self._get_client(project_id, location_id)
        filter_str = ""
        if display_name:
            filter_str = f'display_name=~"(?i).*{display_name}.*"'
        list_config = vertexai_types.ListPromptsConfig(
            filter=filter_str, page_size=page_size
        )

        raw_prompt_refs = client.prompts.list(config=list_config)
        prompt_refs = list(itertools.islice(raw_prompt_refs, page_size))
        prompts = [
            self._get_prompt(prompt_id=ref.prompt_id) for ref in prompt_refs
        ]
        valid_prompts = [p for p in prompts if p is not None]
        formatted_prompts = [
            _build_prompt_details(prompt=p, truncate_texts=True)
            for p in valid_prompts
        ]
        return formatted_prompts

    def _get_prompt(
        self,
        prompt_id: str,
        project_id: str | None = None,
        location_id: str | None = None,
    ) -> vertexai_types.Prompt:
        """Get the prompt content with given prompt id."""
        client = self._get_client(project_id, location_id)
        try:
            return client.prompts.get(prompt_id=prompt_id)
        except exceptions.NotFound as e:
            raise ValueError(f"Prompt {prompt_id} not found.") from e
