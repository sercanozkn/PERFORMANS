import streamlit as st
import os
import json
import base64
import requests
import pandas as pd
from collections import Counter

# --- SAYFA AYARI ---
st.set_page_config(page_title="Notes - Hata Yönetim Sistemi", layout="wide")

# --- GİTHUB API SENKRONİZASYON FONKSİYONLARI ---
DATA_FILE = "records_data.json"
CONFIG_FILE = "config_data.json"

def get_github_secrets():
    try:
        token = st.secrets["GITHUB_TOKEN"]
        repo = st.secrets["REPO_NAME"]
        branch = st.secrets.get("BRANCH", "main")
        return token, repo, branch
    except:
        return None, None, None

def load_from_github(file_path):
    token, repo, branch = get_github_secrets()
    if not token or not repo:
        return None
    
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    params = {"ref": branch}
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        file_content_encoded = response.json().get("content", "")
        file_content_bytes = base64.b64decode(file_content_encoded)
        return json.loads(file_content_bytes.decode("utf-8"))
    return None

def save_to_github(file_path, data_dict_or_list, commit_message):
    token, repo, branch = get_github_secrets()
    
    # Her durumda yerel diske de yazalım (yedek olsun)
    if isinstance(data_dict_or_list, list):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data_dict_or_list, f, ensure_ascii=False, indent=4)
    else:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data_dict_or_list, f, ensure_ascii=False, indent=4)

    if not token or not repo:
        return  # Secrets tanımlı değilse sadece yerelde kalır
        
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    
    # Mevcut dosyanın SHA değerini almalıyız (GitHub API güncelleme için SHA ister)
    params = {"ref": branch}
    sha = None
    res = requests.get(url, headers=headers, params=params)
    if res.status_code == 200:
        sha = res.json().get("sha")
        
    # Veriyi base64 formatına çevir
    json_str = json.dumps(data_dict_or_list, ensure_ascii=False, indent=4)
    encoded_content = base64.b64encode(json_str.encode("utf-8")).decode("utf-8")
    
    payload = {
        "message": commit_message,
        "content": encoded_content,
        "branch": branch
    }
    if sha:
        payload["sha"] = sha
        
    requests.put(url, headers=headers, json=payload)

# --- VERİ VE AYARLARI YÜKLEME ---
def load_records():
    # Önce GitHub'dan çekmeyi dene, yoksa yerel dosyaya bak
    gh_data = load_from_github(DATA_FILE)
    if gh_data is not None:
        return gh_data
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def load_config():
    gh_data = load_from_github(CONFIG_FILE)
    if gh_data is not None:
        return gh_data
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"username": "admin", "password": "1234"}
    return {"username": "admin", "password": "1234"}

# --- OTURUM (SESSION STATE) BAŞLANGIÇ DEĞERLERİ ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

config = load_config()
if "username" not in st.session_state:
    st.session_state.username = config["username"]

if "password" not in st.session_state:
    st.session_state.password = config["password"]

if "records" not in st.session_state:
    st.session_state.records = load_records()

if "edit_index" not in st.session_state:
    st.session_state.edit_index = None

if "zoomed_image" not in st.session_state:
    st.session_state.zoomed_image = None

# --- KULLANICI GİRİŞ FONKSİYONU ---
def check_password():
    current_config = load_config()
    if not st.session_state.authenticated:
        st.title("🔒 Giriş Yap")
        st.write("Lütfen devam etmek için kullanıcı adı ve şifrenizi girin.")

        with st.form("login_form"):
            username = st.text_input("Kullanıcı Adı:")
            password = st.text_input("Şifre:", type="password")
            submit = st.form_submit_button("Giriş Yap")
            if submit:
                if username == current_config["username"] and password == current_config["password"]:
                    st.session_state.authenticated = True
                    st.success("Giriş başarılı! Yönlendiriliyorsunuz...")
                    st.rerun()
                else:
                    st.error("Kullanıcı adı veya şifre hatalı!")
        return False
    return True

if not check_password():
    st.stop()

# --- ANA UYGULAMA ---
UPLOAD_DIR = "uploaded_images"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# Notion Tarzı Üst Başlık
st.title("📄 Notes - Hata Takip Paneli")
st.markdown("---")

