"""NZE Intelligence - Passive design explorer page."""
import json, os
import streamlit as st
import ui
import passive
from rnzeb_engine import MJ_PER_KWH

HERE = os.path.dirname(os.path.abspath(__file__))
EE = json.load(open(os.path.join(HERE, "ee_tables.json")))
SYSTEMS = {"Steel": "steel", "Reinforced concrete": "rc", "Timber": "timber"}

ui.css()
with st.sidebar:
    system, btype, _ = ui.sidebar_building(SYSTEMS, "p_", with_life=False)

key = f"{SYSTEMS[system]}_{'low' if btype == 'RNZE building' else 'trad'}"
E1 = sum(m["qty_kg"] * m["ee_factor"] for m in EE[key] if not m.get("excluded")) / MJ_PER_KWH

ui.header("Passive design explorer",
          "Concept preview: simplified physics and stated assumptions. Explore how orientation, window-wall ratio, "
          "natural ventilation and the building envelope change energy demand, generation and the net zero year, "
          "compared with the Optimum case-study design.")
ui.band(btype, system, "rnze" if btype == "RNZE building" else "trad")
passive.render(btype, E1, system)
