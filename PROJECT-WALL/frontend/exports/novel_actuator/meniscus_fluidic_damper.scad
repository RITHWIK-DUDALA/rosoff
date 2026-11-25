// PROJECT W.A.L.L. - HYPER-ACTUATOR Mk-1: Constant Meniscus Pressure Buffer Tank & Damper
// Drawing Ref: DWG-WALL-HACT-005 | Material: Turned Delrin / Clear Polycarbonate Sight Window
// Regulates negative meniscus vacuum (-1.45 kPa) preventing nozzle drool & vertical hydrostatics.
// Features diamond knurled cap, MPXV5004 sensor boss, and Luer retention barb.
// Complies with ISO 2768-mK tolerances | Designed for CNC Lathe Turning & Milling

$fn = 32;

module meniscus_fluidic_damper(
    tank_dia = 26.0,
    tank_h = 42.0,
    wall_t = 2.2
) {
    difference() {
        union() {
            // Main Turned Delrin Body
            cylinder(d=tank_dia, h=tank_h);

            // Knurled Threaded Top Cap Flange
            translate([0, 0, tank_h - 4.5]) {
                cylinder(d=tank_dia + 6.0, h=4.5);
                // Diamond Knurl Grip Representation
                for (a = [0:15:345]) {
                    rotate([0, 0, a])
                        translate([(tank_dia + 5.8)/2, 0, 0])
                            cylinder(d=1.2, h=4.5);
                }
            }

            // NXP MPXV5004DP Differential Pressure Transducer Boss
            translate([tank_dia/2 - 2.0, -7.0, 14.0])
                cube([8.0, 14.0, 16.0]);

            // Lower Liquid Supply Barb
            translate([0, 0, -6.5]) {
                cylinder(d=4.2, h=6.5);
                translate([0, 0, 2.0]) cylinder(d1=5.2, d2=4.2, h=2.5); // Retention Barb Ring
            }
        }

        // 1. Internal Fluid Buffer Chamber
        translate([0, 0, wall_t])
            cylinder(d=tank_dia - 2*wall_t, h=tank_h);

        // 2. Liquid Discharge Port
        translate([0, 0, -7.0])
            cylinder(d=2.4, h=wall_t + 8.0);

        // 3. Top Vacuum Air Port (Connects to PWM Micro-Diaphragm Pump)
        translate([-5.0, 0, tank_h - 6.0]) cylinder(d=3.2, h=10.0);

        // 4. Fluid Level Inspection Sight Window
        translate([0, tank_dia/2 - 2.0, 10.0])
            cube([6.0, 4.0, 20.0], center=true);

        // 5. Pressure Transducer Sense Tap
        translate([tank_dia/2 - 4.0, 0, 22.0])
            rotate([0, 90, 0])
                cylinder(d=2.0, h=10.0);

        // 6. 3x M2.5 Cap Screws
        for (a = [0, 120, 240]) {
            rotate([0, 0, a])
                translate([(tank_dia + 2.5)/2, 0, tank_h - 5.0])
                    cylinder(d=2.2, h=6.0);
        }
    }
}

// Standalone render
color([0.55, 0.75, 0.90, 0.85])
    meniscus_fluidic_damper();
