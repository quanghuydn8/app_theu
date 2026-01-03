import streamlit as st
import pandas as pd
from dotenv import load_dotenv

# 1. Load biến môi trường
load_dotenv()

# 2. Import các module
from modules.data_handler import (
    fetch_all_orders,
    kiem_tra_ket_noi,
    tai_danh_sach_trang_thai,
    luu_danh_sach_trang_thai
)
from modules.ui_components import (
    render_order_management,
    hien_thi_form_tao_don
)

# ============================================
# CẤU HÌNH TRANG & CSS
# ============================================
st.set_page_config(
    page_title="Hệ thống Quản lý Xưởng Thêu",
    page_icon="🧵",
    layout="wide",
    initial_sidebar_state="expanded"
)

def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        * { font-family: 'Inter', sans-serif; }
        .main { background-color: #f8f9fa; }
        div[data-testid="stMetric"], div.stButton > button { border-radius: 8px; }
        button[kind="primary"] { background-color: #2563eb; transition: 0.3s; }
        button[kind="primary"]:hover { background-color: #1d4ed8; box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3); }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# ============================================
# KIỂM TRA KẾT NỐI
# ============================================
if "db_connected" not in st.session_state:
    with st.spinner("🔄 Đang kết nối máy chủ dữ liệu..."):
        if kiem_tra_ket_noi():
            st.session_state.db_connected = True
        else:
            st.error("❌ MẤT KẾT NỐI SUPABASE! Vui lòng kiểm tra file .env hoặc mạng internet.")
            st.stop()

# ============================================
# SIDEBAR
# ============================================
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>🧵 Xưởng Thêu 4.0</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    page = st.radio(
        "Điều hướng",
        ["📊 Quản lý Đơn hàng", "📝 Tạo Đơn Mới", "⚙️ Cấu hình"],
        index=0
    )
    
    st.markdown("---")
    st.success("🟢 Hệ thống Online")

# ============================================
# MAIN ROUTER
# ============================================

if page == "📊 Quản lý Đơn hàng":
    df_orders = fetch_all_orders()
    render_order_management(df_orders)

elif page == "📝 Tạo Đơn Mới":
    hien_thi_form_tao_don()

elif page == "⚙️ Cấu hình":
    st.title("⚙️ Cấu hình Trạng thái")
    df_status = tai_danh_sach_trang_thai()
    edited_df = st.data_editor(df_status, num_rows="dynamic", use_container_width=True)
    
    if st.button("💾 Lưu Cấu Hình", type="primary"):
        if luu_danh_sach_trang_thai(edited_df):
            st.success("✅ Đã lưu cấu hình!")
            st.cache_data.clear()