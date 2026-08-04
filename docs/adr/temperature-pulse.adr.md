# ADR: Temperature Pulse Propagation in a Marine Horizontal Pipeline

## Status
Proposed

## Context
The user wants to simulate the propagation of a thermal pulse along a 1000 m horizontal submarine pipeline carrying dead crude oil. A rectangular temperature pulse (+60 °C, 500 s duration) is injected at the inlet starting at t = 1000 s; the response is tracked via time-trend gauges at every 100 m. The deliverable includes the `.mr3` input file, a Python build script, and a Jupyter notebook with temporal temperature evolution plots.

---

## System Description
A single horizontal production pipe (1000 m, ID 0.1524 m) carries dead crude oil (API 35.95, GOR 0, no free gas) in a marine environment at 20 °C. Liquid enters through a prescribed flow-rate source at the inlet (Q = 3000 sm³/d, constant) whose temperature follows a step schedule: base 20 °C → 80 °C at t = 1000 s → 20 °C at t = 1500 s. The outlet drains to a separator held at 15 kgf/cm². No service line, no artificial lift, no valves.

Estimated fluid velocity: Q/A ≈ 0.03472 m³/s / 0.01824 m² ≈ **1.9 m/s**. The thermal front reaches the outlet at t ≈ 1526 s; the pulse tail exits at t ≈ 2026 s.

---

## Decisions

### Simulation mode
| Item | Value |
|------|-------|
| `system` | `"PROD"` |
| `initialConfig.transient` | `true` |
| `initialConfig.initialCondition` | `1` (start from steady-state solution) |
| `initialConfig.gasLine` | `false` |
| `initialConfig.xyMode` | `false` (direct angle mode) |
| `initialConfig.pressureTable` | `true` (performance for transient) |
| `time.finalTime` | `3000` s |

### Fluids
Single black-oil production fluid, no gas fluid, no complementary fluid.

| Field | Value |
|-------|-------|
| `productionFluid[0].id` | `0` |
| `productionFluid[0].api` | `35.95` |
| `productionFluid[0].gor` | `0.0` sm³/sm³ |
| `productionFluid[0].gasDensity` | `0.845` (air = 1) |
| `productionFluid[0].bsw` | `0.0` |
| Viscosity | `deadOilModel: 3` (Glaso, **default**) |
| Viscosity | `liveOilModel: 0` (Beggs & Robinson, **default**) |

Precomputed property table grid (`compTable`, required when `pressureTable: true`):

| Field | Value |
|-------|-------|
| `numPoints` | `50` |
| `minPressure` | `1.0` kgf/cm² |
| `maxPressure` | `60.0` kgf/cm² |
| `minTemperature` | `15.0` °C |
| `maxTemperature` | `90.0` °C |

### Materials & cross-sections

**material (id → properties):**

| id | label | type | conductivity W/(m·°C) | specificHeat J/(kg·°C) | rho kg/m³ |
|----|-------|------|-----------------------|------------------------|-----------|
| `"steel"` | carbon-steel | 0 (solid) | 50 | 500 | 7800 |

**crossSection:**

| id | innerDiameter m | roughness m | layers |
|----|-----------------|-------------|--------|
| `"cs-6in"` | 0.1524 | 1.83e-4 | 1 layer: materialId=`"steel"`, `THICKNESS`, thickness=0.00711 m, discretization=2 |

> Layer thickness 0.00711 m corresponds to 6″ Schedule 40 wall. `discretization: 2` radial nodes for transient heat conduction accuracy.

### Pipeline geometry

One production segment (`productionPipe`):

| Field | Value |
|-------|-------|
| `id` | `"pipe-main"` |
| `label` | `"flowline"` |
| `crossSectionId` | `"cs-6in"` |
| `formationId` | *(none — not buried)* |
| `environment` | `0` (user-defined medium) |
| `angle` | `0.0` radians (horizontal) |
| `discretization` | `[{ "numCells": 20, "length": 50.0 }]` — 20 cells × 50 m = 1000 m |
| `initialAndAmbientConditions.measuredPosition` | `[0, 1]` |
| `initialAndAmbientConditions.ambientTemp` | `[20.0, 20.0]` °C |
| `initialAndAmbientConditions.ambientVel` | `[0.3, 0.3]` m/s |

> No `initialConditions` pressure/temperature profiles needed: `initialCondition: 1` uses the steady-state solver.

### Boundary conditions

**Inlet — `liquidSource` (array, 1 entry):**

Temperature pulse encoded as a near-step using 1-second ramps to remain piecewise-linear:

| Field | Value |
|-------|-------|
| `prodFluidId` | `0` |
| `measuredLength` | `0.1` m (inlet) |
| `time` | `[0, 1000, 1001, 1500, 1501, 3000]` s |
| `temperature` | `[20, 20, 80, 80, 20, 20]` °C |
| `liquidFlowRate` | `[3000, 3000, 3000, 3000, 3000, 3000]` sm³/d |

**Outlet — `separator`:**

```json
"separator": { "active": true, "time": [0], "pressure": [15.0] }
```

### Equipment & events

No valves, no artificial lift, no service line. The only transient event is the inlet temperature schedule above.

### Time schedule

```json
"time": {
  "finalTime": 3000,
  "times":  [0,    990,  1000, 1499, 1500, 1510, 3000],
  "maxDT":  [5.0,  0.5,  0.2,  0.2,  0.2,  0.5,  5.0],
  "saveSnapshot": [1000, 1500, 3000]
}
```

Rationale: maxDT = 0.2 s in the ±10 s window around each temperature step (t = 1000 s and t = 1500 s); relaxed to 5 s in the quiet phases. Snapshots at pulse start, pulse end, and final time for restart capability.

### Outputs

**`productionProfile`** — spatial snapshots to visualise pulse propagation along the pipe:

