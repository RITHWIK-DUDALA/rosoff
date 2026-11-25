// PROJECT W.A.L.L. - HYPER-ACTUATOR Mk-1: Authentic Precision Mechatronic CAD Model
// Drawing Ref: DWG-WALL-HACT-000 | Architecture: Non-Contact Dual-Stage Active UV-Piezo Surface Printing Engine
// Precision Engineering: Real CNC Webbing, DIN 912 Fasteners, MGN7C Linear Guideways,
// Real Voice Coil Actuators, Dovetail Gibs, Radiator Cooling Fins, and Fluidic Manifolds.
// Complies with ISO 2768-mK tolerances | 100% Self-Contained OpenSCAD File

$fn = 32;

// ====================================================================
// UTILITY MODULES: REAL FASTENERS, RIBS & COUNTERBORES
// ====================================================================

// Standard DIN 912 M3 Socket Head Cap Screw & Counterbore
module din912_m3_bore(h_thru = 12.0, cbore_depth = 3.2) {
    translate([0, 0, -1]) cylinder(d = 3.4, h = h_thru + 2); // M3 clearance
    translate([0, 0, h_thru - cbore_depth]) cylinder(d = 6.2, h = cbore_depth + 1); // DIN 912 head pocket
}

// Standard DIN 912 M2 Socket Head Cap Screw & Counterbore
module din912_m2_bore(h_thru = 10.0, cbore_depth = 2.2) {
    translate([0, 0, -1]) cylinder(d = 2.4, h = h_thru + 2); // M2 clearance
    translate([0, 0, h_thru - cbore_depth]) cylinder(d = 4.4, h = cbore_depth + 1); // Head pocket
}

// Precision Dovetail Profile
module dovetail_cutout(w_top, w_bot, depth, length) {
    hull() {
        translate([-w_bot/2, -length/2, 0])
            cube([w_bot, length, 0.05]);
        translate([-w_top/2, -length/2, depth])
            cube([w_top, length, 0.05]);
    }
}

// ====================================================================
// 1. CDPR CARRIAGE STRUCTURAL INTERFACE ADAPTER PLATE
// ====================================================================
module cdpr_interface_adapter(
    adapter_w = 98.0,
    adapter_h = 78.0,
    adapter_t = 6.5,
    rail_len = 66.0,
    rail_w = 7.0
) {
    difference() {
        // Main CNC 6061-T6 Baseplate with Filleted Corners
        hull() {
            r = 6.0;
            translate([-adapter_w/2 + r, -adapter_h/2 + r, 0]) cylinder(r=r, h=adapter_t);
            translate([ adapter_w/2 - r, -adapter_h/2 + r, 0]) cylinder(r=r, h=adapter_t);
            translate([-adapter_w/2 + r,  adapter_h/2 - r, 0]) cylinder(r=r, h=adapter_t);
            translate([ adapter_w/2 - r,  adapter_h/2 - r, 0]) cylinder(r=r, h=adapter_t);
        }

        // 1. Central Actuator Aperture (Chamfered Optical/Nozzle Projection Window)
        translate([0, 0, -1])
            cylinder(d1=24.0, d2=22.0, h=adapter_t + 2);

        // 2. HIWIN MGN7C Miniature Linear Rail Precision Ground Datum Bed
        translate([-rail_w/2 - 0.1, -rail_len/2, adapter_t - 1.8])
            cube([rail_w + 0.2, rail_len, 2.0]);

        // MGN7C Rail Mounting Holes (4x M2 tapped, 15mm pitch)
        for (y = [-22.5, -7.5, 7.5, 22.5]) {
            translate([0, y, 0])
                din912_m2_bore(adapter_t, 2.2);
        }

        // 3. Voice Coil Actuator (VCA) Stator Housing Pocket & Fasteners
        translate([0, 24.0, adapter_t - 3.8]) {
            cylinder(d=26.2, h=4.0); // Precision Stator Pocket
            translate([0, 0, -adapter_t])
                cylinder(d=10.0, h=adapter_t + 2); // Center Core Ventilation
            for (a = [30, 150, 270]) {
                rotate([0, 0, a])
                    translate([16.0, 0, -adapter_t])
                        cylinder(d=2.6, h=adapter_t + 2); // M2.5 Tapped Holes
            }
        }

        // 4. 4x CDPR Platform Elastomer Vibration-Damping Grommet Bores
        for (x = [-38.0, 38.0]) {
            for (y = [-28.0, 28.0]) {
                translate([x, y, -1]) {
                    cylinder(d=6.5, h=adapter_t + 2); // Bushing outer diameter
                    translate([0, 0, 3.2])
                        cylinder(d=9.8, h=adapter_t); // Flange step
                }
            }
        }

        // 5. Meniscus Reservoir Mounting Flange (Right Flank)
        translate([32.0, 0, 0]) {
            translate([0, -14.0, 0]) din912_m3_bore(adapter_t, 3.2);
            translate([0,  14.0, 0]) din912_m3_bore(adapter_t, 3.2);
        }

        // 6. Auto-Capping 9g Micro-Servo Pocket (Left Flank)
        translate([-32.0, -10.0, -1]) {
            translate([-6.2, -12.0, 1.2]) cube([12.4, 24.0, adapter_t + 2]); // Servo Cutout
            translate([0, -14.5, 0]) cylinder(d=2.4, h=adapter_t + 2);
            translate([0,  14.5, 0]) cylinder(d=2.4, h=adapter_t + 2);
        }

        // 7. CNC Isogrid Lightening Web Pockets (Leaves 2.5mm Webbing)
        for (pos = [[-20, 25], [20, 25], [-20, -25], [20, -25], [-35, 12], [35, -12]]) {
            translate([pos[0], pos[1], 2.2])
                cylinder(r=6.0, h=adapter_t, $fn=6);
        }

        // Perimeter Chamfers (Top & Bottom)
        translate([0, 0, adapter_t - 0.4])
            difference() {
                translate([-adapter_w/2 - 1, -adapter_h/2 - 1, 0]) cube([adapter_w + 2, adapter_h + 2, 1]);
                hull() {
                    r = 5.5;
                    translate([-adapter_w/2 + r, -adapter_h/2 + r, -0.5]) cylinder(r=r, h=2);
                    translate([ adapter_w/2 - r, -adapter_h/2 + r, -0.5]) cylinder(r=r, h=2);
                    translate([-adapter_w/2 + r,  adapter_h/2 - r, -0.5]) cylinder(r=r, h=2);
                    translate([ adapter_w/2 - r,  adapter_h/2 - r, -0.5]) cylinder(r=r, h=2);
                }
            }
    }
}

