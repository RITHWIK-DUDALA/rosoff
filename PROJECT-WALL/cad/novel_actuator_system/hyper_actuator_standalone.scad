// PROJECT W.A.L.L. - HYPER-ACTUATOR Mk-1: Complete Standalone CAD Model
// Drawing ALL-HACT-000 | Architecture: Non-Contact Dual-Stage Active UV-Piezo Surface Printing Engine
// 100% Self-Contained OpenSCAD File - Zero External Dependencies
// Open directly in OpenSCAD (F5 for Preview, F6 for Render)

$fn = 32;

// ====================================================================
// 1. CDPR CARRIAGE STRUCTURAL INTERFACE ADAPTER PLATE
// ====================================================================
module cdpr_interface_adapter(
    adapter_w = 98.0,
    adapter_h = 78.0,
    adapter_t = 6.0,
    center_bore_dia = 22.0,
    rail_len = 64.0,
    rail_w = 7.0
) {
    difference() {
        // Main Adapter Plate Body
        hull() {
            r = 5.0;
            translate([-adapter_w/2 + r, -adapter_h/2 + r, 0]) cylinder(r=r, h=adapter_t);
            translate([ adapter_w/2 - r, -adapter_h/2 + r, 0]) cylinder(r=r, h=adapter_t);
            translate([-adapter_w/2 + r,  adapter_h/2 - r, 0]) cylinder(r=r, h=adapter_t);
            translate([ adapter_w/2 - r,  adapter_h/2 - r, 0]) cylinder(r=r, h=adapter_t);
        }

        // Central Actuation Aperture (Pass-Through for Printhead Orifice Face)
        translate([0, 0, -1])
            cylinder(d=center_bore_dia, h=adapter_t + 2);

        // MGN7C Miniature Linear Rail Precision Locating Slot
        translate([-rail_w/2, -rail_len/2, adapter_t - 1.5])
            cube([rail_w, rail_len, 2.0]);

        // MGN7C Rail M2 Counterbored Mounting Holes (4x at 15mm pitch)
        for (y = [-22.5, -7.5, 7.5, 22.5]) {
            translate([0, y, -1]) {
                cylinder(d=2.4, h=adapter_t + 2);
                cylinder(d=4.4, h=3.0);
            }
        }

        // Voice Coil Actuator (VCA) Stator Housing Pocket
        translate([0, 24.0, adapter_t - 3.5]) {
            cylinder(d=26.0, h=4.0);
            translate([0, 0, -adapter_t])
                cylinder(d=12.0, h=adapter_t + 2);
            for (a = [30, 150, 270]) {
                rotate([0, 0, a])
                    translate([16.0, 0, -adapter_t])
                        cylinder(d=2.7, h=adapter_t + 2);
            }
        }

        // 4x Vibration-Damping Elastomer Grommet Bores
        for (x = [-38.0, 38.0]) {
            for (y = [-28.0, 28.0]) {
                translate([x, y, -1]) {
                    cylinder(d=6.5, h=adapter_t + 2);
                    translate([0, 0, 3.0])
                        cylinder(d=9.5, h=4.0);
                }
            }
        }

        // Fluidic Reservoir Mounting Holes
        translate([32.0, 0, -1]) {
            translate([0, -14.0, 0]) cylinder(d=3.2, h=adapter_t + 2);
            translate([0,  14.0, 0]) cylinder(d=3.2, h=adapter_t + 2);
        }

        // Auto-Capping 9g Servo Mounting Pocket
        translate([-32.0, -10.0, -1]) {
            translate([-6.0, -11.5, 1]) cube([12.5, 23.0, adapter_t + 2]);
            translate([0, -14.5, 0]) cylinder(d=2.2, h=adapter_t + 2);
            translate([0,  14.5, 0]) cylinder(d=2.2, h=adapter_t + 2);
        }

        // Hexagonal Weight-Reduction Pockets
        for (pos = [[-20, 26], [20, 26], [-20, -26], [20, -26]]) {
            translate([pos[0], pos[1], 1.5])
                cylinder(r=5.5, h=adapter_t, $fn=6);
        }
    }
}

