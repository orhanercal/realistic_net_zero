"""NZE Intelligence - RNZEB calculator page."""
import json, os
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import ui
from ui import PAL, INK
from rnzeb_engine import Operation, Generation, energy_net_zero, MJ_PER_KWH

HERE = os.path.dirname(os.path.abspath(__file__))
EE = json.load(open(os.path.join(HERE, "ee_tables.json")))
SYSTEMS = {"Steel": "steel", "Reinforced concrete": "rc", "Timber": "timber"}

# Case-study presets (published RNZEB case study, Sustainable Horizons 17, 100163, 2026)
OPS = {
    "low": dict(heat_kw=8.98, hours=1800, eff=3.5, cool_th=4350.0, cool_cop=3.5, light=702.4, appl=3720.0),
    "typ": dict(heat_kw=26.45, hours=1800, eff=0.92, cool_th=4350.0, cool_cop=1.0, light=4793.0, appl=5125.0),
}
DESC = {"low": ["Heat pump (COP 3.5)", "Heat pump cooling (COP 3.5)", "LED lighting", "A+++ appliances"],
        "typ": ["Gas boiler (92% efficient)", "Air conditioner", "Incandescent lighting", "Typical appliances"]}
GEN = dict(pv=39.9, irr=980, eff=0.215, wind=6025.4)
KW_PER_ROTOR, M_PER_ROTOR, RIDGE_M, SOUTH_ROOF_M2 = 0.4, 1.2, 8.8, 47.5   # RidgeBlade RB1: 5 rotors = 2 kW
CF_DEFAULT = round(100 * GEN["wind"] / (6 * KW_PER_ROTOR * 8760), 2)      # = 28.66 % (6 rotors, 6,025.4 kWh/yr)
C_SYS = {"Steel": "#7FA3C6", "Reinforced concrete": "#C2A27C", "Timber": "#7FAF8F"}
C_BAR = "#D8C3A0"

ui.css()


def table(key):
    rows = [m for m in EE[key] if not m.get("excluded")]
    df = pd.DataFrame(rows)[["material", "qty_kg", "ee_factor"]]
    return df.rename(columns={"material": "Material type", "qty_kg": "Quantity (kg)", "ee_factor": "Embodied energy (MJ/kg)"})


def ee_kwh(df):
    return float((df["Quantity (kg)"] * df["Embodied energy (MJ/kg)"]).sum() / MJ_PER_KWH)


def make_op(p):
    return Operation(heating_load_kw=p["heat_kw"], heating_hours=p["hours"], heating_eff=p["eff"],
                     cooling_kwh_thermal=p["cool_th"], cooling_cop=p["cool_cop"],
                     lighting_kwh=p["light"], appliances_kwh=p["appl"])


def fmt(x, sign=False):
    s = f"{abs(x):,.0f}"
    return ("+" if x > 0 else "−" if x < 0 else "") + s if sign else f"{x:,.0f}"


def box(title, sub=None):
    st.markdown(f'<div class="boxtitle">{title}</div>' + (f'<div class="boxsub">{sub}</div>' if sub else ""),
                unsafe_allow_html=True)


def style_fig(fig, h=430, ytitle="kWh"):
    fig.update_layout(height=h, margin=dict(l=10, r=10, t=42, b=10), plot_bgcolor="white", paper_bgcolor="white",
                      font=dict(color=INK), legend=dict(orientation="h", y=-0.18), yaxis_title=ytitle)
    fig.update_xaxes(gridcolor="#EEF2F1"); fig.update_yaxes(gridcolor="#EEF2F1", zerolinecolor="#C9D8D7")
    return fig


def balance_trace(fig, e1, e2, e3, life, name, color, dash=None, mark=True, label=True):
    yrs = list(range(0, life + 1))
    fig.add_trace(go.Scatter(x=yrs, y=[-e1 + (e3 - e2) * y for y in yrs], mode="lines", name=name,
                             line=dict(color=color, width=3, dash=dash)))
    if mark:
        fig.add_trace(go.Scatter(x=[0], y=[-e1], mode="markers+text", marker=dict(size=9, color=color),
                                 text=[f"Embodied energy debt: −{e1:,.0f} kWh" if label else ""], textposition="bottom right",
                                 textfont=dict(size=12, color=color), showlegend=False, hoverinfo="skip"))
        r = energy_net_zero(e1, e2, e3, lifespan=life)
        if r["year_reached"] and r["years_exact"] <= life:
            fig.add_trace(go.Scatter(x=[r["years_exact"]], y=[0], mode="markers+text", marker=dict(size=10, color=color),
                                     text=[f"Net zero: {r['years_exact']:.1f} yrs"], textposition="bottom left",
                                     textfont=dict(size=12, color=color), showlegend=False, hoverinfo="skip"))


