import inspect
import re

from sympy import sympify, pi, sqrt, N

# The expression comes from the model, which may have just read a web page, and sympify
# evaluates it as Python. Only plain maths is let through: no quotes, underscores,
# brackets, assignments or attribute access.
_ALLOWED = re.compile(r"^[0-9a-zA-Z\s.,+\-*/^()%!]+$")
_ATTRIBUTE = re.compile(r"[a-zA-Z)]\s*\.\s*[a-zA-Z]")


def _number(value) -> str:
    numeric = float(N(value, 10))
    if numeric == int(numeric) and abs(numeric) < 1e15:
        return str(int(numeric))
    return f"{numeric:.4f}"


def evaluate_expression(expr: str) -> str:
    expr = expr.strip()
    if not _ALLOWED.match(expr) or _ATTRIBUTE.search(expr):
        return "Could not evaluate: only numbers, operators and maths functions such as sqrt, sin or pi are allowed."
    try:
        result = sympify(expr.replace("^", "**"), evaluate=True)
        try:
            return _number(result)
        except (TypeError, ValueError):
            return str(result)   # symbolic or complex answer
    except Exception as e:
        return f"Could not evaluate: {e}"


def _f(value) -> float:
    return float(N(value, 10))


_GEOMETRY = {
    "circle_area": lambda r: f"Area = π × {r}² = {_f(pi * sympify(r)**2):.4f} sq units",
    "circle_circumference": lambda r: f"Circumference = 2π × {r} = {_f(2 * pi * sympify(r)):.4f} units",
    "rectangle_area": lambda w, h: f"Area = {w} × {h} = {_f(sympify(w) * sympify(h)):.4f} sq units",
    "rectangle_perimeter": lambda w, h: f"Perimeter = 2({w} + {h}) = {_f(2 * (sympify(w) + sympify(h))):.4f} units",
    "triangle_area": lambda b, h: f"Area = ½ × {b} × {h} = {_f(sympify(b) * sympify(h) / 2):.4f} sq units",
    "cylinder_volume": lambda r, h: f"Volume = π × {r}² × {h} = {_f(pi * sympify(r)**2 * sympify(h)):.4f} cubic units",
    "cylinder_surface": lambda r, h: f"Surface = 2π{r}({r}+{h}) = {_f(2 * pi * sympify(r) * (sympify(r) + sympify(h))):.4f} sq units",
    "sphere_volume": lambda r: f"Volume = (4/3)π × {r}³ = {_f(sympify(4) / 3 * pi * sympify(r)**3):.4f} cubic units",
    "pythagorean_c": lambda a, b: f"Hypotenuse c = √({a}² + {b}²) = {_f(sqrt(sympify(a)**2 + sympify(b)**2)):.4f} units",
    "pythagorean_a": lambda c, b: f"Side a = √({c}² - {b}²) = {_f(sqrt(sympify(c)**2 - sympify(b)**2)):.4f} units",
}

GEOMETRY_FORMULAS = list(_GEOMETRY.keys())


def geometry(formula: str, dimensions: dict) -> str:
    if formula not in _GEOMETRY:
        available = ", ".join(GEOMETRY_FORMULAS)
        return f"Unknown formula '{formula}'. Available: {available}"
    fn = _GEOMETRY[formula]
    wanted = list(inspect.signature(fn).parameters)
    # Dimensions are matched by name, so {"h": 10, "r": 2} and {"r": 2, "h": 10} give the same answer.
    given = {str(k).strip().lower(): v for k, v in (dimensions or {}).items()}
    if set(given) != set(wanted):
        return f"{formula} needs exactly these dimensions: {', '.join(wanted)}. Got: {', '.join(given) or 'none'}."
    for name, value in given.items():
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return f"Dimension '{name}' must be a number, got {value!r}."
    try:
        return fn(**given)
    except Exception as e:
        return f"Error computing {formula}: {e}"
