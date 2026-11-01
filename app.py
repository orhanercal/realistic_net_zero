"""NZE Intelligence - RNZEB prototype (embodied + operational energy, realistic net zero)."""
import json, os
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import passive
from rnzeb_engine import Operation, Generation, energy_net_zero, MJ_PER_KWH

HERE = os.path.dirname(os.path.abspath(__file__))
EE = json.load(open(os.path.join(HERE, "ee_tables.json")))
SYSTEMS = {"Steel": "steel", "Reinforced concrete": "rc", "Timber": "timber"}

# Case-study presets (Ercal & Shafique, Sustainable Horizons 2026)
OPS = {
    "low": dict(heat_kw=8.98, hours=1800, eff=3.5, cool_th=4350.0, cool_cop=3.5, light=702.4, appl=3720.0),
    "typ": dict(heat_kw=26.45, hours=1800, eff=0.92, cool_th=4350.0, cool_cop=1.0, light=4793.0, appl=5125.0),
}
DESC = {"low": ["Heat pump (COP 3.5)", "Heat pump cooling (COP 3.5)", "LED lighting", "A+++ appliances"],
        "typ": ["Gas boiler (92% efficient)", "Air conditioner", "Incandescent lighting", "Typical appliances"]}
GEN = dict(pv=39.9, irr=980, eff=0.215, wind=6025.4)

# Pastel palette: RNZE = light tones, Traditional = one tone darker
PAL = {"rnze": {"e1": ("#F8F2E7", "#E4D7BE"), "e2": ("#EBF2FA", "#CADBEC"), "e3": ("#EBF5EE", "#C7E0CF")},
       "trad": {"e1": ("#EFE4CF", "#D6C29D"), "e2": ("#DCE7F3", "#B4CAE2"), "e3": ("#DCEBE1", "#AFCFBA")}}
INK, MUTED = "#14302E", "#5B6E6C"
C_TRAD, C_RNZE = "#A8875A", "#2F6B5A"                      # dark sand / dark green
C_SYS = {"Steel": "#7FA3C6", "Reinforced concrete": "#C2A27C", "Timber": "#7FAF8F"}
C_BAR = "#D8C3A0"

st.set_page_config(page_title="NZE Intelligence | RNZEB prototype", layout="wide")


def css():
    rules = []
    for tone, boxes in PAL.items():
        for e, (bg, bd) in boxes.items():
            rules.append(f".st-key-{e}_{tone}{{background:{bg};border:1px solid {bd};border-radius:12px;padding:12px 12px 6px}}")
    st.markdown("<style>" + "\n".join(rules) + """
    .card-row{display:flex;gap:14px;align-items:stretch;margin:6px 0 18px}
    .card{border-radius:12px;padding:14px 16px;display:flex;flex-direction:column;color:%s}
    .card h4{margin:0 0 6px;font-size:1.02rem}
    .card .sub{color:%s;font-size:.9rem;margin-bottom:8px}
    .card table{width:100%%;border-collapse:collapse;font-size:.88rem}
    .card td,.card th{padding:3px 4px;border-bottom:1px solid rgba(0,0,0,.08);text-align:left}
    .card td.n,.card th.n{text-align:right;white-space:nowrap}
    .card .total{margin-top:auto;padding-top:12px}
    .card .total .lab{font-size:.85rem;color:%s}
    .card .total .val{font-size:1.45rem;font-weight:600;line-height:1.2;white-space:nowrap}
    .res-row{display:flex;gap:16px;justify-content:center;align-items:stretch;margin:4px 0 22px}
    .res{background:#FAFAF7;border:1px solid #DADFDE;border-radius:12px;padding:14px 28px;text-align:center;min-width:280px}
    .res .lab{font-size:.88rem;color:%s} .res .val{font-size:1.9rem;font-weight:600;color:%s}
    .pill{display:inline-block;border-radius:999px;padding:2px 10px;font-size:.8rem;margin-top:4px}
    .pill.ok{background:#E3F2E7;color:#24613F} .pill.bad{background:#F8E3E1;color:#8A2E25}
    .brand{font-weight:700;letter-spacing:.04em;color:%s;font-size:.9rem;margin-bottom:2px}
    .apptitle{font-size:1.9rem;font-weight:700;color:%s;margin:0 0 4px;line-height:1.2}
    .band{border-radius:12px;padding:14px 18px;margin:6px 0 14px;display:flex;align-items:center;gap:14px;color:%s}
    .chip{border:1px solid rgba(0,0,0,.2);border-radius:999px;padding:3px 12px;font-size:.9rem;background:rgba(255,255,255,.55)}
    .struct{font-size:1.5rem;font-weight:800;letter-spacing:.06em}
    .sec{font-size:1.25rem;font-weight:700;color:%s;margin:8px 0 2px}
    .boxtitle{font-weight:700;font-size:1.02rem;color:%s;margin-bottom:0}
    .boxsub{color:%s;font-size:.88rem;margin-bottom:4px}
    table.sum{width:100%%;border-collapse:collapse;font-size:.92rem;color:%s}
    table.sum th{text-align:right;padding:6px 8px;border-bottom:2px solid #C9D8D7;vertical-align:bottom}
    table.sum th:first-child,table.sum td:first-child{text-align:left}
    table.sum td{text-align:right;padding:6px 8px;white-space:nowrap}
    table.sum tr.pairend td{border-bottom:2px solid #C9D8D7}
    .pos{color:#3F8A5F;font-weight:600} .neg{color:#B5544A;font-weight:600}
    .bomfoot{border:1px solid #E6EAEA;border-top:none;border-radius:0 0 10px 10px;margin-top:-16px;padding:8px 14px;text-align:right;font-weight:600;background:#FAFBFB}
    </style>""" % (INK, MUTED, MUTED, MUTED, INK, MUTED, INK, INK, INK, INK, MUTED, INK), unsafe_allow_html=True)


