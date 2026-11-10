"""Passive design explorer.

Core heating method = the published RNZEB method (Sustainable Horizons, 17, 100163, 2026):
    load = (sum U*A*dT + 0.33*ACH*V*dT) * 1.2 ;  annual heat = load * 1800 h ;  energy = heat / efficiency
Passive effects (solar gain, daylight, PV yield, mechanical ventilation) are added as DIFFERENCES from the
published 'Optimum' design, so the Optimum settings reproduce the paper exactly.
"""
import os
import streamlit as st
import plotly.graph_objects as go
from rnzeb_engine import energy_net_zero

HERE = os.path.dirname(os.path.abspath(__file__))
DT, HOURS, SAFETY = 22, 1800, 1.2
Q_INF = 0.33 * 1 * 566 * DT                      # infiltration, 1 ACH, V = 566 m3 (paper)
A_ROOF, A_FLOOR = 120.2, 94.6                    # Revit take-off (paper Tables 12 and 17)
ENVELOPE = {  # U-values W/m2K (paper Tables 12 and 17)
    "No insulation, single glazing": dict(wall=1.7, roof=2.0, win=5.0, floor=1.0, g=0.85),
    "Insulated (rock wool, green roof), double glazing": dict(wall=0.3, roof=0.2, win=1.6, floor=0.25, g=0.75),
}
# Facades: base azimuth (Optimum), gross area (m2, scaled to Revit total 227 m2), Optimum window area (scaled to 28.75 m2)
FACADES = {
    "Front facade": (180, 50.65, 19.90),
    "Right facade": (90, 62.85, 7.94),
    "Rear facade": (0, 50.65, 0.57),
    "Left facade": (270, 62.85, 0.34),
}
DIRS = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
# ASSUMPTIONS (literature-typical values for London)
I_HEAT = {"S": 290, "SE": 240, "SW": 240, "E": 160, "W": 160, "NE": 100, "NW": 100, "N": 85}  # kWh/m2, Oct-Apr, vertical
PV_FACTOR = {"S": 1.00, "SE": 0.95, "SW": 0.95, "E": 0.80, "W": 0.80, "NE": 0.65, "NW": 0.65, "N": 0.57}
# Summer (May-Sep) vertical solar gain on glazing, weighted towards afternoon peaks: west and east glazing
# drive cooling most, north glazing least (assumption, London).
I_COOL = {"S": 330, "SE": 340, "SW": 370, "E": 300, "W": 360, "NE": 170, "NW": 210, "N": 110}  # kWh/m2
COOL_UTIL, COOL_TH = 0.35, 4350.0               # share of summer gain that becomes cooling load; paper thermal demand
# Daylight weight of glazing by orientation (north light is diffuse but still useful; assumption)
DL = {"S": 1.00, "SE": 1.00, "SW": 1.00, "E": 0.95, "W": 0.95, "NE": 0.85, "NW": 0.85, "N": 0.80}
FRAME, UTIL = 0.7, 0.6
MECH_VENT = 400                                  # kWh/yr, whole-house mechanical ventilation (~45 W continuous)
LIGHT = {"Traditional building": dict(day=1205 + 1241 + 219, bed=262 + 262 + 395 + 460, serv=219 + 77 + 59 + 160 + 80 + 154),
         "RNZE building": dict(day=175.2 + 182.5 + 32.8, bed=38.3 + 38.3 + 60.2 + 65.7, serv=32.8 + 11 + 8.7 + 24 + 11 + 21.9)}
PAPER = {"Traditional building": dict(heat=51749.0, cool=4350.0, appl=5125.0, eff=0.92, gen=False),
         "RNZE building": dict(heat=4618.0, cool=1243.0, appl=3720.0, eff=3.5, gen=True)}
PV_OPT, WIND = 8406.9, 6025.4
OPT_PCT = {f: round(100 * w / g, 1) for f, (_, g, w) in FACADES.items()}


def az_to_dir(az):
    return {0: "N", 45: "NE", 90: "E", 135: "SE", 180: "S", 225: "SW", 270: "W", 315: "NW"}[az % 360]


def facade_dirs(main_dir):
    rot = DIRS.index(main_dir) * 45
    return {f: az_to_dir(a + rot) for f, (a, _, _) in FACADES.items()}


