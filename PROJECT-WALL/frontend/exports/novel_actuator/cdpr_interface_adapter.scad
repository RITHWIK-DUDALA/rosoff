// PROJECT W.A.L.L. - HYPER-ACTUATOR Mk-1: CDPR Carriage Structural Interface Adapter Plate
// Drawing Ref: DWG-WALL-HACT-001 | Material: 6061-T6 Aluminum / Carbon Fiber Composite
// Attaches to CDPR Baseplate. Mounts MGN7C Stainless Linear Rail, VCA Stator, and Fluidics.
// Complies with ISO 2768-mK tolerances | Designed for CNC Milling / FDM 3D Printing

$fn = 32;

// Standard DIN 912 M3 Socket Head Cap Screw & Counterbore
module din912_m3_bore(h_thru = 12.0, cbore_depth = 3.2) {
    translate([0, 0, -1]) cylinder(d = 3.4, h = h_thru + 2); // M3 clearance
    translate([0, 0, h_thru - cbore_depth]) cylinder(d = 6.2, h = cbore_depth + 1); // DIN 912 head pocket
}

// Standard DIN 912 M2 Socket Head Cap Screw & Counterbore
module din912_m2_bore(h_thru = 10.0, cbore_depth = 2.2) {
    translate([0, 0, -1]) cylinder(d = 2.4, h = h_thru + 2); // M2 clearance
    translate([0, 0, h_thru - cbore_depth]) cylinder(d = 4.4, h = cbore_depth + 1); // Head pocket
}

module cdpr_interface_adapter(
    adapter_w = 98.0,
    adapter_h = 78.0,
    adapter_t = 6.5,
    rail_len = 66.0,
    rail_w = 7.0
) {
    difference() {
        // Main CNC 6061-T6 Baseplate with Filleted Corners
        hull() {
            r = 6.0;
            translate([-adapter_w/2 + r, -adapter_h/2 + r, 0]) cylinder(r=r, h=adapter_t);
            translate([ adapter_w/2 - r, -adapter_h/2 + r, 0]) cylinder(r=r, h=adapter_t);
            translate([-adapter_w/2 + r,  adapter_h/2 - r, 0]) cylinder(r=r, h=adapter_t);
            translate([ adapter_w/2 - r,  adapter_h/2 - r, 0]) cylinder(r=r, h=adapter_t);
        }

        // 1. Central Actuator Aperture (Chamfered Optical/Nozzle Projection Window)
        translate([0, 0, -1])
            cylinder(d1=24.0, d2=22.0, h=adapter_t + 2);

        // 2. HIWIN MGN7C Miniature Linear Rail Precision Ground Datum Bed
        translate([-rail_w/2 - 0.1, -rail_len/2, adapter_t - 1.8])
            cube([rail_w + 0.2, rail_len, 2.0]);

        // MGN7C Rail Mounting Holes (4x M2 tapped, 15mm pitch)
        for (y = [-22.5, -7.5, 7.5, 22.5]) {
            translate([0, y, 0])
                din912_m2_bore(adapter_t, 2.2);
        }

        // 3. Voice Coil Actuator (VCA) Stator Housing Pocket & Fasteners
        translate([0, 24.0, adapter_t - 3.8]) {
            cylinder(d=26.2, h=4.0); // Precision Stator Pocket
            translate([0, 0, -adapter_t])
                cylinder(d=10.0, h=adapter_t + 2); // Center Core Ventilation
            for (a = [30, 150, 270]) {
                rotate([0, 0, a])
                    translate([16.0, 0, -adapter_t])
                        cylinder(d=2.6, h=adapter_t + 2); // M2.5 Tapped Holes
            }
        }

        // 4. 4x CDPR Platform Elastomer Vibration-Damping Grommet Bores
        for (x = [-38.0, 38.0]) {
            for (y = [-28.0, 28.0]) {
                translate([x, y, -1]) {
                    cylinder(d=6.5, h=adapter_t + 2); // Bushing outer diameter
                    translate([0, 0, 3.2])
                        cylinder(d=9.8, h=adapter_t); // Flange step
                }
            }
        }

        // 5. Meniscus Reservoir Mounting Flange (Right Flank)
        translate([32.0, 0, 0]) {
            translate([0, -14.0, 0]) din912_m3_bore(adapter_t, 3.2);
            translate([0,  14.0, 0]) din912_m3_bore(adapter_t, 3.2);
        }

        // 6. Auto-Capping 9g Micro-Servo Pocket (Left Flank)
        translate([-32.0, -10.0, -1]) {
            translate([-6.2, -12.0, 1.2]) cube([12.4, 24.0, adapter_t + 2]); // Servo Cutout
            translate([0, -14.5, 0]) cylinder(d=2.4, h=adapter_t + 2);
            translate([0,  14.5, 0]) cylinder(d=2.4, h=adapter_t + 2);
        }

        // 7. CNC Isogrid Lightening Web Pockets (Leaves 2.5mm Webbing)
        for (pos = [[-20, 25], [20, 25], [-20, -25], [20, -25], [-35, 12], [35, -12]]) {
            translate([pos[0], pos[1], 2.2])
                cylinder(r=6.0, h=adapter_t, $fn=6);
        }

        // Perimeter Chamfers (Top & Bottom)
        translate([0, 0, adapter_t - 0.4])
            difference() {
                translate([-adapter_w/2 - 1, -adapter_h/2 - 1, 0]) cube([adapter_w + 2, adapter_h + 2, 1]);
                hull() {
                    r = 5.5;
                    translate([-adapter_w/2 + r, -adapter_h/2 + r, -0.5]) cylinder(r=r, h=2);
                    translate([ adapter_w/2 - r, -adapter_h/2 + r, -0.5]) cylinder(r=r, h=2);
                    translate([-adapter_w/2 + r,  adapter_h/2 - r, -0.5]) cylinder(r=r, h=2);
                    translate([ adapter_w/2 - r,  adapter_h/2 - r, -0.5]) cylinder(r=r, h=2);
                }
            }
    }
}

// Standalone render
color([0.22, 0.25, 0.29])
    cdpr_interface_adapter();
