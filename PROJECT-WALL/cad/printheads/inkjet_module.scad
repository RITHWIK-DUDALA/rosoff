// PROJECT W.A.L.L. - Module A: 48-Nozzle Drop-on-Demand Piezo Inkjet Printhead
// Drawing Ref: DWG-WALL-CAD-005 | Material: 6061-T6 Aluminum / Silicon MEMS Orifice Plate
// Droplet Volume: 14.0 pL | Firing Frequency: 100 Hz - 15 kHz | Standoff: 2.0 mm
// Complies with ISO 2768-mK tolerances

$fn = 48;

// Blueprint Dimensions (Section 5.2)
head_w = 26.0;
head_l = 30.0;
head_h = 36.0;

plate_w = 18.0;
plate_l = 22.0;
plate_h = 2.0;

fpc_slot_w = 16.0;
fpc_slot_t = 1.2;

luer_d = 4.2;
luer_spacing = 12.0;

dovetail_w_top = 33.5;
dovetail_w_bot = 37.5;
dovetail_h = 3.8;

module piezo_printhead() {
    difference() {
        union() {
            // Main CNC Anodized Aluminum Printhead Manifold Body
            translate([-head_w/2, -head_l/2, 0])
                cube([head_w, head_l, head_h]);

            // Silicon Orifice Plate Mounting Boss (Bottom Face)
            translate([-plate_w/2, -plate_l/2, -plate_h])
                cube([plate_w, plate_l, plate_h]);

            // Quick-Release Dovetail Runner (Engages Platform Chassis)
            translate([0, 0, head_h])
                hull() {
                    translate([-dovetail_w_top/2, -head_l/2, 0])
                        cube([dovetail_w_top, head_l, 0.1]);
                    translate([-dovetail_w_bot/2, -head_l/2, dovetail_h])
                        cube([dovetail_w_bot, head_l, 0.1]);
                }
        }

        // Dual Internal Ink Delivery Reservoirs (CMYK Ink & Purge Lines)
        translate([-luer_spacing/2, 0, 8])
            cylinder(d=6.0, h=head_h);
        translate([ luer_spacing/2, 0, 8])
            cylinder(d=6.0, h=head_h);

        // Dual Female Luer-Lock Fluidic Ports (Top Inlets for PTFE Tubing)
        translate([-luer_spacing/2, 0, head_h - 4])
            cylinder(d=luer_d, h=dovetail_h + 5);
        translate([ luer_spacing/2, 0, head_h - 4])
            cylinder(d=luer_d, h=dovetail_h + 5);

        // 26-Pin Gold FPC Flex Ribbon Slot (Rear Exit)
        translate([-fpc_slot_w/2, head_l/2 - fpc_slot_t - 1, 6])
            cube([fpc_slot_w, fpc_slot_t + 2, head_h - 10]);

        // 48-Nozzle Orifice Pattern Representation (Dual Staggered Rows, Pitch 0.254mm)
        for (i = [0:11]) {
            translate([-1.2, (i - 5.5) * 1.5, -plate_h - 0.5])
                cylinder(d=0.6, h=plate_h + 1);
            translate([ 1.2, (i - 5.5) * 1.5, -plate_h - 0.5])
                cylinder(d=0.6, h=plate_h + 1);
        }

        // M3 Clamping Set-Screw Hole
        translate([head_w/2 - 3, 0, head_h/2])
            rotate([0, 90, 0])
                cylinder(d=2.5, h=6);
    }
}

piezo_printhead();