# ---------------- Sidebar ----------------
with st.sidebar:
    system, btype, life = ui.sidebar_building(SYSTEMS, "c_")
    rnze = btype == "RNZE building"
    tone = "rnze" if rnze else "trad"
    p = dict(OPS["low" if rnze else "typ"]); g = dict(GEN)
    k = tone

    st.header("Adjust inputs")
    with st.container(key=f"e1_{tone}"):
        st.markdown("**E1 Materials**")
        uploaded = st.file_uploader("Upload a BIM material take-off (Revit, Archicad or other BIM tools) as CSV: "
                                    "Material type, Quantity (kg), Embodied energy (MJ/kg)", type="csv")
    with st.container(key=f"e2_{tone}"):
        st.markdown("**E2 Operation**")
        p["heat_kw"] = st.number_input("Heating load (kW)", 0.0, 100.0, p["heat_kw"], 0.1, key="hk" + k)
        p["hours"] = st.number_input("Heating hours / year", 0, 8760, p["hours"], 50, key="hh" + k)
        if rnze:
            p["eff"] = st.number_input("Heat pump COP (Coefficient of Performance)", 0.5, 6.0, p["eff"], 0.01, key="ef" + k)
            p["cool_th"] = st.number_input("Cooling demand, thermal (kWh/yr), heat pump cooling", 0.0, 50000.0,
                                           p["cool_th"], 50.0, key="ct" + k)
            p["cool_cop"] = st.number_input("Heat pump cooling COP (Coefficient of Performance)", 0.5, 6.0,
                                            p["cool_cop"], 0.1, key="cc" + k)
            p["light"] = st.number_input("Lighting, LED (kWh/yr)", 0.0, 20000.0, p["light"], 10.0, key="li" + k)
            p["appl"] = st.number_input("Appliances, A+++ (kWh/yr)", 0.0, 20000.0, p["appl"], 10.0, key="ap" + k)
        else:
            p["eff"] = st.number_input("Gas boiler efficiency (0.92 = 92%)", 0.5, 1.0, p["eff"], 0.01, key="ef" + k)
            p["cool_th"] = st.number_input("Cooling demand, thermal (kWh/yr), air conditioning", 0.0, 50000.0,
                                           p["cool_th"], 50.0, key="ct" + k)
            st.caption("Air conditioning: electricity use as in the published case study.")
            p["light"] = st.number_input("Lighting, incandescent (kWh/yr)", 0.0, 20000.0, p["light"], 10.0, key="li" + k)
            p["appl"] = st.number_input("Appliances, typical (kWh/yr)", 0.0, 20000.0, p["appl"], 10.0, key="ap" + k)
    with st.container(key=f"e3_{tone}"):
        st.markdown("**E3 Renewable generation**")
        gen_on = rnze
        if not rnze:
            st.caption("Not used in a traditional building.")
            gen_on = st.toggle("What if: add renewables to the traditional building", value=False, key="wi")
        g["pv"] = st.slider("PV area (m²)", 0.0, 400.0, g["pv"], 0.1, key="pv" + k, disabled=not gen_on)
        g["irr"] = st.number_input("Solar irradiance (kWh/m²/yr)", 500, 1500, g["irr"], 10, key="ir" + k, disabled=not gen_on)
        g["eff"] = st.slider("PV efficiency", 0.10, 0.25, g["eff"], 0.005, key="pe" + k, disabled=not gen_on)
        use_wind = st.checkbox("Include roof wind turbine", value=True, key="uw" + k, disabled=not gen_on,
                               help="Ridge-mounted RidgeBlade RB1: 0.4 kW continuous per rotor (5 rotors = 2 kW), "
                                    "1.2 m of ridge per rotor. Wind yield assumed independent of orientation.")
        wind_on = gen_on and use_wind
        rotors = st.number_input("Number of rotors", 1, 10, 6, 1, key="ro" + k, disabled=not wind_on)
        cf = st.slider("Capacity factor (%)", 15.0, 40.0, CF_DEFAULT, 0.01, key="cf" + k, disabled=not wind_on,
                       help="Share of the year the turbine runs at its rated power; typically 15–40%.")
        g["wind"] = rotors * KW_PER_ROTOR * 8760 * cf / 100
        st.caption(f"Wind yield: {g['wind']:,.0f} kWh/yr · ridge length used {rotors * M_PER_ROTOR:.1f} m · "
                   f"roof area ≈ {rotors * M_PER_ROTOR:.1f} m²")

