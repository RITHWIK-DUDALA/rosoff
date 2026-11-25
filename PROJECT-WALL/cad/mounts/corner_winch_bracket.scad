// PROJECT W.A.L.L. - Heavy Corner Winch Mounting L-Bracket
// Drawing Ref: DWG-WALL-CAD-001 | Material: 6061-T6 Aluminum
// Mounts to perimeter frame / suction cup anchor, houses drum bearings & cable guide pulley
// Standard: ISO 2768-mK

$fn = 48;

bracket_w = 75.0;
bracket_l = 75.0;
bracket_t = 6.0;
upright_h = 48.0;

bearing_od = 16.0;
bearing_flange_d = 18.2;
bearing_depth = 5.0;

pulley_clevis_w = 12.0;

module corner_winch_bracket() {
    difference() {
        union() {
            // Main Baseplate (75 x 75 x 6 mm)
            cube([bracket_l, bracket_w, bracket_t]);

            // Upright Bearing Support Tower (Outer Flank)
            translate([0, 0, bracket_t])
                cube([bracket_t + 6, bracket_w, upright_h]);

            // Fairlead Guide Pulley Clevis Boss
            translate([bracket_l - 24, bracket_w - 24, bracket_t])
                cube([20, 20, 22]);
        }

        // 4x M5 Counterbored Corner Mounting Holes
        for (x = [12, bracket_l - 12]) {
            for (y = [12, bracket_w - 12]) {
                translate([x, y, -1]) cylinder(d=5.5, h=bracket_t + 2);
                translate([x, y, 3.0]) cylinder(d=9.5, h=bracket_t);
            }
        }

        // F688ZZ Flanged Bearing Bore (16.0mm H7 reamed bore + 18.2mm flange step)
        translate([-1, bracket_w/2, bracket_t + 24])
            rotate([0, 90, 0]) {
                cylinder(d=bearing_od, h=bracket_t + 8);
                translate([0, 0, bracket_t + 3])
                    cylinder(d=bearing_flange_d, h=3.0);
            }

        // Fairlead Pulley Axle Hole (M4 Reamed Bore) & Cable Pass-Through Window
        translate([bracket_l - 14, bracket_w - 14, bracket_t - 1]) {
            cylinder(d=4.0, h=26);
        }
        translate([bracket_l - 26, bracket_w - 18, bracket_t + 4]) {
            cube([24, 8, 16]);
        }

        // Weight-Reduction Lightening Cutout in Baseplate
        translate([26, 16, -1])
            cube([24, bracket_w - 32, bracket_t + 2]);
    }
}

corner_winch_bracket();
