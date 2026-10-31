"""NZE Intelligence - RNZEB prototype v0.2 (embodied + operational energy, net-zero year)."""
import json, os
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from rnzeb_engine import Operation, Generation, energy_net_zero, MJ_PER_KWH

HERE = os.path.dirname(os.path.abspath(__file__))
EE = json.load(open(os.path.join(HERE, "ee_tables.json")))
SYSTEMS = {"Steel": "steel", "Reinforced concrete": "rc", "Timber": "timber"}

# Case-study presets (Ercal & Shafique, Sustainable Horizons 2026)
OPS = {
    "low": dict(heat_kw=8.98, hours=1800, eff=3.5, cool_th=4350.0, cool_cop=3.5, light=702.4, appl=3720.0,
                desc=["Heat pump (COP 3.5)", "Heat pump cooling (COP 3.5)", "LED lighting", "A+++ appliances"]),
    "typ": dict(heat_kw=26.45, hours=1800, eff=0.92, cool_th=4350.0, cool_cop=1.0, light=4793.0, appl=5125.0,
                desc=["Gas boiler (92% efficient)", "Air conditioner", "Incandescent lighting", "Typical appliances"]),
}
GEN = dict(pv=39.9, irr=980, eff=0.215, wind=6025.4)

st.set_page_config(page_title="NZE Intelligence | RNZEB prototype", layout="wide")
st.title("NZE Intelligence: Realistic Net Zero Energy Building (RNZEB) prototype")
st.caption("Balances embodied energy (E1) and operational energy (E2) against on-site renewable "
           "generation (E3): 0 ≥ E1 + E2 − E3. Method: Ercal & Shafique, Sustainable Horizons (2026). "
           "Prototype v0.3: a concept-stage decision tool, not a compliance tool.")


def table(key):
    rows = [m for m in EE[key] if not m.get("excluded")]
    df = pd.DataFrame(rows)[["material", "qty_kg", "ee_factor"]]
    return df.rename(columns={"material": "Material", "qty_kg": "Quantity (kg)", "ee_factor": "EE (MJ/kg)"})


def ee_kwh(df):
    return float((df["Quantity (kg)"] * df["EE (MJ/kg)"]).sum() / MJ_PER_KWH)


def make_op(p):
    return Operation(heating_load_kw=p["heat_kw"], heating_hours=p["hours"], heating_eff=p["eff"],
                     cooling_kwh_thermal=p["cool_th"], cooling_cop=p["cool_cop"],
                     lighting_kwh=p["light"], appliances_kwh=p["appl"])


# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("1. Building")
    system = st.selectbox("Structural system", list(SYSTEMS))
    btype = st.radio("Building type", ["RNZE building", "Traditional building"],
                     help="RNZE: low embodied energy materials, low operational energy and renewable generation. "
                          "Traditional: typical materials and systems, no on-site generation.")
    mat_low = op_low = gen_on = (btype == "RNZE building")

    p = dict(OPS["low" if op_low else "typ"])
    g = dict(GEN)
    use_wind, uploaded = True, None
    k = f"{int(op_low)}{int(gen_on)}"  # widget keys follow the preset so defaults reset when it changes
    with st.expander("Advanced: adjust inputs"):
        st.markdown("**Operational energy**")
        p["heat_kw"] = st.number_input("Heating load (kW)", 0.0, 100.0, p["heat_kw"], 0.1, key="hk" + k)
        p["hours"] = st.number_input("Heating hours / year", 0, 8760, p["hours"], 50, key="hh" + k)
        p["eff"] = st.number_input("Heating COP (heat pump) or efficiency (boiler)", 0.5, 6.0, p["eff"], 0.01, key="ef" + k)
        p["cool_th"] = st.number_input("Cooling demand, thermal (kWh/yr)", 0.0, 50000.0, p["cool_th"], 50.0, key="ct" + k)
        p["cool_cop"] = st.number_input("Cooling COP", 0.5, 6.0, p["cool_cop"], 0.1, key="cc" + k)
        p["light"] = st.number_input("Lighting (kWh/yr)", 0.0, 20000.0, p["light"], 10.0, key="li" + k)
        p["appl"] = st.number_input("Appliances (kWh/yr)", 0.0, 20000.0, p["appl"], 10.0, key="ap" + k)
        if gen_on:
            st.markdown("**Renewable generation**")
            g["pv"] = st.slider("PV area (m²)", 0.0, 150.0, g["pv"], 0.1, key="pv" + k)
            g["irr"] = st.number_input("Solar irradiance (kWh/m²/yr)", 500, 1500, g["irr"], 10, key="ir" + k)
            g["eff"] = st.slider("PV efficiency", 0.10, 0.25, g["eff"], 0.005, key="pe" + k)
            use_wind = st.checkbox("Include roof wind turbine", value=True, key="uw" + k,
                                   help="Wind is optional; PV-only designs can also reach net zero.")
            g["wind"] = st.number_input("Wind yield (kWh/yr)", 0.0, 20000.0, g["wind"], 50.0,
                                        disabled=not use_wind, key="wy" + k)
        st.markdown("**Materials**")
        uploaded = st.file_uploader("Upload a Revit material take-off (CSV: Material, Quantity (kg), EE (MJ/kg))",
                                    type="csv")
        life = st.slider("Design life (years)", 20, 100, 50)

