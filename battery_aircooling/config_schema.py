"""
Configuration schema validation using Pydantic.

Defines the structure and validation rules for all simulation input parameters.
"""

from typing import Dict, List, Literal, Optional, Any
from pydantic import BaseModel, Field, field_validator, model_validator


class AirProperties(BaseModel):
    """Air inlet conditions and thermophysical properties."""
    
    Tin: float = Field(..., gt=0, description="Inlet temperature [K]")
    Pin: float = Field(..., gt=0, description="Inlet pressure [Pa]")
    mdot: Optional[float] = Field(None, gt=0, description="Mass flow rate [kg/s]")
    Re: Optional[float] = Field(None, gt=0, description="Reynolds number [-]")
    
    # Thermophysical properties (optional, calculated if not provided)
    mu: Optional[float] = Field(None, gt=0, description="Dynamic viscosity [Pa·s]")
    rho: Optional[float] = Field(None, gt=0, description="Density [kg/m³]")
    cp: Optional[float] = Field(None, gt=0, description="Specific heat [J/(kg·K)]")
    k: Optional[float] = Field(None, gt=0, description="Thermal conductivity [W/(m·K)]")
    
    @model_validator(mode='after')
    def check_flow_specification(self) -> 'AirProperties':
        """Ensure either mdot or Re is specified."""
        if self.mdot is None and self.Re is None:
            raise ValueError("Either 'mdot' or 'Re' must be specified")
        return self


class CellGeometry(BaseModel):
    """Battery cell dimensions."""
    
    lx: float = Field(..., gt=0, description="Length [m]")
    ly: float = Field(..., gt=0, description="Width [m]")
    lz: float = Field(..., gt=0, description="Height [m]")


class CellsConfig(BaseModel):
    """Battery cell array configuration."""
    
    n_rows: int = Field(..., gt=0, description="Number of rows")
    n_cols: int = Field(..., gt=0, description="Number of columns")
    q_gen: float = Field(..., gt=0, description="Heat generation per cell [W]")
    size: CellGeometry
    gap_to_channel: float = Field(..., ge=0, description="Gap between cell and channel [m]")
    k_cell: float = Field(default=20.0, gt=0, description="Cell thermal conductivity [W/(m·K)]")
    k_gap: float = Field(default=0.2, gt=0, description="Gap/pad thermal conductivity [W/(m·K)]")


class ChannelConfig(BaseModel):
    """Cooling channel geometry."""
    
    length: float = Field(..., gt=0, description="Channel length [m]")
    width: float = Field(..., gt=0, description="Channel width [m]")
    height: float = Field(..., gt=0, description="Channel height [m]")
    n_parallel: int = Field(default=1, gt=0, description="Number of parallel channels")
    manifold_loss_coeff: float = Field(default=1.5, ge=0, description="Manifold pressure loss coefficient [-]")


class RibsConfig(BaseModel):
    """Rib geometry and arrangement parameters."""
    
    type: Literal["rect", "tri", "semi", "dimple"] = Field(
        default="rect",
        description="Rib cross-section shape"
    )
    pitch: float = Field(..., gt=0, description="Rib pitch (spacing) [m]")
    height: float = Field(..., gt=0, description="Rib height [m]")
    thickness: float = Field(..., gt=0, description="Rib thickness [m]")
    staggered: bool = Field(default=False, description="Staggered arrangement")
    
    @field_validator('height')
    @classmethod
    def check_height_range(cls, v: float) -> float:
        """Validate rib height is in reasonable range."""
        if not 0.0001 <= v <= 0.1:
            raise ValueError("Rib height should be between 0.1 mm and 100 mm")
        return v