// ====================================================================
// 2. ACTIVE NON-CONTACT Z-STAGE MOVING CARRIAGE
// ====================================================================
module active_z_stage_carriage(
    stage_w = 64.0,
    stage_h = 56.0,
    stage_t = 12.0,
    mgn7_hole_x = 12.0,
    mgn7_hole_y = 13.0,
    vca_dia = 22.4,
    vca_depth = 8.5,
    lidar_w = 14.0,
    lidar_h = 9.0,
    lidar_depth = 4.0,
    dovetail_top_w = 28.0,
    dovetail_bot_w = 32.0,
    dovetail_depth = 4.5
) {
    difference() {
        // Main Structural Body
        hull() {
            r = 4.0;
            translate([-stage_w/2 + r, -stage_h/2 + r, 0]) cylinder(r=r, h=stage_t);
            translate([ stage_w/2 - r, -stage_h/2 + r, 0]) cylinder(r=r, h=stage_t);
            translate([-stage_w/2 + r,  stage_h/2 - r, 0]) cylinder(r=r, h=stage_t);
            translate([ stage_w/2 - r,  stage_h/2 - r, 0]) cylinder(r=r, h=stage_t);
        }

        // MGN7C Carriage Block Mounting Holes (4x M2)
        translate([0, -10.0, -1]) {
            for (dx = [-mgn7_hole_x/2, mgn7_hole_x/2]) {
                for (dy = [-mgn7_hole_y/2, mgn7_hole_y/2]) {
                    translate([dx, dy, 0]) {
                        cylinder(d=2.4, h=stage_t + 2);
                        translate([0, 0, stage_t - 2.5])
                            cylinder(d=4.4, h=3.0);
                    }
                }
            }
        }

        // Voice Coil Actuator (VCA) Moving Recess
        translate([0, 14.0, stage_t - vca_depth]) {
            cylinder(d=vca_dia, h=vca_depth + 1);
            translate([0, 0, -stage_t])
                cylinder(d=8.0, h=stage_t + 2);
        }

        // Front Dovetail Slide Receiver Channel
        translate([0, 0, -0.1]) {
            hull() {
                translate([-dovetail_bot_w/2, -stage_h/2 - 1, 0])
                    cube([dovetail_bot_w, stage_h + 2, 0.1]);
                translate([-dovetail_top_w/2, -stage_h/2 - 1, dovetail_depth])
                    cube([dovetail_top_w, stage_h + 2, 0.1]);
            }
        }

        // VL53L4CD Laser Rangefinder Optical Cavity
        translate([stage_w/2 - 12.0, 0, -1]) {
            translate([-lidar_w/2, -lidar_h/2, 1])
                cube([lidar_w, lidar_h, lidar_depth + 1]);
            translate([-3.2, 0, 0]) cylinder(d=3.5, h=stage_t + 2);
            translate([ 3.2, 0, 0]) cylinder(d=3.5, h=stage_t + 2);
            translate([0,  6.5, 0]) cylinder(d=2.2, h=stage_t + 2);
            translate([0, -6.5, 0]) cylinder(d=2.2, h=stage_t + 2);
        }

        // Lateral M3 Cam Lock Thumbscrew Bore
        translate([-stage_w/2 - 1, 0, stage_t/2])
            rotate([0, 90, 0])
                cylinder(d=3.3, h=16.0);

        // Weight-Reduction Pockets
        translate([-stage_w/2 + 10.0,  18.0, 2.0]) cube([8.0, 10.0, stage_t]);
        translate([-stage_w/2 + 10.0, -18.0, 2.0]) cube([8.0, 10.0, stage_t]);
        translate([ stage_w/2 - 16.0,  18.0, 2.0]) cube([8.0, 10.0, stage_t]);
        translate([ stage_w/2 - 16.0, -18.0, 2.0]) cube([8.0, 10.0, stage_t]);
    }
}

