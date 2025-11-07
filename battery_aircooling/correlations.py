"""
Heat transfer and friction correlations for ribbed ducts.

Provides Nusselt number (Nu) and friction factor (f) correlations for various
rib geometries, based on literature and experimental data.
"""

import numpy as np
from typing import Literal, Dict, Tuple
from dataclasses import dataclass


@dataclass
class FlowProperties:
    """Fluid flow and thermophysical properties."""
    
    Re: float  # Reynolds number
    Pr: float  # Prandtl number
    mu: float  # Dynamic viscosity [Pa·s]
    rho: float  # Density [kg/m³]
    cp: float  # Specific heat [J/(kg·K)]
    k: float   # Thermal conductivity [W/(m·K)]


@dataclass
class RibGeometry:
    """Rib geometric parameters (non-dimensional)."""
    
    e_H: float      # Rib height to channel height ratio (e/H)
    p_e: float      # Rib pitch to height ratio (p/e)
    t_e: float      # Rib thickness to height ratio (t/e)
    rib_type: Literal["rect", "tri", "semi", "dimple"]
    staggered: bool


def calc_air_properties(T: float, P: float) -> Dict[str, float]:
    """
    Calculate air thermophysical properties using Sutherland's law.
    
    Args:
        T: Temperature [K]
        P: Pressure [Pa]
    
    Returns:
        Dictionary with properties: mu, rho, cp, k, Pr
    """
    # Reference values at T0 = 273.15 K
    T0 = 273.15
    mu0 = 1.716e-5  # [Pa·s]
    S = 110.4       # Sutherland constant [K]
    
    # Sutherland's formula for viscosity
    mu = mu0 * (T / T0)**1.5 * (T0 + S) / (T + S)
    
    # Ideal gas law for density
    R_specific = 287.05  # J/(kg·K) for air
    rho = P / (R_specific * T)
    
    # Specific heat (temperature-dependent polynomial)
    cp = 1000 + 0.1 * (T - 273.15)  # Simplified [J/(kg·K)]
    
    # Thermal conductivity (temperature-dependent)
    k = 0.024 + 7.5e-5 * (T - 273.15)  # [W/(m·K)]
    
    # Prandtl number
    Pr = mu * cp / k
    
    return {
        "mu": mu,
        "rho": rho,
        "cp": cp,
        "k": k,
        "Pr": Pr,
    }


def calc_Re(u: float, Dh: float, rho: float, mu: float) -> float:
    """
    Calculate Reynolds number.
    
    Args:
        u: Mean velocity [m/s]
        Dh: Hydraulic diameter [m]
        rho: Density [kg/m³]
        mu: Dynamic viscosity [Pa·s]
    
    Returns:
        Reynolds number [-]
    """
    return rho * u * Dh / mu


def calc_hydraulic_diameter(width: float, height: float) -> float:
    """
    Calculate hydraulic diameter for rectangular channel.
    
    Args:
        width: Channel width [m]
        height: Channel height [m]
    
    Returns:
        Hydraulic diameter [m]
    """
    return 4 * width * height / (2 * (width + height))


def Nu_smooth_duct(Re: float, Pr: float, L_Dh: float = 100.0) -> float:
    """
    Gnielinski correlation for smooth duct (baseline).
    
    Valid for: 2300 < Re < 5e6, 0.5 < Pr < 2000, L/Dh > 10
    
    Args:
        Re: Reynolds number
        Pr: Prandtl number
        L_Dh: Length to diameter ratio (for entrance correction)
    
    Returns:
        Nusselt number [-]
    """
    if Re < 2300:
        # Laminar flow (fully developed)
        return 3.66
    
    # Turbulent flow - Gnielinski correlation
    f = (0.790 * np.log(Re) - 1.64)**(-2)  # Petukhov friction factor
    
    numerator = (f / 8) * (Re - 1000) * Pr
    denominator = 1 + 12.7 * np.sqrt(f / 8) * (Pr**(2/3) - 1)
    
    Nu = numerator / denominator
    
    # Entrance effect correction (if L/Dh < 60)
    if L_Dh < 60:
        Nu *= (1 + (L_Dh)**(-0.7))
    
    return Nu


def f_smooth_duct(Re: float) -> float:
    """
    Friction factor for smooth duct.
    
    Args:
        Re: Reynolds number
    
    Returns:
        Darcy friction factor [-]
    """
    if Re < 2300:
        # Laminar flow
        return 64 / Re
    else:
        # Turbulent - Petukhov correlation
        return (0.790 * np.log(Re) - 1.64)**(-2)


