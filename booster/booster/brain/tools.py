from booster.capabilities.search import web_search, youtube_search, open_url
from booster.capabilities.calculator import evaluate_expression, geometry, GEOMETRY_FORMULAS

TOOLS = [
    {
        "name": "web_search",
        "description": "Search the web using DuckDuckGo. Use this for general knowledge, how-to questions, technical specs, or anything that benefits from current information.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"},
                "max_results": {"type": "integer", "description": "Number of results to return (default 5)", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "youtube_search",
        "description": "Search YouTube for video tutorials or demonstrations. Use this when the user asks to find or watch a video.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "YouTube search query"},
                "max_results": {"type": "integer", "description": "Number of results to return (default 5)", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "open_url",
        "description": "Open a URL in the user's default web browser. Use after youtube_search to open the best video result, or to open any webpage.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to open"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "calculate",
        "description": "Evaluate a mathematical expression. Supports arithmetic, algebra, square roots, pi, powers, etc. Always use this for calculations rather than doing math in your head.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Math expression to evaluate, e.g. 'pi * 4**2' or 'sqrt(144)' or '(3/8) * 16'"},
            },
            "required": ["expression"],
        },
    },
    {
        "name": "geometry",
        "description": f"Calculate common geometry formulas used in workshop and construction. Available formulas: {', '.join(GEOMETRY_FORMULAS)}",
        "input_schema": {
            "type": "object",
            "properties": {
                "formula": {
                    "type": "string",
                    "description": "The formula name",
                    "enum": GEOMETRY_FORMULAS,
                },
                "dimensions": {
                    "type": "object",
                    "description": "Dimension values as key-value pairs. For circle: {r: value}. For rectangle: {w: value, h: value}. For cylinder: {r: value, h: value}. For triangle: {b: value, h: value}. For Pythagorean: {a: value, b: value} or {c: value, b: value}.",
                },
            },
            "required": ["formula", "dimensions"],
        },
    },
]


def dispatch_tool(name: str, inputs: dict) -> str:
    if name == "web_search":
        results = web_search(inputs["query"], inputs.get("max_results", 5))
        if not results:
            return "No results found."
        lines = []
        for r in results:
            lines.append(f"Title: {r['title']}\nURL: {r['url']}\nSnippet: {r['snippet']}\n")
        return "\n".join(lines)

    if name == "youtube_search":
        results = youtube_search(inputs["query"], inputs.get("max_results", 5))
        if not results:
            return "No YouTube results found."
        lines = []
        for r in results:
            lines.append(f"Title: {r['title']}\nURL: {r['url']}\nChannel: {r['channel']}\nDuration: {r['duration']}\n")
        return "\n".join(lines)

    if name == "open_url":
        return open_url(inputs["url"])

    if name == "calculate":
        return evaluate_expression(inputs["expression"])

    if name == "geometry":
        return geometry(inputs["formula"], inputs["dimensions"])

    return f"Unknown tool: {name}"
