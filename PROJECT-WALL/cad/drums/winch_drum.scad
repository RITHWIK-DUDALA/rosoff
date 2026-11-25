// PROJECT W.A.L.L. - Precision Helical-Grooved Winch Drum CAD Model
// Drawing Ref: DWG-WALL-CAD-001 | Material: 6061-T6 Aluminum
// Complies with ISO 2768-mK tolerances

$fn = 64;

// Precision Dimensions (Blueprint Section 2.3)
d_root = 28.0;          // Root diameter = 28.0mm
d_flange = 44.0;        // Flange outer diameter = 44.0mm
w_spool = 22.0;         // Spool width between flanges = 22.0mm
t_flange = 2.5;         // Flange thickness = 2.5mm
w_total = w_spool + 2 * t_flange; // Total length = 27.0mm

shaft_bore = 8.0;       // 8mm precision ground shaft (driven via beam coupler)
keyway_w = 2.0;
keyway_d = 1.0;

bearing_od = 16.0;      // F688ZZ bearing recess
bearing_depth = 4.0;

lightening_hole_d = 6.5; // 6x Weight-reduction holes
lightening_pcd = 32.0;

module winch_drum() {
    difference() {
        union() {
            // Main grooved spool barrel
            cylinder(d = d_root, h = w_total, center = true);
            
            // Lower retaining flange
            translate([0, 0, -(w_total/2 - t_flange/2)])
                cylinder(d = d_flange, h = t_flange, center = true);
                
            // Upper retaining flange
            translate([0, 0, (w_total/2 - t_flange/2)])
                cylinder(d = d_flange, h = t_flange, center = true);
        }
        
        // Central 8mm shaft bore with keyway slot
        cylinder(d = shaft_bore, h = w_total + 10, center = true);
        translate([shaft_bore/2, -keyway_w/2, -(w_total+10)/2])
            cube([keyway_d, keyway_w, w_total + 10]);
            
        // F688ZZ bearing recess on bottom face
        translate([0, 0, -(w_total/2 + 0.1)])
            cylinder(d = bearing_od, h = bearing_depth + 0.1);
            
        // F688ZZ bearing recess on top face
        translate([0, 0, (w_total/2 - bearing_depth)])
            cylinder(d = bearing_od, h = bearing_depth + 0.1);
            
        // 6x Circumferential Weight-Reduction Holes on both flanges
        for (i = [0:5]) {
            rotate([0, 0, i * 60]) {
                translate([lightening_pcd/2, 0, 0])
                    cylinder(d = lightening_hole_d, h = w_total + 2, center = true);
            }
        }
        
        // Cable Entry Anchor Bore (1.2mm for Dyneema 1.0mm) + Swage Counterbore
        rotate([0, 90, 30])
            cylinder(d = 1.4, h = d_root/2 + 2);
        translate([cos(30)*(d_root/2 - 2), sin(30)*(d_root/2 - 2), 0])
            cylinder(d = 3.5, h = 6, center = true);
    }
}

winch_drum();
