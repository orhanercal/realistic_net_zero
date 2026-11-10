"""Shared look and feel for both pages."""
import streamlit as st

PAL = {"rnze": {"e1": ("#F8F2E7", "#E4D7BE"), "e2": ("#EBF2FA", "#CADBEC"), "e3": ("#EBF5EE", "#C7E0CF")},
       "trad": {"e1": ("#EFE4CF", "#D6C29D"), "e2": ("#DCE7F3", "#B4CAE2"), "e3": ("#DCEBE1", "#AFCFBA")}}
INK, MUTED = "#14302E", "#5B6E6C"
GOOD, BAD, ZERO = "#3F8A5F", "#B5544A", "#8A9897"


def css():
    rules = []
    for tone, boxes in PAL.items():
        for e, (bg, bd) in boxes.items():
            rules.append(f".st-key-{e}_{tone}{{background:{bg};border:1px solid {bd};border-radius:12px;padding:12px 12px 6px}}")
    st.markdown("<style>" + "\n".join(rules) + """
    [data-testid="stHeaderActionElements"], .stMarkdown a.anchor-link {display:none !important}
    .gap{height:26px}
    .card-row{display:flex;gap:14px;align-items:stretch}
    .card{border-radius:12px;padding:14px 16px;display:flex;flex-direction:column;color:%(ink)s}
    .card .ttl{margin:0 0 6px;font-size:1.02rem;font-weight:700}
    .card .sub{color:%(muted)s;font-size:.9rem;margin-bottom:8px}
    .card table{width:100%%;border-collapse:collapse;font-size:.88rem}
    .card td,.card th{padding:3px 4px;border-bottom:1px solid rgba(0,0,0,.08);text-align:left}
    .card td.n,.card th.n{text-align:right;white-space:nowrap}
    .card .total{margin-top:auto;padding-top:12px}
    .card .total .lab{font-size:.85rem;color:%(muted)s}
    .card .total .val{font-size:1.45rem;font-weight:600;line-height:1.2;white-space:nowrap}
    .note{font-size:.84rem;color:%(bad)s;margin-top:6px}
    .res-row{display:flex;gap:16px;justify-content:center;align-items:stretch;flex-wrap:wrap}
    .res{background:#FAFAF7;border:1px solid #DADFDE;border-radius:12px;padding:14px 28px;text-align:center;min-width:260px}
    .res .lab{font-size:.88rem;color:%(muted)s} .res .val{font-size:1.9rem;font-weight:600;color:%(ink)s}
    .pill{display:inline-block;border-radius:999px;padding:2px 10px;font-size:.8rem;margin-top:4px}
    .pill.ok{background:#E3F2E7;color:#24613F} .pill.bad{background:#F8E3E1;color:#8A2E25} .pill.zero{background:#EEF1F1;color:#5B6E6C}
    .brand{font-weight:700;letter-spacing:.04em;color:%(muted)s;font-size:.9rem;margin-bottom:2px}
    .apptitle{font-size:1.9rem;font-weight:700;color:%(ink)s;margin:0 0 4px;line-height:1.2}
    .band{border-radius:12px;padding:14px 18px;display:flex;align-items:center;gap:14px;color:%(ink)s}
    .chip{border:1px solid rgba(0,0,0,.2);border-radius:999px;padding:3px 12px;font-size:.9rem;background:rgba(255,255,255,.55)}
    .struct{font-size:1.5rem;font-weight:800;letter-spacing:.06em}
    .sec{font-size:1.25rem;font-weight:700;color:%(ink)s;margin:0 0 2px}
    .boxtitle{font-weight:700;font-size:1.02rem;color:%(ink)s;margin-bottom:0}
    .boxsub{color:%(muted)s;font-size:.88rem;margin-bottom:4px}
    .bomfoot{border:1px solid #E6EAEA;border-radius:10px;padding:8px 14px;text-align:right;font-weight:600;background:#FAFBFB}
    table.sum{width:100%%;border-collapse:collapse;font-size:.92rem;color:%(ink)s}
    table.sum th{text-align:right;padding:6px 8px;border-bottom:2px solid #C9D8D7;vertical-align:bottom}
    table.sum th:first-child,table.sum td:first-child{text-align:left}
    table.sum td{text-align:right;padding:6px 8px;white-space:nowrap}
    table.sum tr.pairend td{border-bottom:2px solid #C9D8D7}
    table.sum tr.grp td{font-weight:700;text-align:left;padding-top:10px}
    table.sum tr.tot td{font-weight:700}
    .pos{color:%(good)s;font-weight:600} .neg{color:%(bad)s;font-weight:600} .zero{color:%(zero)s}
    .btype{margin:0 0 10px;color:%(ink)s}
    .btlab{font-size:1.05rem;color:%(muted)s;font-weight:600}
    .btname{font-size:1.25rem;font-weight:800}
    .btdesc{font-size:.92rem;color:%(muted)s;margin-top:2px;max-width:900px}
    .res .fx{font-size:.82rem;color:%(muted)s;margin-top:2px}
    .center{text-align:center}
    </style>""" % dict(ink=INK, muted=MUTED, good=GOOD, bad=BAD, zero=ZERO), unsafe_allow_html=True)