// ====================================================================
// 3. 128-NOZZLE MEMS MICRO-PIEZO PRINTHEAD DOCK
// ====================================================================
module mems_128_printhead_dock(
    head_w = 34.0,
    head_l = 48.0,
    head_h = 32.0,
    plate_w = 12.0,
    plate_l = 28.0,
    plate_h = 1.8,
    dovetail_top_w = 27.5,
    dovetail_bot_w = 31.5,
    dovetail_h = 4.2,
    luer_dia = 4.3,
    luer_spacing = 14.0,
    fpc_slot_w = 22.0,
    fpc_slot_t = 1.4
) {
    difference() {
        union() {
            // Main Printhead Manifold Body
            translate([-head_w/2, -head_l/2, 0])
                cube([head_w, head_l, head_h]);

            // Quick-Release Dovetail Male Slide Runner (Top Face)
            translate([0, 0, head_h])
                hull() {
                    translate([-dovetail_top_w/2, -head_l/2, 0])
                        cube([dovetail_top_w, head_l, 0.1]);
                    translate([-dovetail_bot_w/2, -head_l/2, dovetail_h])
                        cube([dovetail_bot_w, head_l, 0.1]);
                }

            // Silicon Orifice Plate Locating Boss (Bottom Face)
            translate([-plate_w/2, -plate_l/2, -plate_h])
                cube([plate_w, plate_l, plate_h]);
        }

        // Dual Internal Ink Manifold Chambers
        translate([-luer_spacing/2, 0, 6.0])
            cylinder(d=7.0, h=head_h + dovetail_h + 1);
        translate([ luer_spacing/2, 0, 6.0])
            cylinder(d=7.0, h=head_h + dovetail_h + 1);

        // Dual Female Luer-Lock Ports on Top
        translate([-luer_spacing/2, 0, head_h + dovetail_h - 6.0])
            cylinder(d=luer_dia, h=8.0);
        translate([ luer_spacing/2, 0, head_h + dovetail_h - 6.0])
            cylinder(d=luer_dia, h=8.0);

        // Central Piezo Actuator Driving Chamber
        translate([-8.0, -16.0, 4.0])
            cube([16.0, 32.0, head_h - 8.0]);

        // Rear Slot for 34-Pin FPC Ribbon Cable
        translate([-fpc_slot_w/2, head_l/2 - fpc_slot_t - 1.0, 8.0])
            cube([fpc_slot_w, fpc_slot_t + 2.0, head_h - 10.0]);

        // 128-Nozzle Orifice Pattern Representation
        for (i = [0:15]) {
            translate([-1.2, (i - 7.5) * 1.5, -plate_h - 0.5])
                cylinder(d=0.45, h=plate_h + 1.0);
            translate([ 1.2, (i - 7.5) * 1.5 + 0.75, -plate_h - 0.5])
                cylinder(d=0.45, h=plate_h + 1.0);
        }

        // Lateral M3 Set-Screw Dimple
        translate([head_w/2 - 2.5, 0, head_h/2])
            rotate([0, 90, 0])
                cylinder(d=3.2, h=5.0);
    }
}

// ====================================================================
// 4. DUAL IN-SITU 395nm UV-LED PINNING WING
// ====================================================================
module uv_pinning_wing(
    wing_w = 18.0,
    wing_l = 44.0,
    wing_h = 28.0,
    lens_dia = 6.0,
    lens_len = 36.0,
    led_pcb_w = 10.0,
    led_pcb_l = 32.0,
    led_pcb_t = 1.6
) {
    difference() {
        union() {
            // Main Extruded Thermal Radiator Body
            translate([-wing_w/2, -wing_l/2, 0])
                cube([wing_w, wing_l, wing_h]);

            // Side Flange Attachment Lug
            translate([wing_w/2, -wing_l/2 + 6.0, 4.0])
                cube([5.0, wing_l - 12.0, 14.0]);
        }

        // Parabolic Optical Reflector Cavity
        translate([0, 0, -0.1]) {
            hull() {
                translate([-wing_w/2 + 2.0, -led_pcb_l/2, 0])
                    cube([wing_w - 4.0, led_pcb_l, 0.1]);
                translate([-3.0, -led_pcb_l/2, 12.0])
                    cube([6.0, led_pcb_l, 0.1]);
            }
        }

        // 6mm Cylindrical Quartz Lens Retention Channel
        translate([0, 0, 3.0])
            rotate([90, 0, 0])
                cylinder(d=lens_dia, h=lens_len + 2, center=true);

        // LED MCPCB Pocket
        translate([-led_pcb_w/2, -led_pcb_l/2, 12.0])
            cube([led_pcb_w, led_pcb_l, led_pcb_t + 0.2]);

        // Cooling Heat-Sink Flutes
        for (f = [-14, -7, 0, 7, 14]) {
            translate([-wing_w/2 - 1, f - 1.0, 16.0])
                cube([wing_w + 2, 2.0, wing_h - 14.0]);
        }

        // M2.5 Side Clamping Bolt Holes
        translate([wing_w/2 - 1, -10.0, 11.0])
            rotate([0, 90, 0])
                cylinder(d=2.7, h=8.0);
        translate([wing_w/2 - 1,  10.0, 11.0])
            rotate([0, 90, 0])
                cylinder(d=2.7, h=8.0);
    }
}