# ---------------- Calculations ----------------
key = f"{SYSTEMS[system]}_{'low' if mat_low else 'trad'}"
df = pd.read_csv(uploaded) if uploaded is not None else table(key)
st.subheader(f"{btype}: {system.lower()} structure")
with st.expander("Bill of materials (editable: change quantities or factors and the results update)", expanded=True):
    df = st.data_editor(df, num_rows="dynamic", width="stretch", key=f"bom_{key}")
op = make_op(p)
gen = Generation(pv_area_m2=g["pv"], irradiance_kwh_m2=g["irr"], pv_eff=g["eff"],
                 wind_kwh=g["wind"] if use_wind else 0) if gen_on else Generation(pv_area_m2=0, wind_kwh=0)
E1, E2, E3 = ee_kwh(df), op.annual_kwh(), gen.annual_kwh()
res = energy_net_zero(E1, E2, E3, lifespan=life)

# ---------------- Summary of the three energy flows ----------------
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("**E1 Materials**")
    st.write("Low embodied energy materials" if mat_low else "Typical materials")
    st.metric("Embodied energy", f"{E1:,.0f} kWh")
with c2:
    st.markdown("**E2 Operation**")
    b = op.breakdown()
    st.dataframe(pd.DataFrame({"Use": ["Heating", "Cooling", "Lighting", "Appliances"],
                               "System": p["desc"] if "desc" in p else OPS["low" if op_low else "typ"]["desc"],
                               "kWh/yr": [round(b[x]) for x in ["heating", "cooling", "lighting", "appliances"]]}),
                 hide_index=True, width="stretch")
    st.metric("Operational energy", f"{E2:,.0f} kWh/yr")
with c3:
    st.markdown("**E3 Renewable generation**")
    if gen_on:
        gb = gen.breakdown()
        st.dataframe(pd.DataFrame({"Source": [f"Solar PV ({g['pv']:.1f} m²)", "Roof wind turbine"],
                                   "kWh/yr": [round(gb["pv"]), round(gb["wind"])]}), hide_index=True, width="stretch")
        st.metric("Generation", f"{E3:,.0f} kWh/yr")
    else:
        st.info("No on-site renewable generation.")
        st.metric("Generation", "0 kWh/yr")

m = st.columns(2)
m[0].metric("Annual balance (generation − operation)", f"{res['surplus_kwh']:,.0f} kWh/yr")
if res["year_reached"]:
    m[1].metric("Realistic net zero reached after", f"{res['years_exact']:.1f} yrs",
                "within design life" if res["within_life"] else "beyond design life",
                delta_color="normal" if res["within_life"] else "inverse")
else:
    m[1].metric("Realistic net zero reached after", "Never",
                "no on-site generation" if not gen_on else "generation does not cover operation", delta_color="inverse")

tabs = ["Your design", "Traditional vs RNZE comparison"]
T = st.tabs(tabs)

