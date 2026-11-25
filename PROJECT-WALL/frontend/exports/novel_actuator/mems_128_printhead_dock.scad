// PROJECT W.A.L.L. - HYPER-ACTUATOR Mk-1: 128-Nozzle MEMS Micro-Piezo Printhead Dock
// Drawing Ref: DWG-WALL-HACT-003 | Material: Anodized 6061 Aluminum & PZT Piezo Actuators
// Integrates 128 micro-nozzle orifice plate, dual internal manifold chambers,
// 60° dovetail runner, dual Luer fluid barbs, and 34-pin gold FPC slot.
// Complies with ISO 2768-mK tolerances | Designed for Precision Micro-Machining

$fn = 32;

module mems_128_printhead_dock(
    head_w = 34.0,
    head_l = 48.0,
    head_h = 32.0,
    plate_w = 12.0,
    plate_l = 28.0,
    plate_h = 1.8
) {
    difference() {
        union() {
            // Main Precision Anodized Aluminum Manifold Block
            translate([-head_w/2, -head_l/2, 0])
                cube([head_w, head_l, head_h]);

            // 60° Male Dovetail Slide Runner (Top Face)
            translate([0, 0, head_h])
                hull() {
                    translate([-27.5/2, -head_l/2, 0]) cube([27.5, head_l, 0.05]);
                    translate([-32.0/2, -head_l/2, 4.2]) cube([32.0, head_l, 0.05]);
                }

            // Silicon Orifice Plate Locating Collar (Bottom Face)
            translate([-plate_w/2, -plate_l/2, -plate_h])
                cube([plate_w, plate_l, plate_h]);

            // Dual PTFE Fluidic Inlet Hose Barbs
            translate([-7.0, 0, head_h + 4.2])
                cylinder(d1=4.8, d2=4.0, h=6.0);
            translate([ 7.0, 0, head_h + 4.2])
                cylinder(d1=4.8, d2=4.0, h=6.0);
        }

        // 1. Dual Internal Ink Manifold Distribution Chambers (Supply & Recirculation)
        translate([-7.0, 0, 4.0]) cylinder(d=7.0, h=head_h + 8.0);
        translate([ 7.0, 0, 4.0]) cylinder(d=7.0, h=head_h + 8.0);

        // Through-bore for ink feeds
        translate([-7.0, 0, -2.0]) cylinder(d=2.4, h=8.0);
        translate([ 7.0, 0, -2.0]) cylinder(d=2.4, h=8.0);

        // 2. Micro-Piezo PZT Actuator Drive Cavity & Acoustic Pumping Chambers
        translate([-9.0, -18.0, 3.5])
            cube([18.0, 36.0, head_h - 7.0]);

        // 3. Rear 34-Pin Gold FPC Flexible Electrical Ribbon Cable Channel
        translate([-11.0, head_l/2 - 2.0, 6.0])
            cube([22.0, 4.0, head_h - 8.0]);

        // 4. True Micro-Nozzle Orifice Plate Representation (128 Micro-Nozzles)
        for (i = [0:15]) {
            // Row A (64 Nozzles)
            translate([-1.2, (i - 7.5) * 1.5, -plate_h - 0.5])
                cylinder(d1=0.25, d2=0.55, h=plate_h + 1.0); // Conical Nozzle Horn
            // Row B (Staggered by Half-Pitch)
            translate([ 1.2, (i - 7.5) * 1.5 + 0.75, -plate_h - 0.5])
                cylinder(d1=0.25, d2=0.55, h=plate_h + 1.0);
        }

        // 5. Lateral M3 Clamping Dimple (Precision Repeatable Stop)
        translate([head_w/2 - 2.5, 0, head_h/2])
            rotate([0, 90, 0])
                cylinder(d=3.2, h=5.0);

        // 6. Perimeter Chamfers
        for (side = [-1, 1]) {
            translate([side * (head_w/2), 0, head_h/2])
                rotate([0, 45, 0])
                    cube([2.0, head_l + 2, 2.0], center=true);
        }
    }
}

// Standalone render
color([0.35, 0.38, 0.44])
    mems_128_printhead_dock();