```json
"productionProfile": {
  "active": true,
  "time": [0, 1000, 1200, 1400, 1530, 1700, 2100, 2500, 3000],
  "temperature": true,
  "pressure": true,
  "holdup": true,
  "usl": true
}
```

**`productionTrend`** — 11 time-series gauges, one per ~100 m station:

| gauge # | label | measuredLength m | dt s |
|---------|-------|-----------------|------|
| 0 | `"x=0m"` | 0 | 1 |
| 1 | `"x=100m"` | 100 | 1 |
| 2 | `"x=200m"` | 200 | 1 |
| 3 | `"x=300m"` | 300 | 1 |
| 4 | `"x=400m"` | 400 | 1 |
| 5 | `"x=500m"` | 500 | 1 |
| 6 | `"x=600m"` | 600 | 1 |
| 7 | `"x=700m"` | 700 | 1 |
| 8 | `"x=800m"` | 800 | 1 |
| 9 | `"x=900m"` | 900 | 1 |
| 10 | `"x=1000m"` | 1000 | 1 |

Each trend entry enables: `temperature: true`, `pressure: true`, `holdup: true`.

> With 20 cells × 50 m, cell centers fall at 25, 75, 125, …, 975 m. Marlim3 maps each `measuredLength` to the nearest cell center; the actual logged position will differ by up to 25 m. The implementation script should use `branch.resultados['productionTrend']` `.attrs['measured_length']` to confirm actual positions and label the notebook plots accordingly.

### Advanced settings

`pressureTable: true` only. All other `initialConfig` fields use default values.

---

## Assumed defaults

| Parameter | Value | Reason |
|-----------|-------|--------|
| Pipe wall thickness | 0.00711 m (7.11 mm) | 6″ Schedule 40 standard; user specified "carbon steel" without thickness |
| Pipe roughness | 1.83e-4 m | Marlim3 default for carbon steel |
| Ambient velocity | 0.3 m/s | Marlim3 planning-skill default for external convection |
| deadOilModel | 3 (Glaso) | Marlim3 default; user did not specify viscosity correlation |
| liveOilModel | 0 (Beggs & Robinson) | Marlim3 default |
| Temperature ramp width | 1 s | Step approximation via piecewise linear; user said "sobe" (step) |
| Layer radial discretization | 2 nodes | Improves transient wall-conduction resolution |
| compTable maxPressure | 60 kgf/cm² | 4× separator pressure; conservative upper bound |

---

## Cross-reference table

| Reference | Source value | Target | OK? |
|-----------|-------------|--------|-----|
| `productionPipe[0].crossSectionId` | `"cs-6in"` | `crossSection[0].id = "cs-6in"` | ✓ |
| `crossSection[0].layers[0].materialId` | `"steel"` | `material[0].id = "steel"` | ✓ |
| `liquidSource[0].prodFluidId` | `0` | `productionFluid[0].id = 0` | ✓ |
| `liquidSource[0].measuredLength` | `0.1 m` | inside pipe total `20 × 50 = 1000 m` | ✓ |
| `productionProfile.time` max | `3000 s` | `time.finalTime = 3000 s` | ✓ |
| `productionTrend[*].measuredLength` max | `1000 m` | inside pipe total `1000 m` | ✓ |
| `compTable` P range | `[1, 60]` kgf/cm² | covers separator 15 + pressure drop | ✓ |
| `compTable` T range | `[15, 90]` °C | covers pulse 80 °C + margin | ✓ |
| Measured lengths sum | 20 × 50 m = 1000 m | intended pipe length 1000 m | ✓ |

---

## Deliverables

- `simulations/temperature-pulse/temperature-pulse.mr3` — JSON simulation input (English keys, `"language": "en"`)
- `simulations/temperature-pulse/build_model.py` — Python script using `marlim3.Branch` to construct and serialize the `.mr3`
- `docs/tutorials/5_temperature_pulse.ipynb` — Jupyter notebook that runs the simulation and plots temporal temperature evolution at each 100 m gauge (11 lines on a single `T × t` axes)
- `docs/temperature-pulse.qa.md` — QA report (written by QA agent after implementation)

---

## Acceptance criteria

1. Steady-state (initial condition) converges: pressure at outlet ≈ 15 kgf/cm²; temperature along the pipe settles to a value between 15 °C and 20 °C (pipe cools to ambient from inlet 20 °C).
2. The trend at `x=0 m` shows temperature rising from 20 °C to ≈80 °C within 2 s of t = 1000 s, and returning to 20 °C within 2 s of t = 1500 s.
3. The thermal front arrives at `x=500 m` gauge at t ≈ 1263 s (±30 s) — consistent with advection time 500/1.9 ≈ 263 s after t = 1000 s.
4. The thermal front arrives at `x=1000 m` gauge at t ≈ 1526 s (±50 s).
5. No energy is created: peak temperature at any interior gauge must not exceed 80 °C; floor must not drop below the ambient 20 °C (ignoring initial cooldown).
6. All 11 trend files are written and readable as DataFrames via `branch.resultados['productionTrend']`.
7. The notebook renders all 11 temperature curves without errors; x-axis spans 0–3000 s.

---

## Skills referenced

- `.github/skills/marlim3-planning-interview/SKILL.md`
- `.github/skills/marlim3-json-schema/SKILL.md`
- `.github/skills/marlim3-fluid-configuration/SKILL.md`
- `.github/skills/marlim3-materials-cross-sections/SKILL.md`
- `.github/skills/marlim3-pipeline-geometry/SKILL.md`
- `.github/skills/marlim3-boundary-conditions/SKILL.md`
- `.github/skills/marlim3-time-transient/SKILL.md`
- `.github/skills/marlim3-output-configuration/SKILL.md`
