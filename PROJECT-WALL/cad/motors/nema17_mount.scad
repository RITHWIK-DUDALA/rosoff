// PROJECT W.A.L.L. - Precision NEMA 17 Stepper Motor Face Mount Bracket
// Drawing Ref: DWG-WALL-CAD-001 | Material: 6061-T6 Aluminum
// Standard: ISO 2768-mK

$fn = 48;

bracket_w = 42.3;
bracket_h = 42.3;
bracket_t = 5.0;
pilot_dia = 22.2;
bolt_spacing = 31.0;
bolt_dia = 3.4;
cbore_dia = 6.2;
cbore_depth = 2.5;

module nema17_face_mount() {
    difference() {
        // Main Mount Flange Plate
        translate([-bracket_w/2, -bracket_h/2, 0])
            cube([bracket_w, bracket_h, bracket_t]);

        // Center 22mm Pilot Boss Locating Collar Bore
        translate([0, 0, -1])
            cylinder(d=pilot_dia, h=bracket_t + 2);

        // 4x M3 Socket Head Cap Screw Mounting Holes with Counterbores (DIN 912)
        for (dx = [-bolt_spacing/2, bolt_spacing/2]) {
            for (dy = [-bolt_spacing/2, bolt_spacing/2]) {
                translate([dx, dy, -1])
                    cylinder(d=bolt_dia, h=bracket_t + 2);
                translate([dx, dy, bracket_t - cbore_depth])
                    cylinder(d=cbore_dia, h=cbore_depth + 1);
            }
        }

        // Side Flange Attachment M4 Tapped Holes
        for (y = [-14, 14]) {
            translate([-bracket_w/2 - 1, y, bracket_t/2])
                rotate([0, 90, 0])
                    cylinder(d=3.3, h=10);
            translate([bracket_w/2 - 9, y, bracket_t/2])
                rotate([0, 90, 0])
                    cylinder(d=3.3, h=10);
        }
    }
}

nema17_face_mount();