def load_w(env, wins):
    u = ENVELOPE[env]; ua = 0
    for f, (_, gross, _) in FACADES.items():
        ua += u["wall"] * (gross - wins[f]) + u["win"] * wins[f]
    ua += u["roof"] * A_ROOF + u["floor"] * A_FLOOR
    return (ua * DT + Q_INF) * SAFETY


def solar_kwh(env, wins, dirs):
    g = ENVELOPE[env]["g"]
    return sum(wins[f] * FRAME * g * I_HEAT[dirs[f]] * UTIL for f in FACADES)


def evaluate(btype, env, main_dir, wwr, natvent):
    base_env = list(ENVELOPE)[0] if btype == "Traditional building" else list(ENVELOPE)[1]
    p = PAPER[btype]
    opt_w = {f: FACADES[f][1] * OPT_PCT[f] / 100 for f in FACADES}
    wins = {f: FACADES[f][1] * wwr[f] / 100 for f in FACADES}
    d0, d1 = facade_dirs("S"), facade_dirs(main_dir)
    ratio = load_w(env, wins) / load_w(base_env, opt_w)
    d_gain = solar_kwh(env, wins, d1) - solar_kwh(base_env, opt_w, d0)
    heat = max(0.0, (p["heat"] * p["eff"] * ratio - d_gain) / p["eff"])
    # Cooling: summer solar gain through the glazing of all four facades, as a difference from Optimum
    g1, g0 = ENVELOPE[env]["g"], ENVELOPE[base_env]["g"]
    d_cool = COOL_UTIL * FRAME * (sum(wins[f] * g1 * I_COOL[d1[f]] for f in FACADES)
                                  - sum(opt_w[f] * g0 * I_COOL[d0[f]] for f in FACADES))
    cool = p["cool"] * max(0.0, COOL_TH + d_cool) / COOL_TH
    # Lighting: daylight from the glazing of all four facades, weighted by orientation
    L = LIGHT[btype]
    r = sum(wins[f] * DL[d1[f]] for f in FACADES) / sum(opt_w[f] * DL[d0[f]] for f in FACADES)
    m_wwr = 1 + 0.5 * (1 - r) if r <= 1 else 1 - 0.15 * min(r - 1, 1)
    light = L["day"] * m_wwr + L["bed"] + L["serv"]
    vent = 0 if natvent else MECH_VENT
    pv = PV_OPT * PV_FACTOR[main_dir] if p["gen"] else 0.0
    wind = WIND if p["gen"] else 0.0
    return {"Heating": heat, "Cooling": cool, "Lighting": light, "Appliances": p["appl"],
            "Mechanical ventilation": vent, "PV": pv, "Wind": wind, "gen": pv + wind,
            "E2": heat + cool + light + p["appl"] + vent}


def compass_svg(main_dir):
    rot = DIRS.index(main_dir) * 45
    return f"""<div class="center"><svg viewBox="0 0 220 220" width="200" height="200" xmlns="http://www.w3.org/2000/svg">
<circle cx="110" cy="110" r="96" fill="#F7FAFA" stroke="#C9D8D7"/>
<text x="110" y="24" text-anchor="middle" font-size="14" font-weight="700" fill="#14302E">N</text>
<text x="110" y="206" text-anchor="middle" font-size="12" fill="#5B6E6C">S</text>
<text x="200" y="114" text-anchor="middle" font-size="12" fill="#5B6E6C">E</text>
<text x="20" y="114" text-anchor="middle" font-size="12" fill="#5B6E6C">W</text>
<g transform="rotate({rot} 110 110)">
  <rect x="80" y="62" width="60" height="70" fill="#EFE4CF" stroke="#A8875A" stroke-width="2"/>
  <rect x="96" y="132" width="38" height="14" fill="#EBF2FA" stroke="#7FA3C6" stroke-width="1.5"/>
  <line x1="80" y1="97" x2="140" y2="97" stroke="#A8875A" stroke-dasharray="3 3"/>
  <rect x="84" y="100" width="52" height="28" fill="#DCE7F3" opacity=".9"/>
  <text x="110" y="160" text-anchor="middle" font-size="10" fill="#14302E">Front facade</text>
</g></svg></div>"""