def gap():
    st.markdown('<div class="gap"></div>', unsafe_allow_html=True)


def header(title, caption):
    st.markdown(f'<div class="brand">NZE INTELLIGENCE</div><div class="apptitle">{title}</div>', unsafe_allow_html=True)
    st.caption(caption)
    st.divider()


BTYPE = {
    "RNZE building": ("Realistic Net Zero Energy Building (RNZEB)", "#24613F",
                      "Low-embodied-energy materials, low operational energy (heat pump, LED lighting, A+++ appliances) "
                      "and on-site renewable generation (solar PV and a roof wind turbine) that repays the energy used "
                      "to build and run the house."),
    "Traditional building": ("Traditional building", "#8A5A2B",
                             "Typical materials and operational energy (gas boiler, air conditioning, incandescent "
                             "lighting, typical appliances), with no on-site renewable generation."),
}


def band(btype, system, tone):
    pt = PAL[tone]
    name, colr, desc = BTYPE[btype]
    st.markdown(f'<div class="btype"><span class="btlab">Building type:</span> '
                f'<span class="btname" style="color:{colr}">{name}</span><div class="btdesc">{desc}</div></div>',
                unsafe_allow_html=True)
    st.markdown(f'<div class="band" style="background:linear-gradient(90deg,{pt["e1"][0]},{pt["e2"][0]},{pt["e3"][0]});'
                f'border:1px solid {pt["e2"][1]}"><span class="chip">{btype}</span>'
                f'<span class="struct">{system.upper()} STRUCTURE</span></div>', unsafe_allow_html=True)


def sidebar_building(systems, key_prefix, with_life=True):
    st.header("Building")
    with st.container(border=True):
        system = st.selectbox("Structural system", list(systems), key=key_prefix + "sys")
    with st.container(border=True):
        btype = st.radio("Building type", ["Traditional building", "RNZE building"], index=1, key=key_prefix + "type",
                         help="RNZE: low embodied energy materials, low operational energy and renewable generation. "
                              "Traditional: typical materials and systems, no on-site generation.")
    life = 50
    if with_life:
        with st.container(border=True):
            life = st.slider("Design life (years)", 20, 100, 50, key=key_prefix + "life")
    st.divider()
    return system, btype, life


# ---------- image helpers ----------
import base64, functools, os as _os


@functools.lru_cache(maxsize=64)
def b64(path):
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def strip(items):
    """items: list of (path, caption). A thin row of equal thumbnails."""
    cells = "".join(f'<div class="th"><div class="im"><img src="{b64(p)}"></div><div class="c">{c}</div></div>'
                    for p, c in items)
    st.markdown(f'<div class="strip" style="grid-template-columns:repeat({len(items)},1fr)">{cells}</div>',
                unsafe_allow_html=True)


EXTRA_CSS = """<style>
.strip{display:grid;gap:12px}
.th{border:1px solid #E1E6E6;border-radius:10px;padding:8px;display:flex;flex-direction:column;align-items:center;gap:6px;background:#FCFDFD}
.th .im{height:120px;width:100%;display:flex;align-items:center;justify-content:center}
.th img{max-height:120px;max-width:100%;object-fit:contain}
.th .c{font-size:.78rem;color:#5B6E6C}
.ptitle{font-size:1.55rem;font-weight:800;color:#14302E;line-height:1.2}
.psub{font-size:.98rem;color:#5B6E6C;margin:2px 0 4px}
.skbox{display:flex;align-items:center;justify-content:center;gap:14px;height:100%}
.skbox img{max-width:100%;object-fit:contain}
.skcap{font-size:.78rem;color:#7A8A88;text-align:center;margin-top:6px}
.st-key-phdr, .st-key-phdr2, .st-key-phdr3, .st-key-phdr4, .st-key-popt3, .st-key-popt4 {background:#FAFBFB}
</style>"""


def extra_css():
    st.markdown(EXTRA_CSS, unsafe_allow_html=True)
