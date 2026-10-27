"""NZE Intelligence - RNZEB prototype v0 (embodied + operational energy, net-zero year)."""
import json, os
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from rnzeb_engine import Operation, Generation, energy_net_zero, MJ_PER_KWH

HERE = os.path.dirname(os.path.abspath(__file__))
EE = json.load(open(os.path.join(HERE, "ee_tables.json")))
SYSTEMS = {"Steel": "steel", "Reinforced concrete": "rc", "Timber": "timber"}

st.set_page_config(page_title="NZE Intelligence | RNZEB prototype", layout="wide")
st.title("NZE Intelligence: Realistic Net Zero Energy Building (RNZEB) prototype")
st.caption("Balances embodied energy (E1) and operational energy (E2) against on-site renewable "
           "generation (E3): 0 ≥ E1 + E2 − E3. Method: Ercal & Shafique, Sustainable Horizons (2026).")


def table(key):
    rows = [m for m in EE[key] if not m.get("excluded")]
    df = pd.DataFrame(rows)[["material", "qty_kg", "ee_factor"]]
    return df.rename(columns={"material": "Material", "qty_kg": "Quantity (kg)", "ee_factor": "EE (MJ/kg)"})


def ee_kwh(df):
    return float((df["Quantity (kg)"] * df["EE (MJ/kg)"]).sum() / MJ_PER_KWH)


# ---------------- Sidebar inputs ----------------
with st.sidebar:
    st.header("1. Design")
    system = st.selectbox("Structural system", list(SYSTEMS))
    spec = st.radio("Material specification", ["Low embodied energy", "Uninsulated reference"])
    uploaded = st.file_uploader("Or upload a Revit material take-off (CSV: Material, Quantity (kg), EE (MJ/kg))",
                                type="csv")

    ref = not spec.startswith("Low")
    D = dict(heat_kw=26.45, eff=0.92, cool_cop=1.0, light=4793.0, appl=5125.0, pv=0.0, wind=False) if ref else \
        dict(heat_kw=8.98, eff=3.5, cool_cop=3.5, light=702.4, appl=3720.0, pv=39.9, wind=True)
    k = "ref" if ref else "low"   # widget keys per spec so defaults reset when the spec changes

    st.header("2. Operation (annual)")
    heat_kw = st.number_input("Heating load (kW)", 0.0, 100.0, D["heat_kw"], 0.1, key=f"hk{k}")
    heat_h = st.number_input("Heating hours / year", 0, 8760, 1800, 50)
    eff = st.number_input("Heating COP (heat pump) or efficiency (gas boiler)", 0.5, 6.0, D["eff"], 0.01, key=f"ef{k}")
    cool_cop = st.number_input("Cooling COP", 0.5, 6.0, D["cool_cop"], 0.1, key=f"cc{k}")
    cool_th = st.number_input("Cooling demand, thermal (kWh/yr)", 0.0, 50000.0, 4350.0, 50.0)
    light = st.number_input("Lighting (kWh/yr)", 0.0, 20000.0, D["light"], 10.0, key=f"li{k}")
    appl = st.number_input("Appliances (kWh/yr)", 0.0, 20000.0, D["appl"], 10.0, key=f"ap{k}")

    st.header("3. Renewable generation")
    pv_area = st.slider("PV area (m²)", 0.0, 150.0, D["pv"], 0.1, key=f"pv{k}")
    irr = st.number_input("Solar irradiance (kWh/m²/yr)", 500, 1500, 980, 10)
    pv_eff = st.slider("PV efficiency", 0.10, 0.25, 0.215, 0.005)
    use_wind = st.checkbox("Include roof wind turbine", value=D["wind"], key=f"wi{k}")
    wind = st.number_input("Wind yield (kWh/yr)", 0.0, 20000.0, 6025.4, 50.0, disabled=not use_wind,
                           help="Urban micro-wind yields are highly site-dependent; use a conservative estimate.")
    life = st.slider("Design life (years)", 20, 100, 50)

# ---------------- Calculations ----------------
key = f"{SYSTEMS[system]}_{'low' if spec.startswith('Low') else 'trad'}"
if uploaded is not None:
    df = pd.read_csv(uploaded)
    source = "uploaded take-off"
else:
    df = table(key)
    source = f"{system}, {spec.lower()} (Revit take-off, case study house)"

