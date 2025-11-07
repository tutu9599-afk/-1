# Battery Air Cooling Simulator

A comprehensive Python package for simulating and optimizing air-cooled battery pack thermal management with parametric rib channel designs.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 Purpose

This simulator enables evaluation of **cooling channel rib geometry effects** on battery pack thermal performance, focusing on:

- **Rib shape variations** (rectangular, triangular, semicircular, dimple)
- **Geometric parameters** (height, pitch, thickness)
- **Performance trade-offs** between heat transfer enhancement and pressure drop

The tool provides two simulation modes:
1. **ROM (Reduced-Order Model)**: Fast correlation-based 1D/quasi-2D network model
2. **CFD Mode**: OpenFOAM integration for high-fidelity RANS simulations

---

## 🚀 Features

### Core Capabilities

- ✅ **Parametric geometry generation** using CadQuery
- ✅ **ROM solver** with heat transfer correlations (Gnielinski, Han et al.)
- ✅ **Parallel channel flow distribution** with pressure balancing
- ✅ **Thermal resistance networks** for cell-to-fluid heat transfer
- ✅ **Performance metrics** (Tmax, ΔT, ΔP, Ppump, JF factor)
- ✅ **Parameter sweeps** for design space exploration
- ✅ **Pareto optimization** for multi-objective analysis
- ✅ **Rich visualizations** (temperature distributions, Pareto fronts, spider charts)
- ✅ **OpenFOAM interface** (optional) for CFD validation

### Performance Metrics

The simulator calculates:

| Metric | Description | Unit |
|--------|-------------|------|
| **Tmax** | Maximum cell temperature | °C |
| **dT_pack** | Temperature spread (Tmax - Tmin) | K |
| **UniformityIndex** | 1 - σ_T / T_mean | - |
| **ΔP** | Total pressure drop | Pa |
| **Ppump** | Required pumping power | W |
| **JF Factor** | (Nu/Nu₀) / (f/f₀)^(1/3) | - |

---

## 📦 Installation

### Prerequisites

- Python 3.9 or higher
- pip package manager

### Basic Installation

```bash
# Clone repository
git clone <repository-url>
cd battery_aircooling

# Install dependencies
pip install -r requirements.txt

# Install package in development mode
pip install -e .
```

### Optional Dependencies

```bash
# For CFD meshing support
pip install meshio

# For 3D visualization
pip install pyvista

# For optimization
pip install optuna
```

### Verify Installation

```bash
battery-aircooling --version
```

---

## 🎓 Quick Start

### 1. Validate Example Configuration

```bash
battery-aircooling validate --config examples/study_rib_sweep.yaml
```

### 2. Run Single Simulation

```bash
battery-aircooling run --config examples/study_rib_sweep.yaml --mode ROM
```

Output:
- `results/summary.txt` - Text summary of results
- `results/metrics.json` - Performance metrics
- `results/figs/` - Generated plots

### 3. Run Parameter Sweep

```bash
battery-aircooling sweep --config examples/study_rib_sweep.yaml
```

This performs a sweep over rib height values and generates:
- `results/sweep_ribs_height.csv` - Tabular results
- `results/best_config.json` - Optimal configuration
- `results/figs/sweep_ribs_height.png` - Performance plots

---

## 📖 Usage Guide

### Configuration File Structure

The YAML configuration defines all simulation parameters:

