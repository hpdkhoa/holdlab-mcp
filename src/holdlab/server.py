"""Hold Lab: Measures the hand and arm, keeps joint limits as walls, and places holds on an object by rule.

8 tools, each an action tool over the existing lab functions (40 former tools).
Merged from: poselab-mcp, fakepose-mcp.
"""

import importlib

from mcp.server.mcpserver import MCPServer

from .actions import add_action_tool
from .tools import TOOLS

mcp = MCPServer(
    "holdlab",
    instructions="Measures the hand and arm, keeps joint limits as walls, and places holds on an object by rule. Each tool takes `action` and that action's `args`; the tool description lists them.",
)


def load(spec):
    return {action: getattr(importlib.import_module(module), fn) for module, fn, action in spec}


for _name, (_summary, _spec) in TOOLS.items():
    add_action_tool(mcp, _name, _summary, load(_spec))


def main():
    mcp.run()


if __name__ == "__main__":
    main()
