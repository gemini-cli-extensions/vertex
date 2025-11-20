"""Module for defining tools for the CLI agent."""

from collections.abc import Sequence

from absl import app
from mcp.server import fastmcp

from . import tools


def main(argv: Sequence[str]) -> None:
    if len(argv) > 1:
        raise app.UsageError("Too many command-line arguments.")

    prompt_manager = tools.VertexPromptManager()

    # Create an MCP server
    mcp = fastmcp.FastMCP("VertexMcpServer")

    mcp.add_tool(prompt_manager.read_prompt)
    mcp.add_tool(prompt_manager.create_prompt)
    mcp.add_tool(prompt_manager.update_prompt)
    mcp.add_tool(prompt_manager.delete_prompt)
    mcp.add_tool(prompt_manager.list_prompts)

    mcp.run()


if __name__ == "__main__":
    app.run(main)
