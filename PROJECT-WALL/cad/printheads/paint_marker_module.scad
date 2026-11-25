// PROJECT W.A.L.L. - Module B: Spring-Compliant Paint Marker Actuator
// Drawing Ref: DWG-WALL-CAD-006 | Material: 6061-T6 Aluminum / Acrylic Felt Nib
// Preload Normal Force: 1.20 N (Maintained via ASTM A228 Spring) | Standoff: 0.0 mm (Contact)
// Complies with ISO 2768-mK tolerances

$fn = 48;

// Blueprint Dimensions (Section 5.3)
collet_od = 24.0;
collet_id = 16.2; // Accommodates standard 15.0 - 16.5 mm markers
sleeve_len = 48.0;

knurl_ring_od = 28.0;
knurl_ring_len = 10.0;

spring_seat_od = 12.0;
spring_seat_depth = 8.0;

switch_mount_x = 14.0;
switch_mount_y = 12.0;

dovetail_w_top = 33.5;
dovetail_w_bot = 37.5;
dovetail_h = 3.8;

module paint_marker_module() {
    difference() {
        union() {
            // Main Cylindrical Split-Collet Marker Sleeve
            cylinder(d=collet_od, h=sleeve_len);

            // Knurled Threaded Adjuster Collar Ring
            translate([0, 0, 16.0])
                cylinder(d=knurl_ring_od, h=knurl_ring_len);

            // Omron D2F-01 Micro-Switch Contact Sensor Mounting Bracket
            translate([collet_od/2 - 2, -switch_mount_y/2, 12.0])
                cube([10.0, switch_mount_y, 22.0]);

            // Quick-Release Dovetail Runner (Engages Platform Chassis)
            translate([0, 0, sleeve_len])
                hull() {
                    translate([-dovetail_w_top/2, -collet_od/2, 0])
                        cube([dovetail_w_top, collet_od, 0.1]);
                    translate([-dovetail_w_bot/2, -collet_od/2, dovetail_h])
                        cube([dovetail_w_bot, collet_od, 0.1]);
                }
        }

        // Central Marker Barrel Through-Bore (16.2mm reamed bore)
        translate([0, 0, -1])
            cylinder(d=collet_id, h=sleeve_len + dovetail_h + 2);

        // Helical Compliance Spring Seating Counterbore (Top Face)
        translate([0, 0, sleeve_len - spring_seat_depth])
            cylinder(d=spring_seat_od, h=spring_seat_depth + dovetail_h + 1);

        // 4x Longitudinal Split-Collet Clamping Slots (0.8mm width)
        for (a = [0, 90, 180, 270]) {
            rotate([0, 0, a])
                translate([-0.5, 0, -1])
                    cube([1.0, collet_od/2 + 2, 24.0]);
        }

        // Omron D2F Micro-Switch M2 Mounting Holes (6.5mm pitch)
        translate([collet_od/2 + 3, 0, 16.0]) {
            translate([0, -3.25, 0]) rotate([0, 90, 0]) cylinder(d=1.8, h=10);
            translate([0,  3.25, 0]) rotate([0, 90, 0]) cylinder(d=1.8, h=10);
        }

        // M4 Clamping Screw Through-Hole (Split Collar Tightening)
        translate([0, collet_od/2 - 3, 21.0])
            rotate([90, 0, 0])
                cylinder(d=3.3, h=12);
    }
}

paint_marker_module();