// ====================================================================
// 5. CONSTANT MENISCUS PRESSURE BUFFER TANK & DAMPER
// ====================================================================
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

        // Internal Fluid Buffer Chamber
        translate([0, 0, wall_t])
            cylinder(d=tank_dia - 2*wall_t, h=tank_h);

        // Discharge Port
        translate([0, 0, -7.0])
            cylinder(d=2.4, h=wall_t + 8.0);

        // Top Ports
        translate([-5.0, 0, tank_h - 6.0]) cylinder(d=3.2, h=10.0);
        translate([ 5.0, 0, tank_h - 6.0]) cylinder(d=3.2, h=10.0);

        // Pressure Sensor Sense Tap
        translate([tank_dia/2 - 4.0, 0, 22.0])
            rotate([0, 90, 0])
                cylinder(d=2.0, h=10.0);
    }
}

// ====================================================================
// 6. MOTORIZED AUTO-SEALING CAPPING STATION
// ====================================================================
module auto_capping_station(
    arm_len = 38.0,
    arm_w = 14.0,
    arm_t = 6.0,
    cap_w = 16.0,
    cap_l = 32.0,
    servo_spline_d = 4.8
) {
    difference() {
        union() {
            hull() {
                cylinder(d=12.0, h=arm_t);
                translate([arm_len, 0, 0])
                    cylinder(d=cap_w, h=arm_t);
            }
            translate([arm_len - cap_l/2, -cap_w/2, arm_t])
                cube([cap_l, cap_w, 2.5]);
            translate([arm_len - (cap_l-4)/2, -(cap_w-4)/2, arm_t + 2.5])
                difference() {
                    cube([cap_l - 4, cap_w - 4, 2.0]);
                    translate([1.5, 1.5, -0.5])
                        cube([cap_l - 7, cap_w - 7, 3.0]);
                }
        }

        // Servo Spline Bore
        translate([0, 0, -1])
            cylinder(d=servo_spline_d, h=arm_t + 2);

        // Drain Port
        translate([arm_len, 0, -1])
            cylinder(d=2.6, h=arm_t + 6.0);
    }
}

// ====================================================================
// 7. COMPLETE MASTER SYSTEM ASSEMBLY (ALL MODULES COMBINED)
// ====================================================================
module hyper_actuator_complete_system(z_standoff = 1.5) {
    // 1. CDPR Base Adapter
    color([0.22, 0.24, 0.28])
        cdpr_interface_adapter();

    // 2. MGN7C Linear Rail
    color([0.82, 0.85, 0.88]) {
        translate([-3.5, -30.0, 4.5]) cube([7.0, 60.0, 4.8]);
        translate([-8.5, -11.5, 9.3]) cube([17.0, 23.0, 5.0]);
    }

    // 3. Voice Coil Actuator (VCA) Stator
    color([0.75, 0.60, 0.20])
        translate([0, 24.0, 4.0]) cylinder(d=24.0, h=14.0);

    // 4. Active Moving Z-Carriage
    translate([0, 0, 14.3 + z_standoff]) {
        color([0.18, 0.20, 0.25])
            active_z_stage_carriage();

        // Voice Coil Moving Bobbin
        color([0.85, 0.45, 0.15])
            translate([0, 14.0, -8.0]) cylinder(d=20.0, h=10.0);

        // ST Micro-LiDAR VL53L4CD
        color([0.15, 0.45, 0.85])
            translate([20.0, 0, 8.0]) cube([12.0, 8.0, 1.6]);

        // 5. 128-Nozzle MEMS Printhead Dock
        translate([0, 0, -28.0]) {
            color([0.30, 0.33, 0.38])
                mems_128_printhead_dock();
            color([0.90, 0.75, 0.20])
                translate([-10.0, 23.0, 12.0]) cube([20.0, 0.4, 25.0]);
        }

        // 6. Dual UV Wings
        color([0.45, 0.48, 0.52]) {
            translate([-27.0, 0, -24.0]) uv_pinning_wing();
            translate([ 27.0, 0, -24.0]) rotate([0, 0, 180]) uv_pinning_wing();
        }
    }

    // 7. Onboard Meniscus Fluidic Tank
    color([0.60, 0.80, 0.95])
        translate([32.0, 0, 6.0]) meniscus_fluidic_damper();

    // 8. Auto Capping 9g Servo & Arm
    color([0.15, 0.17, 0.20])
        translate([-32.0, -10.0, 6.0]) {
            cube([12.0, 22.0, 22.0]);
            translate([6.0, 17.0, 24.0]) rotate([0, 0, -45]) auto_capping_station();
        }
}

// Render complete assembly
hyper_actuator_complete_system();