css()


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


def style_fig(fig, h=360, ytitle="kWh"):
    fig.update_layout(height=h, margin=dict(l=10, r=10, t=42, b=10), plot_bgcolor="white", paper_bgcolor="white",
                      font=dict(color=INK), legend=dict(orientation="h", y=-0.22), yaxis_title=ytitle)
    fig.update_xaxes(gridcolor="#EEF2F1"); fig.update_yaxes(gridcolor="#EEF2F1", zerolinecolor="#C9D8D7")
    return fig


def balance_trace(fig, e1, e2, e3, life, name, color, dash=None, mark=True, label=True):
    yrs = list(range(0, life + 1))
    fig.add_trace(go.Scatter(x=yrs, y=[-e1 + (e3 - e2) * y for y in yrs], mode="lines", name=name,
                             line=dict(color=color, width=3, dash=dash)))
    if mark:
        fig.add_trace(go.Scatter(x=[0], y=[-e1], mode="markers+text", marker=dict(size=9, color=color),
                                 text=[f"Embodied energy debt: −{e1:,.0f} kWh" if label else ""], textposition="bottom right",
                                 textfont=dict(size=11, color=color), showlegend=False, hoverinfo="skip"))
        r = energy_net_zero(e1, e2, e3, lifespan=life)
        if r["year_reached"] and r["years_exact"] <= life:
            fig.add_trace(go.Scatter(x=[r["years_exact"]], y=[0], mode="markers+text", marker=dict(size=10, color=color),
                                     text=[f"Net zero: {r['years_exact']:.1f} yrs"], textposition="bottom left",
                                     textfont=dict(size=11, color=color), showlegend=False, hoverinfo="skip"))


# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("Building")
    system = st.selectbox("Structural system", list(SYSTEMS))
    btype = st.radio("Building type", ["Traditional building", "RNZE building"], index=1,
                     help="RNZE: low embodied energy materials, low operational energy and renewable generation. "
                          "Traditional: typical materials and systems, no on-site generation.")
    life = st.slider("Design life (years)", 20, 100, 50)
    rnze = btype == "RNZE building"
    tone = "rnze" if rnze else "trad"
    p = dict(OPS["low" if rnze else "typ"]); g = dict(GEN)
    k = tone

    st.header("Adjust inputs")
    with st.container(key=f"e1_{tone}"):
        st.markdown("**E1 Materials**")
        uploaded = st.file_uploader("Upload a Revit material take-off (CSV: Material type, Quantity (kg), "
                                    "Embodied energy (MJ/kg))", type="csv")
    with st.container(key=f"e2_{tone}"):
        st.markdown("**E2 Operation**")
        p["heat_kw"] = st.number_input("Heating load (kW)", 0.0, 100.0, p["heat_kw"], 0.1, key="hk" + k)
        p["hours"] = st.number_input("Heating hours / year", 0, 8760, p["hours"], 50, key="hh" + k)
        p["eff"] = st.number_input("Heating COP (heat pump) or efficiency (boiler)", 0.5, 6.0, p["eff"], 0.01, key="ef" + k)
        p["cool_th"] = st.number_input("Cooling demand, thermal (kWh/yr)", 0.0, 50000.0, p["cool_th"], 50.0, key="ct" + k)
        p["cool_cop"] = st.number_input("Cooling COP", 0.5, 6.0, p["cool_cop"], 0.1, key="cc" + k)
        p["light"] = st.number_input("Lighting (kWh/yr)", 0.0, 20000.0, p["light"], 10.0, key="li" + k)
        p["appl"] = st.number_input("Appliances (kWh/yr)", 0.0, 20000.0, p["appl"], 10.0, key="ap" + k)
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
                               help="Wind is optional; PV-only designs can also reach net zero.")
        g["wind"] = st.number_input("Wind yield (kWh/yr)", 0.0, 100000.0, g["wind"], 50.0,
                                    disabled=not (gen_on and use_wind), key="wy" + k)

# ---------------- Header ----------------
st.markdown('<div class="brand">NZE INTELLIGENCE</div><div class="apptitle">Realistic Net Zero Energy Building (RNZEB)</div>',
            unsafe_allow_html=True)
st.caption("Balances embodied energy (E1) and operational energy (E2) against on-site renewable generation (E3): "
           "**0 ≥ E1 + E2 − E3**. Method: Ercal & Shafique, Sustainable Horizons (2026). "
           "Prototype: a concept-stage decision tool, not a compliance tool.")
st.divider()
pt = PAL[tone]
st.markdown(f'<div class="band" style="background:linear-gradient(90deg,{pt["e1"][0]},{pt["e2"][0]},{pt["e3"][0]});'
            f'border:1px solid {pt["e2"][1]}"><span class="chip">{btype}</span>'
            f'<span class="struct">{system.upper()} STRUCTURE</span></div>', unsafe_allow_html=True)

# ---------------- Bill of materials (editable, always open) ----------------
key = f"{SYSTEMS[system]}_{tone if rnze else 'trad'}".replace("_rnze", "_low")
sk, vk = f"bom_{key}", f"bomv_{key}"
if uploaded is not None:
    st.session_state[sk] = pd.read_csv(uploaded); st.session_state[vk] = st.session_state.get(vk, 0) + 1
if sk not in st.session_state:
    st.session_state[sk] = table(key); st.session_state[vk] = 0
base = st.session_state[sk].copy()
base["Total (MJ)"] = (base["Quantity (kg)"] * base["Embodied energy (MJ/kg)"]).round(1)
h1, h2 = st.columns([5, 1], vertical_alignment="bottom")
h1.markdown('<div class="sec">Bill of materials</div>', unsafe_allow_html=True)
if h2.button("+ Add material", width="stretch"):
    st.session_state[sk] = pd.concat([st.session_state[sk], pd.DataFrame([{"Material type": "New material",
        "Quantity (kg)": 0.0, "Embodied energy (MJ/kg)": 0.0}])], ignore_index=True)
    st.session_state[vk] += 1; st.rerun()
st.caption("Edit any quantity or factor, or add a material with + Add material (or the empty row at the bottom). "
           "All results update instantly.")
edited = st.data_editor(base, num_rows="dynamic", width="stretch", hide_index=True, row_height=28,
                        height=int((len(base) + 2) * 28 + 6), key=f"ed_{key}_{st.session_state[vk]}",
                        disabled=["Total (MJ)"],
                        column_config={"Quantity (kg)": st.column_config.NumberColumn(format="%.2f"),
                                       "Embodied energy (MJ/kg)": st.column_config.NumberColumn(format="%.2f"),
                                       "Total (MJ)": st.column_config.NumberColumn(format="%.1f")})
clean = edited.drop(columns=["Total (MJ)"]).dropna(subset=["Quantity (kg)", "Embodied energy (MJ/kg)"])
if not clean.reset_index(drop=True).equals(st.session_state[sk].reset_index(drop=True)):
    st.session_state[sk] = clean.reset_index(drop=True); st.session_state[vk] += 1; st.rerun()