# --- KULLANICI AYARLARI ---
current_config = load_config()
with st.sidebar.expander("⚙️ Hesap Ayarları"):
    yeni_kullanici = st.text_input("Yeni Kullanıcı Adı", value=current_config["username"])
    yeni_sifre = st.text_input("Yeni Şifre", type="password")
    
    if st.button("Bilgileri Güncelle"):
        pass_to_save = yeni_sifre if yeni_sifre else current_config["password"]
        save_to_github(CONFIG_FILE, {"username": yeni_kullanici, "password": pass_to_save}, "Update config settings")
        st.session_state.username = yeni_kullanici
        st.session_state.password = pass_to_save
        st.success("Bilgiler kalıcı olarak güncellendi! Yeniden giriş yapın.")
        st.session_state.authenticated = False
        st.rerun()

if st.sidebar.button("Çıkış Yap"):
    st.session_state.authenticated = False
    st.rerun()

# --- BÜYÜTÜLEN RESİM İÇİN X İLE KAPATMA PENCERESİ ---
if st.session_state.zoomed_image:
    col_z1, col_z2 = st.columns([10, 1])
    with col_z1:
        st.markdown("### 🔍 Resim Büyük Önizleme")
    with col_z2:
        if st.button("❌ Kapat", key="close_zoom"):
            st.session_state.zoomed_image = None
            st.rerun()
            
    if os.path.exists(st.session_state.zoomed_image):
        st.image(st.session_state.zoomed_image, use_column_width=True)
    st.markdown("---")

