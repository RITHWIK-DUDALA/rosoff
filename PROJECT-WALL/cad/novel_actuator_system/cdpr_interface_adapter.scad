// PROJECT W.A.L.L. - HYPER-ACTUATOR Mk-1: CDPR Carriage Structural Interface Adapter Plate
// Drawing Ref: DWG-WALL-HACT-001 | Material: 6061-T6 Aluminum / Carbon Fiber Composite
// Attaches to CDPR Baseplate. Mounts MGN7C Stainless Linear Rail, VCA Stator, and Fluidics.
// Complies with ISO 2768-mK tolerances | Designed for CNC Milling / FDM 3D Printing

$fn = 32;

module cdpr_interface_adapter(
    adapter_w = 98.0,
    adapter_h = 78.0,
    adapter_t = 6.0,
    center_bore_dia = 22.0,
    rail_len = 64.0,
    rail_w = 7.0
) {
    difference() {
        // Main Adapter Plate Body
        hull() {
            r = 5.0;
            translate([-adapter_w/2 + r, -adapter_h/2 + r, 0]) cylinder(r=r, h=adapter_t);
            translate([ adapter_w/2 - r, -adapter_h/2 + r, 0]) cylinder(r=r, h=adapter_t);
            translate([-adapter_w/2 + r,  adapter_h/2 - r, 0]) cylinder(r=r, h=adapter_t);
            translate([ adapter_w/2 - r,  adapter_h/2 - r, 0]) cylinder(r=r, h=adapter_t);
        }

        // 1. Central Actuation Aperture (Pass-Through for Printhead Orifice Face)
        translate([0, 0, -1])
            cylinder(d=center_bore_dia, h=adapter_t + 2);

        // 2. MGN7C Miniature Linear Rail Precision Locating Slot (Depth 1.5mm)
        translate([-rail_w/2, -rail_len/2, adapter_t - 1.5])
            cube([rail_w, rail_len, 2.0]);

        // 3. MGN7C Rail M2 Counterbored Mounting Holes (4x at 15mm pitch)
        for (y = [-22.5, -7.5, 7.5, 22.5]) {
            translate([0, y, -1]) {
                cylinder(d=2.4, h=adapter_t + 2); // M2 clearance
                cylinder(d=4.4, h=3.0); // M2 screw head counterbore from rear
            }
        }

        // 4. Voice Coil Actuator (VCA) Stator Housing Pocket & Fasteners
        translate([0, 24.0, adapter_t - 3.5]) {
            cylinder(d=26.0, h=4.0);
            translate([0, 0, -adapter_t])
                cylinder(d=12.0, h=adapter_t + 2); // Central ventilation hole
            // 3x M2.5 Stator Retention Screws
            for (a = [30, 150, 270]) {
                rotate([0, 0, a])
                    translate([16.0, 0, -adapter_t])
                        cylinder(d=2.7, h=adapter_t + 2);
            }
        }

        // 5. 4x Vibration-Damping Elastomer Grommet Bores (Mounts to CDPR Baseplate)
        for (x = [-38.0, 38.0]) {
            for (y = [-28.0, 28.0]) {
                translate([x, y, -1]) {
                    cylinder(d=6.5, h=adapter_t + 2); // Damping grommet outer bore
                    translate([0, 0, 3.0])
                        cylinder(d=9.5, h=4.0); // Flange step
                }
            }
        }

        // 6. Fluidic Reservoir Mounting Boss Tapped Holes (Right Flange)
        translate([32.0, 0, -1]) {
            translate([0, -14.0, 0]) cylinder(d=3.2, h=adapter_t + 2); // M3 tap
            translate([0,  14.0, 0]) cylinder(d=3.2, h=adapter_t + 2); // M3 tap
        }

        // 7. Auto-Capping 9g Servo Mounting Pocket (Left Flange)
        translate([-32.0, -10.0, -1]) {
            translate([-6.0, -11.5, 1]) cube([12.5, 23.0, adapter_t + 2]); // 9g servo body cutout
            translate([0, -14.5, 0]) cylinder(d=2.2, h=adapter_t + 2); // M2 mounting screw
            translate([0,  14.5, 0]) cylinder(d=2.2, h=adapter_t + 2); // M2 mounting screw
        }

        // 8. Hexagonal Weight-Reduction Pockets
        for (pos = [[-20, 26], [20, 26], [-20, -26], [20, -26]]) {
            translate([pos[0], pos[1], 1.5])
                cylinder(r=5.5, h=adapter_t, $fn=6);
        }
    }
}

cdpr_interface_adapter();
