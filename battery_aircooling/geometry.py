"""
Parametric CAD geometry generation using CadQuery.

Generates 3D models of battery pack components including:
- Cooling channels with various rib geometries
- Battery cells
- Complete module assembly
"""

from typing import Literal, Optional, List, Tuple
import numpy as np

try:
    import cadquery as cq
    CADQUERY_AVAILABLE = True
except ImportError:
    CADQUERY_AVAILABLE = False
    cq = None


class RibProfile:
    """Generate rib cross-section profiles."""
    
    @staticmethod
    def rectangular(height: float, thickness: float) -> List[Tuple[float, float]]:
        """Rectangular rib profile."""
        t_half = thickness / 2
        return [
            (-t_half, 0),
            (-t_half, height),
            (t_half, height),
            (t_half, 0),
        ]
    
    @staticmethod
    def triangular(height: float, thickness: float) -> List[Tuple[float, float]]:
        """Triangular rib profile."""
        t_half = thickness / 2
        return [
            (-t_half, 0),
            (0, height),
            (t_half, 0),
        ]
    
    @staticmethod
    def semicircular(height: float, thickness: float) -> List[Tuple[float, float]]:
        """Semicircular rib profile (approximated)."""
        n_points = 20
        angles = np.linspace(0, np.pi, n_points)
        
        # Radius is rib height
        r = height
        t_half = thickness / 2
        
        points = []
        # Bottom edge
        points.append((-t_half, 0))
        
        # Semicircle
        for angle in angles:
            x = r * np.cos(angle)
            y = r * np.sin(angle)
            points.append((x * thickness / (2 * r), y))
        
        # Bottom edge
        points.append((t_half, 0))
        
        return points


def create_rib_geometry(
    rib_type: Literal["rect", "tri", "semi", "dimple"],
    height: float,
    thickness: float,
    length: float
) -> Optional[object]:
    """
    Create a single rib geometry.
    
    Args:
        rib_type: Rib cross-section type
        height: Rib height [m]
        thickness: Rib thickness [m]
        length: Rib length (channel width) [m]
    
    Returns:
        CadQuery Workplane object or None if CadQuery not available
    """
    if not CADQUERY_AVAILABLE:
        return None
    
    # Get profile points based on type
    if rib_type == "rect":
        profile = RibProfile.rectangular(height * 1000, thickness * 1000)  # mm
    elif rib_type == "tri":
        profile = RibProfile.triangular(height * 1000, thickness * 1000)
    elif rib_type == "semi":
        profile = RibProfile.semicircular(height * 1000, thickness * 1000)
    else:  # dimple - simplified as shallow hemisphere
        profile = RibProfile.semicircular(height * 1000, thickness * 1000)
    
    # Create 2D profile
    rib_profile = cq.Workplane("XZ").polyline(profile).close()
    
    # Extrude along Y direction (channel width)
    rib = rib_profile.extrude(length * 1000)  # mm
    
    return rib


def create_ribbed_channel(
    length: float,
    width: float,
    height: float,
    rib_type: Literal["rect", "tri", "semi", "dimple"],
    rib_height: float,
    rib_thickness: float,
    rib_pitch: float,
    staggered: bool = False
) -> Optional[object]:
    """
    Create cooling channel with ribs.
    
    Args:
        length: Channel length [m]
        width: Channel width [m]
        height: Channel height [m]
        rib_type: Rib cross-section type
        rib_height: Rib height [m]
        rib_thickness: Rib thickness [m]
        rib_pitch: Spacing between ribs [m]
        staggered: Whether ribs are staggered on top/bottom walls
    
    Returns:
        CadQuery Workplane object or None
    """
    if not CADQUERY_AVAILABLE:
        return None
    
    # Convert to mm for CadQuery
    L, W, H = length * 1000, width * 1000, height * 1000
    
    # Create base channel box
    channel = cq.Workplane("XY").box(L, W, H)
    
    # Calculate number of ribs
    n_ribs = int(L / (rib_pitch * 1000))
    
    # Add ribs to bottom wall
    for i in range(n_ribs):
        x_pos = (i + 0.5) * rib_pitch * 1000 - L / 2
        
        # Create rib
        rib = create_rib_geometry(rib_type, rib_height, rib_thickness, width)
        
        if rib is not None:
            # Position rib at bottom
            rib_positioned = rib.translate((x_pos, 0, -H / 2))
            channel = channel.union(rib_positioned)
    
    # Add ribs to top wall
    for i in range(n_ribs):
        if staggered:
            # Offset by half pitch
            x_pos = (i + 1.0) * rib_pitch * 1000 - L / 2
        else:
            x_pos = (i + 0.5) * rib_pitch * 1000 - L / 2
        
        # Create rib
        rib = create_rib_geometry(rib_type, rib_height, rib_thickness, width)
        
        if rib is not None:
            # Position rib at top (inverted)
            rib_positioned = rib.rotate((0, 0, 0), (1, 0, 0), 180).translate((x_pos, 0, H / 2))
            channel = channel.union(rib_positioned)
    
    return channel


