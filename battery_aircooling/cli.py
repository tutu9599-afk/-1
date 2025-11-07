"""
Command-line interface for battery air cooling simulator.

Provides easy-to-use CLI for running simulations, parameter sweeps,
and generating reports.
"""

import click
import sys
from pathlib import Path
import pandas as pd
import json
from tqdm import tqdm
from typing import Optional

from battery_aircooling.config_schema import SimulationConfig
from battery_aircooling.physics_rom import ROMSolver
from battery_aircooling.physics_post import (
    calculate_metrics,
    metrics_to_dict,
    summarize_results,
    compare_configurations,
    calculate_pareto_front,
)
from battery_aircooling.visualize import (
    plot_sweep_results,
    plot_pareto_front,
    plot_spider_chart,
    generate_all_plots,
)
from battery_aircooling.meshing import create_mesh


@click.group()
@click.version_option(version="0.1.0")
def main() -> None:
    """
    Battery Air Cooling Simulator
    
    A comprehensive tool for simulating and optimizing air-cooled battery pack
    thermal management with parametric rib channel designs.
    """
    pass


@main.command()
@click.option(
    '--config', '-c',
    type=click.Path(exists=True),
    required=True,
    help='Path to YAML configuration file'
)
@click.option(
    '--mode', '-m',
    type=click.Choice(['ROM', 'CFD'], case_sensitive=False),
    default='ROM',
    help='Simulation mode'
)
@click.option(
    '--output', '-o',
    type=click.Path(),
    default='results',
    help='Output directory'
)
@click.option(
    '--plot/--no-plot',
    default=True,
    help='Generate plots'
)
@click.option(
    '--report/--no-report',
    default=True,
    help='Generate text report'
)
@click.option(
    '--export-case',
    is_flag=True,
    help='Export CFD case files (CFD mode only)'
)
def run(
    config: str,
    mode: str,
    output: str,
    plot: bool,
    report: bool,
    export_case: bool
) -> None:
    """
    Run a single simulation with the given configuration.
    
    Example:
        battery-aircooling run --config examples/study_rib_sweep.yaml --mode ROM
    """
    click.echo(f"🔧 Loading configuration from: {config}")
    
    try:
        # Load configuration
        sim_config = SimulationConfig.from_yaml(config)
        sim_config.solver.mode = mode
        sim_config.output_dir = output
        
        # Create output directory
        output_path = Path(output)
        output_path.mkdir(parents=True, exist_ok=True)
        
        click.echo(f"📊 Running {mode} simulation...")
        
        if mode.upper() == 'ROM':
            # Run ROM simulation
            solver = ROMSolver(sim_config)
            
            with click.progressbar(length=100, label='Solving') as bar:
                results = solver.solve()
                bar.update(100)
            
            # Calculate metrics
            metrics = calculate_metrics(
                results,
                sim_config.metrics,
                Q_gen_total=sim_config.cells.n_rows * sim_config.cells.n_cols * sim_config.cells.q_gen
            )
            
            click.echo(f"✅ Simulation completed (converged: {results.converged}, iterations: {results.iterations})")
            
            # Print summary
            if report:
                summary = summarize_results(metrics)
                click.echo("\n" + summary)
                
                # Save summary
                summary_file = output_path / "summary.txt"
                with open(summary_file, 'w') as f:
                    f.write(summary)
                click.echo(f"📄 Summary saved to: {summary_file}")
            
            # Save metrics to JSON
            metrics_dict = metrics_to_dict(metrics)
            json_file = output_path / "metrics.json"
            with open(json_file, 'w') as f:
                json.dump(metrics_dict, f, indent=2)
            click.echo(f"💾 Metrics saved to: {json_file}")
            
            # Generate plots
            if plot:
                click.echo("📈 Generating plots...")
                plot_files = generate_all_plots(results, metrics, output_dir=str(output_path / "figs"))
                for name, path in plot_files.items():
                    click.echo(f"  - {name}: {path}")
        
        elif mode.upper() == 'CFD':
            click.echo("⚠️  CFD mode requires OpenFOAM installation")
            
            if export_case:
                click.echo("📦 Exporting CFD case...")
                mesh_data = create_mesh(sim_config, mode='CFD')
                
                if 'error' in mesh_data:
                    click.echo(f"❌ Error: {mesh_data['error']}")
                    sys.exit(1)
                
                click.echo(f"✅ CFD case exported to: {sim_config.output_dir}/case")
                click.echo("   Run OpenFOAM manually:")
                click.echo("   1. cd case")
                click.echo("   2. blockMesh")
                click.echo("   3. snappyHexMesh -overwrite")
                click.echo("   4. Run solver (e.g., simpleFoam)")
            else:
                click.echo("💡 Use --export-case to generate CFD case files")
        
        click.echo("\n✨ Done!")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option(
    '--config', '-c',
    type=click.Path(exists=True),
    required=True,
    help='Path to YAML configuration file'
)
@click.option(
    '--output', '-o',
    type=click.Path(),
    default='results',
    help='Output directory'
)
@click.option(
    '--plot/--no-plot',
    default=True,
    help='Generate plots'
)
def sweep(config: str, output: str, plot: bool) -> None:
    """
    Run parameter sweep defined in configuration.
    
    Example:
        battery-aircooling sweep --config examples/study_rib_sweep.yaml
    """
    click.echo(f"🔧 Loading configuration from: {config}")
    
    try:
        # Load configuration
        sim_config = SimulationConfig.from_yaml(config)
        
        if sim_config.sweep is None or len(sim_config.sweep) == 0:
            click.echo("❌ No sweep parameters defined in configuration")
            sys.exit(1)
        
        # Create output directory
        output_path = Path(output)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Run sweep for each parameter
        all_results = []
        
        for sweep_param in sim_config.sweep:
            param_path = sweep_param.path
            param_values = sweep_param.values
            
            click.echo(f"\n📊 Sweeping parameter: {param_path}")
            click.echo(f"   Values: {param_values}")
            
            # Initialize solver
            solver = ROMSolver(sim_config)
            
            # Run sweep
            results_list = []
            metrics_list = []
            
            with click.progressbar(param_values, label='Running sweep') as bar:
                for value in bar:
                    # Modify config
                    config_copy = sim_config.model_copy(deep=True)
                    config_copy.set_parameter_by_path(param_path, value)
                    
                    # Solve
                    solver_copy = ROMSolver(config_copy)
                    result = solver_copy.solve(max_iter=100, tol=1e-4)
                    
                    # Calculate metrics
                    metrics = calculate_metrics(
                        result,
                        config_copy.metrics,
                        Q_gen_total=config_copy.cells.n_rows * config_copy.cells.n_cols * config_copy.cells.q_gen
                    )
                    
                    results_list.append(result)
                    metrics_list.append(metrics)
            
            click.echo(f"✅ Sweep completed: {len(param_values)} points")
            
            # Save results to CSV
            df_data = []
            for value, metrics in zip(param_values, metrics_list):
                row = {param_path: value}
                row.update(metrics_to_dict(metrics))
                df_data.append(row)
            
            df = pd.DataFrame(df_data)
            csv_file = output_path / f"sweep_{param_path.replace('.', '_')}.csv"
            df.to_csv(csv_file, index=False)
            click.echo(f"💾 Results saved to: {csv_file}")
            
            # Generate plots
            if plot:
                click.echo("📈 Generating sweep plots...")
                
                # Extract parameter name and unit
                param_name = param_path.split('.')[-1]
                param_unit = ""
                if 'height' in param_name or 'pitch' in param_name or 'thickness' in param_name:
                    param_unit = "m"
                elif 'mdot' in param_name:
                    param_unit = "kg/s"
                
                plot_file = output_path / "figs" / f"sweep_{param_path.replace('.', '_')}.png"
                plot_file.parent.mkdir(parents=True, exist_ok=True)
                
                plot_sweep_results(
                    param_values,
                    metrics_list,
                    param_name,
                    param_unit,
                    output_path=str(plot_file),
                    show=False
                )
                click.echo(f"  - Sweep plot: {plot_file}")
            
            all_results.append({
                'param': param_path,
                'values': param_values,
                'metrics': metrics_list,
            })
        
        # Find best configuration
        click.echo("\n🏆 Finding best configuration...")
        
        best_idx = 0
        best_score = float('inf')
        
        for i, metrics in enumerate(all_results[0]['metrics']):
            if metrics.objective_score < best_score:
                best_score = metrics.objective_score
                best_idx = i
        
        best_config = {
            all_results[0]['param']: all_results[0]['values'][best_idx]
        }
        best_metrics = all_results[0]['metrics'][best_idx]
        
        click.echo(f"   Best configuration: {best_config}")
        click.echo(f"   Objective score: {best_score:.3f}")
        click.echo(f"   T_max: {best_metrics.T_max - 273.15:.2f}°C")
        click.echo(f"   P_pump: {best_metrics.P_pump:.3f}W")
        
        # Save best config
        best_file = output_path / "best_config.json"
        with open(best_file, 'w') as f:
            json.dump({
                'configuration': best_config,
                'metrics': metrics_to_dict(best_metrics),
                'objective_score': best_score,
            }, f, indent=2)
        click.echo(f"💾 Best configuration saved to: {best_file}")
        
        click.echo("\n✨ Sweep completed!")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


