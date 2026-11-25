// PROJECT W.A.L.L. - HYPER-ACTUATOR Mk-1: Motorized Auto-Sealing Capping Station
// Drawing Ref: DWG-WALL-HACT-006 | Material: Anodized 6061-T6 Aluminum / Platinum-Cured Silicone
// Seals printhead orifice face during park/idle, prevents solvent evaporation,
// and routes purged waste ink via suction drain.
// Complies with ISO 2768-mK tolerances | Designed for CNC Milling & Silicone Overmolding

$fn = 32;

module auto_capping_station(
    arm_len = 38.0,
    arm_t = 6.0
) {
    difference() {
        union() {
            // Articulated Swing Arm Beam with Reinforcing Rib
            hull() {
                cylinder(d=14.0, h=arm_t);
                translate([arm_len, 0, 0]) cylinder(d=18.0, h=arm_t);
            }

            // Distal Silicone Sealing Boot Retention Tray
            translate([arm_len - 16.0, -8.0, arm_t])
                cube([32.0, 16.0, 2.5]);

            // Dual Concentric Platinum Silicone Sealing Lips
            translate([arm_len - 14.0, -6.0, arm_t + 2.5])
                difference() {
                    cube([28.0, 12.0, 2.2]);
                    translate([1.5, 1.5, -0.5]) cube([25.0, 9.0, 3.2]);
                }
            translate([arm_len - 11.0, -3.5, arm_t + 2.5])
                difference() {
                    cube([22.0, 7.0, 2.2]);
                    translate([1.5, 1.5, -0.5]) cube([19.0, 4.0, 3.2]);
                }
        }

        // 1. 9g Metal Gear Servo 21T Micro-Spline Bore & Retention Bolt
        translate([0, 0, -1]) {
            cylinder(d=4.9, h=arm_t + 2); // Spline Fit
            translate([0, 0, arm_t - 2.0]) cylinder(d=6.8, h=3.0);
        }

        // 2. Peristaltic Suction Waste Evacuation Drain Port
        translate([arm_len, 0, -1])
            cylinder(d=2.6, h=arm_t + 6.0);

        // 3. Weight-Reduction Skeletonized Cutouts
        translate([16.0, -3.0, -1]) cube([12.0, 6.0, arm_t + 2]);
    }
}

// Standalone render
color([0.92, 0.58, 0.12])
    auto_capping_station();