st.subheader(f"Bill of materials: {source}")
df = st.data_editor(df, num_rows="dynamic", width="stretch", key=f"bom_{key}")
df["Embodied energy (kWh)"] = df["Quantity (kg)"] * df["EE (MJ/kg)"] / MJ_PER_KWH

op = Operation(heating_load_kw=heat_kw, heating_hours=heat_h, heating_eff=eff,
               cooling_kwh_thermal=cool_th, cooling_cop=cool_cop, lighting_kwh=light, appliances_kwh=appl)
gen = Generation(pv_area_m2=pv_area, irradiance_kwh_m2=irr, pv_eff=pv_eff, wind_kwh=wind if use_wind else 0)
E1, E2, E3 = ee_kwh(df), op.annual_kwh(), gen.annual_kwh()
res = energy_net_zero(E1, E2, E3, lifespan=life)

c = st.columns(5)
c[0].metric("Embodied energy E1", f"{E1:,.0f} kWh")
c[1].metric("Operation E2", f"{E2:,.0f} kWh/yr")
c[2].metric("Generation E3", f"{E3:,.0f} kWh/yr")
c[3].metric("Annual surplus", f"{res['surplus_kwh']:,.0f} kWh/yr")
if res["year_reached"]:
    c[4].metric("Net zero reached after", f"{res['years_exact']:.1f} yrs",
                "within design life" if res["within_life"] else "beyond design life",
                delta_color="normal" if res["within_life"] else "inverse")
else:
    c[4].metric("Net zero reached after", "Never", "generation ≤ operation", delta_color="inverse")

# ---------------- Charts ----------------
left, right = st.columns(2)
years = list(range(0, life + 1))
balance = [-E1 + max(res["surplus_kwh"], -1e12) * y for y in years]
fig = go.Figure(go.Scatter(x=years, y=balance, mode="lines", name="Cumulative balance"))
fig.add_hline(y=0, line_dash="dash")
fig.update_layout(title="Cumulative energy balance (−E1 + years × surplus)",
                  xaxis_title="Year", yaxis_title="kWh", height=380)
left.plotly_chart(fig, width="stretch")

top = df.sort_values("Embodied energy (kWh)", ascending=False).head(8)
bar = go.Figure(go.Bar(x=top["Embodied energy (kWh)"], y=top["Material"], orientation="h"))
bar.update_layout(title="Largest embodied-energy contributors", xaxis_title="kWh", height=380,
                  yaxis={"autorange": "reversed"})
right.plotly_chart(bar, width="stretch")

# ---------------- Recommendations ----------------
st.subheader("Recommendations")
recs = []
if uploaded is None and key.endswith("trad"):
    trad, low = EE[key], EE[key.replace("trad", "low")]
    for a, b in zip(trad, low):
        if a.get("excluded") or b.get("excluded"):
            continue
        before, after = a["qty_kg"] * a["ee_factor"], b["qty_kg"] * b["ee_factor"]
        if after < before:
            recs.append({"Replace": a["material"], "With": b["material"],
                         "Saving (kWh)": round((before - after) / MJ_PER_KWH),
                         "Saving (%)": round(100 * (before - after) / before)})
if recs:
    st.write("Low-embodied-energy substitutions (functionally equivalent, from case-study library):")
    st.dataframe(pd.DataFrame(recs).sort_values("Saving (kWh)", ascending=False), width="stretch")
if res["surplus_kwh"] <= 0:
    need = (E2 - E3) / (irr * pv_eff) if irr * pv_eff else 0
    st.warning(f"Generation does not cover operation. About {need:,.0f} m² more PV, or lower operational "
               f"demand (insulation, heat pump, LED, A+++ appliances), is needed before net zero is possible.")
elif not res["within_life"]:
    extra = E1 / life - res["surplus_kwh"]
    st.info(f"To reach net zero within {life} years, increase the annual surplus by about {extra:,.0f} kWh/yr "
            f"(≈ {extra / (irr * pv_eff):,.0f} m² of additional PV) or reduce embodied energy.")
else:
    st.success("This design reaches realistic net zero energy within its design life.")

st.caption("Prototype v0. Embodied energy factors from ICE (cradle-to-gate); operational energy uses simplified "
           "annual methods from the case study. Not a compliance tool.")
