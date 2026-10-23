import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- SAYFA AYARI ---
st.set_page_config(page_title="Notes - Hata Yönetim Sistemi", layout="wide")

# --- SUPABASE BAĞLANTISI ---
@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["SUPABASE_URL"].strip()
    key = st.secrets["SUPABASE_KEY"].strip()
    return create_client(url, key)

supabase = init_connection()

# --- VERİ TABANI FONKSİYONLARI ---
def load_records():
    try:
        response = supabase.table("notes_records").select("*").execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Kayıtlar yüklenirken hata oluştu: {e}")
        return []

def save_record(record_data):
    try:
        supabase.table("notes_records").insert(record_data).execute()
    except Exception as e:
        st.error(f"Kayıt kaydedilirken hata oluştu: {e}")

def load_config():
    try:
        response = supabase.table("notes_config").select("*").execute()
        if response.data:
            config_dict = {}
            for row in response.data:
                config_dict[row.get("key")] = row.get("value")
            return config_dict
        return {}
    except Exception as e:
        return {}

def save_config(key, value):
    try:
        supabase.table("notes_config").upsert({"key": key, "value": value}).execute()
    except Exception as e:
        st.error(f"Ayar kaydedilirken hata oluştu: {e}")

# --- KULLANICI GİRİŞ KONTROLÜ ---
def check_password():
    def password_entered():
        config = load_config()
        admin_pass = config.get("admin_password", "1234")
        
        if st.session_state["username"] == "admin" and st.session_state["password"] == admin_pass:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("## 🔒 Giriş Yap")
        st.markdown("Lütfen devam etmek için kullanıcı adı ve şifrenizi girin.")
        st.text_input("Kullanıcı Adı", key="username")
        st.text_input("Şifre", type="password", key="password")
        st.button("Giriş Yap", on_click=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        st.markdown("## 🔒 Giriş Yap")
        st.text_input("Kullanıcı Adı", key="username")
        st.text_input("Şifre", type="password", key="password")
        st.button("Giriş Yap", on_click=password_entered)
        st.error("😕 Kullanıcı adı veya şifre hatalı")
        return False
    else:
        return True

if not check_password():
    st.stop()

# --- ANA UYGULAMA ---
st.title("📝 Notes - Hata Yönetim Sistemi")
st.success("🟢 Bulut Veritabanı (Supabase) Bağlantısı Aktif!")

records = load_records()

st.subheader("Kayıtlar")
if records:
    df = pd.DataFrame(records)
    st.dataframe(df, use_container_width=True)
else:
    st.info("Henüz kayıt bulunmuyor. Aşağıdan yeni bir kayıt ekleyebilirsiniz.")

with st.form("add_record_form"):
    st.subheader("Yeni Kayıt Ekle")
    title = st.text_input("Başlık / Hata Adı")
    desc = st.text_area("Açıklama")
    submitted = st.form_submit_button("Kaydet")
    
    if submitted and title:
        new_item = {"title": title, "description": desc}
        save_record(new_item)
        st.success("Kayıt başarıyla buluta eklendi!")
        st.rerun()