def Nu_ribbed_duct(
    Re: float,
    Pr: float,
    rib_geom: RibGeometry,
    correlation: str = "han"
) -> float:
    """
    Nusselt number for ribbed duct.
    
    Various correlations available:
    - "han": Han et al. correlation (widely used)
    - "webb": Webb-Eckert correlation
    - "custom": User-defined augmentation
    
    Args:
        Re: Reynolds number
        Pr: Prandtl number
        rib_geom: Rib geometry parameters
        correlation: Correlation type
    
    Returns:
        Nusselt number [-]
    """
    # Baseline smooth duct Nu
    Nu0 = Nu_smooth_duct(Re, Pr)
    
    e_H = rib_geom.e_H
    p_e = rib_geom.p_e
    
    if correlation == "han":
        # Han et al. correlation for rib-roughened channels
        # Nu/Nu0 = C * (e/H)^a * (p/e)^b * Re^c
        
        # Coefficients depend on rib type
        if rib_geom.rib_type == "rect":
            C = 0.138
            a = 0.318
            b = -0.152
            c = 0.0
        elif rib_geom.rib_type == "tri":
            C = 0.165
            a = 0.295
            b = -0.118
            c = 0.0
        elif rib_geom.rib_type == "semi":
            C = 0.142
            a = 0.305
            b = -0.135
            c = 0.0
        else:  # dimple
            C = 0.095
            a = 0.280
            b = -0.090
            c = 0.0
        
        # Staggered arrangement gives higher heat transfer
        if rib_geom.staggered:
            C *= 1.15
        
        # Augmentation factor
        phi_Nu = C * (e_H**a) * (p_e**b) * (Re**(c))
        
        # Ensure minimum augmentation
        phi_Nu = max(1.0, phi_Nu)
        
    elif correlation == "webb":
        # Webb-Eckert correlation
        # More conservative estimate
        phi_Nu = 1.0 + 2.5 * e_H * (10 / p_e)**0.5
        
    else:  # custom or default
        # Simplified empirical model
        # Higher ribs and tighter pitch increase heat transfer
        phi_Nu = 1.0 + 4.0 * e_H * np.exp(-p_e / 8)
        
        # Rib type effect
        type_factor = {
            "rect": 1.0,
            "tri": 1.1,
            "semi": 1.05,
            "dimple": 0.85
        }
        phi_Nu *= type_factor.get(rib_geom.rib_type, 1.0)
    
    Nu = Nu0 * phi_Nu
    
    return Nu


def f_ribbed_duct(
    Re: float,
    rib_geom: RibGeometry,
    correlation: str = "han"
) -> float:
    """
    Friction factor for ribbed duct.
    
    Args:
        Re: Reynolds number
        rib_geom: Rib geometry parameters
        correlation: Correlation type
    
    Returns:
        Darcy friction factor [-]
    """
    # Baseline smooth duct friction factor
    f0 = f_smooth_duct(Re)
    
    e_H = rib_geom.e_H
    p_e = rib_geom.p_e
    
    if correlation == "han":
        # Han et al. correlation for friction
        # f/f0 = C * (e/H)^a * (p/e)^b * Re^c
        
        if rib_geom.rib_type == "rect":
            C = 4.75
            a = 0.68
            b = -0.30
            c = 0.0
        elif rib_geom.rib_type == "tri":
            C = 3.95
            a = 0.62
            b = -0.26
            c = 0.0
        elif rib_geom.rib_type == "semi":
            C = 4.15
            a = 0.65
            b = -0.28
            c = 0.0
        else:  # dimple
            C = 2.85
            a = 0.52
            b = -0.20
            c = 0.0
        
        # Staggered increases pressure drop
        if rib_geom.staggered:
            C *= 1.25
        
        phi_f = C * (e_H**a) * (p_e**b) * (Re**(c))
        
        # Ensure minimum augmentation
        phi_f = max(1.0, phi_f)
        
    else:
        # Simplified model
        # Friction increases with rib height and decreases with pitch
        phi_f = 1.0 + 8.0 * e_H * np.exp(-p_e / 6)
        
        type_factor = {
            "rect": 1.0,
            "tri": 0.85,
            "semi": 0.90,
            "dimple": 0.70
        }
        phi_f *= type_factor.get(rib_geom.rib_type, 1.0)
    
    f = f0 * phi_f
    
    return f


def calc_JF_factor(Nu: float, f: float, Nu0: float, f0: float) -> float:
    """
    Calculate thermal-hydraulic performance factor (JF factor).
    
    JF = (Nu/Nu0) / (f/f0)^(1/3)
    
    Higher JF indicates better overall performance (heat transfer vs pressure drop).
    
    Args:
        Nu: Nusselt number with ribs
        f: Friction factor with ribs
        Nu0: Baseline Nusselt number (smooth)
        f0: Baseline friction factor (smooth)
    
    Returns:
        JF factor [-]
    """
    if f0 <= 0 or f <= 0:
        return 0.0
    
    return (Nu / Nu0) / ((f / f0)**(1/3))


def calc_convection_coefficient(Nu: float, k: float, Dh: float) -> float:
    """
    Calculate convection heat transfer coefficient.
    
    h = Nu * k / Dh
    
    Args:
        Nu: Nusselt number
        k: Thermal conductivity [W/(m·K)]
        Dh: Hydraulic diameter [m]
    
    Returns:
        Convection coefficient [W/(m²·K)]
    """
    return Nu * k / Dh


def calc_pressure_drop(
    f: float,
    L: float,
    Dh: float,
    rho: float,
    u: float,
    K_loss: float = 0.0
) -> float:
    """
    Calculate total pressure drop in channel.
    
    ΔP = f * (L/Dh) * (ρu²/2) + K_loss * (ρu²/2)
    
    Args:
        f: Friction factor
        L: Channel length [m]
        Dh: Hydraulic diameter [m]
        rho: Density [kg/m³]
        u: Mean velocity [m/s]
        K_loss: Additional loss coefficient (bends, manifolds, etc.)
    
    Returns:
        Pressure drop [Pa]
    """
    dynamic_pressure = 0.5 * rho * u**2
    
    # Frictional pressure drop
    dP_friction = f * (L / Dh) * dynamic_pressure
    
    # Minor losses
    dP_minor = K_loss * dynamic_pressure
    
    return dP_friction + dP_minor


def calc_pumping_power(dP: float, Q: float, eta: float = 0.6) -> float:
    """
    Calculate required pumping power.
    
    P_pump = ΔP * Q / η
    
    Args:
        dP: Pressure drop [Pa]
        Q: Volumetric flow rate [m³/s]
        eta: Fan/pump efficiency [-]
    
    Returns:
        Pumping power [W]
    """
    if eta <= 0:
        eta = 0.6  # Default efficiency
    
    return dP * Q / eta
