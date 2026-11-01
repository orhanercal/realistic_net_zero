"""NZE Intelligence - Passive design explorer page (concept)."""
import json, os
import pandas as pd
import streamlit as st
import passive
from rnzeb_engine import MJ_PER_KWH

HERE = os.path.dirname(os.path.abspath(__file__))
EE = json.load(open(os.path.join(HERE, "ee_tables.json")))
SYSTEMS = {"Steel": "steel", "Reinforced concrete": "rc", "Timber": "timber"}

with st.sidebar:
    st.header("Building")
    system = st.selectbox("Structural system", list(SYSTEMS), key="pp_sys")
    btype = st.radio("Building type", ["Traditional building", "RNZE building"], index=1, key="pp_type",
                     help="Starting point: the published traditional or RNZE case-study house.")

key = f"{SYSTEMS[system]}_{'low' if btype == 'RNZE building' else 'trad'}"
E1 = sum(m["qty_kg"] * m["ee_factor"] for m in EE[key] if not m.get("excluded")) / MJ_PER_KWH

st.markdown('<div style="font-weight:700;letter-spacing:.04em;color:#5B6E6C;font-size:.9rem">NZE INTELLIGENCE</div>'
            '<div style="font-size:1.9rem;font-weight:700;color:#14302E;line-height:1.2;margin-bottom:4px">'
            'Passive design explorer (concept)</div>', unsafe_allow_html=True)
st.caption("Concept preview: simplified physics and stated assumptions. Explore how orientation, window-wall ratio, "
           "natural ventilation and the building envelope change energy demand, generation and the net zero year, "
           "compared with the Optimum case-study design.")
st.divider()
passive.render(btype, E1, system)
