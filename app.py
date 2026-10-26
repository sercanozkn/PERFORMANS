import os
import json
from datetime import datetime
import uuid
import streamlit as st
import plotly.express as px
from supabase import create_client, Client

# --- SAYFA AYARI ---
st.set_page_config(page_title="Notes - Kesintisiz Yonetim Sistemi", layout="wide")

# --- SUPABASE BAGLANTISI ---
@st.cache_resource
def init_supabase():
    url = "".join(str(st.secrets.get("SUPABASE_URL", "")).split())
    key = "".join(str(st.secrets.get("SUPABASE_KEY", "")).split())
    if not url.startswith("http"):
        url = "https://" + url
    return create_client(url, key), url

supabase, SUPABASE_URL = init_supabase()
BUCKET_NAME = "notes-media"

# --- OTURUM & KULLANICI YONETIMI ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    st.title("🔐 Notes - Kullanici Girisi")

    with st.form("login_form"):
        username_input = st.text_input("Kullanıcı Adı:")
        password_input = st.text_input("Şifre:", type="password")
        login_btn = st.form_submit_button("Giriş Yap")
        
        if login_btn:
            if username_input.strip().lower() == "sercan" and password_input.strip() == "134679":
                st.session_state["logged_in"] = True
                st.session_state["username"] = "sercan"
                st.success("Giriş başarılı! Yönlendiriliyorsunuz...")
                st.rerun()
            else:
                st.error("Kullanıcı adı veya şifre hatalı!")
    st.stop()

# --- VERILERI YUKLEME ---
def load_records():
    try:
        response = supabase.table("notes_records").select("*").order("id", desc=True).execute()
        records = response.data if response and response.data else []
        for r in records:
            paths = []
            raw_paths = r.get("image_paths", [])
            if isinstance(raw_paths, str):
                try:
                    raw_paths = json.loads(raw_paths.replace("'", '"'))
                except Exception:
                    raw_paths = [raw_paths]
            if not isinstance(raw_paths, list):
                raw_paths = [raw_paths]
            for p in raw_paths:
                if p:
                    p_str = str(p).strip("[]'\" ")
                    if p_str.startswith("http"):
                        for sub_p in p_str.split("https://"):
                            if sub_p.strip():
                                clean_url = "https://" + sub_p.strip("[]'\" ,")
                                if clean_url not in paths:
                                    paths.append(clean_url)
            r["image_paths"] = paths
        return records
    except Exception as e:
        st.error(f"Veriler yüklenirken hata oluştu: {e}")
        return []

def save_images(uploaded_files):
    image_paths = []
    if uploaded_files:
        for uploaded_file in uploaded_files:
            try:
                file_ext = os.path.splitext(uploaded_file.name)[1]
                unique_filename = f"{uuid.uuid4().hex}_{int(datetime.now().timestamp())}{file_ext}"
                file_bytes = uploaded_file.getvalue()
                supabase.storage.from_(BUCKET_NAME).upload(
                    path=unique_filename,
                    file=file_bytes,
                    file_options={"content-type": uploaded_file.type}
                )
                clean_base_url = SUPABASE_URL.rstrip('/')
                public_url = f"{clean_base_url}/storage/v1/object/public/{BUCKET_NAME}/{unique_filename}"
                image_paths.append(public_url)
            except Exception as e:
                st.error(f"Resim yüklenirken hata oluştu: {e}")
    return image_paths

# --- SOL MENU / YONETIM PANELI ---
st.sidebar.title("🛠️ Yonetim Paneli")

with st.sidebar.expander("➕ Yeni Kayit / Hata Ekle", expanded=True):
    with st.form("add_form", clear_on_submit=True):
        new_name = st.text_input("Isim / Baslik:")
        new_date = st.text_input("Tarih:", value=datetime.now().strftime("%d/%m/%Y"))
        new_note = st.text_area("Not / Aciklama:")
        new_images = st.file_uploader("Gorsel Yukle:", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
        
        submit_btn = st.form_submit_button("Tabloya Ekle")
        if submit_btn:
            if not new_name.strip():
                st.warning("Lutfen bir isim/baslik girin.")
            else:
                uploaded_urls = save_images(new_images)
                new_record = {
                    "name": new_name,
                    "date": new_date,
                    "note": new_note,
                    "image_paths": uploaded_urls
                }
                try:
                    supabase.table("notes_records").insert(new_record).execute()
                    st.success("Kayit eklendi!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Hata: {e}")

with st.sidebar.expander("⚙️ Ayarlar", expanded=False):
    st.write("Aktif Kullanıcı: **sercan**")

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Cikis Yap"):
    st.session_state["logged_in"] = False
    st.rerun()

# --- ANA EKRAN ---
st.title("📝 Notes - Hata ve Kayit Takip Paneli")
records = load_records()

if records:
    st.subheader("📊 Istatistikler ve Grafikler")
    col_g1, col_g2 = st.columns(2)
    name_counts = {}
    detailed_data = []
    for r in records:
        name_val = str(r.get("name", "") or r.get("text", "Isimsiz")).strip() or "Isimsiz"
        name_counts[name_val] = name_counts.get(name_val, 0) + 1
        has_image = "Resimli Kayit" if [i for i in r.get("image_paths", []) if str(i).startswith("http")] else "Resimsiz Kayit"
        detailed_data.append({"Isimler": name_val, "Durum": has_image})
    
    chart_data1 = [{"Isimler": k, "Kayit Sayisi": v} for k, v in name_counts.items()]
    with col_g1:
        fig1 = px.bar(chart_data1, x="Isimler", y="Kayit Sayisi", title="👤 Toplam Kayitlar")
        st.plotly_chart(fig1, use_container_width=True)
    with col_g2:
        fig2 = px.histogram(detailed_data, x="Isimler", color="Durum", barmode="group", title="📈 Dagilim")
        st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")
st.subheader("🗂️ Tum Kayitlar")
search_query = st.text_input("🔍 Arama Yap:")
filtered_records = [r for r in records if search_query.lower() in str(r.get("name", "")).lower() or search_query.lower() in str(r.get("note", "")).lower()] if search_query else records

for r in filtered_records:
    rec_id = r.get("id")
    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    c1.markdown(f"**{r.get('name', 'Isimsiz')}**")
    if r.get('note'): c1.caption(r.get('note'))
    c2.write(r.get('date', ''))
    
    imgs = [i for i in r.get("image_paths", []) if str(i).startswith("http")]
    if imgs:
        with c3.expander(f"📷 ({len(imgs)})"):
            for idx, u in enumerate(imgs): c3.markdown(f"[Görsel {idx+1}]({u})")
    else:
        c3.text("-")
        
    if c4.button("Sil", key=f"del_{rec_id}"):
        supabase.table("notes_records").delete().eq("id", rec_id).execute()
        st.rerun()
    st.markdown("---")
