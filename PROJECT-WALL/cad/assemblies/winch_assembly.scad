// PROJECT W.A.L.L. - Complete High-Fidelity Corner Winch Subassembly
// Drawing Ref: DWG-WALL-CAD-001 | Material: 6061-T6 Aluminum / Silicon Steel
// Real-world mechanical CAD assembly: NEMA 17 Stepper, Helical Drum, Dual F688ZZ Bearings,
// Flexible Coupler, Fairlead Guide Pulley, and Vacuum Anchor Mounting Bracket.

$fn = 32;

use <../drums/winch_drum.scad>;

module nema17_stepper_motor() {
    difference() {
        union() {
            // 8-Sided Chamfered Stator Body (42.3 x 42.3 x 34 mm)
            hull() {
                translate([-17, -21.15, 0]) cube([34, 42.3, 34]);
                translate([-21.15, -17, 0]) cube([42.3, 34, 34]);
            }
            // Front Die-Cast Endbell (42.3 x 42.3 x 4 mm)
            translate([-21.15, -21.15, 34])
                cube([42.3, 42.3, 4]);
            // 22mm Pilot Boss Collar
            translate([0, 0, 38])
                cylinder(d=22.0, h=2.5);
            // Rear Die-Cast Endbell
            translate([-21.15, -21.15, -4])
                cube([42.3, 42.3, 4]);
        }

        // 4x Tapped M3 Corner Screws (PCD 31.0 mm)
        for (x = [-15.5, 15.5]) {
            for (y = [-15.5, 15.5]) {
                translate([x, y, 32])
                    cylinder(d=3.0, h=10);
            }
        }

        // Longitudinal Heat-sink Cooling Flutes
        for (f = [-12, -4, 4, 12]) {
            translate([f, -22, 1]) cube([1.5, 44, 32]);
            translate([-22, f, 1]) cube([44, 1.5, 32]);
        }
    }

    // 5mm D-Cut Ground Stainless Steel Shaft (Extension: 24mm)
    difference() {
        translate([0, 0, 40])
            cylinder(d=5.0, h=24);
        translate([2.0, -3.0, 42])
            cube([2.0, 6.0, 24]);
    }

    // 4-Pin JST-XH Stepper Wiring Harness (Red, Blue, Green, Black)
    translate([0, -22, -10]) {
        color([0.9, 0.2, 0.2]) translate([-4.5, 0, 0]) cylinder(d=1.2, h=16);
        color([0.2, 0.5, 0.9]) translate([-1.5, 0, 0]) cylinder(d=1.2, h=16);
        color([0.1, 0.8, 0.3]) translate([ 1.5, 0, 0]) cylinder(d=1.2, h=16);
        color([0.1, 0.1, 0.1]) translate([ 4.5, 0, 0]) cylinder(d=1.2, h=16);
        // Connector Housing
        color([1, 1, 1]) translate([-6.5, -3, -6]) cube([13, 6, 6]);
    }
}

module corner_winch_assembly() {
    // 1. CNC 6061-T6 Corner Mounting Baseplate (75 x 75 x 6 mm)
    color([0.2, 0.22, 0.26]) {
        difference() {
            translate([-37.5, -37.5, 0])
                cube([75, 75, 6]);
            // 4x M5 Counterbores
            for (x = [-28, 28]) {
                for (y = [-28, 28]) {
                    translate([x, y, -1]) cylinder(d=5.5, h=8);
                    translate([x, y, 3]) cylinder(d=9.0, h=4);
                }
            }
        }
    }

    // Dual Vacuum Suction Cups with Brass Barbs
    color([0.12, 0.13, 0.15]) {
        translate([-22, 0, -8]) cylinder(d=44, h=8);
        translate([ 22, 0, -8]) cylinder(d=44, h=8);
    }
    color([0.85, 0.6, 0.15]) {
        translate([-22, 0, -14]) cylinder(d=6, h=6);
        translate([ 22, 0, -14]) cylinder(d=6, h=6);
    }

    // 2. NEMA 17 Motor Body
    color([0.15, 0.17, 0.2])
        translate([0, 0, 10])
            nema17_stepper_motor();

    // 3. Flexible Beam Shaft Coupler (19mm OD x 25mm Length)
    color([0.7, 0.72, 0.75])
        translate([0, 0, 72])
            cylinder(d=19.0, h=25);

    // 4. Helical Grooved Winch Drum
    color([0.65, 0.68, 0.72])
        translate([0, 0, 110])
            winch_drum();

    // 5. Dual F688ZZ Flanged Ball Bearings & Pillow Blocks
    color([0.85, 0.88, 0.9]) {
        translate([0, 0, 96]) cylinder(d=18, h=5);
        translate([0, 0, 137]) cylinder(d=18, h=5);
    }
    color([0.25, 0.28, 0.32]) {
        translate([-26, -20, 95]) cube([10, 40, 48]);
    }

    // 6. Fairlead Tangency Guide Pulley Bracket (Brass Roller)
    color([0.85, 0.6, 0.15])
        translate([18, 18, 118])
            cylinder(d=13.0, h=10);
}

corner_winch_assembly();