def create_battery_cell(
    length: float,
    width: float,
    height: float
) -> Optional[object]:
    """
    Create single battery cell geometry.
    
    Args:
        length: Cell length [m]
        width: Cell width [m]
        height: Cell height [m]
    
    Returns:
        CadQuery Workplane object or None
    """
    if not CADQUERY_AVAILABLE:
        return None
    
    L, W, H = length * 1000, width * 1000, height * 1000
    
    cell = cq.Workplane("XY").box(L, W, H)
    
    return cell


def create_cell_array(
    n_rows: int,
    n_cols: int,
    cell_length: float,
    cell_width: float,
    cell_height: float,
    gap: float = 0.002
) -> Optional[object]:
    """
    Create array of battery cells.
    
    Args:
        n_rows: Number of rows
        n_cols: Number of columns
        cell_length: Individual cell length [m]
        cell_width: Individual cell width [m]
        cell_height: Individual cell height [m]
        gap: Gap between cells [m]
    
    Returns:
        CadQuery Workplane assembly or None
    """
    if not CADQUERY_AVAILABLE:
        return None
    
    # Convert to mm
    L = cell_length * 1000
    W = cell_width * 1000
    H = cell_height * 1000
    g = gap * 1000
    
    # Create assembly
    assembly = None
    
    for i in range(n_rows):
        for j in range(n_cols):
            cell = create_battery_cell(cell_length, cell_width, cell_height)
            
            # Position cell
            x_pos = j * (L + g) - (n_cols - 1) * (L + g) / 2
            y_pos = i * (W + g) - (n_rows - 1) * (W + g) / 2
            
            cell_positioned = cell.translate((x_pos, y_pos, 0))
            
            if assembly is None:
                assembly = cell_positioned
            else:
                assembly = assembly.union(cell_positioned)
    
    return assembly


def create_module_assembly(
    n_channels: int,
    channel_length: float,
    channel_width: float,
    channel_height: float,
    n_cells_per_channel: int,
    cell_length: float,
    cell_width: float,
    cell_height: float,
    rib_type: Literal["rect", "tri", "semi", "dimple"] = "rect",
    rib_height: float = 0.003,
    rib_thickness: float = 0.002,
    rib_pitch: float = 0.02,
    staggered: bool = False
) -> Optional[object]:
    """
    Create complete battery pack module with channels and cells.
    
    Args:
        n_channels: Number of parallel cooling channels
        channel_length: Channel length [m]
        channel_width: Channel width [m]
        channel_height: Channel height [m]
        n_cells_per_channel: Number of cells per channel
        cell_length: Cell length [m]
        cell_width: Cell width [m]
        cell_height: Cell height [m]
        rib_type: Rib cross-section type
        rib_height: Rib height [m]
        rib_thickness: Rib thickness [m]
        rib_pitch: Rib spacing [m]
        staggered: Staggered rib arrangement
    
    Returns:
        CadQuery Workplane assembly or None
    """
    if not CADQUERY_AVAILABLE:
        return None
    
    assembly = None
    
    # Channel spacing
    channel_spacing = (cell_height + channel_height) * 1000  # mm
    
    # Create channels
    for i in range(n_channels):
        channel = create_ribbed_channel(
            channel_length,
            channel_width,
            channel_height,
            rib_type,
            rib_height,
            rib_thickness,
            rib_pitch,
            staggered
        )
        
        y_pos = i * channel_spacing - (n_channels - 1) * channel_spacing / 2
        
        channel_positioned = channel.translate((0, y_pos, 0))
        
        if assembly is None:
            assembly = channel_positioned
        else:
            assembly = assembly.union(channel_positioned)
    
    # Add cells (simplified - positioned between channels)
    # In practice, cells would be more precisely positioned
    
    return assembly


