"""
Mesh generation utilities for ROM and CFD modes.

ROM mode: Internal flow network discretization
CFD mode: Export geometry and prepare for external meshing (OpenFOAM/snappyHexMesh)
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from pathlib import Path

from battery_aircooling.config_schema import SimulationConfig
from battery_aircooling.geometry import (
    create_ribbed_channel,
    create_cell_array,
    export_to_stl,
    export_to_step,
)


class ROMMesh:
    """
    Internal mesh/discretization for ROM solver.
    
    Divides channels and cells into computational nodes.
    """
    
    def __init__(self, config: SimulationConfig):
        """
        Initialize ROM mesh.
        
        Args:
            config: Simulation configuration
        """
        self.config = config
        
        # Channel discretization
        self.n_nodes_axial = 10  # Along channel length
        self.n_channels = config.channel.n_parallel
        
        # Cell discretization
        self.n_cells_total = config.cells.n_rows * config.cells.n_cols
        
    def generate_nodes(self) -> Dict:
        """
        Generate computational nodes for ROM.
        
        Returns:
            Dictionary with node information
        """
        config = self.config
        
        # Axial positions along channel
        x_nodes = np.linspace(0, config.channel.length, self.n_nodes_axial)
        
        # Channel node grid
        channel_nodes = []
        for i in range(self.n_channels):
            for j, x in enumerate(x_nodes):
                node = {
                    "channel_id": i,
                    "node_id": j,
                    "x": x,
                    "T_fluid": config.air.Tin,
                    "T_wall": config.air.Tin,
                }
                channel_nodes.append(node)
        
        # Cell positions
        cell_nodes = []
        for i in range(config.cells.n_rows):
            for j in range(config.cells.n_cols):
                # Calculate cell center position
                x = j * config.cells.size.lx + config.cells.size.lx / 2
                y = i * config.cells.size.ly + config.cells.size.ly / 2
                
                node = {
                    "cell_id": i * config.cells.n_cols + j,
                    "row": i,
                    "col": j,
                    "x": x,
                    "y": y,
                    "T_cell": config.air.Tin,
                    "Q_gen": config.cells.q_gen,
                }
                cell_nodes.append(node)
        
        mesh_data = {
            "channel_nodes": channel_nodes,
            "cell_nodes": cell_nodes,
            "n_nodes_axial": self.n_nodes_axial,
            "n_channels": self.n_channels,
            "n_cells": self.n_cells_total,
        }
        
        return mesh_data


class CFDMeshPreparation:
    """
    Prepare geometry and mesh for CFD simulation.
    
    Exports STL/STEP files for use with OpenFOAM snappyHexMesh.
    """
    
    def __init__(self, config: SimulationConfig, output_dir: str = "case"):
        """
        Initialize CFD mesh preparation.
        
        Args:
            config: Simulation configuration
            output_dir: Output directory for mesh files
        """
        self.config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def export_geometry(self) -> Dict[str, str]:
        """
        Export geometries to STL/STEP format.
        
        Returns:
            Dictionary with file paths
        """
        config = self.config
        
        files = {}
        
        try:
            # Create channel geometry
            channel = create_ribbed_channel(
                length=config.channel.length,
                width=config.channel.width,
                height=config.channel.height,
                rib_type=config.ribs.type,
                rib_height=config.ribs.height,
                rib_thickness=config.ribs.thickness,
                rib_pitch=config.ribs.pitch,
                staggered=config.ribs.staggered,
            )
            
            if channel is not None:
                # Export channel
                channel_stl = str(self.output_dir / "channel.stl")
                channel_step = str(self.output_dir / "channel.step")
                
                export_to_stl(channel, channel_stl, tolerance=0.01)
                export_to_step(channel, channel_step)
                
                files["channel_stl"] = channel_stl
                files["channel_step"] = channel_step
            
            # Create cell array geometry
            cells = create_cell_array(
                n_rows=config.cells.n_rows,
                n_cols=config.cells.n_cols,
                cell_length=config.cells.size.lx,
                cell_width=config.cells.size.ly,
                cell_height=config.cells.size.lz,
                gap=config.cells.gap_to_channel,
            )
            
            if cells is not None:
                # Export cells
                cells_stl = str(self.output_dir / "cells.stl")
                cells_step = str(self.output_dir / "cells.step")
                
                export_to_stl(cells, cells_stl, tolerance=0.01)
                export_to_step(cells, cells_step)
                
                files["cells_stl"] = cells_stl
                files["cells_step"] = cells_step
                
        except Exception as e:
            print(f"Warning: Geometry export failed: {e}")
            print("CadQuery may not be available. CFD mode requires CadQuery installation.")
        
        return files
    
    def generate_background_mesh(self) -> Dict:
        """
        Generate background mesh parameters for snappyHexMesh.
        
        Returns:
            Dictionary with blockMesh parameters
        """
        config = self.config
        
        # Calculate domain bounds with margin
        margin = 0.1  # 10% margin
        
        L = config.channel.length
        W = config.channel.width
        H_total = (config.channel.height + config.cells.size.lz + 
                   config.cells.gap_to_channel) * config.channel.n_parallel
        
        x_min = -margin * L
        x_max = L * (1 + margin)
        y_min = -margin * W
        y_max = W * (1 + margin)
        z_min = -margin * H_total
        z_max = H_total * (1 + margin)
        
        # Cell size based on smallest feature
        min_feature = min(config.ribs.height, config.ribs.thickness)
        base_cell_size = min_feature / 3
        
        # Number of cells in each direction
        nx = int((x_max - x_min) / base_cell_size)
        ny = int((y_max - y_min) / base_cell_size)
        nz = int((z_max - z_min) / base_cell_size)
        
        # Ensure reasonable mesh size
        nx = max(20, min(nx, 200))
        ny = max(20, min(ny, 200))
        nz = max(20, min(nz, 200))
        
        blockMesh_params = {
            "vertices": {
                "x_min": x_min,
                "x_max": x_max,
                "y_min": y_min,
                "y_max": y_max,
                "z_min": z_min,
                "z_max": z_max,
            },
            "blocks": {
                "nx": nx,
                "ny": ny,
                "nz": nz,
            },
            "cell_size": base_cell_size,
        }
        
        return blockMesh_params
    
    def write_snappy_dict(self, geometry_files: Dict[str, str]) -> str:
        """
        Write snappyHexMeshDict configuration file.
        
        Args:
            geometry_files: Dictionary with STL file paths
        
        Returns:
            Path to snappyHexMeshDict file
        """
        config = self.config
        
        # Refinement levels
        refinement_level = 3
        
        snappy_dict = f"""/*--------------------------------*- C++ -*----------------------------------*\\
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
    object      snappyHexMeshDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

castellatedMesh true;
snap            true;
addLayers       false;

geometry
{{
    channel.stl
    {{
        type triSurfaceMesh;
        name channel;
    }}
    
    cells.stl
    {{
        type triSurfaceMesh;
        name cells;
    }}
}};

castellatedMeshControls
{{
    maxLocalCells 1000000;
    maxGlobalCells 2000000;
    minRefinementCells 10;
    maxLoadUnbalance 0.10;
    nCellsBetweenLevels 3;
    
    features
    (
    );
    
    refinementSurfaces
    {{
        channel
        {{
            level ({refinement_level} {refinement_level});
        }}
        cells
        {{
            level ({refinement_level} {refinement_level});
        }}
    }}
    
    resolveFeatureAngle 30;
    
    refinementRegions
    {{
    }}
    
    locationInMesh (0.001 0.001 0.001);
    allowFreeStandingZoneFaces true;
}}

snapControls
{{
    nSmoothPatch 3;
    tolerance 2.0;
    nSolveIter 100;
    nRelaxIter 5;
    nFeatureSnapIter 10;
}}

addLayersControls
{{
    relativeSizes true;
    layers
    {{
    }}
    expansionRatio 1.0;
    finalLayerThickness 0.3;
    minThickness 0.1;
    nGrow 0;
}}

meshQualityControls
{{
    maxNonOrtho 65;
    maxBoundarySkewness 20;
    maxInternalSkewness 4;
    maxConcave 80;
    minVol 1e-13;
    minTetQuality 1e-15;
    minArea -1;
    minTwist 0.02;
    minDeterminant 0.001;
    minFaceWeight 0.02;
    minVolRatio 0.01;
    minTriangleTwist -1;
}}

mergeTolerance 1e-6;

// ************************************************************************* //
"""
        
        snappy_file = self.output_dir / "system" / "snappyHexMeshDict"
        snappy_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(snappy_file, 'w') as f:
            f.write(snappy_dict)
        
        return str(snappy_file)


def create_blockMeshDict(
    length: float,
    width: float,
    height: float,
    nx: int,
    ny: int,
    nz: int,
    output_file: str
) -> None:
    """
    Create OpenFOAM blockMeshDict file.
    
    Args:
        length: Domain length [m]
        width: Domain width [m]
        height: Domain height [m]
        nx: Number of cells in x
        ny: Number of cells in y
        nz: Number of cells in z
        output_file: Path to output blockMeshDict
    """
    content = f"""/*--------------------------------*- C++ -*----------------------------------*\\
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
    object      blockMeshDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

convertToMeters 1;

vertices
(
    (0 0 0)
    ({length} 0 0)
    ({length} {width} 0)
    (0 {width} 0)
    (0 0 {height})
    ({length} 0 {height})
    ({length} {width} {height})
    (0 {width} {height})
);

blocks
(
    hex (0 1 2 3 4 5 6 7) ({nx} {ny} {nz}) simpleGrading (1 1 1)
);

edges
(
);

boundary
(
    inlet
    {{
        type patch;
        faces
        (
            (0 4 7 3)
        );
    }}
    outlet
    {{
        type patch;
        faces
        (
            (1 2 6 5)
        );
    }}
    walls
    {{
        type wall;
        faces
        (
            (0 1 5 4)
            (3 7 6 2)
            (0 3 2 1)
            (4 5 6 7)
        );
    }}
);

mergePatchPairs
(
);

// ************************************************************************* //
"""
    
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        f.write(content)


def create_mesh(config: SimulationConfig, mode: str = "ROM") -> Dict:
    """
    Create mesh based on simulation mode.
    
    Args:
        config: Simulation configuration
        mode: "ROM" or "CFD"
    
    Returns:
        Dictionary with mesh information
    """
    if mode == "ROM":
        mesh = ROMMesh(config)
        mesh_data = mesh.generate_nodes()
        return mesh_data
        
    elif mode == "CFD":
        cfd_mesh = CFDMeshPreparation(config, output_dir=config.output_dir + "/case")
        
        # Export geometry
        geometry_files = cfd_mesh.export_geometry()
        
        # Generate background mesh parameters
        blockmesh_params = cfd_mesh.generate_background_mesh()
        
        # Write snappyHexMeshDict
        if geometry_files:
            snappy_dict = cfd_mesh.write_snappy_dict(geometry_files)
            
            mesh_data = {
                "geometry_files": geometry_files,
                "blockmesh_params": blockmesh_params,
                "snappy_dict": snappy_dict,
            }
        else:
            mesh_data = {
                "error": "Geometry export failed. CadQuery may not be available."
            }
        
        return mesh_data
    
    else:
        raise ValueError(f"Unknown mode: {mode}")
