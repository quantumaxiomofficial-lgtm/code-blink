from code_blink.tools.registry import ToolDef, ToolRegistry


def check_permission(
    registry: ToolRegistry,
    tool_name: str,
    current_level: str,
) -> bool:
    tool = registry.get(tool_name)
    if not tool:
        return True
    levels = {"read": 0, "write": 1, "full": 2}
    return levels.get(current_level, 0) >= levels.get(tool.required_permission, 0)


def filter_schemas_by_permission(
    schemas: list[dict],
    current_level: str,
    registry: ToolRegistry,
) -> list[dict]:
    levels = {"read": 0, "write": 1, "full": 2}
    current = levels.get(current_level, 0)
    filtered = []
    for s in schemas:
        name = s.get("function", {}).get("name", "")
        tool = registry.get(name)
        if tool:
            if current >= levels.get(tool.required_permission, 0):
                filtered.append(s)
        else:
            filtered.append(s)
    return filtered
