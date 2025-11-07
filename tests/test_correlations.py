"""
Unit tests for heat transfer and friction correlations.
"""

import pytest
import numpy as np

from battery_aircooling.correlations import (
    calc_air_properties,
    calc_Re,
    calc_hydraulic_diameter,
    Nu_smooth_duct,
    f_smooth_duct,
    Nu_ribbed_duct,
    f_ribbed_duct,
    calc_JF_factor,
    calc_convection_coefficient,
    calc_pressure_drop,
    RibGeometry,
)


class TestAirProperties:
    """Test air property calculations."""
    
    def test_properties_at_standard_conditions(self) -> None:
        """Test at 25°C, 1 atm."""
        T = 298.15  # K
        P = 101325  # Pa
        
        props = calc_air_properties(T, P)
        
        assert "mu" in props
        assert "rho" in props
        assert "cp" in props
        assert "k" in props
        assert "Pr" in props
        
        # Check reasonable ranges
        assert 1.7e-5 < props["mu"] < 2.0e-5
        assert 1.1 < props["rho"] < 1.3
        assert 1000 < props["cp"] < 1100
        assert 0.024 < props["k"] < 0.030
        assert 0.7 < props["Pr"] < 0.75
    
    def test_properties_temperature_dependence(self) -> None:
        """Test that properties change with temperature."""
        T1 = 273.15  # 0°C
        T2 = 373.15  # 100°C
        P = 101325
        
        props1 = calc_air_properties(T1, P)
        props2 = calc_air_properties(T2, P)
        
        # Viscosity increases with temperature
        assert props2["mu"] > props1["mu"]
        
        # Density decreases with temperature
        assert props2["rho"] < props1["rho"]
        
        # Thermal conductivity increases with temperature
        assert props2["k"] > props1["k"]


class TestReynoldsNumber:
    """Test Reynolds number calculation."""
    
    def test_laminar_flow(self) -> None:
        """Test laminar flow Re calculation."""
        u = 0.1  # m/s
        Dh = 0.01  # m
        rho = 1.2  # kg/m³
        mu = 1.8e-5  # Pa·s
        
        Re = calc_Re(u, Dh, rho, mu)
        
        assert Re > 0
        assert Re < 2300  # Laminar
    
    def test_turbulent_flow(self) -> None:
        """Test turbulent flow Re calculation."""
        u = 10.0  # m/s
        Dh = 0.01  # m
        rho = 1.2  # kg/m³
        mu = 1.8e-5  # Pa·s
        
        Re = calc_Re(u, Dh, rho, mu)
        
        assert Re > 4000  # Turbulent


class TestSmoothDuctCorrelations:
    """Test smooth duct correlations."""
    
    def test_Nu_laminar(self) -> None:
        """Test Nusselt number for laminar flow."""
        Re = 1500
        Pr = 0.71
        
        Nu = Nu_smooth_duct(Re, Pr)
        
        # Laminar fully developed Nu ≈ 3.66
        assert 3.5 < Nu < 4.0
    
    def test_Nu_turbulent(self) -> None:
        """Test Nusselt number for turbulent flow."""
        Re = 10000
        Pr = 0.71
        
        Nu = Nu_smooth_duct(Re, Pr)
        
        # Turbulent Nu > laminar Nu
        assert Nu > 10
    
    def test_Nu_monotonic_with_Re(self) -> None:
        """Test that Nu increases with Re."""
        Pr = 0.71
        Re_values = [5000, 10000, 20000, 50000]
        
        Nu_values = [Nu_smooth_duct(Re, Pr) for Re in Re_values]
        
        # Check monotonic increase
        for i in range(len(Nu_values) - 1):
            assert Nu_values[i+1] > Nu_values[i]
    
    def test_friction_factor_laminar(self) -> None:
        """Test friction factor for laminar flow."""
        Re = 1500
        
        f = f_smooth_duct(Re)
        
        # Laminar f = 64/Re
        expected = 64 / Re
        assert abs(f - expected) < 1e-6
    
    def test_friction_factor_turbulent(self) -> None:
        """Test friction factor for turbulent flow."""
        Re = 10000
        
        f = f_smooth_duct(Re)
        
        # Turbulent f < laminar f
        f_laminar = 64 / Re
        assert f < f_laminar
    
    def test_friction_factor_decreases_with_Re(self) -> None:
        """Test that friction factor decreases with Re in turbulent regime."""
        Re_values = [5000, 10000, 20000, 50000, 100000]
        
        f_values = [f_smooth_duct(Re) for Re in Re_values]
        
        # Check monotonic decrease
        for i in range(len(f_values) - 1):
            assert f_values[i+1] < f_values[i]


