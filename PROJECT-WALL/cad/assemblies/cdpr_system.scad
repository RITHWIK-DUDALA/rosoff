// PROJECT W.A.L.L. - Full 4-Cable Planar Parallel CDPR Machine CAD Assembly
// Drawing Ref: DWG-WALL-CAD-000 | Architecture: 2-DOF 4-Cable Planar Robot
// Real-world physical assembly according to real-world physics and kinematics.
// Complies with ISO 2768-mK tolerances | Strictly zero blue, precision industrial palette.

$fn = 32;

use <../end_effector/platform.scad>;
use <../end_effector/compliance_spring.scad>;
use <../printheads/inkjet_module.scad>;
use <winch_assembly.scad>;

// System Dimensions (mm)
surface_w = 800.0;
surface_h = 600.0;

// Central End-Effector Position (Configurable coordinate)
ee_x = 400.0;
ee_y = 300.0;

module full_cdpr_system() {
    // 1. Structural Surface Board (800 x 600 x 14 mm White Primed Panel)
    color([0.96, 0.97, 0.98])
        cube([surface_w, surface_h, 14]);

    // Extruded Aluminum Perimeter Frame Trim
    color([0.58, 0.62, 0.68]) {
        translate([-4, -4, 0]) cube([surface_w + 8, 4, 18]);
        translate([-4, surface_h, 0]) cube([surface_w + 8, 4, 18]);
        translate([-4, -4, 0]) cube([4, surface_h + 8, 18]);
        translate([surface_w, -4, 0]) cube([4, surface_h + 8, 18]);
    }

    // 2. Printable Margin Boundary Line (100mm Margin in Safety Amber — No Blue)
    color([0.96, 0.62, 0.07]) {
        translate([100, 100, 14.2]) {
            difference() {
                cube([surface_w - 200, surface_h - 200, 1.0]);
                translate([2, 2, -0.5])
                    cube([surface_w - 204, surface_h - 204, 2.0]);
            }
        }
    }

    // 3. Four Corner NEMA 17 Winch Assemblies (A1..A4)
    // A1: Upper-Left (0, 600)
    translate([0, surface_h, 14])
        rotate([0, 0, -90])
            corner_winch_assembly();

    // A2: Upper-Right (800, 600)
    translate([surface_w, surface_h, 14])
        rotate([0, 0, 180])
            corner_winch_assembly();

    // A3: Lower-Left (0, 0)
    translate([0, 0, 14])
        rotate([0, 0, 0])
            corner_winch_assembly();

    // A4: Lower-Right (800, 0)
    translate([surface_w, 0, 14])
        rotate([0, 0, 90])
            corner_winch_assembly();

    // 4. Central Suspended 2-DOF Platform Assembly
    translate([ee_x, ee_y, 16]) {
        // CNC 6061-T6 Pocketed Baseplate
        color([0.58, 0.62, 0.68])
            platform_chassis();

        // 1.2N Helical Compliance Spring
        color([0.96, 0.62, 0.07])
            translate([0, 0, 18])
                helical_spring();

        // Interchangeable Actuator (Module A: Piezo Printhead)
        color([0.22, 0.25, 0.3])
            translate([0, 0, 26])
                piezo_printhead();

        // 3 POM Ball Transfer Standoff Rollers (protruding to wall surface)
        color([0.85, 0.88, 0.9]) {
            translate([-42, 0, -2]) sphere(d=8);
            translate([ 42, 28, -2]) sphere(d=8);
            translate([ 42, -28, -2]) sphere(d=8);
        }
    }

    // 5. Four Braided Dyneema Cables (C1..C4) connecting anchors to platform eyelets
    color([0.95, 0.96, 0.98]) {
        // C1: A1 (18, 582, 120) to B1 (ee_x - 47, ee_y + 34.5, 24)
        hull() {
            translate([18, surface_h - 18, 120]) sphere(d=2.0);
            translate([ee_x - 47, ee_y + 34.5, 24]) sphere(d=2.0);
        }
        // C2: A2 (782, 582, 120) to B2 (ee_x + 47, ee_y + 34.5, 24)
        hull() {
            translate([surface_w - 18, surface_h - 18, 120]) sphere(d=2.0);
            translate([ee_x + 47, ee_y + 34.5, 24]) sphere(d=2.0);
        }
        // C3: A3 (18, 18, 120) to B3 (ee_x - 47, ee_y - 34.5, 24)
        hull() {
            translate([18, 18, 120]) sphere(d=2.0);
            translate([ee_x - 47, ee_y - 34.5, 24]) sphere(d=2.0);
        }
        // C4: A4 (782, 18, 120) to B4 (ee_x + 47, ee_y - 34.5, 24)
        hull() {
            translate([surface_w - 18, 18, 120]) sphere(d=2.0);
            translate([ee_x + 47, ee_y - 34.5, 24]) sphere(d=2.0);
        }
    }
}

full_cdpr_system();
