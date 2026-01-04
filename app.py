import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import time

# 1. Load biến môi trường
load_dotenv()

# 2. Import các module
from modules.data_handler import (
    fetch_all_orders,
    kiem_tra_ket_noi,
    tai_danh_sach_trang_thai,
    luu_danh_sach_trang_thai,
    login_user  # <--- Import hàm Login mới
)
from modules.ui_components import (
    render_order_management,
    hien_thi_form_tao_don
)
from modules.trang_khach_hang import render_customer_page

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
        
        /* Style cho Form Login */
        .login-container {
            max-width: 400px;
            margin: auto;
            padding: 2rem;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# ============================================
# LOGIC ĐĂNG NHẬP (GATEKEEPER)
# ============================================
if 'user' not in st.session_state:
    st.session_state.user = None

def hien_thi_man_hinh_login():
    """Hiển thị form đăng nhập căn giữa"""
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2: # Căn giữa
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=80) # Icon User
        st.markdown("### 🔐 Đăng nhập Hệ thống")
        
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="admin@xuongtheu.com")
            password = st.text_input("Mật khẩu", type="password", placeholder="••••••")
            
            submit = st.form_submit_button("Đăng nhập", type="primary", use_container_width=True)
            
            if submit:
                if not email or not password:
                    st.warning("Vui lòng nhập đầy đủ thông tin!")
                else:
                    with st.spinner("Đang xác thực..."):
                        user = login_user(email, password)
                        if user:
                            st.session_state.user = user
                            st.success("Đăng nhập thành công!")
                            time.sleep(0.5)
                            st.rerun() # Load lại trang để vào App chính
                        else:
                            st.error("Sai email hoặc mật khẩu!")

# ============================================
# LOGIC CHÍNH CỦA APP (MAIN APP)
# ============================================
def main_app():
    # KIỂM TRA KẾT NỐI DB
    if "db_connected" not in st.session_state:
        if kiem_tra_ket_noi():
            st.session_state.db_connected = True
        else:
            st.error("❌ MẤT KẾT NỐI SUPABASE! Kiểm tra mạng hoặc file .env")
            st.stop()

    # SIDEBAR
    with st.sidebar:
        st.markdown("<h2 style='text-align: center;'>🧵 Xưởng Thêu 4.0</h2>", unsafe_allow_html=True)
        
        # Hiển thị thông tin người dùng
        user_email = st.session_state.user.email
        st.info(f"👤 Hi, {user_email.split('@')[0]}")
        
        st.markdown("---")
        
        page = st.radio(
            "Điều hướng",
            ["📊 Quản lý Đơn hàng", "📝 Tạo Đơn Mới", "👥 Quản lý Khách hàng", "⚙️ Cấu hình"],
            index=0
        )
        
        st.markdown("---")
        
        # Nút Đăng xuất
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.user = None
            st.rerun()

    # ROUTER
    if page == "📊 Quản lý Đơn hàng":
        df_orders = fetch_all_orders()
        render_order_management(df_orders)

    elif page == "📝 Tạo Đơn Mới":
        hien_thi_form_tao_don()

    elif page == "👥 Quản lý Khách hàng":
        render_customer_page()

    elif page == "⚙️ Cấu hình":
        st.title("⚙️ Cấu hình Trạng thái")
        df_status = tai_danh_sach_trang_thai()
        edited_df = st.data_editor(df_status, num_rows="dynamic", use_container_width=True)
        
        if st.button("💾 Lưu Cấu Hình", type="primary"):
            if luu_danh_sach_trang_thai(edited_df):
                st.success("✅ Đã lưu cấu hình!")
                st.cache_data.clear()

# ============================================
# ĐIỀU PHỐI (CONTROLLER)
# ============================================

# Nếu chưa đăng nhập -> Hiện Login
if not st.session_state.user:
    hien_thi_man_hinh_login()
# Nếu đã đăng nhập -> Hiện App
else:
    main_app()