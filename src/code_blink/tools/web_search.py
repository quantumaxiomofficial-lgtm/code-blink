from __future__ import annotations

try:
    from ddgs import DDGS

    _ddgs = DDGS()
except ImportError:
    _ddgs = None


async def tool_web_search(query: str, max_results: int = 5) -> str:
    if _ddgs is None:
        return (
            "Error: DuckDuckGo search requires 'ddgs' package.\n"
            "Install: pip install ddgs"
        )
    try:
        results = list(_ddgs.text(query, max_results=max_results))
        if not results:
            return f"No results for: {query}"
        lines = []
        for r in results:
            title = r.get("title", "No title")
            url = r.get("href", r.get("url", "No URL"))
            body = r.get("body", r.get("description", "")).strip()
            lines.append(f"{title}\n  {url}\n  {body[:200]}")
        return "\n---\n".join(lines[:max_results])
    except Exception as e:
        return f"Error searching: {e}"


async def tool_web_fetch(url: str) -> str:
    try:
        import httpx
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, follow_redirects=True)
            resp.raise_for_status()
            text = resp.text
            import re
            text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
            text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
            text = re.sub(r"<[^>]+>", "", text)
            text = re.sub(r"\n\s*\n", "\n", text)
            text = text.strip()
            if len(text) > 5000:
                text = text[:5000] + "\n... (truncated)"
            return text or "No readable content found."
    except Exception as e:
        return f"Error fetching URL: {e}"
