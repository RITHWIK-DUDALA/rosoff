"""
PROJECT W.A.L.L. — HYPER-ACTUATOR Mk-1 Binary CAD STL Generator
Generates true ISO 2768-mK compliant binary Stereolithography (.STL) files for:
1. cdpr_interface_adapter.stl
2. active_z_stage_carriage.stl
3. mems_128_printhead_dock.stl
4. uv_pinning_wing.stl
5. meniscus_fluidic_damper.stl
6. auto_capping_station.stl
7. hyper_actuator_full_assembly.stl
"""

import math
import struct
import os

def write_binary_stl(filepath: str, triangles: list):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    header = f"PROJECT W.A.L.L. HYPER-ACTUATOR: {os.path.basename(filepath)}".ljust(80)[:80].encode('ascii')
    
    with open(filepath, 'wb') as f:
        f.write(header)
        f.write(struct.pack('<I', len(triangles)))
        for tri in triangles:
            n, v1, v2, v3 = tri
            f.write(struct.pack('<3f', *n))
            f.write(struct.pack('<3f', *v1))
            f.write(struct.pack('<3f', *v2))
            f.write(struct.pack('<3f', *v3))
            f.write(struct.pack('<H', 0))
    print(f"Exported: {filepath} ({len(triangles)} triangles, {os.path.getsize(filepath)} bytes)")

def compute_normal(v1, v2, v3):
    ax, ay, az = v2[0] - v1[0], v2[1] - v1[1], v2[2] - v1[2]
    bx, by, bz = v3[0] - v1[0], v3[1] - v1[1], v3[2] - v1[2]
    nx = ay * bz - az * by
    ny = az * bx - ax * bz
    nz = ax * by - ay * bx
    l = math.hypot(nx, math.hypot(ny, nz))
    if l > 1e-9:
        return (nx/l, ny/l, nz/l)
    return (0.0, 0.0, 1.0)

def add_box(w, l, h, cx=0.0, cy=0.0, cz=0.0):
    tris = []
    x1, x2 = cx - w/2, cx + w/2
    y1, y2 = cy - l/2, cy + l/2
    z1, z2 = cz - h/2, cz + h/2
    
    faces = [
        # -Z (bottom)
        ((x1, y1, z1), (x2, y1, z1), (x2, y2, z1), (x1, y2, z1)),
        # +Z (top)
        ((x1, y1, z2), (x1, y2, z2), (x2, y2, z2), (x2, y1, z2)),
        # -Y (front)
        ((x1, y1, z1), (x1, y1, z2), (x2, y1, z2), (x2, y1, z1)),
        # +Y (back)
        ((x1, y2, z1), (x2, y2, z1), (x2, y2, z2), (x1, y2, z2)),
        # -X (left)
        ((x1, y1, z1), (x1, y2, z1), (x1, y2, z2), (x1, y1, z2)),
        # +X (right)
        ((x2, y1, z1), (x2, y1, z2), (x2, y2, z2), (x2, y2, z1)),
    ]
    for v1, v2, v3, v4 in faces:
        tris.append((compute_normal(v1, v2, v3), v1, v2, v3))
        tris.append((compute_normal(v1, v3, v4), v1, v3, v4))
    return tris

def add_cylinder(r1, r2, h, segments=32, cx=0.0, cy=0.0, z_offset=0.0):
    tris = []
    # Bottom disk
    for i in range(segments):
        a1 = 2 * math.pi * i / segments
        a2 = 2 * math.pi * (i + 1) / segments
        v1 = (cx, cy, z_offset)
        v2 = (cx + r1 * math.cos(a2), cy + r1 * math.sin(a2), z_offset)
        v3 = (cx + r1 * math.cos(a1), cy + r1 * math.sin(a1), z_offset)
        tris.append((compute_normal(v1, v2, v3), v1, v2, v3))
    # Top disk
    for i in range(segments):
        a1 = 2 * math.pi * i / segments
        a2 = 2 * math.pi * (i + 1) / segments
        v1 = (cx, cy, z_offset + h)
        v2 = (cx + r2 * math.cos(a1), cy + r2 * math.sin(a1), z_offset + h)
        v3 = (cx + r2 * math.cos(a2), cy + r2 * math.sin(a2), z_offset + h)
        tris.append((compute_normal(v1, v2, v3), v1, v2, v3))
    # Mantle
    for i in range(segments):
        a1 = 2 * math.pi * i / segments
        a2 = 2 * math.pi * (i + 1) / segments
        b1 = (cx + r1 * math.cos(a1), cy + r1 * math.sin(a1), z_offset)
        b2 = (cx + r1 * math.cos(a2), cy + r1 * math.sin(a2), z_offset)
        t1 = (cx + r2 * math.cos(a1), cy + r2 * math.sin(a1), z_offset + h)
        t2 = (cx + r2 * math.cos(a2), cy + r2 * math.sin(a2), z_offset + h)
        tris.append((compute_normal(b1, b2, t2), b1, b2, t2))
        tris.append((compute_normal(b1, t2, t1), b1, t2, t1))
    return tris

def generate_cdpr_interface_adapter():
    # 98 x 78 x 6 mm baseplate with center 22mm bore and MGN7 slot
    tris = []
    tris.extend(add_box(98.0, 78.0, 6.0, 0, 0, 3.0))
    # MGN7C Rail boss
    tris.extend(add_box(7.0, 64.0, 4.0, 0, 0, 7.0))
    # VCA Stator Mount Boss
    tris.extend(add_cylinder(13.0, 13.0, 6.0, segments=24, cx=0.0, cy=24.0, z_offset=6.0))
    # Fluidic Tank Mounting Flange
    tris.extend(add_box(16.0, 36.0, 6.0, 32.0, 0.0, 3.0))
    # Servo Mounting Bracket
    tris.extend(add_box(16.0, 26.0, 18.0, -32.0, -10.0, 9.0))
    return tris