# ---------------- Header and scenario ----------------
ui.header("Realistic Net Zero Energy Building (RNZEB)",
          "Balances embodied energy (E1) and operational energy (E2) against on-site renewable generation (E3): "
          "**0 ≥ E1 + E2 − E3**. Validated against the published case study. "
          "Method: Realistic Net Zero Energy Building (RNZEB), developed by Orhan Ercal (Master's dissertation, "
          "Brunel University London, 2024; Dean's Prize for Innovation and Impact). Peer-reviewed publication: "
          "Sustainable Horizons, 17, 100163 (2026). A concept-stage decision tool, not a compliance tool.")
ui.band(btype, system, tone)
ui.gap()
sk_sys = SYSTEMS[system]
elev_label = "South elevation" if sk_sys == "steel" else "East elevation"
ui.extra_css()
house_img = f"{sk_sys}_rnze_front.png" if rnze else f"{sk_sys}_render.png"
elev_img = f"{sk_sys}_rnze_elev_front.png" if rnze else f"{sk_sys}_elev_front.png"
ui.strip([(os.path.join(HERE, house_img), "House (3D)"),
          (os.path.join(HERE, f"{sk_sys}_structure.png"), "Structure (3D)"),
          (os.path.join(HERE, f"{sk_sys}_section.png"), "Section"),
          (os.path.join(HERE, f"{sk_sys}_elev_structure.png"), "Structure elevation"),
          (os.path.join(HERE, elev_img), elev_label)])
ui.gap(); ui.gap()

# ---------------- Bill of materials ----------------
key = f"{sk_sys}_{'low' if rnze else 'trad'}"
sk, vk = f"bom_{key}", f"bomv_{key}"
if uploaded is not None:
    st.session_state[sk] = pd.read_csv(uploaded); st.session_state[vk] = st.session_state.get(vk, 0) + 1
if sk not in st.session_state:
    st.session_state[sk] = table(key); st.session_state[vk] = 0
base = st.session_state[sk].copy()
base["Total (MJ)"] = (base["Quantity (kg)"] * base["Embodied energy (MJ/kg)"]).map(lambda v: f"{v:,.1f}")
st.markdown('<div class="sec">Bill of materials</div>', unsafe_allow_html=True)
st.caption("Edit any quantity or factor, or add a material below. All results update instantly.")
edited = st.data_editor(base, num_rows="dynamic", width="stretch", hide_index=True, row_height=30,
                        height=int((len(base) + 2) * 30 + 48), key=f"ed_{key}_{st.session_state[vk]}",
                        disabled=["Total (MJ)"],
                        column_config={"Quantity (kg)": st.column_config.NumberColumn(format="%.2f"),
                                       "Embodied energy (MJ/kg)": st.column_config.NumberColumn(format="%.2f"),
                                       "Total (MJ)": st.column_config.TextColumn()})
clean = edited.drop(columns=["Total (MJ)"]).dropna(subset=["Quantity (kg)", "Embodied energy (MJ/kg)"])
if not clean.reset_index(drop=True).equals(st.session_state[sk].reset_index(drop=True)):
    st.session_state[sk] = clean.reset_index(drop=True); st.session_state[vk] += 1; st.rerun()
df = st.session_state[sk]
E1 = ee_kwh(df)
f1, f2 = st.columns([1, 3], vertical_alignment="center")
if f1.button("+ Add material", width="stretch"):
    st.session_state[sk] = pd.concat([st.session_state[sk], pd.DataFrame([{"Material type": "New material",
        "Quantity (kg)": 0.0, "Embodied energy (MJ/kg)": 0.0}])], ignore_index=True)
    st.session_state[vk] += 1; st.rerun()
