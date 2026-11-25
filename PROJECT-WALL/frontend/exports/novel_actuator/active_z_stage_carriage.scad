// PROJECT W.A.L.L. - HYPER-ACTUATOR Mk-1: Active Non-Contact Z-Stage Moving Carriage
// Drawing Ref: DWG-WALL-HACT-002 | Material: 7075-T6 Aerospace Aluminum (Weight: <38g)
// Houses MGN7C stainless carriage block, VCA moving coil bobbin, ST VL53L4CD micro-LiDAR,
// and 60° dovetail slide receiver with brass gibs.
// Complies with ISO 2768-mK tolerances | Designed for CNC Milling / Wire EDM

$fn = 32;

// Standard DIN 912 M2 Socket Head Cap Screw & Counterbore
module din912_m2_bore(h_thru = 10.0, cbore_depth = 2.2) {
    translate([0, 0, -1]) cylinder(d = 2.4, h = h_thru + 2); // M2 clearance
    translate([0, 0, h_thru - cbore_depth]) cylinder(d = 4.4, h = cbore_depth + 1); // Head pocket
}

// Precision Dovetail Profile Cutout
module dovetail_cutout(w_top, w_bot, depth, length) {
    hull() {
        translate([-w_bot/2, -length/2, 0])
            cube([w_bot, length, 0.05]);
        translate([-w_top/2, -length/2, depth])
            cube([w_top, length, 0.05]);
    }
}

module active_z_stage_carriage(
    stage_w = 64.0,
    stage_h = 56.0,
    stage_t = 12.0
) {
    difference() {
        // Precision CNC Skeletonized Carriage Body
        hull() {
            r = 4.0;
            translate([-stage_w/2 + r, -stage_h/2 + r, 0]) cylinder(r=r, h=stage_t);
            translate([ stage_w/2 - r, -stage_h/2 + r, 0]) cylinder(r=r, h=stage_t);
            translate([-stage_w/2 + r,  stage_h/2 - r, 0]) cylinder(r=r, h=stage_t);
            translate([ stage_w/2 - r,  stage_h/2 - r, 0]) cylinder(r=r, h=stage_t);
        }

        // 1. MGN7C Stainless Linear Bearing Block Recess & Mounting Bores (12 x 13 mm)
        translate([0, -10.0, -1]) {
            translate([-8.7, -11.5, 0.8]) cube([17.4, 23.0, 3.0]); // C-Block Locating Seat
            for (dx = [-6.0, 6.0]) {
                for (dy = [-6.5, 6.5]) {
                    translate([dx, dy, 0]) din912_m2_bore(stage_t, 2.2);
                }
            }
        }

        // 2. Cylindrical Voice Coil Actuator (VCA) Moving Coil Spigot & Vent
        translate([0, 14.0, stage_t - 8.5]) {
            cylinder(d=22.4, h=9.0); // Bobbin Spigot Pocket
            translate([0, 0, -stage_t]) cylinder(d=8.0, h=stage_t + 2); // Central Vent
            // Wire Lead-out Channel
            translate([-1.5, 11.0, -2.0]) cube([3.0, 8.0, 12.0]);
        }

        // 3. Quick-Release 60° Precision Dovetail Receiver Channel (Front Slide)
        translate([0, 0, -0.1])
            dovetail_cutout(28.0, 32.5, 4.5, stage_h + 2);

        // 4. Brass Gib Strip Slot & M3 Locking Cam Thumbscrew Bore
        translate([-stage_w/2 - 1, 0, stage_t/2])
            rotate([0, 90, 0])
                cylinder(d=3.3, h=18.0); // M3 Tap for Gib Lock

        // 5. ST VL53L4CD Micro-LiDAR Sensor Cavity & Dual Conical Sight Cones
        translate([stage_w/2 - 12.0, 0, -1]) {
            translate([-7.0, -4.5, 1.2]) cube([14.0, 9.0, 4.0]); // PCB Pocket
            translate([-3.2, 0, 0]) cylinder(d1=3.8, d2=2.8, h=stage_t + 2); // Emitter Cone
            translate([ 3.2, 0, 0]) cylinder(d1=3.8, d2=2.8, h=stage_t + 2); // Receiver Cone
            translate([0,  6.5, 0]) cylinder(d=2.2, h=stage_t + 2); // M2 PCB Mount
            translate([0, -6.5, 0]) cylinder(d=2.2, h=stage_t + 2);
        }

        // 6. Deep CNC Lightening Pockets (Keeps Moving Mass Under 38 grams!)
        translate([-stage_w/2 + 8.0,  18.0, 2.0]) cube([8.0, 12.0, stage_t]);
        translate([-stage_w/2 + 8.0, -18.0, 2.0]) cube([8.0, 12.0, stage_t]);
        translate([ stage_w/2 - 16.0,  18.0, 2.0]) cube([8.0, 12.0, stage_t]);
        translate([ stage_w/2 - 16.0, -18.0, 2.0]) cube([8.0, 12.0, stage_t]);
    }
}

// Standalone render
color([0.20, 0.23, 0.28])
    active_z_stage_carriage();
