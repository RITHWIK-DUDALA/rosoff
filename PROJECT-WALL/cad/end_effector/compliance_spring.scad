// PROJECT W.A.L.L. - 1.2N Standoff Compliance Spring CAD Model
// Drawing Ref: DWG-WALL-CAD-004 | Material: ASTM A228 Music Wire (Spring Steel)
// Free Length L0: 34.0 mm | Preloaded Installed Length: 25.5 mm | Preload Force: 1.20 N
// Spring Rate k: 0.1411 N/mm | Active Coils: 7.5 | Wire Dia: 1.6 mm | Mean Dia: 8.5 mm
// Standard: DIN 2095 Class 1

$fn = 32;

// Spring Geometry Parameters
wire_d = 1.6;
mean_d = 8.5;
free_len = 34.0;
active_coils = 7.5;
total_coils = 9.5;

pitch = (free_len - 2 * wire_d) / active_coils;
steps_per_turn = 24;
total_steps = floor(total_coils * steps_per_turn);

module helical_spring() {
    for (i = [0 : total_steps - 1]) {
        t1 = i / steps_per_turn;
        t2 = (i + 1) / steps_per_turn;
        
        ang1 = t1 * 360;
        ang2 = t2 * 360;
        
        z1 = (i / total_steps) * free_len;
        z2 = ((i + 1) / total_steps) * free_len;
        
        x1 = (mean_d / 2) * cos(ang1);
        y1 = (mean_d / 2) * sin(ang1);
        
        x2 = (mean_d / 2) * cos(ang2);
        y2 = (mean_d / 2) * sin(ang2);
        
        hull() {
            translate([x1, y1, z1]) sphere(d = wire_d);
            translate([x2, y2, z2]) sphere(d = wire_d);
        }
    }
}

helical_spring();