f2.markdown(f'<div class="bomfoot">Total embodied energy: {E1 * MJ_PER_KWH:,.0f} MJ = {E1:,.0f} kWh</div>',
            unsafe_allow_html=True)
ui.gap()

# ---------------- Calculations ----------------
op = make_op(p)
gen = Generation(pv_area_m2=g["pv"], irradiance_kwh_m2=g["irr"], pv_eff=g["eff"],
                 wind_kwh=g["wind"] if use_wind else 0) if gen_on else Generation(pv_area_m2=0, wind_kwh=0)
E2, E3 = op.annual_kwh(), gen.annual_kwh()
res = energy_net_zero(E1, E2, E3, lifespan=life)

# ---------------- E1 / E2 / E3 cards ----------------
pt = PAL[tone]
b = op.breakdown(); ds = DESC["low" if rnze else "typ"]
e2rows = "".join(f'<tr><td>{u}</td><td>{d}</td><td class="n">{b[x]:,.0f}</td></tr>'
                 for u, d, x in zip(["Heating", "Cooling", "Lighting", "Appliances"], ds,
                                    ["heating", "cooling", "lighting", "appliances"]))
if gen_on:
    gb = gen.breakdown()
    e3body = (f'<table><tr><th>Source</th><th class="n">kWh/yr</th></tr>'
              f'<tr><td>Solar PV ({g["pv"]:.1f} m²)</td><td class="n">{gb["pv"]:,.0f}</td></tr>'
              f'<tr><td>Roof wind turbine ({rotors if use_wind else 0} rotors)</td><td class="n">{gb["wind"]:,.0f}</td></tr></table>')
    if g["pv"] > SOUTH_ROOF_M2:
        e3body += f'<div class="note">{g["pv"]:.0f} m² of PV exceeds the ~{SOUTH_ROOF_M2} m² south-facing roof.</div>'
    if use_wind and rotors > 7:
        e3body += (f'<div class="note">{rotors} rotors need about {rotors * M_PER_ROTOR:.1f} m of ridge; '
                   f'the case-study house has about {RIDGE_M} m.</div>')
else:
    e3body = '<div class="sub">No on-site renewable generation.</div>'
if not rnze:
    need = E2 + E1 / life
    pv_need = need / (g["irr"] * g["eff"])
    e3body += (f'<div class="sub" style="margin-top:8px">To reach net zero within {life} years this house would need about '
               f'<b>{pv_need:,.0f} m² of PV</b> ({pv_need / GEN["pv"]:.1f}× the RNZE design, more than the house\'s '
               f'270 m² floor area) or about <b>{need / GEN["wind"]:,.0f} roof wind turbines</b>. Reducing E1 and E2 first '
               f'is the only realistic route.</div>')
c = lambda e: f'background:{pt[e][0]};border:1px solid {pt[e][1]}'
st.markdown(f"""<div class="card-row">
<div class="card" style="flex:2.4;{c('e1')}"><div class="ttl">E1 Materials</div>
<div class="sub">{'Low embodied energy materials' if rnze else 'Typical materials'}</div>
<div class="total"><div class="lab">Embodied energy</div><div class="val">{E1:,.0f} kWh</div></div></div>
<div class="card" style="flex:4;{c('e2')}"><div class="ttl">E2 Operation</div>
<table><tr><th>Use</th><th>System</th><th class="n">kWh/yr</th></tr>{e2rows}</table>
<div class="total"><div class="lab">Operational energy</div><div class="val">{E2:,.0f} kWh/yr</div></div></div>
<div class="card" style="flex:3;{c('e3')}"><div class="ttl">E3 Renewable generation</div>{e3body}
<div class="total"><div class="lab">Generation</div><div class="val">{E3:,.0f} kWh/yr</div></div></div>
</div>""", unsafe_allow_html=True)
ui.gap()

# ---------------- Result boxes ----------------
r1, r2, r3 = round(E1), round(E2), round(E3)
bal_r = r3 - r2
if res["year_reached"]:
    ok = res["within_life"]
    nz, pill = f"{res['years_exact']:.1f} yrs", ("within design life" if ok else "beyond design life")
    fx_nz = f"E1 ÷ (E3 − E2) = {r1:,} ÷ {bal_r:,}"
