"""
Visualization utilities for simulation results.

Provides various plots:
- Temperature distributions
- Pressure drop comparisons
- Performance metrics (spider/radar charts)
- Pareto fronts
- Channel flow distribution
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from battery_aircooling.physics_rom import ROMResults, ChannelState
from battery_aircooling.physics_post import PerformanceMetrics


def setup_plot_style() -> None:
    """Configure matplotlib style for publication-quality plots."""
    plt.rcParams.update({
        'font.size': 11,
        'axes.labelsize': 12,
        'axes.titlesize': 13,
        'xtick.labelsize': 10,
        'ytick.labelsize': 10,
        'legend.fontsize': 10,
        'figure.titlesize': 14,
        'figure.dpi': 100,
        'savefig.dpi': 300,
        'savefig.bbox': 'tight',
        'lines.linewidth': 2,
        'axes.grid': True,
        'grid.alpha': 0.3,
    })


def plot_temperature_distribution(
    results: ROMResults,
    output_path: Optional[str] = None,
    show: bool = True
) -> plt.Figure:
    """
    Plot cell temperature distribution.
    
    Args:
        results: ROM simulation results
        output_path: Path to save figure
        show: Whether to display the plot
    
    Returns:
        Matplotlib figure object
    """
    setup_plot_style()
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    if results.cells is not None and len(results.cells.T_cells) > 0:
        T_cells = results.cells.T_cells - 273.15  # Convert to Celsius
        
        # Histogram
        ax1.hist(T_cells, bins=20, edgecolor='black', alpha=0.7)
        ax1.axvline(results.cells.T_max - 273.15, color='red', 
                    linestyle='--', label=f'Max: {results.cells.T_max - 273.15:.2f}°C')
        ax1.axvline(results.cells.T_mean - 273.15, color='green', 
                    linestyle='--', label=f'Mean: {results.cells.T_mean - 273.15:.2f}°C')
        ax1.axvline(results.cells.T_min - 273.15, color='blue', 
                    linestyle='--', label=f'Min: {results.cells.T_min - 273.15:.2f}°C')
        ax1.set_xlabel('Temperature [°C]')
        ax1.set_ylabel('Frequency')
        ax1.set_title('Cell Temperature Distribution')
        ax1.legend()
        
        # Box plot
        ax2.boxplot([T_cells], vert=True, labels=['Cells'])
        ax2.set_ylabel('Temperature [°C]')
        ax2.set_title('Temperature Statistics')
        ax2.grid(True, alpha=0.3)
    else:
        ax1.text(0.5, 0.5, 'No cell data available', 
                ha='center', va='center', transform=ax1.transAxes)
        ax2.text(0.5, 0.5, 'No cell data available', 
                ha='center', va='center', transform=ax2.transAxes)
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path)
    
    if show:
        plt.show()
    else:
        plt.close()
    
    return fig


def plot_channel_flow_distribution(
    channels: List[ChannelState],
    output_path: Optional[str] = None,
    show: bool = True
) -> plt.Figure:
    """
    Plot mass flow rate distribution across parallel channels.
    
    Args:
        channels: List of channel states
        output_path: Path to save figure
        show: Whether to display the plot
    
    Returns:
        Matplotlib figure object
    """
    setup_plot_style()
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    n_channels = len(channels)
    channel_ids = np.arange(1, n_channels + 1)
    
    mdots = np.array([ch.mdot for ch in channels]) * 1000  # kg/s -> g/s
    pressures = np.array([ch.pressure_drop for ch in channels])
    
    # Mass flow distribution
    ax1.bar(channel_ids, mdots, edgecolor='black', alpha=0.7)
    ax1.axhline(np.mean(mdots), color='red', linestyle='--', 
                label=f'Mean: {np.mean(mdots):.3f} g/s')
    ax1.set_xlabel('Channel Number')
    ax1.set_ylabel('Mass Flow Rate [g/s]')
    ax1.set_title('Flow Distribution Across Channels')
    ax1.legend()
    ax1.set_xticks(channel_ids)
    
    # Pressure drop distribution
    ax2.bar(channel_ids, pressures, edgecolor='black', alpha=0.7, color='orange')
    ax2.axhline(np.mean(pressures), color='red', linestyle='--', 
                label=f'Mean: {np.mean(pressures):.1f} Pa')
    ax2.set_xlabel('Channel Number')
    ax2.set_ylabel('Pressure Drop [Pa]')
    ax2.set_title('Pressure Drop Across Channels')
    ax2.legend()
    ax2.set_xticks(channel_ids)
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path)
    
    if show:
        plt.show()
    else:
        plt.close()
    
    return fig


def plot_sweep_results(
    param_values: List[float],
    metrics_list: List[PerformanceMetrics],
    param_name: str,
    param_unit: str = "",
    output_path: Optional[str] = None,
    show: bool = True
) -> plt.Figure:
    """
    Plot performance metrics vs. swept parameter.
    
    Args:
        param_values: Parameter values
        metrics_list: List of performance metrics
        param_name: Parameter name for x-axis
        param_unit: Parameter unit
        output_path: Path to save figure
        show: Whether to display the plot
    
    Returns:
        Matplotlib figure object
    """
    setup_plot_style()
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Extract metrics
    T_max = np.array([m.T_max - 273.15 for m in metrics_list])
    dT_pack = np.array([m.dT_pack for m in metrics_list])
    Delta_P = np.array([m.Delta_P for m in metrics_list])
    P_pump = np.array([m.P_pump for m in metrics_list])
    JF = np.array([m.JF_factor for m in metrics_list])
    
    xlabel = f"{param_name} [{param_unit}]" if param_unit else param_name
    
    # Maximum temperature
    axes[0, 0].plot(param_values, T_max, 'o-', linewidth=2, markersize=8)
    axes[0, 0].set_xlabel(xlabel)
    axes[0, 0].set_ylabel('Max Temperature [°C]')
    axes[0, 0].set_title('Maximum Cell Temperature')
    axes[0, 0].grid(True, alpha=0.3)
    
    # Temperature spread
    axes[0, 1].plot(param_values, dT_pack, 's-', linewidth=2, markersize=8, color='orange')
    axes[0, 1].set_xlabel(xlabel)
    axes[0, 1].set_ylabel('Temperature Spread [K]')
    axes[0, 1].set_title('Temperature Uniformity (ΔT)')
    axes[0, 1].grid(True, alpha=0.3)
    
    # Pressure drop and pumping power
    ax3 = axes[1, 0]
    ax3_twin = ax3.twinx()
    
    line1 = ax3.plot(param_values, Delta_P, '^-', linewidth=2, markersize=8, 
                     color='green', label='Pressure Drop')
    ax3.set_xlabel(xlabel)
    ax3.set_ylabel('Pressure Drop [Pa]', color='green')
    ax3.tick_params(axis='y', labelcolor='green')
    
    line2 = ax3_twin.plot(param_values, P_pump, 'v-', linewidth=2, markersize=8, 
                          color='red', label='Pumping Power')
    ax3_twin.set_ylabel('Pumping Power [W]', color='red')
    ax3_twin.tick_params(axis='y', labelcolor='red')
    
    ax3.set_title('Hydraulic Performance')
    ax3.grid(True, alpha=0.3)
    
    # JF factor
    axes[1, 1].plot(param_values, JF, 'd-', linewidth=2, markersize=8, color='purple')
    axes[1, 1].set_xlabel(xlabel)
    axes[1, 1].set_ylabel('JF Factor [-]')
    axes[1, 1].set_title('Thermal-Hydraulic Performance (JF Factor)')
    axes[1, 1].grid(True, alpha=0.3)
    axes[1, 1].axhline(1.0, color='black', linestyle='--', alpha=0.5, label='Baseline')
    axes[1, 1].legend()
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path)
    
    if show:
        plt.show()
    else:
        plt.close()
    
    return fig


def plot_pareto_front(
    metrics_list: List[PerformanceMetrics],
    pareto_indices: List[int],
    config_names: Optional[List[str]] = None,
    objective1: str = "T_max",
    objective2: str = "P_pump",
    output_path: Optional[str] = None,
    show: bool = True
) -> plt.Figure:
    """
    Plot Pareto front for two objectives.
    
    Args:
        metrics_list: List of performance metrics
        pareto_indices: Indices of Pareto-optimal configurations
        config_names: Configuration names
        objective1: First objective (x-axis)
        objective2: Second objective (y-axis)
        output_path: Path to save figure
        show: Whether to display the plot
    
    Returns:
        Matplotlib figure object
    """
    setup_plot_style()
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Extract objective values
    obj1_values = np.array([getattr(m, objective1) for m in metrics_list])
    obj2_values = np.array([getattr(m, objective2) for m in metrics_list])
    
    # Convert temperature to Celsius if needed
    if objective1 == "T_max":
        obj1_values -= 273.15
    if objective2 == "T_max":
        obj2_values -= 273.15
    
    # Plot all points
    ax.scatter(obj1_values, obj2_values, s=100, alpha=0.5, label='All Configurations')
    
    # Highlight Pareto front
    pareto_obj1 = obj1_values[pareto_indices]
    pareto_obj2 = obj2_values[pareto_indices]
    
    # Sort for line plot
    sort_idx = np.argsort(pareto_obj1)
    pareto_obj1 = pareto_obj1[sort_idx]
    pareto_obj2 = pareto_obj2[sort_idx]
    
    ax.plot(pareto_obj1, pareto_obj2, 'r-', linewidth=2, alpha=0.7)
    ax.scatter(pareto_obj1, pareto_obj2, s=150, c='red', marker='*', 
               edgecolors='black', linewidth=1.5, label='Pareto Front', zorder=5)
    
    # Labels
    obj1_label = objective1.replace('_', ' ').title()
    obj2_label = objective2.replace('_', ' ').title()
    
    if objective1 == "T_max":
        obj1_label += " [°C]"
    elif objective1 == "P_pump":
        obj1_label += " [W]"
    elif objective1 == "Delta_P":
        obj1_label += " [Pa]"
    
    if objective2 == "T_max":
        obj2_label += " [°C]"
    elif objective2 == "P_pump":
        obj2_label += " [W]"
    elif objective2 == "Delta_P":
        obj2_label += " [Pa]"
    
    ax.set_xlabel(obj1_label)
    ax.set_ylabel(obj2_label)
    ax.set_title(f'Pareto Front: {obj1_label} vs {obj2_label}')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path)
    
    if show:
        plt.show()
    else:
        plt.close()
    
    return fig


def plot_spider_chart(
    metrics_list: List[PerformanceMetrics],
    config_names: List[str],
    output_path: Optional[str] = None,
    show: bool = True
) -> plt.Figure:
    """
    Create spider/radar chart comparing multiple configurations.
    
    Args:
        metrics_list: List of performance metrics
        config_names: Configuration names
        output_path: Path to save figure
        show: Whether to display the plot
    
    Returns:
        Matplotlib figure object
    """
    setup_plot_style()
    
    # Metrics to compare (normalized)
    categories = ['Low T_max', 'Uniformity', 'Low ΔP', 'Low Power', 'High JF']
    n_cats = len(categories)
    
    # Extract and normalize metrics (0 to 1, higher is better)
    data = []
    for metrics in metrics_list:
        T_max_norm = 1.0 / (1.0 + metrics.T_max - 273.15)  # Lower is better
        uniformity_norm = metrics.uniformity_index  # Higher is better
        dP_norm = 1.0 / (1.0 + metrics.Delta_P / 100)  # Lower is better
        power_norm = 1.0 / (1.0 + metrics.P_pump)  # Lower is better
        JF_norm = min(1.0, metrics.JF_factor)  # Higher is better (cap at 1)
        
        data.append([T_max_norm, uniformity_norm, dP_norm, power_norm, JF_norm])
    
    # Radar chart
    angles = np.linspace(0, 2 * np.pi, n_cats, endpoint=False).tolist()
    angles += angles[:1]  # Close the plot
    
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
    
    colors = plt.cm.tab10(np.linspace(0, 1, len(metrics_list)))
    
    for i, (values, name) in enumerate(zip(data, config_names)):
        values += values[:1]  # Close the plot
        ax.plot(angles, values, 'o-', linewidth=2, label=name, color=colors[i])
        ax.fill(angles, values, alpha=0.15, color=colors[i])
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(['0.2', '0.4', '0.6', '0.8', '1.0'])
    ax.set_title('Configuration Comparison (Spider Chart)', y=1.08, fontsize=14)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path)
    
    if show:
        plt.show()
    else:
        plt.close()
    
    return fig


def plot_2d_heatmap(
    param1_values: List[float],
    param2_values: List[float],
    metric_grid: np.ndarray,
    param1_name: str,
    param2_name: str,
    metric_name: str,
    output_path: Optional[str] = None,
    show: bool = True
) -> plt.Figure:
    """
    Plot 2D heatmap for parametric study with two variables.
    
    Args:
        param1_values: First parameter values
        param2_values: Second parameter values
        metric_grid: 2D array of metric values
        param1_name: First parameter name
        param2_name: Second parameter name
        metric_name: Metric name
        output_path: Path to save figure
        show: Whether to display the plot
    
    Returns:
        Matplotlib figure object
    """
    setup_plot_style()
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    im = ax.contourf(param1_values, param2_values, metric_grid, levels=20, cmap='viridis')
    
    # Add contour lines
    contours = ax.contour(param1_values, param2_values, metric_grid, 
                          levels=10, colors='white', alpha=0.4, linewidths=0.5)
    ax.clabel(contours, inline=True, fontsize=8)
    
    ax.set_xlabel(param1_name)
    ax.set_ylabel(param2_name)
    ax.set_title(f'{metric_name} - 2D Parameter Study')
    
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label(metric_name)
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path)
    
    if show:
        plt.show()
    else:
        plt.close()
    
    return fig


def generate_all_plots(
    results: ROMResults,
    metrics: PerformanceMetrics,
    output_dir: str = "figs"
) -> Dict[str, str]:
    """
    Generate all standard plots for a simulation.
    
    Args:
        results: ROM simulation results
        metrics: Performance metrics
        output_dir: Output directory for figures
    
    Returns:
        Dictionary with paths to generated figures
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    generated_files = {}
    
    # Temperature distribution
    temp_dist_file = str(output_path / "temperature_distribution.png")
    plot_temperature_distribution(results, output_path=temp_dist_file, show=False)
    generated_files["temperature_distribution"] = temp_dist_file
    
    # Channel flow distribution
    if results.channels:
        flow_dist_file = str(output_path / "channel_flow_distribution.png")
        plot_channel_flow_distribution(results.channels, output_path=flow_dist_file, show=False)
        generated_files["flow_distribution"] = flow_dist_file
    
    return generated_files