# --- OPEN BUTONUNA BASILINCA AÇILAN DETAY VE DÜZENLEME PANELİ ---
if st.session_state.edit_index is not None:
    idx = st.session_state.edit_index
    if idx < len(st.session_state.records):
        current_record = st.session_state.records[idx]
        
        st.markdown(f"### 📂 Ayrıntı ve Düzenleme Ekranı: {current_record['name']}")
        st.info("Bu alanda seçilen kişinin kayıtlarını/hatalarını inceleyebilir ve güncelleyebilirsiniz.")
        
        with st.form("open_detail_edit_form"):
            edit_name = st.text_input("Text (İsim):", value=current_record.get("name", ""))
            
            try:
                default_date = pd.to_datetime(current_record.get("date")).date()
            except:
                default_date = pd.Timestamp.today().date()
                
            edit_date = st.date_input("Date (Tarih):", value=default_date, format="DD/MM/YYYY")
            edit_note = st.text_area("Not / İçerik:", value=current_record.get("note", ""))
            
            existing_paths = current_record.get("image_paths", [])
            if not existing_paths and current_record.get("image_path"):
                existing_paths = [current_record["image_path"]]
                
            if existing_paths:
                st.write(f"Mevcut Yüklü Resim Sayısı: {len(existing_paths)}")
                
            edit_uploaded_files = st.file_uploader("Files & media (Ekstra Yeni Resimler Ekle):", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
            
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                update_button = st.form_submit_button(label="Değişiklikleri Kaydet")
            with col_f2:
                cancel_button = st.form_submit_button(label="Kapat / Geri Dön")
                
            if update_button:
                if edit_name and edit_note:
                    image_paths = list(existing_paths)
                    if edit_uploaded_files:
                        for uf in edit_uploaded_files:
                            img_path = os.path.join(UPLOAD_DIR, uf.name)
                            with open(img_path, "wb") as f:
                                f.write(uf.getbuffer())
                            if img_path not in image_paths:
                                image_paths.append(img_path)
                    
                    has_img = len(image_paths) > 0
                    st.session_state.records[idx] = {
                        "name": edit_name,
                        "date": str(edit_date),
                        "note": edit_note,
                        "image_path": image_paths[0] if image_paths else None,
                        "image_paths": image_paths,
                        "has_image": has_img
                    }
                    save_to_github(DATA_FILE, st.session_state.records, f"Update record for {edit_name}")
                    st.session_state.edit_index = None
                    st.success("Kayıt başarıyla güncellendi ve GitHub'a kaydedildi!")
                    st.rerun()
                else:
                    st.warning("Lütfen İsim ve Not alanlarını boş bırakmayın.")
                    
            if cancel_button:
                st.session_state.edit_index = None
                st.rerun()
        st.markdown("---")

# --- YENİ KAYIT (HATA) EKLEME FORMU ---
with st.form("entry_form", clear_on_submit=True):
    st.subheader("➕ Yeni Kayıt / Hata Ekle")
    name = st.text_input("Text (İsim):")
    date = st.date_input("Date (Tarih):", format="DD/MM/YYYY")
    note = st.text_area("Not / Açıklama:")
    uploaded_files = st.file_uploader("Files & media (Resim Yükle):", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    
    submit_button = st.form_submit_button(label="Tabloya Ekle")
    
    if submit_button:
        if name and note:
            image_paths = []
            has_image = False
            
            if uploaded_files:
                for uploaded_file in uploaded_files:
                    image_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
                    with open(image_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    image_paths.append(image_path)
                has_image = True
            
            if "records" not in st.session_state:
                st.session_state.records = load_records()
                
            st.session_state.records.append({
                "name": name,
                "date": str(date),
                "note": note,
                "image_path": image_paths[0] if image_paths else None,
                "image_paths": image_paths,
                "has_image": has_image
            })
            save_to_github(DATA_FILE, st.session_state.records, f"Add new record for {name}")
            st.success(f"'{name}' için kayıt/hata başarıyla eklendi ve GitHub'a kaydedildi!")
            st.rerun()
        else:
            st.warning("Lütfen İsim ve Not alanlarını doldurun.")

# --- HATA ANALİZİ, ORTALAMA HESABI VE GRAFİK PANELİ ---
st.session_state.records = load_records() # Güncel verileri GitHub/Diskten oku
if st.session_state.records:
    st.markdown("---")
    st.subheader("📊 Hata Analizi ve Ortalama Paneli")
    
    all_names = [r["name"] for r in st.session_state.records]
    error_counts = Counter(all_names)
    df_errors = pd.DataFrame(list(error_counts.items()), columns=["İsim", "Hata Sayısı"])
    
    ortalama_hata = df_errors["Hata Sayısı"].mean()
    st.metric(label="📈 Kişi Başı Ortalama Hata (Kayıt) Sayısı", value=f"{ortalama_hata:.2f}")
    
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("### 🔴 En Çok Hata Yapanlar (Çoktan Aza)")
        df_max = df_errors.sort_values(by="Hata Sayısı", ascending=False).set_index("İsim")
        st.bar_chart(df_max)
            
    with col_g2:
        st.markdown("### 🟢 En Az Hata Yapanlar (Azdan Çoka)")
        df_min = df_errors.sort_values(by="Hata Sayısı", ascending=True).set_index("İsim")
        st.bar_chart(df_min)

# --- NOTION TARZI TABLO VE SATIR GÖRÜNÜMÜ ---
st.markdown("---")
st.subheader("📋 All notes (Kayıt ve Hata Tablosu)")

if st.session_state.records:
    header_col1, header_col2, header_col3, header_col4, header_col5 = st.columns([1.2, 2.5, 2.5, 1.5, 1.5])
    with header_col1:
        st.markdown("**İşlem (OPEN)**")
    with header_col2:
        st.markdown("**Files & media**")
    with header_col3:
        st.markdown("**Text (İsim / Not)**")
    with header_col4:
        st.markdown("**Date**")
    with header_col5:
        st.markdown("**Actions (Sil)**")
    st.markdown("---")

    for idx, record in enumerate(st.session_state.records):
        row_col1, row_col2, row_col3, row_col4, row_col5 = st.columns([1.2, 2.5, 2.5, 1.5, 1.5])
        
        with row_col1:
            if st.button("OPEN", key=f"open_{idx}"):
                st.session_state.edit_index = idx
                st.rerun()
                
        with row_col2:
            paths = record.get("image_paths", [])
            if not paths and record.get("image_path"):
                paths = [record["image_path"]]
            
            if paths:
                img_cols = st.columns(len(paths) if len(paths) <= 4 else 4)
                for p_idx, img_p in enumerate(paths):
                    if os.path.exists(img_p):
                        col_target = img_cols[p_idx % len(img_cols)]
                        with col_target:
                            st.image(img_p, width=50)
                            if st.button("🔍", key=f"zoom_{idx}_{p_idx}", help="Büyüt"):
                                st.session_state.zoomed_image = img_p
                                st.rerun()
            else:
                st.write("-")
                
        with row_col3:
            st.markdown(f"**{record['name']}**")
            st.caption(f"{record['note']}")
            
        with row_col4:
            st.write(record['date'])
            
        with row_col5:
            if st.button("🗑️ Sil", key=f"del_{idx}"):
                st.session_state.records.pop(idx)
                save_to_github(DATA_FILE, st.session_state.records, f"Delete record {idx}")
                st.rerun()
                
        st.markdown("---")
else:
    st.info("Henüz tabloya eklenmiş kayıt bulunmuyor.")