class SolverConfig(BaseModel):
    """Solver settings and numerical parameters."""
    
    mode: Literal["ROM", "CFD"] = Field(default="ROM", description="Simulation mode")
    turb_model: Literal["kOmegaSST", "kEpsilon"] = Field(
        default="kOmegaSST",
        description="Turbulence model (CFD only)"
    )
    steady: bool = Field(default=True, description="Steady-state simulation")
    max_iter: int = Field(default=1000, gt=0, description="Maximum iterations")
    convergence_tol: float = Field(default=1e-6, gt=0, description="Convergence tolerance")
    n_cells_radial: int = Field(default=20, gt=0, description="Radial mesh cells (CFD)")


class SweepParameter(BaseModel):
    """Single sweep parameter definition."""
    
    path: str = Field(..., description="Parameter path (e.g., 'ribs.height')")
    values: List[float] = Field(..., min_length=1, description="Parameter values to sweep")


class MetricsConfig(BaseModel):
    """Performance metrics to calculate and track."""
    
    targets: List[str] = Field(
        default=["Tmax", "dT_pack", "DeltaP", "Ppump", "UniformityIndex", "JF"],
        description="Metrics to calculate"
    )
    T_limit: float = Field(default=313.15, gt=0, description="Temperature limit [K]")
    eta_fan: float = Field(default=0.6, gt=0, le=1.0, description="Fan efficiency [-]")
    weights: Dict[str, float] = Field(
        default={"Tmax": 3.0, "dT_pack": 1.0, "Ppump": 1.0},
        description="Objective function weights"
    )


class OptimizationConfig(BaseModel):
    """Optimization settings for Optuna-based parameter tuning."""
    
    enabled: bool = Field(default=False, description="Enable optimization")
    n_trials: int = Field(default=100, gt=0, description="Number of optimization trials")
    sampler: Literal["TPE", "Random", "Grid"] = Field(default="TPE")
    
    # Parameter bounds
    bounds: Dict[str, tuple[float, float]] = Field(
        default={
            "ribs.height": (0.001, 0.01),
            "ribs.pitch": (0.005, 0.05),
            "air.mdot": (0.001, 0.1),
        }
    )


class SimulationConfig(BaseModel):
    """Complete simulation configuration."""
    
    name: str = Field(default="battery_cooling_sim", description="Simulation name")
    description: Optional[str] = Field(None, description="Simulation description")
    
    air: AirProperties
    cells: CellsConfig
    channel: ChannelConfig
    ribs: RibsConfig
    solver: SolverConfig = Field(default_factory=SolverConfig)
    
    sweep: Optional[List[SweepParameter]] = Field(None, description="Parameter sweep definition")
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    optimization: OptimizationConfig = Field(default_factory=OptimizationConfig)
    
    output_dir: str = Field(default="results", description="Output directory")
    
    @model_validator(mode='after')
    def validate_rib_geometry(self) -> 'SimulationConfig':
        """Validate rib geometry constraints."""
        if self.ribs.height > self.channel.height * 0.5:
            raise ValueError("Rib height cannot exceed 50% of channel height")
        
        if self.ribs.thickness > self.ribs.pitch * 0.5:
            raise ValueError("Rib thickness cannot exceed 50% of rib pitch")
        
        return self
    
    @classmethod
    def from_yaml(cls, yaml_path: str) -> 'SimulationConfig':
        """Load configuration from YAML file."""
        import yaml
        
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
        
        return cls(**data)
    
    def to_yaml(self, yaml_path: str) -> None:
        """Save configuration to YAML file."""
        import yaml
        
        with open(yaml_path, 'w') as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False, sort_keys=False)
    
    def get_parameter_by_path(self, path: str) -> Any:
        """Get nested parameter value by dot-separated path."""
        parts = path.split('.')
        obj = self
        
        for part in parts:
            obj = getattr(obj, part)
        
        return obj
    
    def set_parameter_by_path(self, path: str, value: Any) -> None:
        """Set nested parameter value by dot-separated path."""
        parts = path.split('.')
        obj = self
        
        for part in parts[:-1]:
            obj = getattr(obj, part)
        
        setattr(obj, parts[-1], value)