```yaml
name: "my_simulation"
description: "Battery cooling study"

air:
  Tin: 298.15          # Inlet temperature [K]
  Pin: 101325          # Inlet pressure [Pa]
  mdot: 0.05           # Mass flow rate [kg/s]

cells:
  n_rows: 4
  n_cols: 8
  q_gen: 15.0          # Heat generation per cell [W]
  size:
    lx: 0.065          # Length [m]
    ly: 0.100          # Width [m]
    lz: 0.018          # Height [m]
  gap_to_channel: 0.002
  k_cell: 20.0         # Thermal conductivity [W/(m·K)]
  k_gap: 0.2

channel:
  length: 0.520
  width: 0.100
  height: 0.010
  n_parallel: 4
  manifold_loss_coeff: 1.5

ribs:
  type: "rect"         # Options: rect, tri, semi, dimple
  pitch: 0.020         # Spacing [m]
  height: 0.003        # Height [m]
  thickness: 0.002     # Thickness [m]
  staggered: false

solver:
  mode: "ROM"          # ROM or CFD
  max_iter: 1000
  convergence_tol: 1.0e-6

# Parameter sweep (optional)
sweep:
  - path: "ribs.height"
    values: [0.001, 0.002, 0.003, 0.004, 0.005]

metrics:
  T_limit: 313.15      # Temperature limit [K]
  eta_fan: 0.6         # Fan efficiency
  weights:
    Tmax: 3.0
    dT_pack: 1.0
    Ppump: 1.0

output_dir: "results"
```

### Python API

```python
from battery_aircooling import SimulationConfig, ROMSolver
from battery_aircooling.physics_post import calculate_metrics, summarize_results

# Load configuration
config = SimulationConfig.from_yaml("examples/study_rib_sweep.yaml")

# Run simulation
solver = ROMSolver(config)
results = solver.solve()

# Calculate metrics
metrics = calculate_metrics(results, config.metrics)

# Print summary
print(summarize_results(metrics))

# Access specific values
print(f"Max Temperature: {metrics.T_max - 273.15:.2f}°C")
print(f"Pumping Power: {metrics.P_pump:.3f}W")
print(f"JF Factor: {metrics.JF_factor:.4f}")
```

### Parameter Sweeps

Sweep multiple parameters simultaneously:

```yaml
sweep:
  - path: "ribs.height"
    values: [0.001, 0.002, 0.003, 0.004, 0.005]
  
  - path: "ribs.pitch"
    values: [0.010, 0.015, 0.020, 0.025, 0.030]
  
  - path: "air.mdot"
    values: [0.02, 0.03, 0.04, 0.05, 0.06]
```

---

## 🔬 Model Details

### ROM (Reduced-Order Model)

The ROM combines:

1. **Flow Network Model**
   - Parallel channel pressure balancing
   - Manifold and local losses
   - Mass conservation enforcement

2. **Heat Transfer Correlations**
   - Smooth duct baseline: Gnielinski correlation
   - Ribbed augmentation: Han et al. correlations
   - Rib geometry effects: e/H, p/e, shape factor

3. **Thermal Resistance Network**
   - Cell internal conduction
   - Gap/pad conduction
   - Channel wall convection
   - Conjugate heat transfer

### CFD Mode (OpenFOAM Integration)

When `mode: "CFD"` is selected:

1. Geometry generation with CadQuery
2. STL export for meshing
3. Automatic OpenFOAM case setup
4. snappyHexMesh configuration
5. RANS solver execution (simpleFoam/pimpleFoam)
6. Post-processing and metric extraction

**Note**: Requires OpenFOAM installation (v2206 or later)

### Rib Geometry Effects

The simulator models four rib types with distinct characteristics:

| Type | Nu Enhancement | Friction Penalty | Best For |
|------|----------------|------------------|----------|
| **Rectangular** | High | High | Maximum heat transfer |
| **Triangular** | Medium-High | Medium | Balanced performance |
| **Semicircular** | Medium | Medium-Low | Low pressure drop |
| **Dimple** | Low-Medium | Low | Minimal pumping power |

---

## 📊 Visualization Examples

The simulator generates various plots automatically:

### Temperature Distribution
- Histogram of cell temperatures
- Box plots showing spread
- Convergence indicators

### Parameter Sweep Results
- Max temperature vs parameter
- Temperature uniformity trends
- Pressure drop and pumping power
- JF factor (thermal-hydraulic performance)

### Pareto Fronts
- Multi-objective optimization
- Trade-off visualization
- Optimal configuration identification

### Spider Charts
- Multi-configuration comparison
- Normalized performance metrics
- Configuration ranking

---

## 🧪 Testing

Run the test suite:

