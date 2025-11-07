"""
Post-processing and performance metrics calculation.

Calculates key performance indicators including:
- Temperature metrics (max, spread, uniformity)
- Pressure drop and pumping power
- Thermal-hydraulic efficiency (JF factor)
- Multi-objective scores
"""

import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass

from battery_aircooling.physics_rom import ROMResults
from battery_aircooling.config_schema import MetricsConfig


@dataclass
class PerformanceMetrics:
    """Complete set of performance metrics."""
    
    # Temperature metrics
    T_max: float  # Maximum cell temperature [K]
    T_min: float  # Minimum cell temperature [K]
    T_mean: float  # Mean cell temperature [K]
    dT_pack: float  # Temperature spread (max - min) [K]
    
    # Uniformity
    uniformity_index: float  # 1 - σ_T / T_mean
    T_std: float  # Standard deviation [K]
    
    # Pressure and power
    Delta_P: float  # Total pressure drop [Pa]
    P_pump: float  # Pumping power [W]
    
    # Thermal efficiency
    Q_removed: float  # Total heat removed [W]
    Q_generated: float  # Total heat generated [W]
    thermal_efficiency: float  # Q_removed / Q_generated
    
    # Thermal-hydraulic performance
    JF_factor: float  # (Nu/Nu0) / (f/f0)^(1/3)
    
    # Multi-objective score
    objective_score: float  # Weighted combination
    
    # Constraint violations
    T_max_violation: float  # How much T_max exceeds limit [K]
    
    # Metadata
    converged: bool
    iterations: int


def calculate_metrics(
    results: ROMResults,
    metrics_config: MetricsConfig,
    Q_gen_total: float = 0.0
) -> PerformanceMetrics:
    """
    Calculate all performance metrics from ROM results.
    
    Args:
        results: ROM simulation results
        metrics_config: Metrics configuration
        Q_gen_total: Total heat generation [W] (optional)
    
    Returns:
        PerformanceMetrics object
    """
    # Temperature metrics
    if results.cells is not None:
        T_max = results.cells.T_max
        T_min = results.cells.T_min
        T_mean = results.cells.T_mean
        dT_pack = results.cells.dT
        T_std = np.std(results.cells.T_cells)
        
        if Q_gen_total == 0.0:
            Q_gen_total = results.cells.Q_gen_total
    else:
        # Fallback if cells not available
        T_max = max(ch.T_wall_mean for ch in results.channels) if results.channels else 300.0
        T_min = min(ch.T_wall_mean for ch in results.channels) if results.channels else 300.0
        T_mean = np.mean([ch.T_wall_mean for ch in results.channels]) if results.channels else 300.0
        dT_pack = T_max - T_min
        T_std = np.std([ch.T_wall_mean for ch in results.channels]) if results.channels else 0.0
    
    # Uniformity index: higher is better (1 = perfectly uniform)
    if T_mean > 0:
        uniformity_index = 1.0 - T_std / T_mean
    else:
        uniformity_index = 0.0
    
    # Pressure and power
    Delta_P = results.total_pressure_drop
    P_pump = results.pumping_power
    
    # Thermal efficiency
    Q_removed = results.total_heat_removed
    if Q_gen_total > 0:
        thermal_efficiency = Q_removed / Q_gen_total
    else:
        thermal_efficiency = 1.0
    
    # JF factor
    JF_factor = results.JF_factor
    
    # Temperature violation
    T_limit = metrics_config.T_limit
    T_max_violation = max(0.0, T_max - T_limit)
    
    # Multi-objective score (lower is better)
    weights = metrics_config.weights
    
    w_Tmax = weights.get("Tmax", 3.0)
    w_dT = weights.get("dT_pack", 1.0)
    w_Ppump = weights.get("Ppump", 1.0)
    
    # Normalize terms
    T_excess = max(0.0, T_max - T_limit)
    
    objective_score = (
        w_Tmax * T_excess +
        w_dT * dT_pack +
        w_Ppump * P_pump / 10.0  # Scale pumping power
    )
    
    # Create metrics object
    metrics = PerformanceMetrics(
        T_max=T_max,
        T_min=T_min,
        T_mean=T_mean,
        dT_pack=dT_pack,
        uniformity_index=uniformity_index,
        T_std=T_std,
        Delta_P=Delta_P,
        P_pump=P_pump,
        Q_removed=Q_removed,
        Q_generated=Q_gen_total,
        thermal_efficiency=thermal_efficiency,
        JF_factor=JF_factor,
        objective_score=objective_score,
        T_max_violation=T_max_violation,
        converged=results.converged,
        iterations=results.iterations,
    )
    
    return metrics


