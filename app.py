import os
import streamlit as st
import pandas as pd
from collections import Counter

# Sayfa yapılandırması
st.set_page_config(page_title="İsim, Not ve Resim Yöneticisi", page_icon="🔒", layout="centered")
if "username" not in st.session_state:
    st.session_state.username = "admin"
if "password" not in st.session_state:
    st.session_state.password = "1234"
# --- KULLANICI GİRİŞ KONTROLÜ ---
def check_password():
    """Kullanıcı adı ve şifre kontrolü yapar."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.title("🔒 Giriş Yap")
        st.write("Lütfen devam etmek için kullanıcı adı ve şifrenizi girin.")
        
        with st.form("login_form"):
            username = st.text_input("Kullanıcı Adı:")
            password = st.text_input("Şifre:", type="password")
            submit = st.form_submit_button("Giriş Yap")
            if submit:
                if username == st.session_state.username and password == st.session_state.password:
                    st.session_state.authenticated = True
                st.success("Giriş başarılı! Yönlendiriliyorsunuz...")
                st.rerun()
            else:
                st.error("Kullanıcı adı veya şifre hatalı!")  
         
    return True

# Eğer giriş yapılmadıysa programın geri kalanını çalıştırma
if not check_password():
    st.stop()

# --- GİRİŞ BAŞARILIYSA AÇILACAK ANA UYGULAMA ---
UPLOAD_DIR = "uploaded_images"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

st.title("📝 Kişi ve Not Yönetim Sistemi")
st.write("Bu program ile isim, not, isteğe bağlı resim kaydedebilir; kayıtları silebilir ve ayrı ayrı grafik analizleri yapabilirsiniz.")
# --- KULLANICI ADI VE ŞİFRE DEĞİŞTİRME PANELİ ---
with st.sidebar.expander("⚙️ Hesap Ayarları"):
        yeni_kullanici = st.text_input("Yeni Kullanıcı Adı", value=st.session_state.username)
        yeni_sifre = st.text_input("Yeni Şifre", type="password")
        
        if st.button("Bilgileri Güncelle"):
            st.session_state.username = yeni_kullanici
            if yeni_sifre:
                st.session_state.password = yeni_sifre
            st.success("Bilgiler güncellendi! Lütfen yeni bilgilerinizle tekrar giriş yapın.")
            st.session_state.authenticated = False
            st.rerun()
# Çıkış yap butonu (İsteğe bağlı)
if st.sidebar.button("Çıkış Yap"):
    st.session_state.authenticated = False
    st.rerun()

# --- VERİ EKLEME FORMU ---
with st.form("entry_form", clear_on_submit=True):
    st.subheader("Yeni Kayıt Ekle")
    name = st.text_input("İsim:")
    date = st.date_input("Tarih:",format="DD/MM/YYYY")
    note = st.text_area("Not:")
    uploaded_file = st.file_uploader("Bir Resim Yükle (İsteğe Bağlı)", type=["jpg", "jpeg", "png"])
    
    submit_button = st.form_submit_button(label="Kaydet")
    
    if submit_button:
        if name and note:
            image_path = None
            has_image = False
            if uploaded_file is not None:
                image_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
                with open(image_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                has_image = True
            
            if "records" not in st.session_state:
                st.session_state.records = []
                
            st.session_state.records.append({
                "name": name,
                 "date": str(date), 
                "note": note,
                "image_path": image_path,
                "has_image": has_image
            })
            st.success(f"'{name}' başarıyla kaydedildi!")
        else:
            st.warning("Lütfen İsim ve Not alanlarını doldurun.")

# --- GRAFİKLER BÖLÜMÜ ---
if "records" in st.session_state and st.session_state.records:
    st.markdown("---")
    st.subheader("📊 İstatistik ve Grafik Paneli")
    
    st.markdown("### 📈 1. Ana Grafik: Genel İsim Tekrar İstatistiği (Çoktan Aza)")
    all_names = [record["name"] for record in st.session_state.records]
    df_all = pd.DataFrame(list(Counter(all_names).items()), columns=["İsim", "Tekrar Sayısı"])
    df_all = df_all.sort_values(by="Tekrar Sayısı", ascending=False).set_index("İsim")
    st.bar_chart(df_all)
    
    resimli_records = [r for r in st.session_state.records if r["has_image"]]
    resimsiz_records = [r for r in st.session_state.records if not r["has_image"]]
    
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        st.markdown("### 🖼️ 2. Resimli Kayıtlar Grafiği")
        if resimli_records:
            img_names = [r["name"] for r in resimli_records]
            df_img = pd.DataFrame(list(Counter(img_names).items()), columns=["İsim", "Tekrar Sayısı"])
            df_img = df_img.sort_values(by="Tekrar Sayısı", ascending=False).set_index("İsim")
            st.bar_chart(df_img)
        else:
            st.info("Henüz resimli kayıt eklenmedi.")
            
    with col_g2:
        st.markdown("### 📄 3. Resimsiz Kayıtlar Grafiği")
        if resimsiz_records:
            no_img_names = [r["name"] for r in resimsiz_records]
            df_no_img = pd.DataFrame(list(Counter(no_img_names).items()), columns=["İsim", "Tekrar Sayısı"])
            df_no_img = df_no_img.sort_values(by="Tekrar Sayısı", ascending=False).set_index("İsim")
            st.bar_chart(df_no_img)
        else:
            st.info("Henüz resimsiz kayıt eklenmedi.")

# --- KAYITLARI LİSTELEME VE SİLME ---
st.markdown("---")
st.subheader("📋 Kayıtlı Veriler ve İşlemler")

if "records" in st.session_state and st.session_state.records:
    for i, record in enumerate(st.session_state.records):
        with st.container():
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                if record["image_path"] and os.path.exists(record["image_path"]):
                    st.image(record["image_path"], width=120)
                else:
                    st.info("Resim yok")
            with col2:
                st.markdown(f"### **{record['name']}**")
                st.write(f"**Not:** {record['note']}")
            with col3:
                if st.button("Sil", key=f"del_{i}"):
                    st.session_state.records.pop(i)
                    st.rerun()
            st.markdown("---")
else:
    st.info("Henüz kayıt eklenmedi.")
