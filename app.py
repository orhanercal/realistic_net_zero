"""NZE Intelligence prototype: two pages."""
import streamlit as st

st.set_page_config(page_title="NZE Intelligence | RNZEB prototype", layout="wide")
nav = st.navigation([
    st.Page("calculator.py", title="RNZEB calculator", default=True),
    st.Page("passive_page.py", title="Passive design explorer"),
])
nav.run()