# ---------------- Tab 1: design ----------------
with T[0]:
    left, right = st.columns(2)
    years = list(range(0, life + 1))
    fig = go.Figure(go.Scatter(x=years, y=[-E1 + res["surplus_kwh"] * y for y in years], mode="lines"))
    fig.add_hline(y=0, line_dash="dash")
    fig.update_layout(title="Cumulative energy balance", xaxis_title="Year", yaxis_title="kWh", height=380)
    left.plotly_chart(fig, width="stretch")
    d2 = df.copy(); d2["Embodied energy (kWh)"] = d2["Quantity (kg)"] * d2["EE (MJ/kg)"] / MJ_PER_KWH
    top = d2.sort_values("Embodied energy (kWh)", ascending=False).head(8)
    bar = go.Figure(go.Bar(x=top["Embodied energy (kWh)"], y=top["Material"], orientation="h"))
    bar.update_layout(title="Largest embodied-energy contributors", xaxis_title="kWh", height=380,
                      yaxis={"autorange": "reversed"})
    right.plotly_chart(bar, width="stretch")

    st.subheader("Recommendations")
    if uploaded is None and not mat_low:
        recs = []
        for a, b2 in zip(EE[key], EE[key.replace("trad", "low")]):
            if a.get("excluded") or b2.get("excluded"):
                continue
            before, after = a["qty_kg"] * a["ee_factor"], b2["qty_kg"] * b2["ee_factor"]
            if after < before:
                recs.append({"Replace": a["material"], "With": b2["material"],
                             "Saving (kWh)": round((before - after) / MJ_PER_KWH),
                             "Saving (%)": round(100 * (before - after) / before)})
        if recs:
            st.write("Lower-embodied-energy substitutions:")
            st.dataframe(pd.DataFrame(recs).sort_values("Saving (kWh)", ascending=False), hide_index=True, width="stretch")
    if not op_low:
        st.write("Operational energy: switch to a heat pump, LED lighting and A+++ appliances and improve insulation "
                 f"(the RNZE systems use about {make_op(OPS['low']).annual_kwh():,.0f} kWh/yr instead of "
                 f"{make_op(OPS['typ']).annual_kwh():,.0f} kWh/yr).")
    if not gen_on:
        st.warning("Without on-site generation the energy debt grows every year and net zero is never reached.")
    elif res["surplus_kwh"] <= 0:
        need = (E2 - E3) / (g["irr"] * g["eff"])
        st.warning(f"Generation does not cover operation: about {need:,.0f} m² more PV, or lower operational demand, is needed.")
    elif not res["within_life"]:
        extra = E1 / life - res["surplus_kwh"]
        st.info(f"To reach net zero within {life} years, add about {extra:,.0f} kWh/yr of surplus "
                f"(≈ {extra / (g['irr'] * g['eff']):,.0f} m² more PV) or reduce embodied energy.")
    else:
        st.success("This design reaches realistic net zero within its design life.")

# ---------------- Tab 2: comparison ----------------
with T[1]:
    t_op, r_op = make_op(OPS["typ"]).annual_kwh(), make_op(OPS["low"]).annual_kwh()
    r_gen = Generation(pv_area_m2=GEN["pv"], wind_kwh=GEN["wind"]).annual_kwh()
    yrs = list(range(0, 51)); colours = {"Steel": "#d62728", "Reinforced concrete": "#1f77b4", "Timber": "#2ca02c"}
    full, zoom, rows = go.Figure(), go.Figure(), []
    for name, sk in SYSTEMS.items():
        e1_t, e1_r = ee_kwh(table(f"{sk}_trad")), ee_kwh(table(f"{sk}_low"))
        bt = [-e1_t - t_op * y for y in yrs]; br = [-e1_r + (r_gen - r_op) * y for y in yrs]
        full.add_trace(go.Scatter(x=yrs, y=bt, name=f"{name}: traditional", line=dict(color=colours[name], dash="dot")))
        full.add_trace(go.Scatter(x=yrs, y=br, name=f"{name}: RNZE", line=dict(color=colours[name])))
        zoom.add_trace(go.Scatter(x=yrs, y=br, name=f"{name}: RNZE", line=dict(color=colours[name])))
        rows.append({"System": name, "Traditional E1 (kWh)": round(e1_t), "RNZE E1 (kWh)": round(e1_r),
                     "Traditional balance at year 50 (kWh)": round(bt[-1]),
                     "RNZE balance at year 50 (kWh)": round(br[-1]),
                     "RNZE net zero after (yrs)": round(energy_net_zero(e1_r, r_op, r_gen)["years_exact"], 1)})
    for f, t in [(full, "50-year cumulative energy balance: traditional houses never recover"),
                 (zoom, "RNZE houses only: when the energy debt is repaid")]:
        f.add_hline(y=0, line_dash="dash")
        f.update_layout(title=t, xaxis_title="Year", yaxis_title="Cumulative balance (kWh)", height=420)
    st.plotly_chart(full, width="stretch"); st.plotly_chart(zoom, width="stretch")
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