else:
    ok, nz = False, "Never"
    pill = "no on-site generation" if not gen_on else "generation does not cover operation"
    fx_nz = "E3 − E2 is negative, so the embodied energy debt is never repaid."
st.markdown(f"""<div class="res-row">
<div class="res"><div class="lab">Annual balance (generation − operation)</div><div class="val">{fmt(bal_r, True)} kWh/yr</div>
<div class="fx">E3 − E2 = {r3:,} − {r2:,}</div></div>
<div class="res"><div class="lab">Realistic net zero reached after</div><div class="val">{nz}</div>
<span class="pill {'ok' if ok else 'bad'}">{pill}</span><div class="fx">{fx_nz}</div></div></div>""", unsafe_allow_html=True)
ui.gap()

T = st.tabs([f"{btype} results", "Traditional vs RNZE comparison"])

# ---------------- Tab 1 ----------------
with T[0]:
    with st.container(border=True):
        box("Cumulative energy balance", "Energy debt from materials, repaid by the annual renewable surplus.")
        fig = go.Figure(); fig.add_hline(y=0, line_dash="dash", line_color="#9AA9A7")
        balance_trace(fig, E1, E2, E3, life, btype, C_SYS[system], dash=None if rnze else "dot")
        fig.update_xaxes(title="Year"); st.plotly_chart(style_fig(fig), width="stretch")
    ui.gap()
    with st.container(border=True):
        box("Largest embodied-energy contributors", "Materials with the highest embodied energy in this design.")
        d2 = df.copy(); d2["kWh"] = d2["Quantity (kg)"] * d2["Embodied energy (MJ/kg)"] / MJ_PER_KWH
        top = d2.sort_values("kWh", ascending=False).head(8)
        bar = go.Figure(go.Bar(x=top["kWh"], y=top["Material type"], orientation="h", marker_color=C_BAR))
        bar.update_yaxes(autorange="reversed"); bar.update_xaxes(title="kWh")
        st.plotly_chart(style_fig(bar, ytitle=""), width="stretch")
    ui.gap()
    with st.container(border=True):
        box("Recommendations")
        if uploaded is None and not rnze:
            recs = []
            for x, y in zip(EE[key], EE[key.replace("trad", "low")]):
                if x.get("excluded") or y.get("excluded"):
                    continue
                bf, af = x["qty_kg"] * x["ee_factor"], y["qty_kg"] * y["ee_factor"]
                if af < bf:
                    recs.append({"Replace": x["material"], "With": y["material"],
                                 "Saving (kWh)": round((bf - af) / MJ_PER_KWH), "Saving (%)": round(100 * (bf - af) / bf)})
            if recs:
                st.write("Lower-embodied-energy substitutions:")
                st.dataframe(pd.DataFrame(recs).sort_values("Saving (kWh)", ascending=False), hide_index=True, width="stretch")
            st.write("Operational energy: switch to a heat pump, LED lighting and A+++ appliances and improve insulation "
                     f"(RNZE systems use about {make_op(OPS['low']).annual_kwh():,.0f} kWh/yr instead of "
                     f"{make_op(OPS['typ']).annual_kwh():,.0f} kWh/yr).")
        if not gen_on:
            st.warning("Without on-site generation the energy debt grows every year and net zero is never reached.")
        elif res["surplus_kwh"] <= 0:
            st.warning(f"Generation does not cover operation: about {(E2 - E3) / (g['irr'] * g['eff']):,.0f} m² more PV, "
                       "or lower operational demand, is needed.")
        elif not res["within_life"]:
            extra = E1 / life - res["surplus_kwh"]
            st.info(f"To reach net zero within {life} years, add about {extra:,.0f} kWh/yr of surplus "
                    f"(≈ {extra / (g['irr'] * g['eff']):,.0f} m² more PV) or reduce embodied energy.")
        else:
            st.success("This design reaches realistic net zero within its design life.")