```bash
# All tests
pytest

# With coverage
pytest --cov=battery_aircooling --cov-report=html

# Specific test module
pytest tests/test_correlations.py -v
```

### Test Coverage

The test suite validates:

- ✅ Air property calculations (Sutherland's law)
- ✅ Reynolds number calculations
- ✅ Heat transfer correlations (Nu monotonicity with Re)
- ✅ Friction factor correlations
- ✅ Rib enhancement effects
- ✅ JF factor calculations
- ✅ Configuration validation (Pydantic schemas)
- ✅ Mass conservation
- ✅ Thermal resistance networks

---

## 🎯 Example Studies

### Study 1: Rib Height Optimization

```bash
battery-aircooling sweep --config examples/study_rib_sweep.yaml
```

**Results**: Identifies optimal rib height balancing heat transfer and pressure drop.

### Study 2: Rib Type Comparison

```bash
battery-aircooling sweep --config examples/compare_rib_types.yaml
```

**Results**: Compares rectangular, triangular, semicircular, and dimple ribs.

### Study 3: Flow Rate Sensitivity

Modify sweep parameters to analyze flow rate effects on cooling performance.

---

## 📐 Model Assumptions and Limitations

### Assumptions

1. **Steady-state operation** (transient effects negligible)
2. **Single-phase air flow** (no condensation)
3. **Uniform heat generation** in cells
4. **Incompressible flow** (low Mach number)
5. **Rigid geometry** (no thermal expansion)
6. **Developed turbulence** (Re > 4000 in ROM)

### Limitations

1. **ROM accuracy**: ±15% vs CFD for complex geometries
2. **Correlation validity**: Limited to correlation parameter ranges
3. **1D thermal model**: Neglects detailed 3D conduction in cells
4. **No radiation**: Convection-conduction only
5. **Simplified manifold**: Detailed manifold flow not captured

### Validation

ROM results should be validated against:
- CFD simulations for complex cases
- Experimental data when available
- Manufacturer specifications

---

## 🛠️ Development

### Code Style

```bash
# Format code
black battery_aircooling/

# Lint
ruff battery_aircooling/

# Type checking
mypy battery_aircooling/
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Ensure all tests pass
5. Submit a pull request

---

## 📚 References

### Heat Transfer Correlations

1. **Gnielinski (1976)**: "New equations for heat and mass transfer in turbulent pipe and channel flow"
2. **Han et al. (1985)**: "Heat transfer and friction in channels with two opposite rib-roughened walls"
3. **Webb & Eckert (1972)**: "Application of rough surfaces to heat exchanger design"

### Battery Thermal Management

4. **Pesaran (2001)**: "Battery thermal management in EVs and HEVs: Issues and solutions"
5. **Wang et al. (2016)**: "Thermal investigation of lithium-ion battery module with different cell arrangement structures and forced air-cooling strategies"

### Validation

This simulator reproduces trends from:
- "공랭식 배터리 팩 모듈의 채널 리브 형상에 따른 냉각 효율 향상 연구" (provided paper)

---

## 📝 License

MIT License - see LICENSE file for details

---

## 🤝 Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Contact: [Your contact information]

---

## 🎓 Citation

If you use this simulator in your research, please cite:

```bibtex
@software{battery_aircooling,
  title = {Battery Air Cooling Simulator},
  author = {Battery Cooling Research Team},
  year = {2024},
  version = {0.1.0},
  url = {https://github.com/your-repo/battery-aircooling}
}
```

---

## 🔄 Changelog

### v0.1.0 (2024)
- Initial release
- ROM solver with correlation-based physics
- OpenFOAM interface (beta)
- Parameter sweep functionality
- Comprehensive visualization suite
- Example configurations and notebooks

---

## 🚦 Roadmap

Future enhancements:

- [ ] Transient thermal analysis
- [ ] Multi-physics coupling (electrical-thermal)
- [ ] Machine learning surrogate models
- [ ] Automated optimization (genetic algorithms)
- [ ] Web-based GUI
- [ ] Cloud deployment support
- [ ] Real-time monitoring integration

---

**Made with ❤️ for battery thermal management research**