class TestRibbedDuctCorrelations:
    """Test ribbed duct correlations."""
    
    def test_Nu_enhancement(self) -> None:
        """Test that ribs enhance heat transfer."""
        Re = 10000
        Pr = 0.71
        
        rib_geom = RibGeometry(
            e_H=0.1,
            p_e=10.0,
            t_e=1.0,
            rib_type="rect",
            staggered=False
        )
        
        Nu_smooth = Nu_smooth_duct(Re, Pr)
        Nu_ribbed = Nu_ribbed_duct(Re, Pr, rib_geom)
        
        # Ribbed should have higher Nu
        assert Nu_ribbed >= Nu_smooth
    
    def test_friction_penalty(self) -> None:
        """Test that ribs increase friction."""
        Re = 10000
        
        rib_geom = RibGeometry(
            e_H=0.1,
            p_e=10.0,
            t_e=1.0,
            rib_type="rect",
            staggered=False
        )
        
        f_smooth = f_smooth_duct(Re)
        f_ribbed = f_ribbed_duct(Re, rib_geom)
        
        # Ribbed should have higher friction
        assert f_ribbed >= f_smooth
    
    def test_rib_height_effect(self) -> None:
        """Test that higher ribs increase Nu and f."""
        Re = 10000
        Pr = 0.71
        
        e_H_values = [0.05, 0.1, 0.15, 0.2]
        
        Nu_values = []
        f_values = []
        
        for e_H in e_H_values:
            rib_geom = RibGeometry(
                e_H=e_H,
                p_e=10.0,
                t_e=1.0,
                rib_type="rect",
                staggered=False
            )
            
            Nu_values.append(Nu_ribbed_duct(Re, Pr, rib_geom))
            f_values.append(f_ribbed_duct(Re, rib_geom))
        
        # Higher ribs should increase both Nu and f
        for i in range(len(e_H_values) - 1):
            assert Nu_values[i+1] >= Nu_values[i]
            assert f_values[i+1] >= f_values[i]


class TestJFFactor:
    """Test JF factor calculation."""
    
    def test_jf_baseline(self) -> None:
        """Test JF factor for smooth duct (should be 1)."""
        Nu = 50.0
        f = 0.02
        Nu0 = 50.0
        f0 = 0.02
        
        JF = calc_JF_factor(Nu, f, Nu0, f0)
        
        assert abs(JF - 1.0) < 1e-6
    
    def test_jf_good_performance(self) -> None:
        """Test JF > 1 for good thermal-hydraulic performance."""
        Nu = 60.0
        f = 0.025
        Nu0 = 50.0
        f0 = 0.02
        
        JF = calc_JF_factor(Nu, f, Nu0, f0)
        
        # Higher heat transfer with modest friction increase
        assert JF > 1.0


class TestConvectionCoefficient:
    """Test convection coefficient calculation."""
    
    def test_convection_coefficient(self) -> None:
        """Test h = Nu * k / Dh."""
        Nu = 50.0
        k = 0.026  # W/(m·K)
        Dh = 0.01  # m
        
        h = calc_convection_coefficient(Nu, k, Dh)
        
        expected = Nu * k / Dh
        assert abs(h - expected) < 1e-6
        
        # Check reasonable range for air
        assert 100 < h < 200


class TestPressureDrop:
    """Test pressure drop calculation."""
    
    def test_pressure_drop_increases_with_length(self) -> None:
        """Test that pressure drop increases with channel length."""
        f = 0.02
        Dh = 0.01
        rho = 1.2
        u = 5.0
        
        L1 = 0.1
        L2 = 0.2
        
        dP1 = calc_pressure_drop(f, L1, Dh, rho, u)
        dP2 = calc_pressure_drop(f, L2, Dh, rho, u)
        
        assert dP2 > dP1
        assert abs(dP2 / dP1 - 2.0) < 0.01  # Should be approximately 2x
    
    def test_pressure_drop_with_minor_loss(self) -> None:
        """Test pressure drop with additional minor losses."""
        f = 0.02
        L = 0.5
        Dh = 0.01
        rho = 1.2
        u = 5.0
        K_loss = 1.5
        
        dP_no_loss = calc_pressure_drop(f, L, Dh, rho, u, K_loss=0)
        dP_with_loss = calc_pressure_drop(f, L, Dh, rho, u, K_loss=K_loss)
        
        assert dP_with_loss > dP_no_loss


class TestMassConservation:
    """Test mass conservation in flow calculations."""
    
    def test_hydraulic_diameter(self) -> None:
        """Test hydraulic diameter calculation for rectangular duct."""
        width = 0.1
        height = 0.01
        
        Dh = calc_hydraulic_diameter(width, height)
        
        # For rectangular: Dh = 4*A/P = 4*w*h/(2*(w+h))
        expected = 4 * width * height / (2 * (width + height))
        assert abs(Dh - expected) < 1e-9
        
        # For square: Dh = side
        Dh_square = calc_hydraulic_diameter(0.01, 0.01)
        assert abs(Dh_square - 0.01) < 1e-9


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
