import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import os

# Tải biến môi trường ngay đầu tiên
load_dotenv()

# Import các module
from modules.data_handler import (
    tai_du_lieu_csv, tao_du_lieu_mau, luu_du_lieu_csv, sync_images_with_dataframe
)
from modules.ui_components import render_order_management, render_ai_design
from modules.dashboard import render_dashboard

# ============================================
# CẤU HÌNH TRANG
# ============================================
st.set_page_config(
    page_title="App Quản lý Đơn hàng Thêu",
    page_icon="🧵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# CACHED DATA LOADER (TỐI ƯU HIỆU NĂNG)
# ============================================
@st.cache_data(ttl=300)  # Cache 5 phút
def load_data_cached():
    """Load dữ liệu với cache để tăng tốc"""
    df = tai_du_lieu_csv()
    if df is None:
        df = tao_du_lieu_mau()
        luu_du_lieu_csv(df)
    return df

# ============================================
# KHỞI TẠO SESSION STATE
# ============================================
if 'df_don_hang' not in st.session_state:
    st.session_state.df_don_hang = load_data_cached()
    sync_images_with_dataframe(st.session_state.df_don_hang)

# ============================================
# SIDEBAR ĐIỀU HƯỚNG
# ============================================
st.sidebar.title("🧵 Menu Điều hướng")

# Hiển thị trạng thái AI nếu đang xử lý
if st.session_state.get('is_processing_ai'):
    st.sidebar.warning(f"⏳ Đang xử lý AI cho đơn {st.session_state.processing_ma_don}...")
    st.sidebar.caption("Bạn có thể tiếp tục làm việc, AI đang chạy ngầm.")

# Menu chọn trang
page = st.sidebar.radio(
    "Chọn trang:",
    ["📦 Quản lý Đơn hàng", "🎨 Trợ lý AI Design", "📊 Dashboard"],
    index=0
)

st.sidebar.markdown("---")

# Thông tin phiên bản
st.sidebar.info("💡 **Phiên bản 3.3 Modular**\n\n- Kiến trúc module hóa\n- Dashboard thống kê\n- Tối ưu hiệu năng")

# ============================================
# ĐIỀU PHỐI TRANG (MAIN ROUTER)
# ============================================
if page == "📦 Quản lý Đơn hàng":
    render_order_management(st.session_state.df_don_hang)

elif page == "🎨 Trợ lý AI Design":
    render_ai_design(st.session_state.df_don_hang)

elif page == "📊 Dashboard":
    render_dashboard(st.session_state.df_don_hang)

# ============================================
# FOOTER
# ============================================
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray; padding: 20px;'>
        <p>🧵 <b>App Quản lý Đơn hàng Thêu</b> | Phiên bản 3.3 Modular | © 2025</p>
        <p>Được xây dựng bằng Streamlit 🎈 + Plotly 📊</p>
    </div>
    """,
    unsafe_allow_html=True
)