def export_to_step(geometry: object, filename: str) -> None:
    """
    Export geometry to STEP file.
    
    Args:
        geometry: CadQuery Workplane object
        filename: Output filename (.step or .stp)
    """
    if not CADQUERY_AVAILABLE or geometry is None:
        return
    
    try:
        geometry.val().exportStep(filename)
    except Exception as e:
        print(f"Warning: Could not export STEP file: {e}")


def export_to_stl(geometry: object, filename: str, tolerance: float = 0.001) -> None:
    """
    Export geometry to STL file (for meshing).
    
    Args:
        geometry: CadQuery Workplane object
        filename: Output filename (.stl)
        tolerance: Mesh tolerance [mm]
    """
    if not CADQUERY_AVAILABLE or geometry is None:
        return
    
    try:
        geometry.val().exportStl(filename, tolerance=tolerance)
    except Exception as e:
        print(f"Warning: Could not export STL file: {e}")


def calculate_channel_volume(
    length: float,
    width: float,
    height: float,
    rib_height: float,
    rib_thickness: float,
    rib_pitch: float
) -> float:
    """
    Calculate net fluid volume in ribbed channel.
    
    Args:
        length: Channel length [m]
        width: Channel width [m]
        height: Channel height [m]
        rib_height: Rib height [m]
        rib_thickness: Rib thickness [m]
        rib_pitch: Rib pitch [m]
    
    Returns:
        Net fluid volume [m³]
    """
    # Base channel volume
    V_base = length * width * height
    
    # Volume blocked by ribs
    n_ribs = int(length / rib_pitch)
    V_rib_single = rib_height * rib_thickness * width
    V_ribs_total = 2 * n_ribs * V_rib_single  # Top and bottom
    
    # Net volume
    V_net = V_base - V_ribs_total
    
    return max(V_net, 0.0)


def calculate_wetted_area(
    length: float,
    width: float,
    height: float,
    rib_height: float,
    rib_thickness: float,
    rib_pitch: float,
    rib_type: Literal["rect", "tri", "semi", "dimple"] = "rect"
) -> float:
    """
    Calculate wetted surface area in ribbed channel.
    
    Args:
        length: Channel length [m]
        width: Channel width [m]
        height: Channel height [m]
        rib_height: Rib height [m]
        rib_thickness: Rib thickness [m]
        rib_pitch: Rib pitch [m]
        rib_type: Rib cross-section type
    
    Returns:
        Wetted area [m²]
    """
    # Base smooth wall area
    A_smooth = 2 * (length * width + length * height) + 2 * width * height
    
    # Additional area from ribs
    n_ribs = int(length / rib_pitch)
    
    if rib_type == "rect":
        # Rectangular ribs add front, back, and top surfaces
        A_rib_single = 2 * rib_height * width + rib_thickness * width
    elif rib_type == "tri":
        # Triangular ribs - two slanted sides
        slant_length = np.sqrt(rib_height**2 + (rib_thickness / 2)**2)
        A_rib_single = 2 * slant_length * width
    elif rib_type == "semi":
        # Semicircular - approximate as half cylinder
        A_rib_single = np.pi * rib_height * width
    else:  # dimple
        # Dimple adds less area
        A_rib_single = np.pi * rib_height * rib_thickness * 0.5
    
    A_ribs_total = 2 * n_ribs * A_rib_single  # Top and bottom
    
    A_total = A_smooth + A_ribs_total
    
    return A_total
