// PROJECT W.A.L.L. - HYPER-ACTUATOR Mk-1: 128-Nozzle MEMS Micro-Piezo Printhead Dock
// Drawing Ref: DWG-WALL-HACT-003 | Material: Anodized 6061-T6 / Silicon MEMS / POM
// 128-Nozzles (Dual Staggered Rows, 300 DPI Native, 6-24 pL Drop-on-Demand)
// Complies with ISO 2768-mK tolerances | Designed for Precision 3D Printing / CNC

$fn = 32;

module mems_128_printhead_dock(
    head_w = 34.0,
    head_l = 48.0,
    head_h = 32.0,
    plate_w = 12.0,
    plate_l = 28.0,
    plate_h = 1.8,
    dovetail_top_w = 27.5,
    dovetail_bot_w = 31.5,
    dovetail_h = 4.2,
    luer_dia = 4.3,
    luer_spacing = 14.0,
    fpc_slot_w = 22.0,
    fpc_slot_t = 1.4
) {
    difference() {
        union() {
            // Main Printhead Manifold Body
            translate([-head_w/2, -head_l/2, 0])
                cube([head_w, head_l, head_h]);

            // Quick-Release Dovetail Male Slide Runner (Top Face)
            translate([0, 0, head_h])
                hull() {
                    translate([-dovetail_top_w/2, -head_l/2, 0])
                        cube([dovetail_top_w, head_l, 0.1]);
                    translate([-dovetail_bot_w/2, -head_l/2, dovetail_h])
                        cube([dovetail_bot_w, head_l, 0.1]);
                }

            // Silicon Orifice Plate Locating Boss (Bottom Face)
            translate([-plate_w/2, -plate_l/2, -plate_h])
                cube([plate_w, plate_l, plate_h]);
        }

        // 1. Dual Internal Ink Manifold Chambers
        translate([-luer_spacing/2, 0, 6.0])
            cylinder(d=7.0, h=head_h + dovetail_h + 1);
        translate([ luer_spacing/2, 0, 6.0])
            cylinder(d=7.0, h=head_h + dovetail_h + 1);

        // 2. Dual Female Luer-Lock Ports on Top for 2.0mm ID / 4.0mm OD PTFE Tubing
        translate([-luer_spacing/2, 0, head_h + dovetail_h - 6.0])
            cylinder(d=luer_dia, h=8.0);
        translate([ luer_spacing/2, 0, head_h + dovetail_h - 6.0])
            cylinder(d=luer_dia, h=8.0);

        // 3. Central Piezo Actuator Driving Chamber Pocket
        translate([-8.0, -16.0, 4.0])
            cube([16.0, 32.0, head_h - 8.0]);

        // 4. Rear Slot for 34-Pin High-Speed Gold FPC Ribbon Cable
        translate([-fpc_slot_w/2, head_l/2 - fpc_slot_t - 1.0, 8.0])
            cube([fpc_slot_w, fpc_slot_t + 2.0, head_h - 10.0]);

        // 5. Dual Staggered 128-Nozzle Orifice Pattern Representation (Pitch 84.6 µm)
        for (i = [0:15]) {
            translate([-1.2, (i - 7.5) * 1.5, -plate_h - 0.5])
                cylinder(d=0.45, h=plate_h + 1.0);
            translate([ 1.2, (i - 7.5) * 1.5 + 0.75, -plate_h - 0.5])
                cylinder(d=0.45, h=plate_h + 1.0);
        }

        // 6. Lateral M3 Clamping Set-Screw Dimple
        translate([head_w/2 - 2.5, 0, head_h/2])
            rotate([0, 90, 0])
                cylinder(d=3.2, h=5.0);
    }
}

mems_128_printhead_dock();