# ---------------- Tab 2 ----------------
with T[1]:
    t_op, r_op = make_op(OPS["typ"]).annual_kwh(), make_op(OPS["low"]).annual_kwh()
    r_gen = Generation(pv_area_m2=GEN["pv"], wind_kwh=GEN["wind"]).annual_kwh()
    vals = {n: (ee_kwh(table(f"{s}_trad")), ee_kwh(table(f"{s}_low"))) for n, s in SYSTEMS.items()}
    et, er = vals[system]

    st.markdown(f'<div class="sec">Selected structure: {system}</div>', unsafe_allow_html=True)
    with st.container(border=True):
        box(f"{system}: traditional vs RNZE", "Traditional houses keep adding energy debt; the RNZE house repays it.")
        f1g = go.Figure(); f1g.add_hline(y=0, line_dash="dash", line_color="#9AA9A7")
        balance_trace(f1g, et, t_op, 0, 50, "Traditional", C_SYS[system], dash="dot", label=False)
        balance_trace(f1g, er, r_op, r_gen, 50, "RNZE", C_SYS[system], label=False)
        f1g.update_xaxes(title="Year"); st.plotly_chart(style_fig(f1g), width="stretch")
    ui.gap()
    with st.container(border=True):
        box(f"{system} RNZE: when the energy debt is repaid", "Embodied energy debt at year 0, repaid by the annual renewable surplus.")
        f2g = go.Figure(); f2g.add_hline(y=0, line_dash="dash", line_color="#9AA9A7")
        balance_trace(f2g, er, r_op, r_gen, 50, "RNZE", C_SYS[system])
        f2g.update_xaxes(title="Year"); st.plotly_chart(style_fig(f2g), width="stretch")

    ui.gap(); st.divider()
    st.markdown('<div class="sec">All structural systems</div>', unsafe_allow_html=True)
    with st.container(border=True):
        box("Traditional vs RNZE: all structures", "Dotted: traditional. Solid: RNZE.")
        f3 = go.Figure(); f3.add_hline(y=0, line_dash="dash", line_color="#9AA9A7")
        for n, (t1, r1) in vals.items():
            balance_trace(f3, t1, t_op, 0, 50, f"{n}: traditional", C_SYS[n], dash="dot", mark=False)
            balance_trace(f3, r1, r_op, r_gen, 50, f"{n}: RNZE", C_SYS[n], mark=False)
        f3.update_xaxes(title="Year"); st.plotly_chart(style_fig(f3, h=460), width="stretch")
    ui.gap()
    with st.container(border=True):
        box("RNZE houses: when the energy debt is repaid", "Same operation and generation; the difference comes from embodied energy alone.")
        f4 = go.Figure(); f4.add_hline(y=0, line_dash="dash", line_color="#9AA9A7")
        for n, (t1, r1) in vals.items():
            balance_trace(f4, r1, r_op, r_gen, 50, f"{n}: RNZE", C_SYS[n], mark=False)
            rr = energy_net_zero(r1, r_op, r_gen)
            f4.add_trace(go.Scatter(x=[0, rr["years_exact"]], y=[-r1, 0], mode="markers", showlegend=False,
                                    marker=dict(size=9, color=C_SYS[n]), hoverinfo="skip"))
        f4.update_xaxes(title="Year"); st.plotly_chart(style_fig(f4, h=460), width="stretch")
    ui.gap()
    with st.container(border=True):
        box("Summary: 50-year energy balance", "Energy used is shown as negative, energy generated as positive.")
        rows = ""
        for n, (t1, r1) in vals.items():
            for lab, e1, e2, e3, last in [("Traditional", t1, t_op, 0, False), ("RNZE", r1, r_op, r_gen, True)]:
                bal = -e1 + (e3 - e2) * 50
                pal = PAL["trad" if lab == "Traditional" else "rnze"]["e2"][0]
                rows += (f'<tr class="{"pairend" if last else ""}" style="background:{pal}"><td>{lab} {n.lower()}</td>'
                         f'<td>{fmt(-e1, True)}</td><td>{fmt(-e2, True)}</td><td>{fmt(e3, True) if e3 else "0"}</td>'
                         f"<td class=\"{'pos' if bal > 0 else 'neg'}\">{fmt(bal, True)}</td></tr>")
        st.markdown(f"""<table class="sum"><tr><th>Building</th><th>E1 Embodied<br>(kWh)</th><th>E2 Operation<br>(kWh/yr)</th>
<th>E3 Renewable<br>(kWh/yr)</th><th>Energy at<br>year 50 (kWh)</th></tr>{rows}</table>""", unsafe_allow_html=True)