df = st.session_state[sk]
E1 = ee_kwh(df)
st.markdown(f'<div class="bomfoot">Total embodied energy: {E1 * MJ_PER_KWH:,.0f} MJ = {E1:,.0f} kWh</div>',
            unsafe_allow_html=True)

# ---------------- Calculations ----------------
op = make_op(p)
gen = Generation(pv_area_m2=g["pv"], irradiance_kwh_m2=g["irr"], pv_eff=g["eff"],
                 wind_kwh=g["wind"] if use_wind else 0) if gen_on else Generation(pv_area_m2=0, wind_kwh=0)
E2, E3 = op.annual_kwh(), gen.annual_kwh()
res = energy_net_zero(E1, E2, E3, lifespan=life)

# ---------------- E1 / E2 / E3 cards ----------------
b = op.breakdown(); ds = DESC["low" if rnze else "typ"]
e2rows = "".join(f'<tr><td>{u}</td><td>{d}</td><td class="n">{b[x]:,.0f}</td></tr>'
                 for u, d, x in zip(["Heating", "Cooling", "Lighting", "Appliances"], ds,
                                    ["heating", "cooling", "lighting", "appliances"]))
if gen_on:
    gb = gen.breakdown()
    e3body = (f'<table><tr><th>Source</th><th class="n">kWh/yr</th></tr>'
              f'<tr><td>Solar PV ({g["pv"]:.1f} m²)</td><td class="n">{gb["pv"]:,.0f}</td></tr>'
              f'<tr><td>Roof wind turbine</td><td class="n">{gb["wind"]:,.0f}</td></tr></table>')
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
<div class="card" style="flex:2.4;{c('e1')}"><h4>E1 Materials</h4>
<div class="sub">{'Low embodied energy materials' if rnze else 'Typical materials'}</div>
<div class="total"><div class="lab">Embodied energy</div><div class="val">{E1:,.0f} kWh</div></div></div>
<div class="card" style="flex:4;{c('e2')}"><h4>E2 Operation</h4>
<table><tr><th>Use</th><th>System</th><th class="n">kWh/yr</th></tr>{e2rows}</table>
<div class="total"><div class="lab">Operational energy</div><div class="val">{E2:,.0f} kWh/yr</div></div></div>
<div class="card" style="flex:3;{c('e3')}"><h4>E3 Renewable generation</h4>{e3body}
<div class="total"><div class="lab">Generation</div><div class="val">{E3:,.0f} kWh/yr</div></div></div>
</div>""", unsafe_allow_html=True)

# ---------------- Result boxes ----------------
if res["year_reached"]:
    ok = res["within_life"]
    nz, pill = f"{res['years_exact']:.1f} yrs", ("within design life" if ok else "beyond design life")
else:
    ok, nz = False, "Never"
    pill = "no on-site generation" if not gen_on else "generation does not cover operation"
st.markdown(f"""<div class="res-row">
<div class="res"><div class="lab">Annual balance (generation − operation)</div><div class="val">{fmt(res['surplus_kwh'], True)} kWh/yr</div></div>
<div class="res"><div class="lab">Realistic net zero reached after</div><div class="val">{nz}</div>
<span class="pill {'ok' if ok else 'bad'}">{pill}</span></div></div>""", unsafe_allow_html=True)

T = st.tabs([f"{btype} results", "Traditional vs RNZE comparison", "Passive design explorer (concept)"])

# ---------------- Tab 1 ----------------
with T[0]:
    a, bcol = st.columns(2, gap="large")
    with a:
        with st.container(border=True):
            box("Cumulative energy balance", "Energy debt from materials, repaid by the annual renewable surplus.")
            fig = go.Figure(); fig.add_hline(y=0, line_dash="dash", line_color="#9AA9A7")
            balance_trace(fig, E1, E2, E3, life, btype, C_SYS[system], dash=None if rnze else "dot")
            fig.update_xaxes(title="Year"); st.plotly_chart(style_fig(fig), width="stretch")
    with bcol:
        with st.container(border=True):
            box("Largest embodied-energy contributors", "Materials with the highest embodied energy in this design.")
            d2 = df.copy(); d2["kWh"] = d2["Quantity (kg)"] * d2["Embodied energy (MJ/kg)"] / MJ_PER_KWH
            top = d2.sort_values("kWh", ascending=False).head(8)
            bar = go.Figure(go.Bar(x=top["kWh"], y=top["Material type"], orientation="h", marker_color=C_BAR))
            bar.update_yaxes(autorange="reversed"); bar.update_xaxes(title="kWh")
            st.plotly_chart(style_fig(bar, ytitle=""), width="stretch")
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
    a, bcol = st.columns(2, gap="large")
    with a:
        with st.container(border=True):
            box(f"{system}: traditional vs RNZE", "Traditional houses keep adding energy debt; the RNZE house repays it.")
            f1 = go.Figure(); f1.add_hline(y=0, line_dash="dash", line_color="#9AA9A7")
            balance_trace(f1, et, t_op, 0, 50, "Traditional", C_SYS[system], dash="dot", label=False)
            balance_trace(f1, er, r_op, r_gen, 50, "RNZE", C_SYS[system], label=False)
            f1.update_xaxes(title="Year"); st.plotly_chart(style_fig(f1), width="stretch")
    with bcol:
        with st.container(border=True):
            box(f"{system} RNZE: when the energy debt is repaid", "Embodied energy debt at year 0, repaid by the annual renewable surplus.")
            f2 = go.Figure(); f2.add_hline(y=0, line_dash="dash", line_color="#9AA9A7")
            balance_trace(f2, er, r_op, r_gen, 50, "RNZE", C_SYS[system])
            f2.update_xaxes(title="Year"); st.plotly_chart(style_fig(f2), width="stretch")

    st.divider()
    st.markdown('<div class="sec">All structural systems</div>', unsafe_allow_html=True)
    a, bcol = st.columns(2, gap="large")
    with a:
        with st.container(border=True):
            box("Traditional vs RNZE: all structures", "Dotted: traditional. Solid: RNZE.")
            f3 = go.Figure(); f3.add_hline(y=0, line_dash="dash", line_color="#9AA9A7")
            for n, (t1, r1) in vals.items():
                balance_trace(f3, t1, t_op, 0, 50, f"{n}: traditional", C_SYS[n], dash="dot", mark=False)
                balance_trace(f3, r1, r_op, r_gen, 50, f"{n}: RNZE", C_SYS[n], mark=False)
            f3.update_xaxes(title="Year"); st.plotly_chart(style_fig(f3, h=400), width="stretch")
    with bcol:
        with st.container(border=True):
            box("RNZE houses: when the energy debt is repaid", "Same operation and generation; the difference comes from embodied energy alone.")
            f4 = go.Figure(); f4.add_hline(y=0, line_dash="dash", line_color="#9AA9A7")
            for n, (t1, r1) in vals.items():
                balance_trace(f4, r1, r_op, r_gen, 50, f"{n}: RNZE", C_SYS[n], mark=False)
                rr = energy_net_zero(r1, r_op, r_gen)
                f4.add_trace(go.Scatter(x=[0, rr["years_exact"]], y=[-r1, 0], mode="markers", showlegend=False,
                                        marker=dict(size=9, color=C_SYS[n]), hoverinfo="skip"))
            f4.update_xaxes(title="Year"); st.plotly_chart(style_fig(f4, h=400), width="stretch")

    with st.container(border=True):
        box("Summary: 50-year energy balance", "Energy used is shown as negative, energy generated as positive.")
        rows = ""
        for n, (t1, r1) in vals.items():
            for lab, e1, e2, e3, last in [("Traditional", t1, t_op, 0, False), ("RNZE", r1, r_op, r_gen, True)]:
                bal = -e1 + (e3 - e2) * 50
                pal = PAL["trad" if lab == "Traditional" else "rnze"]["e2"][0]
                rows += (f'<tr class="{"pairend" if last else ""}" style="background:{pal}"><td>{lab} {n.lower()}</td>'
                         f'<td>{fmt(-e1, True)}</td><td>{fmt(-e2, True)}</td><td>{fmt(e3, True) if e3 else "0"}</td>'
                         f'<td class="{'pos' if bal > 0 else 'neg'}">{fmt(bal, True)}</td></tr>')
        st.markdown(f"""<table class="sum"><tr><th>Building</th><th>E1 Embodied<br>(kWh)</th><th>E2 Operation<br>(kWh/yr)</th>
<th>E3 Renewable<br>(kWh/yr)</th><th>Energy at<br>year 50 (kWh)</th></tr>{rows}</table>""", unsafe_allow_html=True)

# ---------------- Tab 3: passive design explorer ----------------
with T[2]:
    passive.render(btype, E1, system)