def compare_configurations(
    metrics_list: List[PerformanceMetrics],
    config_names: Optional[List[str]] = None
) -> Dict:
    """
    Compare multiple configurations.
    
    Args:
        metrics_list: List of performance metrics for different configs
        config_names: Optional names for each configuration
    
    Returns:
        Dictionary with comparison results
    """
    if not metrics_list:
        return {}
    
    if config_names is None:
        config_names = [f"Config_{i+1}" for i in range(len(metrics_list))]
    
    # Extract key metrics
    T_max_list = [m.T_max for m in metrics_list]
    dT_pack_list = [m.dT_pack for m in metrics_list]
    P_pump_list = [m.P_pump for m in metrics_list]
    JF_list = [m.JF_factor for m in metrics_list]
    obj_list = [m.objective_score for m in metrics_list]
    
    # Find best for each criterion
    idx_best_Tmax = np.argmin(T_max_list)
    idx_best_uniformity = np.argmin(dT_pack_list)
    idx_best_power = np.argmin(P_pump_list)
    idx_best_JF = np.argmax(JF_list)
    idx_best_overall = np.argmin(obj_list)
    
    comparison = {
        "config_names": config_names,
        "T_max": T_max_list,
        "dT_pack": dT_pack_list,
        "P_pump": P_pump_list,
        "JF_factor": JF_list,
        "objective_score": obj_list,
        "best": {
            "lowest_Tmax": config_names[idx_best_Tmax],
            "best_uniformity": config_names[idx_best_uniformity],
            "lowest_power": config_names[idx_best_power],
            "highest_JF": config_names[idx_best_JF],
            "best_overall": config_names[idx_best_overall],
        },
        "rankings": {
            "by_Tmax": sorted(enumerate(T_max_list), key=lambda x: x[1]),
            "by_uniformity": sorted(enumerate(dT_pack_list), key=lambda x: x[1]),
            "by_power": sorted(enumerate(P_pump_list), key=lambda x: x[1]),
            "by_JF": sorted(enumerate(JF_list), key=lambda x: -x[1]),
            "by_overall": sorted(enumerate(obj_list), key=lambda x: x[1]),
        }
    }
    
    return comparison


def calculate_pareto_front(
    metrics_list: List[PerformanceMetrics],
    objective1: str = "T_max",
    objective2: str = "P_pump"
) -> List[int]:
    """
    Find Pareto-optimal configurations for two objectives.
    
    Args:
        metrics_list: List of performance metrics
        objective1: First objective (minimize)
        objective2: Second objective (minimize)
    
    Returns:
        Indices of Pareto-optimal configurations
    """
    n = len(metrics_list)
    
    # Extract objective values
    obj1_values = np.array([getattr(m, objective1) for m in metrics_list])
    obj2_values = np.array([getattr(m, objective2) for m in metrics_list])
    
    # Find Pareto front
    pareto_indices = []
    
    for i in range(n):
        is_dominated = False
        
        for j in range(n):
            if i == j:
                continue
            
            # Check if j dominates i (better in both objectives)
            if obj1_values[j] <= obj1_values[i] and obj2_values[j] <= obj2_values[i]:
                if obj1_values[j] < obj1_values[i] or obj2_values[j] < obj2_values[i]:
                    is_dominated = True
                    break
        
        if not is_dominated:
            pareto_indices.append(i)
    
    return pareto_indices