def sketch(name, caption=None):
    st.image(os.path.join(HERE, name), caption=caption, width="stretch")


def _fmt_change(k, d):
    good_if_down = k not in ("PV", "Wind", "gen")
    if abs(d) < 0.5:
        return '<td class="zero">0</td>'
    good = (d < 0) if good_if_down else (d > 0)
    return f'<td class="{"pos" if good else "neg"}">{d:+,.0f}</td>'


def render(btype, E1, system):
    import ui
    st.caption("Optimum = the published case-study design. The core heating method is the published RNZEB method; "
               "passive effects are added as differences from Optimum. Values marked ⓘ are assumptions. "
               "Not a compliance tool.")
    ui.gap()
    ui.extra_css()
    sysk = {"Steel": "steel", "Reinforced concrete": "rc", "Timber": "timber"}[system]
    tk = "rnze" if btype == "RNZE building" else "trad"
    P = lambda n: os.path.join(HERE, n)
    default_env = 0 if btype == "Traditional building" else 1
    H1, H2, H3 = 520, 636, 310

    # ---------- Row 1: Orientation | building image and compass ----------
    left, right = st.columns(2, gap="large")
    with left:
        with st.container(border=True, height=H1):
            with st.container(border=True, key="phdr"):
                st.markdown('<div class="ptitle">Orientation</div>', unsafe_allow_html=True,
                            help="Changes winter solar gain (heating), summer solar gain (cooling), daylight and PV yield. "
                                 "Assumptions: London vertical irradiance (Oct–Apr), PV yield factors for a ~30° roof. "
                                 "Wind yield assumed independent of orientation.")
                main_dir = st.selectbox("The main facade faces", DIRS,
                                        format_func=lambda d: "S (Optimum)" if d == "S" else d, key="pd_or")
            with st.container(border=True, height=300):
                st.markdown(f'''<div class="skbox" style="height:230px">
<img src="{ui.b64(P("sketch_orientation.png"))}" style="width:48%;max-height:220px">
<img src="{ui.b64(P("sketch_pv_wind.png"))}" style="width:48%;max-height:220px"></div>
<div class="skcap">Plan orientation · PV yield follows the roof orientation · Ridge-mounted wind turbine yield assumed unchanged</div>''',
                            unsafe_allow_html=True)
    with right:
        with st.container(border=True, height=H1):
            st.markdown(f'''<div class="skbox" style="flex-direction:column;gap:6px">
<img src="{ui.b64(P(f"{sysk}_{tk}_front.png"))}" style="max-height:220px">
<div class="skcap">{btype} · {system} structure (case study)</div>
{compass_svg(main_dir)}<div class="skcap">Main facade orientation</div></div>''', unsafe_allow_html=True)
    ui.gap()

    # ---------- Row 2: Window-wall ratio | Natural ventilation + Envelope ----------
    left, right = st.columns(2, gap="large")
    with left:
        with st.container(border=True, height=H2):
            a, b = st.columns(2, vertical_alignment="center")
            with a:
                with st.container(border=True, key="phdr2", height=190):
                    st.markdown('<div style="height:8px"></div><div class="ptitle" style="font-size:1.3rem">Window-wall ratio by facade (%)</div>',
                                unsafe_allow_html=True,
                                help="Each facade changes heating (heat loss and winter sun), cooling (summer sun, "
                                     "highest on west and east glazing, lowest on north) and lighting (daylight). "
                                     "Assumptions: halving the daylight glazing adds ~25% to living-space lighting, "
                                     "doubling it saves ~15%.")
            with b:
                with st.container(border=True, height=190):
                    st.markdown(f'<div class="skbox"><img src="{ui.b64(P("sketch_daylight.png"))}" style="max-height:160px"></div>',
                                unsafe_allow_html=True)
            ui.gap()
            wwr = {}
            cols = st.columns(2)
            for i, f in enumerate(FACADES):
                with cols[i % 2]:
                    with st.container(border=True, height=150):
                        wwr[f] = st.slider(f"{f} (Optimum {OPT_PCT[f]}%)", 0.0, 80.0, OPT_PCT[f], 0.5, key=f"pd_w{i}")
    with right:
        for title, sub, sketchf, kind, kh, ko in [
                ("Natural ventilation", "Ventilation strategy", "sketch_ventilation.png", "nv", "phdr3", "popt3"),
                ("Envelope", "Insulation and glazing", "sketch_envelope.png", "env", "phdr4", "popt4")]:
            with st.container(border=True, height=H3):
                a, b = st.columns(2, vertical_alignment="center")
                with a:
                    with st.container(border=True, key=kh, height=104):
                        st.markdown(f'<div class="ptitle" style="font-size:1.2rem">{title}</div><div class="psub">{sub}</div>',
                                    unsafe_allow_html=True,
                                    help=("Assumption: whole-house mechanical ventilation ~45 W continuous, ~400 kWh/yr."
                                          if kind == "nv" else "U-values from the paper (Tables 12 and 17). Affects heating; glazing type also affects solar gain."))
                    with st.container(border=True, key=ko, height=150):
                        if kind == "nv":
                            natvent = st.radio(title, ["Optimum (openable windows)", "None (mechanical ventilation)"],
                                               key="pd_nv", label_visibility="collapsed").startswith("Optimum")
                        else:
                            env = st.radio(title, list(ENVELOPE), index=default_env, key=f"pd_env_{btype}",
                                           label_visibility="collapsed")
                with b:
                    with st.container(border=True, height=266):
                        st.markdown(f'<div class="skbox"><img src="{ui.b64(P(sketchf))}" style="max-height:230px"></div>',
                                    unsafe_allow_html=True)
            if kind == "nv":
                st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)

    opt = evaluate(btype, list(ENVELOPE)[default_env], "S", dict(OPT_PCT), True)
    des = evaluate(btype, env, main_dir, wwr, natvent)
    ui.gap()

    e2c, e3c = ui.PAL["rnze"]["e2"][0], ui.PAL["rnze"]["e3"][0]
    def row(k, lab, cls=""):
        return (f'<tr class="{cls}"><td>{lab}</td><td>{opt[k]:,.0f}</td><td>{des[k]:,.0f}</td>'
                f'{_fmt_change(k, des[k] - opt[k])}</tr>')
    body = (f'<tr class="grp" style="background:{e2c}"><td colspan="4">E2 · Energy used</td></tr>'
            + "".join(row(k, k) for k in ["Heating", "Cooling", "Lighting", "Appliances", "Mechanical ventilation"])
            + row("E2", "E2 Operation total", "tot").replace('<tr class="tot">', f'<tr class="tot pairend" style="background:{e2c}">')
            + f'<tr class="grp" style="background:{e3c}"><td colspan="4">E3 · Energy generated</td></tr>'
            + row("PV", "PV") + row("Wind", "Wind")
            + row("gen", "E3 Generation total", "tot").replace('<tr class="tot">', f'<tr class="tot" style="background:{e3c}">'))
    title = btype.replace("RNZE building", "RNZE building").replace("Traditional building", "Traditional building")
    with st.container(border=True):
        st.markdown(f'<div class="sec">Results: {title} · {system} structure</div>', unsafe_allow_html=True)
        st.markdown(f'<table class="sum"><tr><th></th><th>Optimum<br>(kWh/yr)</th><th>This design<br>(kWh/yr)</th>'
                    f'<th>Change<br>(kWh/yr)</th></tr>{body}</table>', unsafe_allow_html=True)
    ui.gap()
    r0, r1 = energy_net_zero(E1, opt["E2"], opt["gen"]), energy_net_zero(E1, des["E2"], des["gen"])
    f = lambda r: ("Never" if not r["year_reached"] else
                   "Over 100 yrs" if r["years_exact"] > 100 else f"{r['years_exact']:.1f} yrs")
    e1r = round(E1)
    b0 = round(opt["gen"]) - round(opt["E2"])
    bal = round(des["gen"]) - round(des["E2"])
    d = bal - b0
    pcls = "zero" if d == 0 else ("ok" if d > 0 else "bad")
    fx = lambda r, b: (f"E1 ÷ (E3 − E2) = {e1r:,} ÷ {b:,}" if r["year_reached"]
                       else "E3 − E2 is negative, so the embodied energy debt is never repaid.")
    st.markdown(f"""<div class="res-row">
<div class="res"><div class="lab">Annual balance, this design</div><div class="val">{bal:+,} kWh/yr</div>
<div class="fx">E3 − E2 = {round(des['gen']):,} − {round(des['E2']):,}</div>
<span class="pill {pcls}">{d:+,} vs Optimum</span></div>
<div class="res"><div class="lab">Net zero, Optimum</div><div class="val">{f(r0)}</div>
<div class="fx">{fx(r0, b0)} (published design)</div></div>
<div class="res"><div class="lab">Net zero, this design</div><div class="val">{f(r1)}</div>
<div class="fx">{fx(r1, bal)}</div></div></div>""", unsafe_allow_html=True)
    ui.gap()
    with st.container(border=True):
        st.markdown('<div class="sec">Comparison: annual energy, Optimum vs this design</div>', unsafe_allow_html=True)
        st.caption("Coloured bars: energy used (E2). Green layer: renewable energy generated (E3). "
                   "Where the green layer covers the whole bar, generation meets demand; any uncovered part is a shortfall.")
        st.plotly_chart(comparison_chart(opt, des), width="stretch")


