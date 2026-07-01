from __future__ import annotations
import asyncio
import re

DANGEROUS_PATTERNS: list[tuple[re.Pattern, str]] = [
    # rm -rf / (Unix root)
    (re.compile(r"rm\s+[-/][a-z]*rf[a-z]*\s+/", re.I),
     "rm -rf / is not allowed"),
    # rm -rf ~ (home dir root)
    (re.compile(r"rm\s+[-/][a-z]*rf[a-z]*\s+~([/\\]\s*$|\s*$)", re.I),
     "rm -rf ~ is not allowed"),
    # rm -rf targeting drive root
    (re.compile(r"rm\s+[-/][a-z]*rf[a-z]*\s+[A-Za-z]:[/\\]\s*$", re.I),
     "rm -rf targeting drive root is not allowed"),
    # rm -rf targeting Windows system directories
    (re.compile(r"rm\s+[-/][a-z]*rf[a-z]*\s+.*\\(?:Windows|Program Files|ProgramData|System32|Boot)\b", re.I),
     "rm -rf targeting system directory is not allowed"),
    (re.compile(r"rm\s+[-/][a-z]*rf[a-z]*\s+.*/(?:Windows|Program Files|ProgramData|System32|Boot)\b", re.I),
     "rm -rf targeting system directory is not allowed"),
    # Remove-Item/ri/del/rd/erase targeting drive root (PowerShell style)
    (re.compile(r"(?:Remove-Item|ri)\s+(?:-Recurse\s+)?(?:-Force\s+)?(?:-Path\s+)?[A-Za-z]:[/\\]\s*$", re.I),
     "Deleting a drive root is not allowed"),
    # Remove-Item/ri/del/rd/erase targeting Windows system directories
    (re.compile(r"(?:Remove-Item|ri|del|rd|erase)\s+.*\\(?:Windows|Program Files|ProgramData|System32|Boot)\b", re.I),
     "Deleting system directories is not allowed"),
    # del with flags targeting system paths
    (re.compile(r"(?:del|erase)\s+(?:[-/][a-z]+\s+)*[A-Za-z]:\\(?:Windows|Program Files|ProgramData|System32|Boot)\b", re.I),
     "Bulk deletion from system paths is not allowed"),
    # Remove-Item HKLM (registry)
    (re.compile(r"Remove-Item\s+.*HKLM:", re.I),
     "Removing registry keys is not allowed"),

    # Format
    (re.compile(r"\bformat\s+[A-Za-z]:", re.I),
     "Formatting drives is not allowed"),
    # Diskpart
    (re.compile(r"\bdiskpart\b", re.I),
     "Diskpart is not allowed"),
    # Disk/volume operations
    (re.compile(r"(?:Clear-Disk|Format-Volume|Repair-Volume)", re.I),
     "Disk/volume operations are not allowed"),

    # Shutdown / reboot
    (re.compile(r"\bshutdown\s+[-/][srhlt]", re.I),
     "Shutdown/reboot commands are not allowed"),
    (re.compile(r"(?:Restart-Computer|Stop-Computer)\b", re.I),
     "System restart/stop commands are not allowed"),

    # Raw disk writes
    (re.compile(r"\bdd\s+if=", re.I),
     "Raw disk writes with dd are not allowed"),
]


def _check_safe(command: str) -> str | None:
    for pattern, msg in DANGEROUS_PATTERNS:
        if pattern.search(command):
            return msg
    if not command.strip():
        return "Empty command"
    return None


async def tool_shell(command: str, timeout: int = 60) -> str:
    err = _check_safe(command)
    if err:
        return f"Blocked: {err}"

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            shell=True,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return f"Command timed out after {timeout}s"

        output = ""
        if stdout:
            text = stdout.decode("utf-8", errors="replace")[:5000]
            output += text
        if stderr:
            text = stderr.decode("utf-8", errors="replace")[:2000]
            if output:
                output += "\n--- stderr ---\n"
            output += text

        if proc.returncode != 0:
            output += f"\n(exit code: {proc.returncode})"

        if len(output) > 5000:
            output = output[:5000] + "\n... (truncated at 5000 chars)"

        return output or f"(completed with no output, exit code: {proc.returncode})"

    except FileNotFoundError as e:
        return f"Error: shell not found: {e}"
    except Exception as e:
        return f"Error executing command: {e}"
