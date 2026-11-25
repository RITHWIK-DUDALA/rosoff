// PROJECT W.A.L.L. - HYPER-ACTUATOR Mk-1: Active Non-Contact Z-Stage Carriage
// Drawing Ref: DWG-WALL-HACT-002 | Material: PETG / 6061-T6 Aluminum
// Mounts to MGN7C Miniature Linear Guide Rail. Houses Voice Coil Actuator & VL53L4CD Laser.
// Complies with ISO 2768-mK tolerances | Designed for FDM 3D Printing

$fn = 32;

module active_z_stage_carriage(
    stage_w = 64.0,
    stage_h = 56.0,
    stage_t = 12.0,
    mgn7_hole_x = 12.0,
    mgn7_hole_y = 13.0,
    vca_dia = 22.4,
    vca_depth = 8.5,
    lidar_w = 14.0,
    lidar_h = 9.0,
    lidar_depth = 4.0,
    dovetail_top_w = 28.0,
    dovetail_bot_w = 32.0,
    dovetail_depth = 4.5
) {
    difference() {
        // Main Structural Body
        hull() {
            r = 4.0;
            translate([-stage_w/2 + r, -stage_h/2 + r, 0]) cylinder(r=r, h=stage_t);
            translate([ stage_w/2 - r, -stage_h/2 + r, 0]) cylinder(r=r, h=stage_t);
            translate([-stage_w/2 + r,  stage_h/2 - r, 0]) cylinder(r=r, h=stage_t);
            translate([ stage_w/2 - r,  stage_h/2 - r, 0]) cylinder(r=r, h=stage_t);
        }

        // 1. MGN7C Linear Carriage Mounting Holes (4x M2 Clearance Bores, DIN 912)
        translate([0, -10.0, -1]) {
            for (dx = [-mgn7_hole_x/2, mgn7_hole_x/2]) {
                for (dy = [-mgn7_hole_y/2, mgn7_hole_y/2]) {
                    translate([dx, dy, 0]) {
                        cylinder(d=2.4, h=stage_t + 2);
                        translate([0, 0, stage_t - 2.5])
                            cylinder(d=4.4, h=3.0);
                    }
                }
            }
        }

        // 2. High-Force Voice Coil Actuator (VCA) Recess & Center Bore
        translate([0, 14.0, stage_t - vca_depth]) {
            cylinder(d=vca_dia, h=vca_depth + 1);
            translate([0, 0, -stage_t])
                cylinder(d=8.0, h=stage_t + 2);
        }

        // 3. Central Front Dovetail Slide Receiver Channel (For Printhead Module)
        translate([0, 0, -0.1]) {
            hull() {
                translate([-dovetail_bot_w/2, -stage_h/2 - 1, 0])
                    cube([dovetail_bot_w, stage_h + 2, 0.1]);
                translate([-dovetail_top_w/2, -stage_h/2 - 1, dovetail_depth])
                    cube([dovetail_top_w, stage_h + 2, 0.1]);
            }
        }

        // 4. VL53L4CD Laser Rangefinder Optical Cavity & Emitter Windows
        translate([stage_w/2 - 12.0, 0, -1]) {
            translate([-lidar_w/2, -lidar_h/2, 1])
                cube([lidar_w, lidar_h, lidar_depth + 1]);
            translate([-3.2, 0, 0]) cylinder(d=3.5, h=stage_t + 2);
            translate([ 3.2, 0, 0]) cylinder(d=3.5, h=stage_t + 2);
            translate([0,  6.5, 0]) cylinder(d=2.2, h=stage_t + 2);
            translate([0, -6.5, 0]) cylinder(d=2.2, h=stage_t + 2);
        }

        // 5. M3 Precision Cam Lock Thumbscrew Bore (Lateral Locking)
        translate([-stage_w/2 - 1, 0, stage_t/2])
            rotate([0, 90, 0])
                cylinder(d=3.3, h=16.0);

        // 6. Skeletal Weight-Reduction Pockets
        translate([-stage_w/2 + 10.0,  18.0, 2.0]) cube([8.0, 10.0, stage_t]);
        translate([-stage_w/2 + 10.0, -18.0, 2.0]) cube([8.0, 10.0, stage_t]);
        translate([ stage_w/2 - 16.0,  18.0, 2.0]) cube([8.0, 10.0, stage_t]);
        translate([ stage_w/2 - 16.0, -18.0, 2.0]) cube([8.0, 10.0, stage_t]);
    }
}

active_z_stage_carriage();