CAT_COLORS = {"Heating": "#CBAE97", "Cooling": "#A9C3D6", "Appliances": "#C2BDD6", "Lighting": "#E6D6A6",
              "Mechanical ventilation": "#BCC6C4"}   # soft, muted tones


def comparison_chart(opt, des):
    xs, names = [0, 1], ["Optimum (published design)", "This design"]
    fig = go.Figure()
    for cat, colr in CAT_COLORS.items():
        ys = [opt[cat], des[cat]]
        if max(ys) < 0.5:
            continue
        fig.add_trace(go.Bar(x=xs, y=ys, name=cat, marker_color=colr, width=0.42,
                             text=[f"{cat}<br>{v:,.0f}" if v > 900 else "" for v in ys], textposition="inside",
                             insidetextanchor="middle", textfont=dict(size=11, color="#14302E"),
                             hovertemplate=cat + ": %{y:,.0f} kWh/yr<extra></extra>"))
    top = 0
    for x, r in zip(xs, (opt, des)):
        e2, e3 = r["E2"], r["gen"]
        top = max(top, e2, e3)
        fig.add_annotation(x=x, y=e2, text=f"<b>E2 {e2:,.0f}</b>", showarrow=False, yshift=12,
                           font=dict(size=12, color="#14302E"))
        if e3 > 0:
            fig.add_shape(type="rect", x0=x - 0.32, x1=x + 0.32, y0=0, y1=e3, fillcolor="rgba(95,160,120,0.18)",
                          line=dict(color="#5E9472", width=1.5), layer="above")
            fig.add_shape(type="line", x0=x - 0.32, x1=x + 0.32, y0=e3, y1=e3, line=dict(color="#4E8A64", width=3),
                          layer="above")
            fig.add_annotation(x=x + 0.33, y=e3, text=f"<b>E3 {e3:,.0f}</b>", showarrow=False, xanchor="left",
                               font=dict(size=12, color="#4E8A64"))
            dlt = round(e3) - round(e2)
            fig.add_annotation(x=x, y=max(e2, e3), yshift=34, showarrow=False,
                               text=(f"<b>Surplus +{dlt:,} kWh/yr</b>" if dlt >= 0 else f"<b>Shortfall −{-dlt:,} kWh/yr</b>"),
                               font=dict(size=13, color="#4E8A64" if dlt >= 0 else "#B5544A"))
        else:
            fig.add_annotation(x=x, y=e2, yshift=34, showarrow=False, text="<b>No on-site generation</b>",
                               font=dict(size=13, color="#B5544A"))
    fig.add_trace(go.Bar(x=[None], y=[None], name="E3 renewable generation",
                         marker=dict(color="rgba(95,160,120,0.18)", line=dict(color="#5E9472", width=1.5))))
    fig.update_layout(barmode="stack", height=520, plot_bgcolor="white", paper_bgcolor="white",
                      margin=dict(l=10, r=10, t=30, b=10), font=dict(color="#14302E"),
                      legend=dict(orientation="h", y=-0.12), yaxis_title="kWh/yr", bargap=0.3)
    fig.update_xaxes(tickvals=xs, ticktext=names, range=[-0.6, 1.75])
    fig.update_yaxes(range=[0, top * 1.22], gridcolor="#EEF2F1")
    return fig
