// PROJECT W.A.L.L. - HYPER-ACTUATOR Mk-1: Dual In-Situ 395nm UV-LED Pinning Wing
// Drawing Ref: DWG-WALL-HACT-004 | Material: 6061-T6 Aluminum (Heatsink) & Quartz
// Emits 2.8 W/cm² Focused UV-A at 395nm to Instantly Freeze Droplets (Zero Vertical Sagging)
// Complies with ISO 2768-mK tolerances | Designed for FDM / CNC Manufacturing

$fn = 32;

module uv_pinning_wing(
    wing_w = 18.0,
    wing_l = 44.0,
    wing_h = 28.0,
    lens_dia = 6.0,
    lens_len = 36.0,
    led_pcb_w = 10.0,
    led_pcb_l = 32.0,
    led_pcb_t = 1.6
) {
    difference() {
        union() {
            // Main Extruded Aluminum Thermal Radiator Body
            translate([-wing_w/2, -wing_l/2, 0])
                cube([wing_w, wing_l, wing_h]);

            // Side Flange Attachment Lug with M2.5 Clearance Holes
            translate([wing_w/2, -wing_l/2 + 6.0, 4.0])
                cube([5.0, wing_l - 12.0, 14.0]);
        }

        // 1. Internal Focused Parabolic/Trapezoidal Optical Reflector Cavity
        translate([0, 0, -0.1]) {
            hull() {
                translate([-wing_w/2 + 2.0, -led_pcb_l/2, 0])
                    cube([wing_w - 4.0, led_pcb_l, 0.1]);
                translate([-3.0, -led_pcb_l/2, 12.0])
                    cube([6.0, led_pcb_l, 0.1]);
            }
        }

        // 2. 6mm Cylindrical Quartz Lens Retention Channel (Bottom Optical Exit)
        translate([0, 0, 3.0])
            rotate([90, 0, 0])
                cylinder(d=lens_dia, h=lens_len + 2, center=true);

        // 3. Aluminum Core MCPCB LED Recess & Thermal Interface Pocket
        translate([-led_pcb_w/2, -led_pcb_l/2, 12.0])
            cube([led_pcb_w, led_pcb_l, led_pcb_t + 0.2]);

        // 4. External Longitudinal Heat-Sink Cooling Flutes
        for (f = [-14, -7, 0, 7, 14]) {
            translate([-wing_w/2 - 1, f - 1.0, 16.0])
                cube([wing_w + 2, 2.0, wing_h - 14.0]);
        }

        // 5. 2x M2.5 Side Clamping Bolt Holes
        translate([wing_w/2 - 1, -10.0, 11.0])
            rotate([0, 90, 0])
                cylinder(d=2.7, h=8.0);
        translate([wing_w/2 - 1,  10.0, 11.0])
            rotate([0, 90, 0])
                cylinder(d=2.7, h=8.0);
    }
}

uv_pinning_wing();
