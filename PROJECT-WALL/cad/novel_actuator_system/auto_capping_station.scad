// PROJECT W.A.L.L. - HYPER-ACTUATOR Mk-1: Motorized Auto-Sealing Capping & Purge Dock
// Drawing Ref: DWG-WALL-HACT-006 | Material: PETG (Arm) & Platinum Silicone (Capping Boot)
// Actuated by 9g Micro-Servo. Hermetically Seals 128-Nozzle Orifice Plate During Pauses.
// Complies with ISO 2768-mK tolerances | Designed for FDM 3D Printing

$fn = 32;

module auto_capping_station(
    arm_len = 38.0,
    arm_w = 14.0,
    arm_t = 6.0,
    cap_w = 16.0,
    cap_l = 32.0,
    servo_spline_d = 4.8
) {
    difference() {
        union() {
            // Main Articulated Servo Swing-Arm
            hull() {
                cylinder(d=12.0, h=arm_t);
                translate([arm_len, 0, 0])
                    cylinder(d=cap_w, h=arm_t);
            }

            // Distal Silicone Boot Retention Rim
            translate([arm_len - cap_l/2, -cap_w/2, arm_t])
                cube([cap_l, cap_w, 2.5]);

            // Perimeter Sealing Lip Boss
            translate([arm_len - (cap_l-4)/2, -(cap_w-4)/2, arm_t + 2.5])
                difference() {
                    cube([cap_l - 4, cap_w - 4, 2.0]);
                    translate([1.5, 1.5, -0.5])
                        cube([cap_l - 7, cap_w - 7, 3.0]);
                }
        }

        // 1. 9g Metal Gear Servo 21T Micro-Spline Bore
        translate([0, 0, -1])
            cylinder(d=servo_spline_d, h=arm_t + 2);

        // 2. Waste Ink Drain Port
        translate([arm_len, 0, -1])
            cylinder(d=2.6, h=arm_t + 6.0);
    }
}

auto_capping_station();
