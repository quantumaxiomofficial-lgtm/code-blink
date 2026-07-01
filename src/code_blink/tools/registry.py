from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine


@dataclass
class ToolDef:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., Coroutine[Any, Any, str]]
    required_permission: str = "read"
    required: list[str] = field(default_factory=list)


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolDef] = {}

    def register(self, tool: ToolDef):
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDef | None:
        return self._tools.get(name)

    def list(self) -> list[ToolDef]:
        return list(self._tools.values())

    def schemas(self) -> list[dict]:
        result = []
        for t in self._tools.values():
            result.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": {
                        "type": "object",
                        "properties": t.parameters,
                        "required": t.required,
                    },
                },
            })
        return result

    async def execute(
        self,
        name: str,
        args: dict[str, Any],
        permission_level: str = "read",
    ) -> str:
        tool = self._tools.get(name)
        if not tool:
            return f"Error: unknown tool '{name}'"

        levels = {"read": 0, "write": 1, "full": 2}
        if levels.get(permission_level, 0) < levels.get(tool.required_permission, 0):
            return (
                f"Error: tool '{name}' requires permission "
                f"'{tool.required_permission}', current level is '{permission_level}'"
            )

        try:
            result = await tool.handler(**args)
            return result
        except Exception as e:
            return f"Error executing '{name}': {e}"


_registry: ToolRegistry | None = None


def get_registry() -> ToolRegistry:
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def register_tool(tool: ToolDef):
    get_registry().register(tool)
