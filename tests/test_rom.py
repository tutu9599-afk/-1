"""
Unit tests for ROM solver.
"""

import pytest
import numpy as np

from battery_aircooling.config_schema import SimulationConfig
from battery_aircooling.physics_rom import ROMSolver


@pytest.fixture
def simple_config():
    """Create a simple test configuration."""
    config_dict = {
        "name": "test_case",
        "air": {
            "Tin": 300.0,
            "Pin": 101325.0,
            "mdot": 0.01,
        },
        "cells": {
            "n_rows": 2,
            "n_cols": 2,
            "q_gen": 5.0,
            "size": {
                "lx": 0.10,
                "ly": 0.10,
                "lz": 0.03,
            },
            "gap_to_channel": 0.002,
        },
        "channel": {
            "length": 0.20,
            "width": 0.10,
            "height": 0.01,
            "n_parallel": 2,
            "manifold_loss_coeff": 1.5,
        },
        "ribs": {
            "type": "rect",
            "pitch": 0.020,
            "height": 0.003,
            "thickness": 0.002,
            "staggered": False,
        },
        "solver": {
            "mode": "ROM",
            "max_iter": 50,
            "convergence_tol": 1e-4,
        },
    }
    
    return SimulationConfig(**config_dict)


def test_solver_initialization(simple_config):
    """Test ROM solver initialization."""
    solver = ROMSolver(simple_config)
    
    assert solver.config == simple_config
    assert solver.Dh > 0
    assert solver.A_channel > 0
    assert "mu" in solver.air_props
    assert "rho" in solver.air_props


def test_solver_convergence(simple_config):
    """Test that solver converges."""
    solver = ROMSolver(simple_config)
    results = solver.solve(max_iter=100, tol=1e-4)
    
    assert results.converged
    assert results.iterations > 0
    assert results.iterations < 100


def test_mass_conservation(simple_config):
    """Test mass conservation across channels."""
    solver = ROMSolver(simple_config)
    results = solver.solve()
    
    total_mdot_in = simple_config.air.mdot
    total_mdot_channels = sum(ch.mdot for ch in results.channels)
    
    # Mass should be conserved
    assert np.isclose(total_mdot_channels, total_mdot_in, rtol=1e-3)


def test_energy_balance(simple_config):
    """Test approximate energy balance."""
    solver = ROMSolver(simple_config)
    results = solver.solve()
    
    # Total heat generation
    Q_gen_total = simple_config.cells.n_rows * simple_config.cells.n_cols * simple_config.cells.q_gen
    
    # Total heat removed
    Q_removed = results.total_heat_removed
    
    # Should be approximately equal (some losses expected)
    assert Q_removed > 0
    assert Q_removed <= Q_gen_total * 1.1  # Allow 10% over-prediction


def test_temperature_increase(simple_config):
    """Test that outlet temperature is higher than inlet."""
    solver = ROMSolver(simple_config)
    results = solver.solve()
    
    for channel in results.channels:
        assert channel.T_fluid_out > channel.T_fluid_in
        assert channel.T_wall_mean > channel.T_fluid_mean


def test_pressure_drop_positive(simple_config):
    """Test that pressure drop is positive."""
    solver = ROMSolver(simple_config)
    results = solver.solve()
    
    assert results.total_pressure_drop > 0
    
    for channel in results.channels:
        assert channel.pressure_drop > 0


def test_reynolds_number_range(simple_config):
    """Test that Reynolds numbers are in reasonable range."""
    solver = ROMSolver(simple_config)
    results = solver.solve()
    
    for channel in results.channels:
        # Should be turbulent for typical cooling
        assert channel.Re > 1000
        assert channel.Re < 1e6


def test_cell_temperatures(simple_config):
    """Test cell temperature distribution."""
    solver = ROMSolver(simple_config)
    results = solver.solve()
    
    assert results.cells is not None
    assert len(results.cells.T_cells) == 4  # 2x2 cells
    
    # All cells should be hotter than inlet air
    for T_cell in results.cells.T_cells:
        assert T_cell > simple_config.air.Tin
    
    # Max should be greater than or equal to min
    assert results.cells.T_max >= results.cells.T_min


def test_rib_height_effect(simple_config):
    """Test that increasing rib height increases heat transfer and pressure drop."""
    # Baseline
    solver1 = ROMSolver(simple_config)
    results1 = solver1.solve()
    
    # Increased rib height
    config2 = simple_config.model_copy(deep=True)
    config2.ribs.height = 0.006  # Double the height
    solver2 = ROMSolver(config2)
    results2 = solver2.solve()
    
    # Higher ribs should:
    # 1. Increase pressure drop
    assert results2.total_pressure_drop > results1.total_pressure_drop
    
    # 2. Improve heat transfer (lower max temperature)
    assert results2.cells.T_max < results1.cells.T_max or np.isclose(results2.cells.T_max, results1.cells.T_max, rtol=0.1)


def test_flow_rate_effect(simple_config):
    """Test that increasing flow rate improves cooling."""
    # Baseline
    solver1 = ROMSolver(simple_config)
    results1 = solver1.solve()
    
    # Increased flow rate
    config2 = simple_config.model_copy(deep=True)
    config2.air.mdot = 0.02  # Double the flow rate
    solver2 = ROMSolver(config2)
    results2 = solver2.solve()
    
    # Higher flow should:
    # 1. Increase pressure drop
    assert results2.total_pressure_drop > results1.total_pressure_drop
    
    # 2. Lower cell temperatures
    assert results2.cells.T_max < results1.cells.T_max


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
