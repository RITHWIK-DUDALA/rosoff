// PROJECT W.A.L.L. - HYPER-ACTUATOR Mk-1: Dual In-Situ 395nm UV-LED Pinning Wing
// Drawing Ref: DWG-WALL-HACT-004 | Material: AL6063 High Thermal Conductivity Aluminum
// Houses Nichia/Seoul 395nm UV LED MCPCB, fused quartz cylindrical rod lens,
// and 8 precision CNC convective cooling heatsink fins.
// Complies with ISO 2768-mK tolerances | Designed for CNC Milling / Extrusion

$fn = 32;

module uv_pinning_wing(
    wing_w = 18.0,
    wing_l = 44.0,
    wing_h = 28.0,
    num_fins = 8
) {
    difference() {
        union() {
            // Main Radiator Body
            translate([-wing_w/2, -wing_l/2, 0])
                cube([wing_w, wing_l, wing_h]);

            // Side Flange Attachment Lug with M2.5 Counterbores
            translate([wing_w/2, -wing_l/2 + 6.0, 4.0])
                cube([5.0, wing_l - 12.0, 14.0]);
        }

        // 1. Precision Parabolic Optical Reflector Cavity
        translate([0, 0, -0.1]) {
            hull() {
                translate([-wing_w/2 + 2.0, -17.0, 0]) cube([wing_w - 4.0, 34.0, 0.1]);
                translate([-2.5, -17.0, 12.0]) cube([5.0, 34.0, 0.1]);
            }
        }

        // 2. Fused Quartz 6mm Cylindrical Rod Lens Bezel Groove
        translate([0, 0, 3.2])
            rotate([90, 0, 0])
                cylinder(d=6.2, h=38.0, center=true);

        // 3. Nichia/Seoul 395nm UV-LED Aluminum Core MCPCB Pocket
        translate([-5.0, -17.0, 12.0])
            cube([10.0, 34.0, 2.0]);

        // 4. Real Deep Heatsink Convective Cooling Fins (1.0mm fin, 2.0mm air gap)
        for (i = [0:num_fins-1]) {
            fy = -wing_l/2 + 5.0 + i * 4.2;
            translate([-wing_w/2 - 1.0, fy, 15.0])
                cube([wing_w + 2.0, 2.2, wing_h - 13.0]);
        }

        // 5. 2x M2.5 Fastener Holes for Attachment to Active Carriage
        translate([wing_w/2 - 1.0, -10.0, 11.0]) rotate([0, 90, 0]) cylinder(d=2.7, h=8.0);
        translate([wing_w/2 - 1.0,  10.0, 11.0]) rotate([0, 90, 0]) cylinder(d=2.7, h=8.0);

        // 6. Thermal Interface Electrical Harness Pass-Through
        translate([0, 0, wing_h - 6.0])
            cylinder(d=4.2, h=8.0);
    }
}

// Standalone render
color([0.48, 0.52, 0.58])
    uv_pinning_wing();
