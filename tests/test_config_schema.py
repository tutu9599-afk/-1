"""
Unit tests for configuration schema validation.
"""

import pytest
from pydantic import ValidationError

from battery_aircooling.config_schema import (
    SimulationConfig,
    AirProperties,
    CellsConfig,
    ChannelConfig,
    RibsConfig,
)


class TestAirProperties:
    """Test air properties validation."""
    
    def test_valid_air_with_mdot(self) -> None:
        """Test valid air configuration with mass flow rate."""
        air = AirProperties(
            Tin=298.15,
            Pin=101325,
            mdot=0.05
        )
        
        assert air.Tin == 298.15
        assert air.mdot == 0.05
    
    def test_valid_air_with_Re(self) -> None:
        """Test valid air configuration with Reynolds number."""
        air = AirProperties(
            Tin=298.15,
            Pin=101325,
            Re=10000
        )
        
        assert air.Re == 10000
    
    def test_missing_flow_specification(self) -> None:
        """Test that either mdot or Re must be specified."""
        with pytest.raises(ValidationError):
            AirProperties(
                Tin=298.15,
                Pin=101325
            )
    
    def test_negative_temperature(self) -> None:
        """Test that negative temperature is rejected."""
        with pytest.raises(ValidationError):
            AirProperties(
                Tin=-10,
                Pin=101325,
                mdot=0.05
            )


class TestRibsConfig:
    """Test rib configuration validation."""
    
    def test_valid_ribs(self) -> None:
        """Test valid rib configuration."""
        ribs = RibsConfig(
            type="rect",
            pitch=0.020,
            height=0.003,
            thickness=0.002
        )
        
        assert ribs.type == "rect"
        assert ribs.height == 0.003
    
    def test_rib_height_too_large(self) -> None:
        """Test that very large rib height is rejected."""
        with pytest.raises(ValidationError):
            RibsConfig(
                type="rect",
                pitch=0.020,
                height=0.5,  # 500mm - unrealistic
                thickness=0.002
            )
    
    def test_rib_height_too_small(self) -> None:
        """Test that very small rib height is rejected."""
        with pytest.raises(ValidationError):
            RibsConfig(
                type="rect",
                pitch=0.020,
                height=0.00001,  # 0.01mm - too small
                thickness=0.002
            )


class TestSimulationConfig:
    """Test complete simulation configuration."""
    
    def test_valid_config(self) -> None:
        """Test valid complete configuration."""
        config = SimulationConfig(
            name="test_sim",
            air=AirProperties(
                Tin=298.15,
                Pin=101325,
                mdot=0.05
            ),
            cells=CellsConfig(
                n_rows=4,
                n_cols=8,
                q_gen=15.0,
                size={
                    "lx": 0.065,
                    "ly": 0.100,
                    "lz": 0.018
                },
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
        
        assert config.name == "test_sim"
        assert config.cells.n_rows == 4
    
    def test_rib_too_tall_for_channel(self) -> None:
        """Test that rib height cannot exceed 50% of channel height."""
        with pytest.raises(ValidationError):
            SimulationConfig(
                air=AirProperties(Tin=298.15, Pin=101325, mdot=0.05),
                cells=CellsConfig(
                    n_rows=4, n_cols=8, q_gen=15.0,
                    size={"lx": 0.065, "ly": 0.100, "lz": 0.018},
                    gap_to_channel=0.002
                ),
                channel=ChannelConfig(
                    length=0.520, width=0.100, height=0.010
                ),
                ribs=RibsConfig(
                    type="rect",
                    pitch=0.020,
                    height=0.008,  # 8mm > 50% of 10mm channel
                    thickness=0.002
                )
            )
    
    def test_rib_thickness_too_large(self) -> None:
        """Test that rib thickness cannot exceed 50% of pitch."""
        with pytest.raises(ValidationError):
            SimulationConfig(
                air=AirProperties(Tin=298.15, Pin=101325, mdot=0.05),
                cells=CellsConfig(
                    n_rows=4, n_cols=8, q_gen=15.0,
                    size={"lx": 0.065, "ly": 0.100, "lz": 0.018},
                    gap_to_channel=0.002
                ),
                channel=ChannelConfig(
                    length=0.520, width=0.100, height=0.010
                ),
                ribs=RibsConfig(
                    type="rect",
                    pitch=0.020,
                    height=0.003,
                    thickness=0.015  # 15mm > 50% of 20mm pitch
                )
            )
    
    def test_parameter_path_access(self) -> None:
        """Test getting and setting parameters by path."""
        config = SimulationConfig(
            air=AirProperties(Tin=298.15, Pin=101325, mdot=0.05),
            cells=CellsConfig(
                n_rows=4, n_cols=8, q_gen=15.0,
                size={"lx": 0.065, "ly": 0.100, "lz": 0.018},
                gap_to_channel=0.002
            ),
            channel=ChannelConfig(
                length=0.520, width=0.100, height=0.010
            ),
            ribs=RibsConfig(
                type="rect", pitch=0.020, height=0.003, thickness=0.002
            )
        )
        
        # Get parameter
        height = config.get_parameter_by_path("ribs.height")
        assert height == 0.003
        
        # Set parameter
        config.set_parameter_by_path("ribs.height", 0.005)
        assert config.ribs.height == 0.005


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
