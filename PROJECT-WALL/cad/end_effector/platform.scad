// PROJECT W.A.L.L. - Central Suspended 2-DOF End-Effector Chassis Baseplate
// Drawing Ref: DWG-WALL-CAD-004 | Material: 6061-T6 Aluminum
// Bare Mass: 0.28 kg | Fully Assembled Mass: 0.46 kg
// Standard: ISO 2768-mK

$fn = 48;

// Precision Blueprint Dimensions (Section 4)
plat_w = 110.0;
plat_h = 85.0;
plat_thick = 8.0;
corner_fillet = 6.0;

// Corner Cable Swivel Stud Holes (B1..B4)
eyelet_x = 47.0; // Distance from center
eyelet_y = 34.5;
eyelet_bore = 4.0; // M4 precision reamed bore for swivel shoulder bolt

// 3-Point POM Ball Transfer Standoff Positions
standoff_pts = [
    [-42.0,   0.0],
    [ 42.0,  28.0],
    [ 42.0, -28.0]
];
ball_socket_d = 12.0; // Delrin casing diameter
ball_socket_depth = 5.0;

// Dual 4mm Ground Linear Guide Rod Bosses
rod_span = 36.0;
rod_bore = 4.0;

// Dovetail Receiver Channel Dimensions
dovetail_w_top = 34.0;
dovetail_w_bot = 38.0;
dovetail_depth = 4.0;

module rounded_box(w, h, t, r) {
    hull() {
        translate([-w/2 + r, -h/2 + r, 0]) cylinder(r=r, h=t);
        translate([ w/2 - r, -h/2 + r, 0]) cylinder(r=r, h=t);
        translate([-w/2 + r,  h/2 - r, 0]) cylinder(r=r, h=t);
        translate([ w/2 - r,  h/2 - r, 0]) cylinder(r=r, h=t);
    }
}

module hex_pocket(r, h) {
    cylinder(r=r, h=h, $fn=6);
}

module platform_chassis() {
    difference() {
        // Main CNC 6061-T6 Baseplate
        rounded_box(plat_w, plat_h, plat_thick, corner_fillet);

        // 4 Corner Cable Attachment Eyelet Bores (B1, B2, B3, B4)
        translate([-eyelet_x,  eyelet_y, -1]) cylinder(d=eyelet_bore, h=plat_thick+2);
        translate([ eyelet_x,  eyelet_y, -1]) cylinder(d=eyelet_bore, h=plat_thick+2);
        translate([-eyelet_x, -eyelet_y, -1]) cylinder(d=eyelet_bore, h=plat_thick+2);
        translate([ eyelet_x, -eyelet_y, -1]) cylinder(d=eyelet_bore, h=plat_thick+2);

        // 3-Point Kinematic POM Ball Standoff Sockets
        for (pt = standoff_pts) {
            translate([pt[0], pt[1], -0.1])
                cylinder(d=ball_socket_d, h=ball_socket_depth + 0.1);
            translate([pt[0], pt[1], -1])
                cylinder(d=3.2, h=plat_thick + 2); // M3 center retention screw
        }

        // Dual 4mm Linear Guide Rod Precision Bores (H7 Fit)
        translate([-rod_span/2, 0, -1]) cylinder(d=rod_bore, h=plat_thick+2);
        translate([ rod_span/2, 0, -1]) cylinder(d=rod_bore, h=plat_thick+2);

        // Central Actuator Aperture
        translate([0, 0, -1])
            cylinder(d=22.0, h=plat_thick+2);

        // Quick-Release Dovetail Slide Receiver Channel (Milled on top face)
        translate([0, 0, plat_thick - dovetail_depth])
            hull() {
                translate([-dovetail_w_top/2, -plat_h/2 - 1, 0])
                    cube([dovetail_w_top, plat_h + 2, dovetail_depth + 1]);
                translate([-dovetail_w_bot/2, -plat_h/2 - 1, dovetail_depth])
                    cube([dovetail_w_bot, plat_h + 2, 0.1]);
            }

        // Knurled M4 Locking Thumbscrew Side Bore
        translate([plat_w/2 - 12, 0, plat_thick/2])
            rotate([0, 90, 0])
                cylinder(d=3.3, h=16); // M4 tap drill size

        // ST VL53L1X ToF Laser Sensor Optical Aperture & Mounting Holes
        translate([22.0, 0, -1]) {
            // Emitter & Receiver Lens Windows
            translate([-3.0, 0, 0]) cylinder(d=3.2, h=plat_thick+2);
            translate([ 3.0, 0, 0]) cylinder(d=3.2, h=plat_thick+2);
            // M2 PCB Mounting Screws
            translate([0,  8.0, 0]) cylinder(d=2.2, h=plat_thick+2);
            translate([0, -8.0, 0]) cylinder(d=2.2, h=plat_thick+2);
        }

        // Umbilical Drag Bracket Mounting Holes (Top Flange)
        translate([-10.0, plat_h/2 - 6.0, -1]) cylinder(d=3.2, h=plat_thick+2);
        translate([ 10.0, plat_h/2 - 6.0, -1]) cylinder(d=3.2, h=plat_thick+2);

        // Hexagonal Weight-Reduction Pocket Insets (Lightening Webbing)
        translate([-26.0,  20.0, 1.5]) hex_pocket(7.5, plat_thick);
        translate([-26.0, -20.0, 1.5]) hex_pocket(7.5, plat_thick);
        translate([  0.0,  26.0, 1.5]) hex_pocket(6.5, plat_thick);
        translate([  0.0, -26.0, 1.5]) hex_pocket(6.5, plat_thick);
    }
}

platform_chassis();
