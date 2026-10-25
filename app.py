import os
import json
import pandas as pd
from datetime import datetime
import uuid
import streamlit as st
import plotly.express as px
from supabase import create_client, Client

# --- SAYFA AYARI ---
st.set_page_config(page_title="Notes - Kesintisiz Yönetim Sistemi", layout="wide", page_icon="📝")

# --- SUPABASE BAĞLANTISI ---
@st.cache_resource
def init_supabase() -> Client:
    url = str(st.secrets.get("SUPABASE_URL", "")).strip()
    key = str(st.secrets.get("SUPABASE_KEY", "")).strip()
    
    url = url.strip('"').strip("'")
    key = key.strip('"').strip("'")
    
    if not url or not key:
        st.error("Supabase URL veya API Anahtarı Secrets alanında bulunamadı!")
        st.stop()
    return create_client(url, key)

supabase = init_supabase()
