"""
OpenFOAM interface for CFD simulations.

Automates OpenFOAM case setup, execution, and post-processing.
Optional module - requires OpenFOAM installation.
"""

import subprocess
import shutil
from pathlib import Path
from typing import Dict, Optional, List
import time

from battery_aircooling.config_schema import SimulationConfig


class OpenFOAMCase:
    """
    Manage OpenFOAM case setup and execution.
    """
    
    def __init__(self, config: SimulationConfig, case_dir: str = "case"):
        """
        Initialize OpenFOAM case.
        
        Args:
            config: Simulation configuration
            case_dir: Case directory path
        """
        self.config = config
        self.case_dir = Path(case_dir)
        self.case_dir.mkdir(parents=True, exist_ok=True)
        
        # Create standard OpenFOAM directory structure
        self.constant_dir = self.case_dir / "constant"
        self.system_dir = self.case_dir / "system"
        self.zero_dir = self.case_dir / "0"
        
        for d in [self.constant_dir, self.system_dir, self.zero_dir]:
            d.mkdir(parents=True, exist_ok=True)
    
    def write_control_dict(self) -> str:
        """Write controlDict file."""
        
        if self.config.solver.steady:
            application = "simpleFoam"
            time_scheme = "steadyState"
            max_time = self.config.solver.max_iter
        else:
            application = "pimpleFoam"
            time_scheme = "Euler"
            max_time = 100.0
        
        control_dict = f"""/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  v2206                                 |
|   \\\\  /    A nd           | Website:  www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      controlDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

application     {application};

startFrom       startTime;

startTime       0;

stopAt          endTime;

endTime         {max_time};

deltaT          1;

writeControl    timeStep;

writeInterval   100;

purgeWrite      2;

writeFormat     ascii;

writePrecision  6;

writeCompression off;

timeFormat      general;

timePrecision   6;

runTimeModifiable true;

functions
{{
    forces
    {{
        type            forces;
        libs            (forces);
        writeControl    timeStep;
        writeInterval   10;
        patches         (walls);
        rho             rhoInf;
        rhoInf          {self.config.air.rho or 1.225};
        CofR            (0 0 0);
    }}
}}

// ************************************************************************* //
"""
        
        file_path = self.system_dir / "controlDict"
        with open(file_path, 'w') as f:
            f.write(control_dict)
        
        return str(file_path)
    
    def write_fv_schemes(self) -> str:
        """Write fvSchemes file."""
        
        fv_schemes = """/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  v2206                                 |
|   \\  /    A nd           | Website:  www.openfoam.com                      |
|    \\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSchemes;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

ddtSchemes
{
    default         steadyState;
}

gradSchemes
{
    default         Gauss linear;
}

divSchemes
{
    default         none;
    div(phi,U)      bounded Gauss linearUpwind grad(U);
    div(phi,k)      bounded Gauss upwind;
    div(phi,omega)  bounded Gauss upwind;
    div(phi,epsilon) bounded Gauss upwind;
    div(phi,T)      bounded Gauss upwind;
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}

laplacianSchemes
{
    default         Gauss linear corrected;
}

interpolationSchemes
{
    default         linear;
}

snGradSchemes
{
    default         corrected;
}

wallDist
{
    method meshWave;
}

// ************************************************************************* //
"""
        
        file_path = self.system_dir / "fvSchemes"
        with open(file_path, 'w') as f:
            f.write(fv_schemes)
        
        return str(file_path)
    
    def write_fv_solution(self) -> str:
        """Write fvSolution file."""
        
        fv_solution = f"""/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  v2206                                 |
|   \\  /    A nd           | Website:  www.openfoam.com                      |
|    \\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    location    "system";
    object      fvSolution;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

solvers
{{
    p
    {{
        solver          GAMG;
        tolerance       {self.config.solver.convergence_tol};
        relTol          0.01;
        smoother        GaussSeidel;
    }}

    U
    {{
        solver          smoothSolver;
        smoother        GaussSeidel;
        tolerance       {self.config.solver.convergence_tol};
        relTol          0.1;
    }}

    "(k|omega|epsilon)"
    {{
        solver          smoothSolver;
        smoother        GaussSeidel;
        tolerance       {self.config.solver.convergence_tol};
        relTol          0.1;
    }}

    T
    {{
        solver          smoothSolver;
        smoother        GaussSeidel;
        tolerance       {self.config.solver.convergence_tol};
        relTol          0.1;
    }}
}}

SIMPLE
{{
    nNonOrthogonalCorrectors 0;
    consistent      yes;
    
    residualControl
    {{
        p               {self.config.solver.convergence_tol};
        U               {self.config.solver.convergence_tol};
        "(k|omega|epsilon)" {self.config.solver.convergence_tol};
        T               {self.config.solver.convergence_tol};
    }}
}}

relaxationFactors
{{
    equations
    {{
        U               0.7;
        k               0.7;
        omega           0.7;
        epsilon         0.7;
        T               0.7;
    }}
}}

// ************************************************************************* //
"""
        
        file_path = self.system_dir / "fvSolution"
        with open(file_path, 'w') as f:
            f.write(fv_solution)
        
        return str(file_path)
    
    def write_boundary_conditions(self) -> List[str]:
        """Write initial and boundary condition files."""
        
        files = []
        
        # Velocity (U)
        U_file = self.zero_dir / "U"
        U_content = f"""/*--------------------------------*- C++ -*----------------------------------*\\
FoamFile
{{
    version     2.0;
    format      ascii;
    class       volVectorField;
    object      U;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 1 -1 0 0 0 0];

internalField   uniform (0 0 0);

boundaryField
{{
    inlet
    {{
        type            fixedValue;
        value           uniform (1 0 0);
    }}

    outlet
    {{
        type            zeroGradient;
    }}

    walls
    {{
        type            noSlip;
    }}
}}

// ************************************************************************* //
"""
        with open(U_file, 'w') as f:
            f.write(U_content)
        files.append(str(U_file))
        
        # Pressure (p)
        p_file = self.zero_dir / "p"
        p_content = """/*--------------------------------*- C++ -*----------------------------------*\\
FoamFile
{
    version     2.0;
    format      ascii;
    class       volScalarField;
    object      p;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -2 0 0 0 0];

internalField   uniform 0;

boundaryField
{
    inlet
    {
        type            zeroGradient;
    }

    outlet
    {
        type            fixedValue;
        value           uniform 0;
    }

    walls
    {
        type            zeroGradient;
    }
}

// ************************************************************************* //
"""
        with open(p_file, 'w') as f:
            f.write(p_content)
        files.append(str(p_file))
        
        # Turbulence fields (k, omega for kOmegaSST)
        if self.config.solver.turb_model == "kOmegaSST":
            # k
            k_file = self.zero_dir / "k"
            k_content = """/*--------------------------------*- C++ -*----------------------------------*\\
FoamFile
{
    version     2.0;
    format      ascii;
    class       volScalarField;
    object      k;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 2 -2 0 0 0 0];

internalField   uniform 0.01;

boundaryField
{
    inlet
    {
        type            fixedValue;
        value           uniform 0.01;
    }

    outlet
    {
        type            zeroGradient;
    }

    walls
    {
        type            kqRWallFunction;
        value           uniform 0.01;
    }
}

// ************************************************************************* //
"""
            with open(k_file, 'w') as f:
                f.write(k_content)
            files.append(str(k_file))
            
            # omega
            omega_file = self.zero_dir / "omega"
            omega_content = """/*--------------------------------*- C++ -*----------------------------------*\\
FoamFile
{
    version     2.0;
    format      ascii;
    class       volScalarField;
    object      omega;
}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

dimensions      [0 0 -1 0 0 0 0];

internalField   uniform 1;

boundaryField
{
    inlet
    {
        type            fixedValue;
        value           uniform 1;
    }

    outlet
    {
        type            zeroGradient;
    }

    walls
    {
        type            omegaWallFunction;
        value           uniform 1;
    }
}

// ************************************************************************* //
"""
            with open(omega_file, 'w') as f:
                f.write(omega_content)
            files.append(str(omega_file))
        
        return files
    
    def setup_case(self) -> Dict[str, List[str]]:
        """
        Set up complete OpenFOAM case.
        
        Returns:
            Dictionary with created file paths
        """
        files = {
            'control': [],
            'schemes': [],
            'solution': [],
            'bc': [],
        }
        
        # Write system files
        files['control'].append(self.write_control_dict())
        files['schemes'].append(self.write_fv_schemes())
        files['solution'].append(self.write_fv_solution())
        
        # Write boundary conditions
        files['bc'] = self.write_boundary_conditions()
        
        return files
    
    def run_blockmesh(self) -> bool:
        """Run blockMesh utility."""
        try:
            result = subprocess.run(
                ['blockMesh', '-case', str(self.case_dir)],
                capture_output=True,
                text=True,
                timeout=60
            )
            return result.returncode == 0
        except Exception as e:
            print(f"blockMesh failed: {e}")
            return False
    
    def run_snappyhexmesh(self) -> bool:
        """Run snappyHexMesh utility."""
        try:
            result = subprocess.run(
                ['snappyHexMesh', '-overwrite', '-case', str(self.case_dir)],
                capture_output=True,
                text=True,
                timeout=600
            )
            return result.returncode == 0
        except Exception as e:
            print(f"snappyHexMesh failed: {e}")
            return False
    
    def run_solver(self, solver: str = "simpleFoam") -> bool:
        """
        Run OpenFOAM solver.
        
        Args:
            solver: Solver name (simpleFoam, pimpleFoam, etc.)
        
        Returns:
            True if successful
        """
        try:
            result = subprocess.run(
                [solver, '-case', str(self.case_dir)],
                capture_output=True,
                text=True,
                timeout=3600
            )
            return result.returncode == 0
        except Exception as e:
            print(f"Solver {solver} failed: {e}")
            return False
    
    def check_convergence(self) -> Dict:
        """
        Check simulation convergence from log files.
        
        Returns:
            Dictionary with convergence information
        """
        log_file = self.case_dir / "log.simpleFoam"
        
        if not log_file.exists():
            return {"converged": False, "reason": "Log file not found"}
        
        # Simple convergence check (could be enhanced)
        with open(log_file, 'r') as f:
            content = f.read()
        
        if "End" in content:
            return {"converged": True, "iterations": "completed"}
        else:
            return {"converged": False, "reason": "Incomplete simulation"}


def check_openfoam_available() -> bool:
    """
    Check if OpenFOAM is available.
    
    Returns:
        True if OpenFOAM is installed and sourced
    """
    try:
        result = subprocess.run(
            ['which', 'simpleFoam'],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception:
        return False
