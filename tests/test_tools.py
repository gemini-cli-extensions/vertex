import unittest
from unittest.mock import MagicMock, patch

from google.api_core import exceptions
from vertex.tools import (
    PromptDetails,
    VertexPromptManager,
    _build_prompt_details,
)


class TestVertexPromptManager(unittest.TestCase):
    def setUp(self):
        self.manager = VertexPromptManager()
        self.mock_client = MagicMock()

    @patch("vertex.tools.Client")
    def test_get_client(self, mock_client_constructor):
        mock_client_constructor.return_value = self.mock_client
        client = self.manager._get_client(
            project_id="test-project", location_id="test-location"
        )
        self.assertEqual(client, self.mock_client)
        mock_client_constructor.assert_called_with(
            project="test-project", location="test-location"
        )

    def test_build_prompt_details(self):
        # Create a mock prompt object
        mock_prompt = MagicMock()
        mock_prompt.prompt_id = "123"
        mock_prompt.dataset.display_name = "Test Prompt"
        mock_prompt.prompt_data.system_instruction.parts = [
            MagicMock(text="System instruction")
        ]
        mock_prompt.prompt_data.contents = [
            MagicMock(parts=[MagicMock(text="Hello"), MagicMock(text=" World")])
        ]

        prompt_details = _build_prompt_details(mock_prompt)

        self.assertIsInstance(prompt_details, PromptDetails)
        self.assertEqual(prompt_details.prompt_id, "123")
        self.assertEqual(prompt_details.display_name, "Test Prompt")
        self.assertEqual(
            prompt_details.system_instruction, "System instruction"
        )
        self.assertEqual(prompt_details.contents, "Hello World")

    @patch("vertex.tools.Client")
    def test_read_prompt_success(self, mock_client_constructor):
        mock_client_constructor.return_value = self.mock_client
        mock_prompt = MagicMock()
        mock_prompt.prompt_id = "123"
        mock_prompt.dataset.display_name = "Test Prompt"
        mock_prompt.prompt_data.model = "gemini-pro"
        mock_prompt.prompt_data.system_instruction.parts = [
            MagicMock(text="System instruction")
        ]
        mock_prompt.prompt_data.contents = [
            MagicMock(parts=[MagicMock(text="Hello")])
        ]

        self.mock_client.prompts.get.return_value = mock_prompt

        prompt_details = self.manager.read_prompt(
            prompt_id="123", project_id="test-project"
        )
        self.assertEqual(prompt_details.prompt_id, "123")
        self.mock_client.prompts.get.assert_called_with(prompt_id="123")

    @patch("vertex.tools.Client")
    def test_read_prompt_not_found(self, mock_client_constructor):
        mock_client_constructor.return_value = self.mock_client
        self.mock_client.prompts.get.side_effect = exceptions.NotFound(
            "Prompt not found"
        )

        with self.assertRaises(ValueError) as context:
            self.manager.read_prompt(prompt_id="123", project_id="test-project")
        self.assertIn("Prompt 123 not found", str(context.exception))

    @patch("vertex.tools.Client")
    def test_delete_prompt_success(self, mock_client_constructor):
        mock_client_constructor.return_value = self.mock_client
        self.manager.delete_prompt(prompt_id="123", project_id="test-project")
        self.mock_client.prompts.delete.assert_called_with(prompt_id="123")

    @patch("vertex.tools.Client")
    def test_delete_prompt_not_found(self, mock_client_constructor):
        mock_client_constructor.return_value = self.mock_client
        self.mock_client.prompts.delete.side_effect = exceptions.NotFound(
            "Prompt not found"
        )

        with self.assertRaises(ValueError) as context:
            self.manager.delete_prompt(
                prompt_id="123", project_id="test-project"
            )
        self.assertIn("Prompt 123 not found", str(context.exception))


if __name__ == "__main__":
    unittest.main()
