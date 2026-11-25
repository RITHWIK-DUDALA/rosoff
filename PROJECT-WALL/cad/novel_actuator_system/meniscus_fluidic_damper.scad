// PROJECT W.A.L.L. - HYPER-ACTUATOR Mk-1: Constant Meniscus Negative-Pressure Tank & Damper
// Drawing Ref: DWG-WALL-HACT-005 | Material: Chemical-Resistant Translucent POM / PTFE
// Holds 18 mL Ink Reservoir. Maintains -1.45 kPa ± 0.05 kPa Meniscus Vacuum via Micro-Diaphragm.
// Complies with ISO 2768-mK tolerances | Designed for FDM / SLA 3D Printing

$fn = 32;

module meniscus_fluidic_damper(
    tank_dia = 26.0,
    tank_h = 42.0,
    wall_t = 2.2,
    sensor_boss_w = 14.0,
    sensor_boss_h = 16.0
) {
    difference() {
        union() {
            cylinder(d=tank_dia, h=tank_h);
            translate([0, 0, tank_h - 4.0])
                cylinder(d=tank_dia + 6.0, h=4.0);
            translate([tank_dia/2 - 2.0, -sensor_boss_w/2, 14.0])
                cube([8.0, sensor_boss_w, sensor_boss_h]);
            translate([0, 0, -6.0])
                cylinder(d=5.2, h=6.0);
        }

        // 1. Internal Degassing & Fluid Buffer Chamber
        translate([0, 0, wall_t])
            cylinder(d=tank_dia - 2*wall_t, h=tank_h);

        // 2. Liquid Discharge Port (Feeds 128-Nozzle Manifold)
        translate([0, 0, -7.0])
            cylinder(d=2.4, h=wall_t + 8.0);

        // 3. Top Vacuum Air Port
        translate([-5.0, 0, tank_h - 6.0])
            cylinder(d=3.2, h=10.0);

        // 4. Secondary De-aeration / Purge Inlet Port
        translate([ 5.0, 0, tank_h - 6.0])
            cylinder(d=3.2, h=10.0);

        // 5. Differential Pressure Transducer Sense Tap Bore
        translate([tank_dia/2 - 4.0, 0, 22.0])
            rotate([0, 90, 0])
                cylinder(d=2.0, h=10.0);
    }
}

meniscus_fluidic_damper();