@main.command()
@click.option(
    '--config', '-c',
    type=click.Path(exists=True),
    required=True,
    help='Path to YAML configuration file'
)
def validate(config: str) -> None:
    """
    Validate configuration file.
    
    Example:
        battery-aircooling validate --config examples/study_rib_sweep.yaml
    """
    click.echo(f"🔍 Validating configuration: {config}")
    
    try:
        sim_config = SimulationConfig.from_yaml(config)
        click.echo("✅ Configuration is valid!")
        
        # Print summary
        click.echo("\nConfiguration Summary:")
        click.echo(f"  Name: {sim_config.name}")
        click.echo(f"  Mode: {sim_config.solver.mode}")
        click.echo(f"  Channels: {sim_config.channel.n_parallel}")
        click.echo(f"  Cells: {sim_config.cells.n_rows}x{sim_config.cells.n_cols}")
        click.echo(f"  Rib type: {sim_config.ribs.type}")
        click.echo(f"  Rib height: {sim_config.ribs.height*1000:.2f} mm")
        click.echo(f"  Rib pitch: {sim_config.ribs.pitch*1000:.2f} mm")
        
        if sim_config.sweep:
            click.echo(f"\nSweep parameters:")
            for sp in sim_config.sweep:
                click.echo(f"  - {sp.path}: {len(sp.values)} values")
        
    except Exception as e:
        click.echo(f"❌ Validation failed: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument('output_dir', type=click.Path(exists=True))
def report(output_dir: str) -> None:
    """
    Generate comprehensive report from simulation results.
    
    Example:
        battery-aircooling report results/
    """
    click.echo(f"📊 Generating report from: {output_dir}")
    
    output_path = Path(output_dir)
    
    # Check for results files
    csv_files = list(output_path.glob("sweep_*.csv"))
    
    if not csv_files:
        click.echo("❌ No sweep results found")
        sys.exit(1)
    
    click.echo(f"Found {len(csv_files)} sweep result files")
    
    # Load and summarize
    for csv_file in csv_files:
        click.echo(f"\n📈 {csv_file.name}:")
        df = pd.read_csv(csv_file)
        
        # Find best
        best_idx = df['objective_score'].idxmin()
        best_row = df.iloc[best_idx]
        
        click.echo(f"  Best configuration:")
        for col in df.columns[:3]:
            click.echo(f"    {col}: {best_row[col]}")
    
    click.echo("\n✨ Report generated!")


if __name__ == '__main__':
    main()