def summarize_results(metrics: PerformanceMetrics) -> str:
    """
    Generate text summary of results.
    
    Args:
        metrics: Performance metrics
    
    Returns:
        Formatted summary string
    """
    summary = f"""
Performance Summary
==================

Temperature:
  Max:        {metrics.T_max:.2f} K ({metrics.T_max - 273.15:.2f} °C)
  Min:        {metrics.T_min:.2f} K ({metrics.T_min - 273.15:.2f} °C)
  Mean:       {metrics.T_mean:.2f} K ({metrics.T_mean - 273.15:.2f} °C)
  Spread:     {metrics.dT_pack:.2f} K
  Std Dev:    {metrics.T_std:.2f} K
  Uniformity: {metrics.uniformity_index:.4f}

Pressure & Power:
  ΔP:         {metrics.Delta_P:.2f} Pa
  P_pump:     {metrics.P_pump:.3f} W

Heat Transfer:
  Q_removed:  {metrics.Q_removed:.2f} W
  Q_gen:      {metrics.Q_generated:.2f} W
  Efficiency: {metrics.thermal_efficiency:.4f}

Performance:
  JF Factor:  {metrics.JF_factor:.4f}
  Objective:  {metrics.objective_score:.3f}

Convergence:
  Converged:  {metrics.converged}
  Iterations: {metrics.iterations}
"""
    
    if metrics.T_max_violation > 0:
        summary += f"\n⚠️  WARNING: T_max exceeds limit by {metrics.T_max_violation:.2f} K\n"
    
    return summary


def metrics_to_dict(metrics: PerformanceMetrics) -> Dict:
    """
    Convert metrics to dictionary for export.
    
    Args:
        metrics: Performance metrics
    
    Returns:
        Dictionary with all metrics
    """
    return {
        "T_max_K": metrics.T_max,
        "T_max_C": metrics.T_max - 273.15,
        "T_min_K": metrics.T_min,
        "T_min_C": metrics.T_min - 273.15,
        "T_mean_K": metrics.T_mean,
        "T_mean_C": metrics.T_mean - 273.15,
        "dT_pack_K": metrics.dT_pack,
        "T_std_K": metrics.T_std,
        "uniformity_index": metrics.uniformity_index,
        "Delta_P_Pa": metrics.Delta_P,
        "P_pump_W": metrics.P_pump,
        "Q_removed_W": metrics.Q_removed,
        "Q_generated_W": metrics.Q_generated,
        "thermal_efficiency": metrics.thermal_efficiency,
        "JF_factor": metrics.JF_factor,
        "objective_score": metrics.objective_score,
        "T_max_violation_K": metrics.T_max_violation,
        "converged": metrics.converged,
        "iterations": metrics.iterations,
    }


def calculate_sensitivity(
    base_metrics: PerformanceMetrics,
    varied_metrics: PerformanceMetrics,
    param_change: float
) -> Dict[str, float]:
    """
    Calculate sensitivity (normalized derivatives).
    
    Args:
        base_metrics: Baseline metrics
        varied_metrics: Metrics after parameter change
        param_change: Relative parameter change (e.g., 0.1 for 10% increase)
    
    Returns:
        Dictionary of sensitivities for each metric
    """
    if param_change == 0:
        return {}
    
    sensitivities = {}
    
    # Temperature sensitivity
    sensitivities["T_max"] = (varied_metrics.T_max - base_metrics.T_max) / param_change
    sensitivities["dT_pack"] = (varied_metrics.dT_pack - base_metrics.dT_pack) / param_change
    sensitivities["uniformity"] = (varied_metrics.uniformity_index - base_metrics.uniformity_index) / param_change
    
    # Pressure sensitivity
    sensitivities["Delta_P"] = (varied_metrics.Delta_P - base_metrics.Delta_P) / param_change
    sensitivities["P_pump"] = (varied_metrics.P_pump - base_metrics.P_pump) / param_change
    
    # Performance sensitivity
    sensitivities["JF_factor"] = (varied_metrics.JF_factor - base_metrics.JF_factor) / param_change
    sensitivities["objective"] = (varied_metrics.objective_score - base_metrics.objective_score) / param_change
    
    return sensitivities
