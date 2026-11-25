// PROJECT W.A.L.L. - HYPER-ACTUATOR Mk-1: Binary STL Direct Viewer
// Opens and renders the true manufacturing binary STL files directly in OpenSCAD.
// Press F5 in OpenSCAD for instant 3D inspection.

$fn = 32;

module view_hyper_actuator_stls() {
    // 1. CDPR Carriage Interface Adapter Baseplate
    color([0.22, 0.24, 0.28])
        import("exports/cdpr_interface_adapter.stl");

    // 2. Active Moving Z-Stage Carriage
    color([0.30, 0.35, 0.42])
        translate([0, 0, 16.0])
            import("exports/active_z_stage_carriage.stl");

    // 3. 128-Nozzle MEMS Micro-Piezo Printhead Dock
    color([0.45, 0.48, 0.54])
        translate([0, 0, -12.0])
            import("exports/mems_128_printhead_dock.stl");

    // 4. Dual In-Situ 395nm UV-LED Pinning Wings (Left & Right)
    color([0.55, 0.58, 0.64]) {
        translate([-27.0, 0, -8.0])
            import("exports/uv_pinning_wing.stl");
        translate([ 27.0, 0, -8.0])
            rotate([0, 0, 180])
                import("exports/uv_pinning_wing.stl");
    }

    // 5. Constant Meniscus Fluidic Reservoir & Damper
    color([0.40, 0.75, 0.95])
        translate([32.0, 0, 6.0])
            import("exports/meniscus_fluidic_damper.stl");

    // 6. Motorized Auto-Sealing Capping Station
    color([0.95, 0.60, 0.15])
        translate([-32.0, -10.0, 24.0])
            import("exports/auto_capping_station.stl");
}

// Or render the unified master STL:
// import("exports/hyper_actuator_assembly.stl");

view_hyper_actuator_stls();

