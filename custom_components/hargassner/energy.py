"""Validated conversion of a cumulative pellet counter to fuel energy."""
from math import isfinite


def pellet_energy_kwh(value, unit, state_class, factor=4.8):
    """Return fuel energy, never convert missing/invalid readings to zero.

    Only cumulative kg consumption is accepted. In particular the stock sensor
    (state_class=total) must not silently become an energy consumption source.
    """
    if unit != "kg" or state_class != "total_increasing" or isinstance(value, bool):
        return None
    try:
        mass = float(value)
        energy = mass * factor
    except (TypeError, ValueError, OverflowError):
        return None
    if not isfinite(mass) or mass < 0 or not isfinite(energy):
        return None
    return round(energy, 6)
