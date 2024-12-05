import streamlit as st
import sys
import time

sys.path.append('packages')

# Set the page configuration
st.set_page_config(page_title='ClimALM', page_icon='🌍', layout='wide')

# Inizializza il tempo all'avvio dell'app
if "start_time" not in st.session_state:
    st.session_state.start_time = time.time()

# Calcola il tempo di utilizzo
elapsed_time = time.time() - st.session_state.start_time

st.title('ClimALM')

st.subheader('Collection of streamlit dashboard with implementation of Climate Services tools powered by AI')

st.write(f"Tempo di utilizzo dell'app: {elapsed_time:.2f} secondi")
