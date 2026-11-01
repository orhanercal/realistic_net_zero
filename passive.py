"""Passive design explorer.

Core heating method = the published RNZEB method (Sustainable Horizons, 17, 100163, 2026):
    load = (sum U*A*dT + 0.33*ACH*V*dT) * 1.2 ;  annual heat = load * 1800 h ;  energy = heat / efficiency
Passive effects (solar gain, daylight, PV yield, mechanical ventilation) are added as DIFFERENCES from the
published 'Optimum' design, so the Optimum settings reproduce the paper exactly.
"""
import os
import streamlit as st
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
LIGHT_ORIENT = {"S": 1.00, "SE": 1.035, "SW": 1.035, "E": 1.07, "W": 1.07, "NE": 1.11, "NW": 1.11, "N": 1.15}
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
    L = LIGHT[btype]; r = (wwr["Front facade"] / 100) / (opt_w["Front facade"] / FACADES["Front facade"][1])
    m_wwr = 1 + 0.5 * (1 - r) if r <= 1 else 1 - 0.15 * min(r - 1, 1)
    light = L["day"] * m_wwr * LIGHT_ORIENT[d1["Front facade"]] + L["bed"] + L["serv"]
    vent = 0 if natvent else MECH_VENT
    pv = PV_OPT * PV_FACTOR[main_dir] if p["gen"] else 0.0
    wind = WIND if p["gen"] else 0.0
    return {"Heating": heat, "Cooling": p["cool"], "Lighting": light, "Appliances": p["appl"],
            "Mechanical ventilation": vent, "PV": pv, "Wind": wind, "gen": pv + wind,
            "E2": heat + p["cool"] + light + p["appl"] + vent}


def compass_svg(main_dir):
    rot = DIRS.index(main_dir) * 45
    return f"""<div class="center"><svg viewBox="0 0 220 220" width="230" height="230" xmlns="http://www.w3.org/2000/svg">
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
    left, right = st.columns([3, 2], gap="large")
    with left:
        with st.container(border=True):
            a, b = st.columns([3, 2], vertical_alignment="center")
            with a:
                main_dir = st.selectbox("Orientation: the main facade faces", DIRS,
                                        format_func=lambda d: "S (Optimum)" if d == "S" else d, key="pd_or",
                                        help="Changes solar gain for heating, daylight in living spaces and PV yield. "
                                             "Assumptions: London vertical irradiance (Oct–Apr), PV yield factors for a ~30° roof. "
                                             "Wind yield assumed independent of orientation.")
            with b:
                sketch("sketch_orientation.png")
            _, mid, _ = st.columns([1, 3, 1])
            with mid:
                sketch("sketch_pv_wind.png", "PV yield follows the roof orientation")
        ui.gap()
        with st.container(border=True):
            a, b = st.columns([3, 2], vertical_alignment="center")
            a.markdown("**Window-wall ratio by facade (%)**")
            with b:
                sketch("sketch_daylight.png")
            wwr = {}
            cols = st.columns(2)
            for i, f in enumerate(FACADES):
                with cols[i % 2]:
                    with st.container(border=True):
                        wwr[f] = st.slider(f"{f} (Optimum {OPT_PCT[f]}%)", 0.0, 80.0, OPT_PCT[f], 0.5, key=f"pd_w{i}",
                                           help="More glazing raises heat loss and solar gain; front-facade glazing also "
                                                "drives daylight in living spaces (assumption: halving it adds ~25% to their "
                                                "lighting, doubling it saves ~15%).")
        ui.gap()
        with st.container(border=True):
            a, b = st.columns([3, 2], vertical_alignment="center")
            with a:
                natvent = st.radio("Natural ventilation", ["Optimum (openable windows)", "None (mechanical ventilation)"],
                                   key="pd_nv",
                                   help="Assumption: whole-house mechanical ventilation ~45 W continuous, ~400 kWh/yr.") \
                    .startswith("Optimum")
            with b:
                sketch("sketch_ventilation.png")
        ui.gap()
        with st.container(border=True):
            a, b = st.columns([3, 2], vertical_alignment="center")
            default_env = 0 if btype == "Traditional building" else 1
            with a:
                env = st.radio("Envelope", list(ENVELOPE), index=default_env, key=f"pd_env_{btype}",
                               help="U-values from the paper (Tables 12 and 17). Affects heating only.")
            with b:
                sketch("sketch_envelope.png")
    with right:
        with st.container(border=True):
            img = "traditional.png" if btype == "Traditional building" else "rnze.png"
            st.image(os.path.join(HERE, img), caption=f"{btype} (case study)", width="stretch")
            st.markdown(compass_svg(main_dir), unsafe_allow_html=True)

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
    bal, d = des["gen"] - des["E2"], (des["gen"] - des["E2"]) - (opt["gen"] - opt["E2"])
    pcls = "zero" if abs(d) < 0.5 else ("ok" if d > 0 else "bad")
    st.markdown(f"""<div class="res-row">
<div class="res"><div class="lab">Annual balance, this design</div><div class="val">{bal:+,.0f} kWh/yr</div>
<span class="pill {pcls}">{d:+,.0f} vs Optimum</span></div>
<div class="res"><div class="lab">Net zero, Optimum</div><div class="val">{f(r0)}</div></div>
<div class="res"><div class="lab">Net zero, this design</div><div class="val">{f(r1)}</div></div></div>""",
                unsafe_allow_html=True)
