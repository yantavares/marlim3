"""
Build script for the temperature-pulse simulation.

Constructs the Marlim3 Branch programmatically and writes
simulations/temperature-pulse/temperature-pulse.mr3.

Usage:
    uv run python simulations/temperature-pulse/build_model.py
    uv run python simulations/temperature-pulse/build_model.py --simulate
"""

import argparse
import os
import sys

import marlim3

# ---------------------------------------------------------------------------
# Model definition
# ---------------------------------------------------------------------------

def build() -> marlim3.Branch:
    case = marlim3.Branch()
    case.system = "PROD"

    # --- initialConfig ---
    case.initialConfig = {
        "gasLine": False,
        "transient": True,
        "initialCondition": 1,   # start from steady-state solution
        "xyMode": False,
        "pressureTable": True,
    }

    # --- Fluid ---
    case.productionFluid = [
        {
            "id": 0,
            "api": 35.95,
            "gor": 0.0,
            "gasDensity": 0.845,
            "bsw": 0.0,
        }
    ]

    # --- Precomputed property table grid (required when pressureTable=True) ---
    case.compTable = {
        "numPoints": 50,
        "minPressure": 1.0,
        "maxPressure": 60.0,
        "minTemperature": 15.0,
        "maxTemperature": 90.0,
    }

    # --- Material ---
    case.material = [
        {
            "id": 0,
            "label": "carbon-steel",
            "type": 0,          # solid
            "conductivity": 50,
            "specificHeat": 500,
            "rho": 7800,
        }
    ]

    # --- Cross-section: 6" Sch 40, ID=0.1524 m ---
    case.crossSection = [
        {
            "id": 0,
            "label": "cs-6in",
            "innerDiameter": 0.1524,
            "roughness": 1.83e-4,
            "layers": [
                {
                    "label": "steel-wall",
                    "materialId": 0,
                    "layerMeasurementType": "THICKNESS",
                    "thickness": 0.00711,   # 6" Sch 40 wall thickness
                    "discretization": 2,    # radial nodes for transient accuracy
                }
            ],
        }
    ]

    # --- Production pipe: 1000 m horizontal, seawater at 20 °C ---
    case.productionPipe = [
        {
            "id": 0,
            "label": "flowline",
            "crossSectionId": 0,
            "environment": 1,       # seawater
            "angle": 0.0,           # horizontal
            "discretization": [{"numCells": 20, "length": 50.0}],
            "initialConditions": {
                "measuredPosition": [0, 1],
                "ambientTemp": [4.0, 4.0],
                "ambientVel": [0.3, 0.3],
            },
        }
    ]

    # --- Liquid source: inlet at 0.1 m with temperature pulse ---
    # Temperature schedule: 20°C base → 80°C at t=1000s (500s pulse) → 20°C
    # 1-second ramps approximate a step change (piecewise-linear interpolation)
    case.liquidSource = [
        {
            "id": 0,
            "prodFluidId": 0,
            "measuredLength": 0.1,
            "time":          [0,    1000, 1001, 1500, 1501, 3000],
            "temperature":   [20,   20,   80,   80,   20,   20],
            "liquidFlowRate": [3000, 3000, 3000, 3000, 3000, 3000],
        }
    ]

    # --- Outlet: separator at 15 kgf/cm² ---
    case.separator = {"active": True, "time": [0], "pressure": [15.0]}

    # --- Time schedule ---
    case.time = {
        "finalTime": 3000,
        "times": [0,   990,  1000, 1499, 1500, 1510, 3000],
        "maxDT": [5.0, 0.5,  0.2,  0.2,  0.2,  0.5,  5.0],
        "saveSnapshot": [1000, 1500, 3000],
    }

    # --- Spatial profiles at key times ---
    case.productionProfile = {
        "active": True,
        "time": [0, 1000, 1200, 1400, 1530, 1700, 2100, 2500, 3000],
        "temperature": True,
        "pressure": True,
        "holdup": True,
        "usl": True,
    }

    # --- Time-trend gauges every 100 m (11 gauges) ---
    gauge_positions = range(0, 1001, 100)   # 0, 100, 200, ..., 1000 m
    case.productionTrend = [
        {
            "active": True,
            "measuredLength": pos,
            "dt": 1.0,
            "label": f"x={pos}m",
            "temperature": True,
            "pressure": True,
            "holdup": True,
        }
        for pos in gauge_positions
    ]

    return case


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Build (and optionally run) the temperature-pulse simulation.")
    parser.add_argument("--simulate", action="store_true", help="Run the simulation after building.")
    args = parser.parse_args()

    case = build()

    # to_json() writes relative to CWD — chdir to the simulation folder first
    script_dir = os.path.dirname(os.path.abspath(__file__))
    original_cwd = os.getcwd()
    try:
        os.chdir(script_dir)
        case.to_json("temperature-pulse")
    finally:
        os.chdir(original_cwd)
    print(f"Wrote: {script_dir}/temperature-pulse.mr3")

    if args.simulate:
        sim_cwd = os.getcwd()
        try:
            os.chdir(script_dir)
            case.simulate(label="temperature-pulse", directory="results")
        finally:
            os.chdir(sim_cwd)
        print("Simulation complete. Results in simulations/temperature-pulse/results/")
        print(f"  productionProfile shape: {case.resultados['productionProfile'].shape}")
        print(f"  productionTrend gauges : {len(case.resultados['productionTrend'])}")


if __name__ == "__main__":
    main()
