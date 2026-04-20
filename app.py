import streamlit as st
import cv2
import numpy as np
import pandas as pd
from datetime import datetime
from PIL import Image
import re
import base64

# ===== CONFIG =====
st.set_page_config(page_title="QR Scanner Modern", layout="wide")

# ===== LOGIN SYSTEM =====
users = {
    "admin": "123",
    "petugas": "456"
}

if "login" not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    st.title("🔐 Login Sistem")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in users and users[username] == password:
            st.session_state.login = True
            st.success("Login berhasil!")
            st.rerun()
        else:
            st.error("Username / Password salah")

    st.stop()

# ===== SIDEBAR =====
def get_base64(file):
    with open(file, "rb") as f:
        return base64.b64encode(f.read()).decode()

img = get_base64("bg_sidebar.png")

st.sidebar.image("logo.png", width=100)
st.sidebar.markdown("## 📌 Sistem Scanner QR")

# 🔥 LOGOUT
if st.sidebar.button("Logout"):
    st.session_state.login = False
    st.rerun()

# 🔥 BACKGROUND SIDEBAR
st.markdown(f"""
<style>
section[data-testid="stSidebar"] {{
    background: linear-gradient(rgba(0,0,0,0.6), rgba(0,0,0,0.6)),
                url("data:image/png;base64,{img}");
    background-size: cover;
}}
section[data-testid="stSidebar"] * {{
    color: white !important;
}}
</style>
""", unsafe_allow_html=True)

# ===== DATA =====
try:
    df = pd.read_csv("data.csv")
except:
    df = pd.DataFrame(columns=[
        "Nama","NIM","Prodi","Pelayanan","Petugas","Status","Waktu"
    ])

# ===== FUNCTION =====
def clean_text(text):
    text = text.split(":", 1)[-1]
    return re.sub(r"[^a-zA-Z0-9\s]", "", text).strip()

def process_qr_data(data):
    try:
        p = data.split("|")
        if len(p) < 4:
            return None
        return clean_text(p[0]), clean_text(p[1]), clean_text(p[2]), clean_text(p[3])
    except:
        return None

def is_duplicate_today(nim, pelayanan):
    if df.empty:
        return False
    df["Waktu"] = pd.to_datetime(df["Waktu"])
    today = datetime.now().date()
    return any(
        (df["NIM"].astype(str)==str(nim)) &
        (df["Pelayanan"].astype(str)==str(pelayanan)) &
        (df["Waktu"].dt.date==today)
    )

def save_data(row):
    global df
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv("data.csv", index=False)

def generate_pdf(filtered_df, bulan):
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet

    doc = SimpleDocTemplate("laporan.pdf")
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"LAPORAN BULAN {bulan}", styles["Title"]))
    elements.append(Paragraph("<br/><br/>", styles["Normal"]))

    data = [["Nama","NIM","Prodi","Pelayanan","Petugas","Status","Waktu"]]
    for _,r in filtered_df.iterrows():
        data.append(list(r.astype(str)))

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.grey),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("GRID",(0,0),(-1,-1),1,colors.black),
        ("FONTSIZE",(0,0),(-1,-1),8)
    ]))

    elements.append(table)
    doc.build(elements)

# ===== UI =====
st.title("📷 DATA SCAN PELAYANAN")

menu = st.sidebar.selectbox("Menu", [
    "Scanner Camera",
    "Dashboard",
    "Data",
    "Cetak PDF"
])

# ===== SCANNER ONLINE =====
if menu == "Scanner Camera":
    st.subheader("📷 Scan QR (Online)")

    img_file = st.camera_input("Ambil foto QR")

    if img_file:
        bytes_data = np.asarray(bytearray(img_file.read()), dtype=np.uint8)
        img = cv2.imdecode(bytes_data, 1)

        # 🔥 PERBAIKI KONTRAS
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        detector = cv2.QRCodeDetector()

        data, _, _ = detector.detectAndDecode(img)

        if not data:
            data, _, _ = detector.detectAndDecode(gray)

        st.write("DEBUG QR:", data)

        if data:
            result = process_qr_data(data)

            if result:
                nama, nim, prodi, pelayanan = result

                st.success(f"✔ {nama}")

                petugas = st.selectbox("Petugas", ["Ikinta Winanto","Gatot Edy Susanto"])
                status = st.selectbox("Status", ["Diambil Sendiri","Orang Lain"])

                if st.button("Simpan"):
                    if not is_duplicate_today(nim, pelayanan):
                        save_data({
                            "Nama":nama,
                            "NIM":nim,
                            "Prodi":prodi,
                            "Pelayanan":pelayanan,
                            "Petugas":petugas,
                            "Status":status,
                            "Waktu":datetime.now()
                        })
                        st.success("Tersimpan!")
                    else:
                        st.warning("Sudah pernah hari ini")
            else:
                st.error("Format QR tidak sesuai")
        else:
            st.error("QR tidak terbaca")

# ===== DASHBOARD =====
elif menu == "Dashboard":
    if not df.empty:
        df["Waktu"] = pd.to_datetime(df["Waktu"])
        st.metric("Total Data", len(df))
    else:
        st.info("Belum ada data")

# ===== DATA =====
elif menu == "Data":
    if not df.empty:
        df = df.sort_values(by="Waktu", ascending=False)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Kosong")

# ===== PDF =====
elif menu == "Cetak PDF":
    if not df.empty:
        df["Waktu"] = pd.to_datetime(df["Waktu"])
        bulan = st.selectbox("Pilih Bulan", sorted(df["Waktu"].dt.month.unique()))
        filtered = df[df["Waktu"].dt.month==bulan]

        if st.button("Generate PDF"):
            generate_pdf(filtered, bulan)
            with open("laporan.pdf","rb") as f:
                st.download_button("Download PDF", f, "laporan.pdf")
    else:
        st.info("Belum ada data")
