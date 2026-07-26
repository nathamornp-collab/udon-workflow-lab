import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date

# ---------------------------------------------------------
# 1. ตั้งค่าหน้าตาของเว็บแอปพลิเคชัน
# ---------------------------------------------------------
st.set_page_config(
    page_title="ระบบติดตามงาน & ใบเสนอราคา | Quick Win",
    layout="wide"
)

# รายการสถานะงานมาตรฐาน
STATUS_OPTIONS = ["⏳ รอเสนอราคา", "⏳ รอติดตามใบเสนอราคา", "✅ ตกลงทำสัญญา/มัดจำแล้ว", "❌ ลูกค้าปฏิเสธ"]

# Custom CSS สำหรับ Mobile-friendly UX และ Job Cards
st.markdown("""
    <style>
    /* Styling สำหรับ Job Cards (งานค้าง) */
    .job-card {
        background-color: #f8f9fa;
        border: 2px solid #ff9800;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 10px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
    }
    .job-card h4 {
        color: #e65100;
        margin-top: 0;
        margin-bottom: 8px;
        font-size: 1.1rem;
    }
    .job-card p {
        margin: 4px 0;
        color: #333333;
        font-size: 0.95rem;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 🔗 การตั้งค่า URL เชื่อมต่อ Google Sheets & Webhook
# ---------------------------------------------------------
# 1. ลิงก์สำหรับ "อ่านข้อมูล" จาก Google Sheets
SHEET_READ_URL = "https://docs.google.com/spreadsheets/d/12KeIv0rd3EcpXlpghdlOjpfJsfsx-SRPQpELS9IKr1g/gviz/tq?tqx=out:csv"

# 2. ลิงก์ Webhook สำหรับ "บันทึกข้อมูล" จาก Google Apps Script
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycby-qnEhEijn6UJHfwVuxH_-lHp1BInJt2GO7XcyZ9pnxgVZCaS3Gn-K0OfgtIhiB9UTMQ/exec"

# ---------------------------------------------------------
# 2. ฟังก์ชันดึงข้อมูลจาก Google Sheets
# ---------------------------------------------------------
@st.cache_data(ttl=2)  # ตั้งค่าแคชให้รีเฟรชข้อมูลทุก 2 วินาที
def load_data(url):
    try:
        df_sheets = pd.read_csv(url)
        return df_sheets
    except Exception as e:
        return pd.DataFrame(columns=["รหัสงาน", "ชื่อลูกค้า", "เบอร์โทร", "ประเภทงาน", "มูลค่าเสนอราคา (บาท)", "สถานะงาน", "วันที่ต้องติดตาม"])

# โหลดข้อมูลเข้าสู่ตัวแปร df
df = load_data(SHEET_READ_URL)

# ---------------------------------------------------------
# 3. ส่วนหัวของโปรแกรม (Header)
# ---------------------------------------------------------
st.title("🎯 ระบบติดตามงานและลูกค้า (Customer & Job Follow-up)")
st.subheader("Udon Workflow Lab — อ่าน & บันทึกข้อมูลถาวร Real-time")
st.markdown("---")

# ---------------------------------------------------------
# 4. เมนูด้านข้าง: ฟอร์มบันทึกงานใหม่ลง Google Sheets
# ---------------------------------------------------------
st.sidebar.header("➕ บันทึกลูกค้า/งานใหม่จาก LINE")
with st.sidebar.form("new_job_form", clear_on_submit=True):
    customer_name = st.text_input("ชื่อลูกค้า / ชื่อร้าน")
    phone = st.text_input("เบอร์โทรศัพท์ / LINE ID")
    job_type = st.selectbox("ประเภทงาน", ["ร้านป้าย/โรงพิมพ์", "งานกระจก/อลูมิเนียม", "งานรับเหมา/ซ่อมบำรุง", "ติดตั้งแอร์/กล้อง", "อื่นๆ"])
    price = st.number_input("ประเมินมูลค่างาน (บาท)", min_value=0, step=1000, value=5000)
    status = st.selectbox("สถานะปัจจุบัน", STATUS_OPTIONS)
    follow_date = st.date_input("วันที่ต้องติดตามผลครั้งถัดไป", value=date.today())
    
    submitted = st.form_submit_button("💾 บันทึกข้อมูลลง Google Sheets")
    
    if submitted:
        if customer_name.strip() == "":
            st.sidebar.error("กรุณากรอกชื่อลูกค้าครับ!")
        else:
            # สร้างรหัสงานให้อัตโนมัติ (เช่น JOB-001, JOB-002)
            new_id = f"JOB-{len(df) + 1:03d}"
            
            # เตรียมแพ็กเกจข้อมูลส่งหา Webhook
            payload = {
                "action": "create",
                "job_id": new_id,
                "customer_name": customer_name,
                "phone": phone,
                "job_type": job_type,
                "price": price,
                "status": status,
                "follow_date": follow_date.strftime("%Y-%m-%d")
            }
            
            # ยิงข้อมูลไปหา Google Apps Script
            with st.spinner("กำลังบันทึกลง Google Sheets..."):
                try:
                    response = requests.post(WEBHOOK_URL, json=payload, timeout=10)
                    if response.status_code == 200:
                        st.sidebar.success(f"บันทึกรหัส {new_id} เรียบร้อยแล้ว!")
                        st.cache_data.clear()  # ล้างแคชเพื่อให้ตารางอัปเดตข้อมูลใหม่ทันที
                        st.rerun()
                    else:
                        st.sidebar.error("เกิดข้อผิดพลาดในการบันทึก กรุณาเช็กการตั้งค่า Webhook")
                except Exception as ex:
                    st.sidebar.error(f"การเชื่อมต่อผิดพลาด: {ex}")

# ---------------------------------------------------------
# 5. สรุปผลตัวเลขสำคัญเชิงธุรกิจ (KPI Dashboard Metrics)
# ---------------------------------------------------------
total_jobs = len(df) if not df.empty else 0
pending_jobs = len(df[df["สถานะงาน"].astype(str).str.contains("⏳")]) if total_jobs > 0 and "สถานะงาน" in df.columns else 0
total_value = pd.to_numeric(df["มูลค่าเสนอราคา (บาท)"], errors='coerce').sum() if total_jobs > 0 and "มูลค่าเสนอราคา (บาท)" in df.columns else 0

col1, col2, col3 = st.columns(3)
col1.metric("📋 งานทั้งหมดในระบบ", f"{total_jobs} รายการ")
col2.metric("⏳ งานค้างติดตามผล", f"{pending_jobs} รายการ", delta_color="inverse")
col3.metric("💰 มูลค่างานรวมใน Pipeline", f"{total_value:,.0f} บาท")

st.markdown("---")

# ---------------------------------------------------------
# 6. รายการงานที่ "ต้องติดตามวันนี้" (Action Items for Today)
# ---------------------------------------------------------
st.write("### 🚨 รายการที่ต้องโทรติดตามวันนี้ / งานเกินกำหนด")
today_str = date.today().strftime("%Y-%m-%d")

if total_jobs > 0 and "วันที่ต้องติดตาม" in df.columns and "สถานะงาน" in df.columns:
    due_today = df[(df["วันที่ต้องติดตาม"].astype(str) <= today_str) & (df["สถานะงาน"].astype(str).str.contains("⏳"))]
    if len(due_today) > 0:
        st.warning(f"พบงานค้างที่ต้องติดตาม {len(due_today)} รายการ ดังนี้:")
        for idx, row in due_today.iterrows():
            job_id = row.get('รหัสงาน', '')
            cust_name = row.get('ชื่อลูกค้า', '')
            phone = row.get('เบอร์โทร', '-')
            job_type = row.get('ประเภทงาน', '-')
            price_val = row.get('มูลค่าเสนอราคา (บาท)', 0)
            current_status = row.get('สถานะงาน', STATUS_OPTIONS[0])
            follow_d = row.get('วันที่ต้องติดตาม', '-')
            
            try:
                price_str = f"{float(price_val):,.0f} บาท"
            except (ValueError, TypeError):
                price_str = f"{price_val} บาท"
                
            st.markdown(f"""
                <div class="job-card">
                    <h4>📌 {job_id} - {cust_name}</h4>
                    <p>📞 <b>เบอร์โทร:</b> {phone}</p>
                    <p>🛠️ <b>ประเภทงาน:</b> {job_type}</p>
                    <p>💰 <b>มูลค่าเสนอราคา:</b> {price_str}</p>
                    <p>⏳ <b>สถานะงานปัจจุบัน:</b> {current_status}</p>
                    <p>📅 <b>วันที่ต้องติดตาม:</b> {follow_d}</p>
                </div>
            """, unsafe_allow_html=True)
            
            # ส่วนอัปเดตสถานะในแต่ละการ์ดงาน
            c_select, c_btn = st.columns([3, 2])
            with c_select:
                def_idx = STATUS_OPTIONS.index(current_status) if current_status in STATUS_OPTIONS else 0
                new_st = st.selectbox(
                    "เลือกสถานะใหม่",
                    options=STATUS_OPTIONS,
                    index=def_idx,
                    key=f"card_status_{job_id}_{idx}",
                    label_visibility="collapsed"
                )
            with c_btn:
                if st.button("🔄 อัปเดตสถานะ", key=f"card_btn_{job_id}_{idx}"):
                    update_payload = {
                        "action": "update",
                        "job_id": str(job_id).strip(),
                        "status": new_st
                    }
                    with st.spinner(f"กำลังอัปเดตรหัส {job_id}..."):
                        try:
                            resp = requests.post(WEBHOOK_URL, json=update_payload, timeout=10)
                            if resp.status_code == 200:
                                st.success(f"อัปเดตรหัส {job_id} เป็น {new_st} สำเร็จ!")
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error("เกิดข้อผิดพลาดในการบันทึกข้อมูล")
                        except Exception as ex:
                            st.error(f"การเชื่อมต่อผิดพลาด: {ex}")
            st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)
    else:
        st.success("🎉 ดีเยี่ยม! ไม่มีรายการงานค้างตกหล่นในวันนี้")
else:
    st.info("ยังไม่มีข้อมูลในระบบ ลองบันทึกงานแรกทางเมนูด้านซ้ายดูครับ")

st.markdown("---")

# ---------------------------------------------------------
# 7. แสดงตารางข้อมูลสดจาก Google Sheets & Quick Update
# ---------------------------------------------------------
st.write("### 📊 ตารางสถานะงานที่ดึงมาจาก Google Sheets")

# เครื่องมืออัปเดตสถานะด่วนสำหรับงานใดๆ ในตาราง
if not df.empty and "รหัสงาน" in df.columns:
    with st.expander("🛠️ อัปเดตสถานะงานด่วน (Quick Status Update)"):
        col_id, col_stat, col_btn = st.columns([2, 2, 1])
        with col_id:
            selected_job_id = st.selectbox("เลือกงานที่ต้องการอัปเดต:", df["รหัสงาน"].unique(), key="quick_update_job_id")
        with col_stat:
            current_job_row = df[df["รหัสงาน"] == selected_job_id]
            current_st = current_job_row["สถานะงาน"].values[0] if not current_job_row.empty and "สถานะงาน" in current_job_row.columns else STATUS_OPTIONS[0]
            def_idx = STATUS_OPTIONS.index(current_st) if current_st in STATUS_OPTIONS else 0
            quick_new_status = st.selectbox("สถานะใหม่:", STATUS_OPTIONS, index=def_idx, key="quick_update_status")
        with col_btn:
            st.write("") # เว้นระยะ
            st.write("")
            if st.button("🔄 อัปเดต", key="quick_update_submit"):
                update_payload = {
                    "action": "update",
                    "job_id": str(selected_job_id).strip(),
                    "status": quick_new_status
                }
                with st.spinner(f"กำลังอัปเดตรหัส {selected_job_id}..."):
                    try:
                        resp = requests.post(WEBHOOK_URL, json=update_payload, timeout=10)
                        if resp.status_code == 200:
                            st.success(f"อัปเดต {selected_job_id} เป็น {quick_new_status} เรียบร้อย!")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error("เกิดข้อผิดพลาดในการบันทึก")
                    except Exception as ex:
                        st.error(f"เชื่อมต่อผิดพลาด: {ex}")

# ช่องค้นหาข้อมูล (Search Bar) ด้านบนตาราง
search_query = st.text_input("🔍 ค้นหาข้อมูล (ชื่อลูกค้า หรือ เบอร์โทร):", placeholder="พิมพ์ชื่อลูกค้า หรือ เบอร์โทรศัพท์ เพื่อค้นหา...")

if search_query and not df.empty:
    filtered_df = df[
        df["ชื่อลูกค้า"].astype(str).str.contains(search_query, case=False, na=False) |
        df["เบอร์โทร"].astype(str).str.contains(search_query, case=False, na=False)
    ]
else:
    filtered_df = df

st.dataframe(filtered_df, use_container_width=True)

if st.button("🔄 ดึงข้อมูลล่าสุด"):
    st.cache_data.clear()
    st.rerun()
