// PROJECT W.A.L.L. - Modular Suction Cup Manifold Mount
// Adapts corner winch assembly to smooth surface walls via pneumatic suction cup
$fn = 32;

manifold_dia = 65.0;
manifold_thick = 8.0;
fitting_dia = 6.0; // 6mm push-to-connect vacuum fitting
winch_bolt_spacing = 40.0;

module suction_cup_adapter() {
    difference() {
        cylinder(d=manifold_dia, h=manifold_thick);

        // Center vacuum plenum chamber
        translate([0, 0, -1])
            cylinder(d=manifold_dia - 12, h=manifold_thick - 3);

        // Central vacuum port fitting
        translate([0, 0, manifold_thick - 4])
            cylinder(d=fitting_dia, h=5);

        // Winch bracket mounting holes
        for (dx = [-winch_bolt_spacing/2, winch_bolt_spacing/2]) {
            translate([dx, 0, -1])
                cylinder(d=4.2, h=manifold_thick+2);
        }
    }
}

suction_cup_adapter();