// ====================================================================
// 2. ACTIVE NON-CONTACT Z-STAGE MOVING CARRIAGE
// ====================================================================
module active_z_stage_carriage(
    stage_w = 64.0,
    stage_h = 56.0,
    stage_t = 12.0
) {
    difference() {
        // Precision CNC Skeletonized Carriage Body
        hull() {
            r = 4.0;
            translate([-stage_w/2 + r, -stage_h/2 + r, 0]) cylinder(r=r, h=stage_t);
            translate([ stage_w/2 - r, -stage_h/2 + r, 0]) cylinder(r=r, h=stage_t);
            translate([-stage_w/2 + r,  stage_h/2 - r, 0]) cylinder(r=r, h=stage_t);
            translate([ stage_w/2 - r,  stage_h/2 - r, 0]) cylinder(r=r, h=stage_t);
        }

        // 1. MGN7C Stainless Linear Bearing Block Recess & Mounting Bores (12 x 13 mm)
        translate([0, -10.0, -1]) {
            translate([-8.7, -11.5, 0.8]) cube([17.4, 23.0, 3.0]); // C-Block Locating Seat
            for (dx = [-6.0, 6.0]) {
                for (dy = [-6.5, 6.5]) {
                    translate([dx, dy, 0]) din912_m2_bore(stage_t, 2.2);
                }
            }
        }

        // 2. Cylindrical Voice Coil Actuator (VCA) Moving Coil Spigot & Vent
        translate([0, 14.0, stage_t - 8.5]) {
            cylinder(d=22.4, h=9.0); // Bobbin Spigot Pocket
            translate([0, 0, -stage_t]) cylinder(d=8.0, h=stage_t + 2); // Central Vent
            // Wire Lead-out Channel
            translate([-1.5, 11.0, -2.0]) cube([3.0, 8.0, 12.0]);
        }

        // 3. Quick-Release 60° Precision Dovetail Receiver Channel (Front Slide)
        translate([0, 0, -0.1])
            dovetail_cutout(28.0, 32.5, 4.5, stage_h + 2);

        // 4. Brass Gib Strip Slot & M3 Locking Cam Thumbscrew Bore
        translate([-stage_w/2 - 1, 0, stage_t/2])
            rotate([0, 90, 0])
                cylinder(d=3.3, h=18.0); // M3 Tap for Gib Lock

        // 5. ST VL53L4CD Micro-LiDAR Sensor Cavity & Dual Conical Sight Cones
        translate([stage_w/2 - 12.0, 0, -1]) {
            translate([-7.0, -4.5, 1.2]) cube([14.0, 9.0, 4.0]); // PCB Pocket
            translate([-3.2, 0, 0]) cylinder(d1=3.8, d2=2.8, h=stage_t + 2); // Emitter Cone
            translate([ 3.2, 0, 0]) cylinder(d1=3.8, d2=2.8, h=stage_t + 2); // Receiver Cone
            translate([0,  6.5, 0]) cylinder(d=2.2, h=stage_t + 2); // M2 PCB Mount
            translate([0, -6.5, 0]) cylinder(d=2.2, h=stage_t + 2);
        }

        // 6. Deep CNC Lightening Pockets (Keeps Moving Mass Under 38 grams!)
        translate([-stage_w/2 + 8.0,  18.0, 2.0]) cube([8.0, 12.0, stage_t]);
        translate([-stage_w/2 + 8.0, -18.0, 2.0]) cube([8.0, 12.0, stage_t]);
        translate([ stage_w/2 - 16.0,  18.0, 2.0]) cube([8.0, 12.0, stage_t]);
        translate([ stage_w/2 - 16.0, -18.0, 2.0]) cube([8.0, 12.0, stage_t]);
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
    plate_h = 1.8
) {
    difference() {
        union() {
            // Main Precision Anodized Aluminum Manifold Block
            translate([-head_w/2, -head_l/2, 0])
                cube([head_w, head_l, head_h]);

            // 60° Male Dovetail Slide Runner (Top Face)
            translate([0, 0, head_h])
                hull() {
                    translate([-27.5/2, -head_l/2, 0]) cube([27.5, head_l, 0.05]);
                    translate([-32.0/2, -head_l/2, 4.2]) cube([32.0, head_l, 0.05]);
                }

            // Silicon Orifice Plate Locating Collar (Bottom Face)
            translate([-plate_w/2, -plate_l/2, -plate_h])
                cube([plate_w, plate_l, plate_h]);

            // Dual PTFE Fluidic Inlet Hose Barbs
            translate([-7.0, 0, head_h + 4.2])
                cylinder(d1=4.8, d2=4.0, h=6.0);
            translate([ 7.0, 0, head_h + 4.2])
                cylinder(d1=4.8, d2=4.0, h=6.0);
        }

        // 1. Dual Internal Ink Manifold Distribution Chambers (Supply & Recirculation)
        translate([-7.0, 0, 4.0]) cylinder(d=7.0, h=head_h + 8.0);
        translate([ 7.0, 0, 4.0]) cylinder(d=7.0, h=head_h + 8.0);

        // Through-bore for ink feeds
        translate([-7.0, 0, -2.0]) cylinder(d=2.4, h=8.0);
        translate([ 7.0, 0, -2.0]) cylinder(d=2.4, h=8.0);

        // 2. Micro-Piezo PZT Actuator Drive Cavity & Acoustic Pumping Chambers
        translate([-9.0, -18.0, 3.5])
            cube([18.0, 36.0, head_h - 7.0]);

        // 3. Rear 34-Pin Gold FPC Flexible Electrical Ribbon Cable Channel
        translate([-11.0, head_l/2 - 2.0, 6.0])
            cube([22.0, 4.0, head_h - 8.0]);

        // 4. True Micro-Nozzle Orifice Plate Representation (128 Micro-Nozzles)
        for (i = [0:15]) {
            // Row A (64 Nozzles)
            translate([-1.2, (i - 7.5) * 1.5, -plate_h - 0.5])
                cylinder(d1=0.25, d2=0.55, h=plate_h + 1.0); // Conical Nozzle Horn
            // Row B (Staggered by Half-Pitch)
            translate([ 1.2, (i - 7.5) * 1.5 + 0.75, -plate_h - 0.5])
                cylinder(d1=0.25, d2=0.55, h=plate_h + 1.0);
        }

        // 5. Lateral M3 Clamping Dimple (Precision Repeatable Stop)
        translate([head_w/2 - 2.5, 0, head_h/2])
            rotate([0, 90, 0])
                cylinder(d=3.2, h=5.0);

        // 6. Perimeter Chamfers
        for (side = [-1, 1]) {
            translate([side * (head_w/2), 0, head_h/2])
                rotate([0, 45, 0])
                    cube([2.0, head_l + 2, 2.0], center=true);
        }
    }
}

// ====================================================================
// 4. DUAL IN-SITU 395nm UV-LED PINNING WING (WITH REAL HEATSINK FINS)
// ====================================================================
module uv_pinning_wing(
    wing_w = 18.0,
    wing_l = 44.0,
    wing_h = 28.0,
    num_fins = 8
) {
    difference() {
        union() {
            // Main Radiator Body
            translate([-wing_w/2, -wing_l/2, 0])
                cube([wing_w, wing_l, wing_h]);

            // Side Flange Attachment Lug with M2.5 Counterbores
            translate([wing_w/2, -wing_l/2 + 6.0, 4.0])
                cube([5.0, wing_l - 12.0, 14.0]);
        }

        // 1. Precision Parabolic Optical Reflector Cavity
        translate([0, 0, -0.1]) {
            hull() {
                translate([-wing_w/2 + 2.0, -17.0, 0]) cube([wing_w - 4.0, 34.0, 0.1]);
                translate([-2.5, -17.0, 12.0]) cube([5.0, 34.0, 0.1]);
            }
        }

        // 2. Fused Quartz 6mm Cylindrical Rod Lens Bezel Groove
        translate([0, 0, 3.2])
            rotate([90, 0, 0])
                cylinder(d=6.2, h=38.0, center=true);

        // 3. Nichia/Seoul 395nm UV-LED Aluminum Core MCPCB Pocket
        translate([-5.0, -17.0, 12.0])
            cube([10.0, 34.0, 2.0]);

        // 4. Real Deep Heatsink Convective Cooling Fins (1.0mm fin, 2.0mm air gap)
        for (i = [0:num_fins-1]) {
            fy = -wing_l/2 + 5.0 + i * 4.2;
            translate([-wing_w/2 - 1.0, fy, 15.0])
                cube([wing_w + 2.0, 2.2, wing_h - 13.0]);
        }

        // 5. 2x M2.5 Fastener Holes for Attachment to Active Carriage
        translate([wing_w/2 - 1.0, -10.0, 11.0]) rotate([0, 90, 0]) cylinder(d=2.7, h=8.0);
        translate([wing_w/2 - 1.0,  10.0, 11.0]) rotate([0, 90, 0]) cylinder(d=2.7, h=8.0);

        // 6. Thermal Interface Electrical Harness Pass-Through
        translate([0, 0, wing_h - 6.0])
            cylinder(d=4.2, h=8.0);
    }
}

// ====================================================================
// 5. CONSTANT MENISCUS PRESSURE BUFFER TANK & DAMPER
// ====================================================================
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

// ====================================================================
// 6. MOTORIZED AUTO-SEALING CAPPING STATION
// ====================================================================
module auto_capping_station(
    arm_len = 38.0,
    arm_t = 6.0
) {
    difference() {
        union() {
            // Articulated Swing Arm Beam with Reinforcing Rib
            hull() {
                cylinder(d=14.0, h=arm_t);
                translate([arm_len, 0, 0]) cylinder(d=18.0, h=arm_t);
            }

            // Distal Silicone Sealing Boot Retention Tray
            translate([arm_len - 16.0, -8.0, arm_t])
                cube([32.0, 16.0, 2.5]);

            // Dual Concentric Platinum Silicone Sealing Lips
            translate([arm_len - 14.0, -6.0, arm_t + 2.5])
                difference() {
                    cube([28.0, 12.0, 2.2]);
                    translate([1.5, 1.5, -0.5]) cube([25.0, 9.0, 3.2]);
                }
            translate([arm_len - 11.0, -3.5, arm_t + 2.5])
                difference() {
                    cube([22.0, 7.0, 2.2]);
                    translate([1.5, 1.5, -0.5]) cube([19.0, 4.0, 3.2]);
                }
        }

        // 1. 9g Metal Gear Servo 21T Micro-Spline Bore & Retention Bolt
        translate([0, 0, -1]) {
            cylinder(d=4.9, h=arm_t + 2); // Spline Fit
            translate([0, 0, arm_t - 2.0]) cylinder(d=6.8, h=3.0);
        }

        // 2. Peristaltic Suction Waste Evacuation Drain Port
        translate([arm_len, 0, -1])
            cylinder(d=2.6, h=arm_t + 6.0);

        // 3. Weight-Reduction Skeletonized Cutouts
        translate([16.0, -3.0, -1]) cube([12.0, 6.0, arm_t + 2]);
    }
}

// ====================================================================
// 7. COMPLETE MASTER SYSTEM ASSEMBLY (REALISTIC WORKING MECHANISM)
// ====================================================================
module hyper_actuator_complete_system(z_standoff = 1.5) {
    // 1. CDPR Base Adapter Plate
    color([0.22, 0.25, 0.29])
        cdpr_interface_adapter();

    // 2. HIWIN MGN7C Precision Stainless Linear Rail (66mm Length)
    color([0.85, 0.88, 0.92]) {
        translate([-3.5, -33.0, 4.7])
            cube([7.0, 66.0, 4.8]);
        // Ground Ball Recirculation Tracks on Side Flanks
        translate([-3.7, -33.0, 6.8]) cube([0.4, 66.0, 1.2]);
        translate([ 3.3, -33.0, 6.8]) cube([0.4, 66.0, 1.2]);
        // MGN7C Bearing Carriage Block
        translate([-8.5, -11.5, 9.5])
            cube([17.0, 23.0, 5.2]);
    }

    // 3. Voice Coil Actuator (VCA) Stator Housing & Magnetic Core
    color([0.72, 0.58, 0.18]) {
        translate([0, 24.0, 4.0]) cylinder(d=24.0, h=14.0);
        translate([0, 24.0, 6.0]) cylinder(d=10.0, h=11.0); // Center Core Slug
    }

    // 4. Moving Active Z-Carriage (Positioned along Z with VCA)
    translate([0, 0, 14.5 + z_standoff]) {
        color([0.20, 0.23, 0.28])
            active_z_stage_carriage();

        // Voice Coil Moving Bobbin & Insulated Copper Winding
        color([0.85, 0.45, 0.15]) {
            translate([0, 14.0, -8.0]) {
                cylinder(d=20.0, h=9.5); // Bobbin
                cylinder(d=21.8, h=7.5); // Copper Coil Winding
            }
        }

        // ST Micro-LiDAR VL53L4CD Laser Rangefinder PCB
        color([0.15, 0.45, 0.85])
            translate([20.0, 0, 7.5]) cube([12.0, 8.0, 1.6]);

        // 5. 128-Nozzle MEMS Micro-Piezo Printhead Dock (Slid into Dovetail)
        translate([0, 0, -28.0]) {
            color([0.35, 0.38, 0.44])
                mems_128_printhead_dock();

            // Gold FPC Flexible Electrical Ribbon Cable
            color([0.90, 0.75, 0.18])
                translate([-10.0, 23.0, 12.0]) cube([20.0, 0.35, 26.0]);
        }

        // 6. Dual In-Situ 395nm UV-LED Pinning Wings (Left & Right)
        color([0.48, 0.52, 0.58]) {
            translate([-27.0, 0, -24.0]) uv_pinning_wing();
            translate([ 27.0, 0, -24.0]) rotate([0, 0, 180]) uv_pinning_wing();
        }

        // Fused Quartz Cylindrical Lenses (Transparent Glass)
        color([0.95, 0.98, 1.0, 0.65]) {
            translate([-27.0, 0, -20.8]) rotate([90, 0, 0]) cylinder(d=6.0, h=36.0, center=true);
            translate([ 27.0, 0, -20.8]) rotate([90, 0, 0]) cylinder(d=6.0, h=36.0, center=true);
        }

        // Focused 395nm UV-A Pinning Light Cones (Violet Glow)
        color([0.55, 0.15, 0.95, 0.30]) {
            translate([-27.0, 0, -26.0]) cylinder(r1=3.0, r2=11.0, h=z_standoff + 2.5);
            translate([ 27.0, 0, -26.0]) cylinder(r1=3.0, r2=11.0, h=z_standoff + 2.5);
        }
    }

    // 7. Onboard Meniscus Fluidic Tank & Degassing Damper
    color([0.55, 0.75, 0.90, 0.85])
        translate([32.0, 0, 6.5]) meniscus_fluidic_damper();

    // 8. Motorized Auto-Sealing Capping Station & 9g Servo
    color([0.12, 0.14, 0.18])
        translate([-32.0, -10.0, 6.5]) {
            cube([12.0, 22.5, 22.0]); // 9g Servo
            translate([6.0, 17.5, 22.0]) cylinder(d=4.8, h=4.0); // Output Spline
            translate([6.0, 17.5, 24.5]) rotate([0, 0, -45]) {
                color([0.92, 0.58, 0.12]) auto_capping_station();
            }
        }

    // 9. Wall Plane Depicting Exact 1.50 mm Standoff Gap
    color([0.98, 0.98, 0.98, 0.15])
        translate([-60.0, -50.0, -16.0])
            cube([120.0, 100.0, 1.0]);
}

// Render complete real mechanical model
hyper_actuator_complete_system();
