"""
Reduced-Order Model (ROM) for battery pack thermal-hydraulic simulation.

Implements 1D/quasi-2D network model combining:
- Flow distribution in parallel channels
- Pressure drop calculation with rib effects
- Conjugate heat transfer (cells-channel walls)
- Thermal resistance networks
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

from battery_aircooling.correlations import (
    calc_air_properties,
    calc_Re,
    calc_hydraulic_diameter,
    Nu_smooth_duct,
    f_smooth_duct,
    Nu_ribbed_duct,
    f_ribbed_duct,
    RibGeometry,
    FlowProperties,
    calc_convection_coefficient,
    calc_pressure_drop,
    calc_JF_factor,
)
from battery_aircooling.geometry import calculate_channel_volume, calculate_wetted_area
from battery_aircooling.config_schema import SimulationConfig


@dataclass
class ChannelState:
    """State variables for a single cooling channel."""
    
    mdot: float = 0.0  # Mass flow rate [kg/s]
    velocity: float = 0.0  # Mean velocity [m/s]
    Re: float = 0.0  # Reynolds number
    pressure_drop: float = 0.0  # Pressure drop [Pa]
    
    T_fluid_in: float = 300.0  # Inlet temperature [K]
    T_fluid_out: float = 300.0  # Outlet temperature [K]
    T_fluid_mean: float = 300.0  # Mean bulk temperature [K]
    T_wall_mean: float = 300.0  # Mean wall temperature [K]
    
    Nu: float = 0.0  # Nusselt number
    h: float = 0.0  # Convection coefficient [W/(m²·K)]
    f: float = 0.0  # Friction factor
    
    Q_total: float = 0.0  # Total heat removed [W]


@dataclass
class CellState:
    """State variables for battery cells."""
    
    T_cells: np.ndarray = field(default_factory=lambda: np.array([]))  # Cell temperatures [K]
    T_max: float = 300.0
    T_min: float = 300.0
    T_mean: float = 300.0
    dT: float = 0.0  # Temperature spread
    Q_gen_total: float = 0.0  # Total heat generation [W]


@dataclass
class ROMResults:
    """Complete ROM simulation results."""
    
    channels: List[ChannelState] = field(default_factory=list)
    cells: Optional[CellState] = None
    
    total_pressure_drop: float = 0.0
    total_heat_removed: float = 0.0
    pumping_power: float = 0.0
    
    JF_factor: float = 0.0
    
    converged: bool = False
    iterations: int = 0


class ROMSolver:
    """
    Reduced-Order Model solver for battery air cooling.
    
    Solves coupled thermal-hydraulic problem using:
    1. Flow distribution in parallel channels (pressure balance)
    2. Heat transfer via correlations (Nu, h)
    3. Thermal resistance network (cell-to-fluid)
    """
    
    def __init__(self, config: SimulationConfig):
        """
        Initialize ROM solver.
        
        Args:
            config: Simulation configuration
        """
        self.config = config
        
        # Extract key parameters
        self.air_props = self._initialize_air_properties()
        self.Dh = calc_hydraulic_diameter(config.channel.width, config.channel.height)
        self.A_channel = config.channel.width * config.channel.height
        
        # Rib geometry (non-dimensional)
        self.rib_geom = RibGeometry(
            e_H=config.ribs.height / config.channel.height,
            p_e=config.ribs.pitch / config.ribs.height,
            t_e=config.ribs.thickness / config.ribs.height,
            rib_type=config.ribs.type,
            staggered=config.ribs.staggered,
        )
        
        # Initialize results structure
        self.results = ROMResults()
    
    def _initialize_air_properties(self) -> Dict[str, float]:
        """Calculate or use provided air properties."""
        config = self.config
        
        # Calculate properties from T and P
        props = calc_air_properties(config.air.Tin, config.air.Pin)
        
        # Override with user-provided values if available
        if config.air.mu is not None:
            props["mu"] = config.air.mu
        if config.air.rho is not None:
            props["rho"] = config.air.rho
        if config.air.cp is not None:
            props["cp"] = config.air.cp
        if config.air.k is not None:
            props["k"] = config.air.k
        if "Pr" not in props:
            props["Pr"] = props["mu"] * props["cp"] / props["k"]
        
        return props
    
    def solve(self, max_iter: int = 100, tol: float = 1e-4) -> ROMResults:
        """
        Solve coupled thermal-hydraulic problem.
        
        Args:
            max_iter: Maximum iterations
            tol: Convergence tolerance (relative change)
        
        Returns:
            ROMResults object with solution
        """
        config = self.config
        n_channels = config.channel.n_parallel
        
        # Total mass flow rate
        if config.air.mdot is not None:
            mdot_total = config.air.mdot
        else:
            # Estimate from Reynolds number
            u_target = config.air.Re * self.air_props["mu"] / (self.air_props["rho"] * self.Dh)
            mdot_total = self.air_props["rho"] * u_target * self.A_channel * n_channels
        
        # Initialize channel states
        channels = [ChannelState() for _ in range(n_channels)]
        
        # Initial guess: equal distribution
        mdot_per_channel = mdot_total / n_channels
        for ch in channels:
            ch.mdot = mdot_per_channel
            ch.T_fluid_in = config.air.Tin
        
        # Iterative solution
        for iteration in range(max_iter):
            # Store previous values for convergence check
            mdot_prev = np.array([ch.mdot for ch in channels])
            
            # 1. Calculate pressure drop in each channel
            for ch in channels:
                ch.velocity = ch.mdot / (self.air_props["rho"] * self.A_channel)
                ch.Re = calc_Re(ch.velocity, self.Dh, self.air_props["rho"], self.air_props["mu"])
                
                # Friction factor with ribs
                ch.f = f_ribbed_duct(ch.Re, self.rib_geom, correlation="han")
                
                # Pressure drop
                ch.pressure_drop = calc_pressure_drop(
                    ch.f,
                    config.channel.length,
                    self.Dh,
                    self.air_props["rho"],
                    ch.velocity,
                    K_loss=config.channel.manifold_loss_coeff
                )
            
            # 2. Redistribute flow to balance pressures
            # Use average pressure as target
            p_avg = np.mean([ch.pressure_drop for ch in channels])
            
            for ch in channels:
                # Adjust flow rate based on pressure deviation
                # Simple proportional correction
                dp_error = ch.pressure_drop - p_avg
                correction_factor = 1.0 - 0.1 * dp_error / (p_avg + 1e-6)
                ch.mdot *= max(0.1, min(2.0, correction_factor))
            
            # Enforce total mass conservation
            mdot_sum = sum(ch.mdot for ch in channels)
            for ch in channels:
                ch.mdot *= mdot_total / mdot_sum
            
            # 3. Calculate heat transfer in each channel
            for i, ch in enumerate(channels):
                # Recalculate flow properties
                ch.velocity = ch.mdot / (self.air_props["rho"] * self.A_channel)
                ch.Re = calc_Re(ch.velocity, self.Dh, self.air_props["rho"], self.air_props["mu"])
                
                # Nusselt number with ribs
                ch.Nu = Nu_ribbed_duct(
                    ch.Re,
                    self.air_props["Pr"],
                    self.rib_geom,
                    correlation="han"
                )
                
                # Convection coefficient
                ch.h = calc_convection_coefficient(ch.Nu, self.air_props["k"], self.Dh)
                
                # Heat transfer calculation
                # Simplified: assume heat from cells flows to channel
                # Number of cells adjacent to this channel
                n_cells_per_channel = config.cells.n_rows * config.cells.n_cols // n_channels
                Q_gen_channel = n_cells_per_channel * config.cells.q_gen
                
                # Thermal resistance network
                R_total = self._calculate_thermal_resistance(ch.h)
                
                # Estimate mean wall and fluid temperatures
                # Using NTU-effectiveness method (simplified)
                A_heat = calculate_wetted_area(
                    config.channel.length,
                    config.channel.width,
                    config.channel.height,
                    config.ribs.height,
                    config.ribs.thickness,
                    config.ribs.pitch,
                    config.ribs.type,
                )
                
                # Effectiveness
                C_fluid = ch.mdot * self.air_props["cp"]
                NTU = ch.h * A_heat / (C_fluid + 1e-9)
                effectiveness = 1 - np.exp(-NTU)
                
                # Outlet temperature
                if C_fluid > 1e-9:
                    dT_fluid = Q_gen_channel / C_fluid
                else:
                    dT_fluid = 0.0
                
                ch.T_fluid_out = ch.T_fluid_in + dT_fluid
                ch.T_fluid_mean = (ch.T_fluid_in + ch.T_fluid_out) / 2
                
                # Wall temperature (from heat flux)
                q_flux = Q_gen_channel / (A_heat + 1e-9)
                ch.T_wall_mean = ch.T_fluid_mean + q_flux / (ch.h + 1e-9)
                
                ch.Q_total = Q_gen_channel
            
            # 4. Check convergence
            mdot_curr = np.array([ch.mdot for ch in channels])
            rel_change = np.max(np.abs(mdot_curr - mdot_prev) / (mdot_prev + 1e-9))
            
            if rel_change < tol:
                self.results.converged = True
                self.results.iterations = iteration + 1
                break
        
        # 5. Calculate cell temperatures
        cell_state = self._calculate_cell_temperatures(channels)
        
        # 6. Assemble results
        self.results.channels = channels
        self.results.cells = cell_state
        self.results.total_pressure_drop = np.mean([ch.pressure_drop for ch in channels])
        self.results.total_heat_removed = sum(ch.Q_total for ch in channels)
        
        # Pumping power
        Q_vol_total = mdot_total / self.air_props["rho"]
        self.results.pumping_power = self.results.total_pressure_drop * Q_vol_total / config.metrics.eta_fan
        
        # JF factor (thermal-hydraulic performance)
        Nu0 = Nu_smooth_duct(channels[0].Re, self.air_props["Pr"])
        f0 = f_smooth_duct(channels[0].Re)
        self.results.JF_factor = calc_JF_factor(channels[0].Nu, channels[0].f, Nu0, f0)
        
        return self.results
    
    def _calculate_thermal_resistance(self, h_conv: float) -> float:
        """
        Calculate total thermal resistance from cell center to fluid.
        
        Args:
            h_conv: Convection coefficient [W/(m²·K)]
        
        Returns:
            Total thermal resistance [K/W]
        """
        config = self.config
        
        # Cell internal conduction resistance
        L_cell = config.cells.size.lx
        A_cell = config.cells.size.ly * config.cells.size.lz
        R_cell = L_cell / (2 * config.cells.k_cell * A_cell)
        
        # Gap/pad conduction resistance
        L_gap = config.cells.gap_to_channel
        R_gap = L_gap / (config.cells.k_gap * A_cell)
        
        # Convection resistance
        A_conv = config.channel.length * config.channel.width
        R_conv = 1 / (h_conv * A_conv)
        
        # Series resistances
        R_total = R_cell + R_gap + R_conv
        
        return R_total
    
    def _calculate_cell_temperatures(self, channels: List[ChannelState]) -> CellState:
        """
        Calculate battery cell temperatures.
        
        Args:
            channels: List of channel states
        
        Returns:
            CellState with temperature distribution
        """
        config = self.config
        n_cells_total = config.cells.n_rows * config.cells.n_cols
        n_channels = len(channels)
        
        # Simplified: assign cells to nearest channel
        T_cells = np.zeros(n_cells_total)
        
        cells_per_channel = n_cells_total // n_channels
        
        for i in range(n_channels):
            ch = channels[i]
            
            # Calculate cell temperature from wall temperature and thermal resistance
            R_cell_to_wall = self._calculate_thermal_resistance(ch.h)
            
            # Cell temperature
            Q_per_cell = config.cells.q_gen
            dT_cell_wall = Q_per_cell * R_cell_to_wall
            
            T_cell = ch.T_wall_mean + dT_cell_wall
            
            # Assign to cells in this channel's zone
            idx_start = i * cells_per_channel
            idx_end = min((i + 1) * cells_per_channel, n_cells_total)
            T_cells[idx_start:idx_end] = T_cell
        
        # Create cell state
        cell_state = CellState(
            T_cells=T_cells,
            T_max=np.max(T_cells),
            T_min=np.min(T_cells),
            T_mean=np.mean(T_cells),
            dT=np.max(T_cells) - np.min(T_cells),
            Q_gen_total=n_cells_total * config.cells.q_gen,
        )
        
        return cell_state
    
    def sweep_parameter(
        self,
        param_path: str,
        values: List[float],
        base_config: Optional[SimulationConfig] = None
    ) -> List[ROMResults]:
        """
        Perform parameter sweep.
        
        Args:
            param_path: Parameter path (e.g., 'ribs.height')
            values: List of parameter values
            base_config: Base configuration (uses self.config if None)
        
        Returns:
            List of ROMResults for each parameter value
        """
        if base_config is None:
            base_config = self.config
        
        results_list = []
        
        for value in values:
            # Create new config with modified parameter
            config_copy = base_config.model_copy(deep=True)
            config_copy.set_parameter_by_path(param_path, value)
            
            # Create new solver with modified config
            solver = ROMSolver(config_copy)
            
            # Solve
            result = solver.solve()
            results_list.append(result)
        
        return results_list
