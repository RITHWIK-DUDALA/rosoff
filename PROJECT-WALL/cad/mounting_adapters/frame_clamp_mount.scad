// PROJECT W.A.L.L. - Mechanical Edge Clamp Adapter
// Clamps corner winch onto extrusion rails or wooden board edges
$fn = 32;

clamp_w = 40.0;
clamp_d = 50.0;
clamp_h = 45.0;
jaw_gap = 22.0; // Fits up to 20mm board or 2020 extrusion

module frame_clamp() {
    difference() {
        cube([clamp_w, clamp_d, clamp_h]);

        // C-clamp cutout
        translate([-1, 15, 10])
            cube([clamp_w + 2, clamp_d, jaw_gap]);

        // Clamping screw threaded hole (M6)
        translate([clamp_w/2, 32, -1])
            cylinder(d=6.0, h=12);

        // Winch bracket attachment holes
        translate([10, 8, clamp_h - 8])
            cylinder(d=4.2, h=10);
        translate([clamp_w - 10, 8, clamp_h - 8])
            cylinder(d=4.2, h=10);
    }
}

frame_clamp();

