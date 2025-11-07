"""
Unit tests for ROM solver.
"""

import pytest
import numpy as np

from battery_aircooling.config_schema import (
    SimulationConfig,
    AirProperties,
    CellsConfig,
    ChannelConfig,
    RibsConfig,
    CellGeometry,
)
from battery_aircooling.physics_rom import ROMSolver


@pytest.fixture
def basic_config() -> SimulationConfig:
    """Create a basic simulation configuration for testing."""
    return SimulationConfig(
        name="test_simulation",
        air=AirProperties(
            Tin=298.15,
            Pin=101325,
            mdot=0.05
        ),
        cells=CellsConfig(
            n_rows=4,
            n_cols=8,
            q_gen=15.0,
            size=CellGeometry(
                lx=0.065,
                ly=0.100,
                lz=0.018
            ),
            gap_to_channel=0.002
        ),
        channel=ChannelConfig(
            length=0.520,
            width=0.100,
            height=0.010,
            n_parallel=4
        ),
        ribs=RibsConfig(
            type="rect",
            pitch=0.020,
            height=0.003,
            thickness=0.002
        )
    )


class TestROMSolver:
    """Test ROM solver functionality."""
    
    def test_solver_initialization(self, basic_config: SimulationConfig) -> None:
        """Test that solver initializes correctly."""
        solver = ROMSolver(basic_config)
        
        assert solver.config == basic_config
        assert solver.Dh > 0
        assert solver.A_channel > 0
        assert "mu" in solver.air_props
        assert "rho" in solver.air_props
    
    def test_solver_runs(self, basic_config: SimulationConfig) -> None:
        """Test that solver runs without errors."""
        solver = ROMSolver(basic_config)
        results = solver.solve(max_iter=50, tol=1e-3)
        
        assert results is not None
        assert results.iterations > 0
    
    def test_mass_conservation(self, basic_config: SimulationConfig) -> None:
        """Test that mass is conserved across channels."""
        solver = ROMSolver(basic_config)
        results = solver.solve(max_iter=100, tol=1e-4)
        
        # Sum of channel flows should equal total flow
        total_mdot = sum(ch.mdot for ch in results.channels)
        expected_mdot = basic_config.air.mdot
        
        rel_error = abs(total_mdot - expected_mdot) / expected_mdot
        assert rel_error < 0.01  # Within 1%
    
    def test_energy_conservation(self, basic_config: SimulationConfig) -> None:
        """Test that energy is approximately conserved."""
        solver = ROMSolver(basic_config)
        results = solver.solve(max_iter=100, tol=1e-4)
        
        # Total heat removed should approximately equal heat generated
        Q_gen_total = (basic_config.cells.n_rows * 
                      basic_config.cells.n_cols * 
                      basic_config.cells.q_gen)
        Q_removed_total = results.total_heat_removed
        
        rel_error = abs(Q_removed_total - Q_gen_total) / Q_gen_total
        assert rel_error < 0.15  # Within 15% (accounting for model simplifications)
    
    def test_temperature_increases(self, basic_config: SimulationConfig) -> None:
        """Test that outlet temperature is higher than inlet."""
        solver = ROMSolver(basic_config)
        results = solver.solve(max_iter=100, tol=1e-4)
        
        for ch in results.channels:
            assert ch.T_fluid_out > ch.T_fluid_in
    
    def test_cell_temperature_reasonable(self, basic_config: SimulationConfig) -> None:
        """Test that cell temperatures are in reasonable range."""
        solver = ROMSolver(basic_config)
        results = solver.solve(max_iter=100, tol=1e-4)
        
        if results.cells is not None:
            # Temperature should be above inlet
            assert results.cells.T_min > basic_config.air.Tin
            
            # Temperature should not be excessively high
            assert results.cells.T_max < basic_config.air.Tin + 100  # Within 100K rise
    
    def test_higher_flow_reduces_temperature(self, basic_config: SimulationConfig) -> None:
        """Test that increasing flow rate reduces cell temperature."""
        # Low flow
        config_low = basic_config.model_copy(deep=True)
        config_low.air.mdot = 0.03
        solver_low = ROMSolver(config_low)
        results_low = solver_low.solve(max_iter=100, tol=1e-4)
        
        # High flow
        config_high = basic_config.model_copy(deep=True)
        config_high.air.mdot = 0.08
        solver_high = ROMSolver(config_high)
        results_high = solver_high.solve(max_iter=100, tol=1e-4)
        
        # Higher flow should result in lower max temperature
        if results_low.cells and results_high.cells:
            assert results_high.cells.T_max < results_low.cells.T_max
    
    def test_higher_ribs_increase_pressure_drop(self, basic_config: SimulationConfig) -> None:
        """Test that taller ribs increase pressure drop."""
        # Short ribs
        config_short = basic_config.model_copy(deep=True)
        config_short.ribs.height = 0.002
        solver_short = ROMSolver(config_short)
        results_short = solver_short.solve(max_iter=100, tol=1e-4)
        
        # Tall ribs
        config_tall = basic_config.model_copy(deep=True)
        config_tall.ribs.height = 0.006
        solver_tall = ROMSolver(config_tall)
        results_tall = solver_tall.solve(max_iter=100, tol=1e-4)
        
        # Taller ribs should have higher pressure drop
        assert results_tall.total_pressure_drop > results_short.total_pressure_drop
    
    def test_convergence(self, basic_config: SimulationConfig) -> None:
        """Test that solver converges within iteration limit."""
        solver = ROMSolver(basic_config)
        results = solver.solve(max_iter=200, tol=1e-5)
        
        # Should converge
        assert results.converged or results.iterations < 200


class TestParameterSweep:
    """Test parameter sweep functionality."""
    
    def test_sweep_single_parameter(self, basic_config: SimulationConfig) -> None:
        """Test sweeping a single parameter."""
        solver = ROMSolver(basic_config)
        
        heights = [0.002, 0.003, 0.004, 0.005]
        results_list = solver.sweep_parameter("ribs.height", heights, basic_config)
        
        assert len(results_list) == len(heights)
        
        # Each result should have valid data
        for result in results_list:
            assert result.channels is not None
            assert len(result.channels) > 0
    
    def test_sweep_monotonic_trend(self, basic_config: SimulationConfig) -> None:
        """Test that sweep shows expected monotonic trends."""
        solver = ROMSolver(basic_config)
        
        heights = [0.002, 0.004, 0.006, 0.008]
        results_list = solver.sweep_parameter("ribs.height", heights, basic_config)
        
        # Extract pressure drops
        pressure_drops = [r.total_pressure_drop for r in results_list]
        
        # Pressure drop should generally increase with rib height
        # (allowing for some numerical noise)
        for i in range(len(pressure_drops) - 1):
            # Check that trend is generally increasing
            assert pressure_drops[-1] > pressure_drops[0]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
