"""units.py — unit conversion with exact factors (length, mass, volume, time, speed, area, pressure, temperature, data)."""
from fractions import Fraction

import sympy as sp

from ..errors import MathError, UsageError
from ..fmt import approx, box, mstr
from ..registry import command

F = Fraction
_T = {
    "length": {"mm": F(1, 1000), "cm": F(1, 100), "m": F(1), "km": F(1000), "in": F(254, 10000), "ft": F(3048, 10000),
               "yd": F(9144, 10000), "mi": F(1609344, 1000), "nmi": F(1852)},
    "mass": {"mg": F(1, 1000000), "g": F(1, 1000), "kg": F(1), "tonne": F(1000), "oz": F(28349523125, 10 ** 12),
             "lb": F(45359237, 10 ** 8), "ton": F(45359237 * 2000, 10 ** 8)},
    "volume": {"ml": F(1, 1000), "l": F(1), "tsp": F(492892159375, 10 ** 14), "tbsp": F(1478676478125, 10 ** 14), "floz": F(295735295625, 10 ** 13),
               "cup": F(2365882365, 10 ** 10), "pt": F(473176473, 10 ** 9), "qt": F(946352946, 10 ** 9), "gal": F(3785411784, 10 ** 9), "m3": F(1000)},
    "time": {"s": F(1), "min": F(60), "hr": F(3600), "day": F(86400), "week": F(604800), "year": F(31557600)},
    "area": {"mm2": F(1, 10 ** 6), "cm2": F(1, 10 ** 4), "m2": F(1), "km2": F(10 ** 6), "in2": F(64516, 10 ** 8), "ft2": F(9290304, 10 ** 8),
             "yd2": F(83612736, 10 ** 8), "acre": F(40468564224, 10 ** 7), "hectare": F(10000), "mi2": F(2589988110336, 10 ** 6)},
    "pressure": {"pa": F(1), "kpa": F(1000), "atm": F(101325), "bar": F(100000), "psi": F(6894757293168, 10 ** 9), "mmhg": F(133322387415, 10 ** 9)},
    "data": {"bit": F(1, 8), "byte": F(1), "kb": F(1000), "mb": F(10 ** 6), "gb": F(10 ** 9), "tb": F(10 ** 12), "kib": F(1024), "mib": F(1024 ** 2), "gib": F(1024 ** 3)},
}
_ALIAS = {"meter": "m", "meters": "m", "metre": "m", "foot": "ft", "feet": "ft", "inch": "in", "inches": "in", "yard": "yd", "yards": "yd",
          "mile": "mi", "miles": "mi", "kilometer": "km", "kilometers": "km", "centimeter": "cm", "centimeters": "cm", "millimeter": "mm",
          "gram": "g", "grams": "g", "kilogram": "kg", "kilograms": "kg", "pound": "lb", "pounds": "lb", "lbs": "lb", "ounce": "oz", "ounces": "oz",
          "liter": "l", "liters": "l", "litre": "l", "gallon": "gal", "gallons": "gal", "quart": "qt", "pint": "pt", "second": "s", "seconds": "s", "sec": "s",
          "minute": "min", "minutes": "min", "hour": "hr", "hours": "hr", "hrs": "hr", "days": "day", "weeks": "week", "years": "year",
          "atmosphere": "atm", "pascal": "pa", "fahrenheit": "f", "celsius": "c", "kelvin": "k", "fl_oz": "floz", "sqft": "ft2", "sqm": "m2",
          "bytes": "byte", "bits": "bit", "kilobyte": "kb", "megabyte": "mb", "gigabyte": "gb", "terabyte": "tb", "milliliter": "ml", "liters": "l"}
_SPEED = {"mph": ("mi", "hr"), "kph": ("km", "hr"), "kmh": ("km", "hr"), "km/h": ("km", "hr"), "m/s": ("m", "s"), "mps": ("m", "s"),
          "ft/s": ("ft", "s"), "fps": ("ft", "s"), "knot": ("nmi", "hr"), "knots": ("nmi", "hr")}
_TEMP = {"f", "c", "k"}


def _canon(u):
    u = u.strip().lower().replace("°", "").replace("_", "")
    return _ALIAS.get(u, u)


def _cat(u):
    for name, table in _T.items():
        if u in table:
            return name
    return None


def _pretty(x: Fraction, unit: str) -> str:
    """Terminating decimals print as decimals; anything else as an exact fraction plus ≈ decimal."""
    r = sp.Rational(x.numerator, x.denominator)
    d = int(r.q)
    for p in (2, 5):
        while d % p == 0:
            d //= p
    dec = approx(r, 12)
    if d == 1 or r.is_Integer:
        return f"{dec} {unit}"
    return f"{mstr(r)} {unit}  ≈ {approx(r, 8)} {unit}"


@command("units", "Units", "units <value> <from> <to>", "Convert units exactly: length, mass, volume, time, speed, area, pressure, temperature, data.",
         aliases=("convert",), examples=("units 60 mph m/s", "units 5 ft cm", "units 98.6 F C", "units 3 atm Pa", "units 2 gal l"))
def units(ctx, a):
    w = a.rest.split()
    if len(w) < 3:
        w += [ctx.ask(p) for p in ("value", "from unit", "to unit")[len(w):]]
    val = ctx.number(w[0], "value")
    fr, to = w[1], w[2]
    fr_c, to_c = _canon(fr), _canon(to)
    v = F(int(val.p), int(val.q)) if val.is_Rational else None
    if v is None:
        raise MathError("The value must be a plain number.")
    if fr_c in _TEMP and to_c in _TEMP:
        c = {"c": v, "f": (v - 32) * F(5, 9), "k": v - F(27315, 100)}[fr_c]
        out = {"c": c, "f": c * F(9, 5) + 32, "k": c + F(27315, 100)}[to_c]
        box(f"Temperature: {w[0]}° {fr.upper()} → {to.upper()}", [
            "°C = (°F − 32) × 5/9     °F = °C × 9/5 + 32     K = °C + 273.15",
            f"{w[0]}° {fr.upper()} = {_pretty(out, '°' + to_c.upper())}"])
        return
    fk, tk = fr.strip().lower(), to.strip().lower()
    if fk in _SPEED or tk in _SPEED:
        if fk not in _SPEED or tk not in _SPEED:
            raise MathError("Both units must be speeds (mph, km/h, m/s, ft/s, knots).")
        (l1, t1), (l2, t2) = _SPEED[fk], _SPEED[tk]
        out = v * _T["length"][l1] / _T["time"][t1] / (_T["length"][l2] / _T["time"][t2])
        box(f"Speed: {w[0]} {fr} → {to}", [f"{w[0]} {fr} = {_pretty(out, to)}"])
        return
    c1, c2 = _cat(fr_c), _cat(to_c)
    if c1 is None:
        raise MathError(f"I don't know the unit '{fr}'.")
    if c2 is None:
        raise MathError(f"I don't know the unit '{to}'.")
    if c1 != c2:
        raise MathError(f"Can't convert {c1} to {c2} — they measure different things.")
    out = v * _T[c1][fr_c] / _T[c1][to_c]
    box(f"{c1.title()}: {w[0]} {fr} → {to}", [f"{w[0]} {fr} = {_pretty(out, to)}"])
