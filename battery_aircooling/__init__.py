"""
Battery Air Cooling Simulator

A comprehensive package for simulating and optimizing air-cooled battery pack
thermal management with parametric rib channel designs.
"""

__version__ = "0.1.0"
__author__ = "Battery Cooling Research Team"

from battery_aircooling.config_schema import SimulationConfig
from battery_aircooling.physics_rom import ROMSolver
from battery_aircooling.physics_post import calculate_metrics

__all__ = [
    "SimulationConfig",
    "ROMSolver",
    "calculate_metrics",
]