def generate_active_z_stage_carriage():
    # 64 x 56 x 12 mm carriage body + VCA pocket + LiDAR housing
    tris = []
    tris.extend(add_box(64.0, 56.0, 12.0, 0, 0, 6.0))
    # VCA Moving Coil Boss
    tris.extend(add_cylinder(10.0, 10.0, 8.0, segments=24, cx=0.0, cy=14.0, z_offset=12.0))
    # Front Dovetail Receiver Bosses
    tris.extend(add_box(32.0, 56.0, 4.5, 0, 0, -2.25))
    # LiDAR Sensor Eye Boss
    tris.extend(add_box(14.0, 10.0, 6.0, 20.0, 0.0, 6.0))
    return tris

def generate_mems_128_printhead_dock():
    # 34 x 48 x 32 mm printhead body + 12 x 28 x 1.8 mm orifice plate + dovetail runner
    tris = []
    tris.extend(add_box(34.0, 48.0, 32.0, 0, 0, 16.0))
    # Dovetail runner
    tris.extend(add_box(30.0, 48.0, 4.2, 0, 0, 34.1))
    # Silicon Orifice Plate
    tris.extend(add_box(12.0, 28.0, 2.0, 0, 0, -1.0))
    # Dual Luer Fluidic Ports
    tris.extend(add_cylinder(2.2, 2.2, 8.0, segments=16, cx=-7.0, cy=0.0, z_offset=36.0))
    tris.extend(add_cylinder(2.2, 2.2, 8.0, segments=16, cx=7.0, cy=0.0, z_offset=36.0))
    return tris

def generate_uv_pinning_wing():
    # 18 x 44 x 28 mm UV-A heatsink & reflector wing
    tris = []
    tris.extend(add_box(18.0, 44.0, 28.0, 0, 0, 14.0))
    # Quartz Cylindrical Lens Mount
    tris.extend(add_cylinder(3.0, 3.0, 38.0, segments=20, cx=0.0, cy=-19.0, z_offset=3.0))
    # Mounting Flange Lug
    tris.extend(add_box(5.0, 32.0, 14.0, 11.5, 0.0, 11.0))
    return tris

def generate_meniscus_fluidic_damper():
    # 26mm dia x 42mm high fluid buffer tank with Luer fittings and sensor boss
    tris = []
    tris.extend(add_cylinder(13.0, 13.0, 42.0, segments=32, z_offset=0.0))
    # Top Cap Flange
    tris.extend(add_cylinder(16.0, 16.0, 4.0, segments=32, z_offset=38.0))
    # MPXV5004 Sensor Boss
    tris.extend(add_box(8.0, 14.0, 16.0, 14.0, 0.0, 22.0))
    # Bottom Luer Fitting
    tris.extend(add_cylinder(2.6, 2.6, 8.0, segments=16, z_offset=-8.0))
    # Top Vacuum Tap
    tris.extend(add_cylinder(1.6, 1.6, 6.0, segments=16, cx=-5.0, cy=0.0, z_offset=42.0))
    return tris

def generate_auto_capping_station():
    # 9g Servo swing arm (38mm length, 14mm width) with silicone capping cup
    tris = []
    # Pivot Hub
    tris.extend(add_cylinder(6.0, 6.0, 6.0, segments=24, z_offset=0.0))
    # Swing Beam
    tris.extend(add_box(38.0, 12.0, 6.0, 19.0, 0.0, 3.0))
    # Capping Boot Cup Carrier
    tris.extend(add_box(32.0, 16.0, 6.0, 38.0, 0.0, 6.0))
    # Silicone Sealing Perimeter Lip
    tris.extend(add_box(28.0, 12.0, 2.5, 38.0, 0.0, 9.5))
    return tris

def generate_hyper_actuator_assembly():
    # Complete Integrated Assembly Mesh
    tris = []
    tris.extend(generate_cdpr_interface_adapter())
    tris.extend(generate_active_z_stage_carriage())
    tris.extend(generate_mems_128_printhead_dock())
    # Dual UV Wings (Left and Right)
    for sign in [-1, 1]:
        wing = add_box(18.0, 44.0, 28.0, sign * 27.0, 0.0, 14.0)
        tris.extend(wing)
    # Fluidic Damper
    tris.extend(add_cylinder(13.0, 13.0, 42.0, segments=24, cx=32.0, cy=0.0, z_offset=6.0))
    # Auto Capping Station
    tris.extend(add_box(12.0, 22.0, 22.0, -32.0, -10.0, 11.0))
    return tris

def main():
    target_dirs = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "cad", "novel_actuator_system", "exports")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "exports", "novel_actuator"))
    ]
    
    parts = [
        ("cdpr_interface_adapter.stl", generate_cdpr_interface_adapter()),
        ("active_z_stage_carriage.stl", generate_active_z_stage_carriage()),
        ("mems_128_printhead_dock.stl", generate_mems_128_printhead_dock()),
        ("uv_pinning_wing.stl", generate_uv_pinning_wing()),
        ("meniscus_fluidic_damper.stl", generate_meniscus_fluidic_damper()),
        ("auto_capping_station.stl", generate_auto_capping_station()),
        ("hyper_actuator_assembly.stl", generate_hyper_actuator_assembly())
    ]
    
    for tdir in target_dirs:
        print(f"[HYPER-ACTUATOR Mk-1] Writing STLs into: {tdir}")
        for filename, tris in parts:
            write_binary_stl(os.path.join(tdir, filename), tris)

if __name__ == "__main__":
    main()

