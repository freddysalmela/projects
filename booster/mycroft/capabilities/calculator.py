import math
from sympy import sympify, pi, sqrt, simplify, N
from sympy.core.sympify import SympifyError


def evaluate_expression(expr: str) -> str:
    try:
        result = sympify(expr, evaluate=True)
        numeric = float(N(result, 6))
        if numeric == int(numeric):
            return str(int(numeric))
        return f"{numeric:.4f}"
    except (SympifyError, Exception) as e:
        return f"Could not evaluate: {e}"


_GEOMETRY = {
    "circle_area": lambda r: f"Area = π × {r}² = {float(N(pi * sympify(r)**2, 6)):.4f} sq units",
    "circle_circumference": lambda r: f"Circumference = 2π × {r} = {float(N(2 * pi * sympify(r), 6)):.4f} units",
    "rectangle_area": lambda w, h: f"Area = {w} × {h} = {float(sympify(w) * sympify(h)):.4f} sq units",
    "rectangle_perimeter": lambda w, h: f"Perimeter = 2({w} + {h}) = {float(2 * (sympify(w) + sympify(h))):.4f} units",
    "triangle_area": lambda b, h: f"Area = ½ × {b} × {h} = {float(sympify(b) * sympify(h) / 2):.4f} sq units",
    "cylinder_volume": lambda r, h: f"Volume = π × {r}² × {h} = {float(N(pi * sympify(r)**2 * sympify(h), 6)):.4f} cubic units",
    "cylinder_surface": lambda r, h: f"Surface = 2π{r}({r}+{h}) = {float(N(2 * pi * sympify(r) * (sympify(r) + sympify(h)), 6)):.4f} sq units",
    "sphere_volume": lambda r: f"Volume = (4/3)π × {r}³ = {float(N(4/3 * pi * sympify(r)**3, 6)):.4f} cubic units",
    "pythagorean_c": lambda a, b: f"Hypotenuse c = √({a}² + {b}²) = {float(N(sqrt(sympify(a)**2 + sympify(b)**2), 6)):.4f} units",
    "pythagorean_a": lambda c, b: f"Side a = √({c}² - {b}²) = {float(N(sqrt(sympify(c)**2 - sympify(b)**2), 6)):.4f} units",
}

GEOMETRY_FORMULAS = list(_GEOMETRY.keys())


def geometry(formula: str, dimensions: dict) -> str:
    if formula not in _GEOMETRY:
        available = ", ".join(GEOMETRY_FORMULAS)
        return f"Unknown formula '{formula}'. Available: {available}"
    fn = _GEOMETRY[formula]
    try:
        args = list(dimensions.values())
        return fn(*args)
    except Exception as e:
        return f"Error computing {formula}: {e}"
