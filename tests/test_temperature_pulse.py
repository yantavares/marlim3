"""Integration tests for the temperature-pulse simulation (see docs/adr/temperature-pulse.adr.md)."""
import os

import pandas as pd
import pytest

import marlim3
from marlim3._download import executable_exists

CASE = os.path.join(
    os.path.dirname(__file__), "..", "simulations", "temperature-pulse", "temperature-pulse.mr3"
)

skip_sem_executavel = pytest.mark.skipif(
    not executable_exists(), reason="Executável Marlim3 não encontrado"
)


# ---------------------------------------------------------------------------
# Structural tests — no executable required
# ---------------------------------------------------------------------------

def test_input_loads():
    """The .mr3 file must load without errors."""
    caso = marlim3.Branch()
    caso.from_json(CASE)
    assert caso.system == "PROD"


def test_cross_references():
    """Every cross-reference in the ADR cross-reference table must resolve."""
    caso = marlim3.Branch()
    caso.from_json(CASE)

    cs_ids = {c["id"] for c in caso.crossSection}
    mat_ids = {m["id"] for m in caso.material}
    fluid_ids = {f["id"] for f in caso.productionFluid}

    # productionPipe → crossSection
    for pipe in caso.productionPipe:
        assert pipe["crossSectionId"] in cs_ids, (
            f"pipe {pipe['id']}: crossSectionId {pipe['crossSectionId']!r} not in crossSection ids {cs_ids}"
        )

    # crossSection layers → material
    for cs in caso.crossSection:
        for layer in cs.get("layers", []):
            assert layer["materialId"] in mat_ids, (
                f"cs {cs['id']}: layer materialId {layer['materialId']!r} not in material ids {mat_ids}"
            )

    # liquidSource → productionFluid
    for src in caso.liquidSource:
        assert src["prodFluidId"] in fluid_ids, (
            f"liquidSource {src['id']}: prodFluidId {src['prodFluidId']!r} not in fluid ids {fluid_ids}"
        )


def test_liquid_source_arrays_consistent():
    """liquidSource time/temperature/liquidFlowRate arrays must have equal length."""
    caso = marlim3.Branch()
    caso.from_json(CASE)
    for src in caso.liquidSource:
        n = len(src["time"])
        assert len(src["temperature"]) == n, "temperature array length mismatch"
        assert len(src["liquidFlowRate"]) == n, "liquidFlowRate array length mismatch"


def test_time_arrays_consistent():
    """time.times and time.maxDT must have equal length; times[0]==0."""
    caso = marlim3.Branch()
    caso.from_json(CASE)
    t = caso.time
    assert len(t["times"]) == len(t["maxDT"]), "times/maxDT length mismatch"
    assert t["times"][0] == 0, "times must start at 0"
    assert t["finalTime"] > 0


def test_profile_times_within_final_time():
    """All productionProfile times must be <= finalTime."""
    caso = marlim3.Branch()
    caso.from_json(CASE)
    final = caso.time["finalTime"]
    for t in caso.productionProfile["time"]:
        assert t <= final, f"profile time {t} > finalTime {final}"


def test_trend_positions_within_pipe():
    """All productionTrend measuredLength values must be within the pipe total length."""
    caso = marlim3.Branch()
    caso.from_json(CASE)
    total = sum(
        d["numCells"] * d["length"]
        for pipe in caso.productionPipe
        for d in pipe["discretization"]
    )
    for trend in caso.productionTrend:
        pos = trend["measuredLength"]
        assert 0 <= pos <= total, f"trend position {pos} outside pipe length [0, {total}]"


def test_eleven_trend_gauges():
    """Must have exactly 11 trend gauges (0–1000 m, every 100 m)."""
    caso = marlim3.Branch()
    caso.from_json(CASE)
    assert len(caso.productionTrend) == 11


def test_comtable_covers_operating_envelope():
    """compTable temperature range must cover the pulse peak (80°C)."""
    caso = marlim3.Branch()
    caso.from_json(CASE)
    ct = caso.compTable
    assert ct["maxTemperature"] >= 80.0, "compTable maxTemperature must cover pulse temperature"
    assert ct["maxPressure"] >= 15.0, "compTable maxPressure must cover separator pressure"


# ---------------------------------------------------------------------------
# Simulation test — requires executable
# ---------------------------------------------------------------------------

def _simular(caso, label, tmp_path):
    original_cwd = os.getcwd()
    try:
        os.chdir(str(tmp_path))
        caso.simulate(label=label, directory="resultados")
    finally:
        os.chdir(original_cwd)


@skip_sem_executavel
@pytest.mark.simulacao
def test_simulation_runs_and_results_present(tmp_path):
    """Full transient run must complete and return both profile and trend results."""
    caso = marlim3.Branch()
    caso.from_json(CASE)
    _simular(caso, "temperature-pulse", tmp_path)

    assert "productionProfile" in caso.resultados
    df_prof = caso.resultados["productionProfile"]
    assert isinstance(df_prof, pd.DataFrame) and not df_prof.empty

    assert "productionTrend" in caso.resultados
    trends = caso.resultados["productionTrend"]
    assert len(trends) == 11, f"Expected 11 trend gauges, got {len(trends)}"


@skip_sem_executavel
@pytest.mark.simulacao
def test_acceptance_criteria(tmp_path):
    """ADR acceptance criteria: pulse shape and propagation timing."""
    caso = marlim3.Branch()
    caso.from_json(CASE)
    _simular(caso, "temperature-pulse", tmp_path)

    trends = caso.resultados["productionTrend"]

    # Criterion 1: outlet pressure ≈ 15 kgf/cm² in steady-state profile
    df_prof = caso.resultados["productionProfile"]
    pres_col = [c for c in df_prof.columns if "Pressure" in c or "Pressao" in c][0]
    # Profile MultiIndex level 0 = time (integer seconds); level 1 = row index
    t0 = df_prof.index.get_level_values(0).unique()[0]
    outlet_p = df_prof.loc[t0].iloc[-1][pres_col]
    assert abs(outlet_p - 15.0) < 1.5, f"Outlet pressure {outlet_p:.1f} not near 15 kgf/cm²"

    # Criterion 2: gauge at x=0 m must reach ≥ 75°C within 5 s of t=1001
    gauge_0 = next(
        df for df in trends.values()
        if df.attrs.get("label", "") == "x=0m"
    )
    temp_col_t = [c for c in gauge_0.columns if "Temperature" in c or "Temperatura" in c][0]
    window = gauge_0.loc[(gauge_0.index >= 1000) & (gauge_0.index <= 1010)]
    assert window[temp_col_t].max() >= 75.0, "Gauge x=0m did not reach ≥75°C near t=1001s"

    # Criterion 3: gauge at x=500 m must reach ≥ 60°C between t=1200 and t=1400
    gauge_500 = next(
        df for df in trends.values()
        if df.attrs.get("label", "") == "x=500m"
    )
    temp_col_t = [c for c in gauge_500.columns if "Temperature" in c or "Temperatura" in c][0]
    window_500 = gauge_500.loc[(gauge_500.index >= 1200) & (gauge_500.index <= 1400)]
    assert window_500[temp_col_t].max() >= 60.0, "Gauge x=500m did not reach ≥60°C between t=1200–1400s"

    # Criterion 4: no energy created — max temperature at any interior gauge ≤ 81°C
    for df in trends.values():
        t_col = [c for c in df.columns if "Temperature" in c or "Temperatura" in c][0]
        assert df[t_col].max() <= 81.0, (
            f"Gauge {df.attrs.get('label')} exceeded 81°C (max={df[t_col].max():.1f})"
        )
