import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image
import io
from modules.data_handler import (
    luu_du_lieu_csv, luu_anh_pet, luu_anh_design, tai_anh_design, 
    check_file_exists, tao_chi_tiet_don_hang
)
from modules.ai_logic import xuly_ai_gemini, gen_anh_mau_theu
from modules.notifier import send_telegram_notification

def tao_badge_trang_thai(trang_thai):
    mau_sac = {
        "New": "#808080", "Đã xác nhận": "#4CAF50", "Đang thiết kế": "#2196F3",
        "Chờ duyệt thiết kế": "#FF9800", "Đã duyệt thiết kế": "#4CAF50",
        "Đang sản xuất": "#9C27B0", "Hoàn thành sản xuất": "#00BCD4",
        "Đang đóng gói": "#FF5722", "Sẵn sàng giao hàng": "#8BC34A",
        "Đang giao hàng": "#FFC107", "Đã gửi vận chuyển": "#4CAF50"
    }
    color = mau_sac.get(trang_thai, "#808080")
    return f'<span style="background-color: {color}; color: white; padding: 5px 10px; border-radius: 5px; font-size: 12px; font-weight: bold;">{trang_thai}</span>'

def tao_mau_nen_trang_thai(val):
    mau_sac = {
        "New": "#808080", "Đã xác nhận": "#4CAF50", "Đang thiết kế": "#2196F3",
        "Chờ duyệt thiết kế": "#FF9800", "Đã duyệt thiết kế": "#4CAF50",
        "Đang sản xuất": "#9C27B0", "Hoàn thành sản xuất": "#00BCD4",
        "Đang đóng gói": "#FF5722", "Sẵn sàng giao hàng": "#8BC34A",
        "Đang giao hàng": "#FFC107", "Đã gửi vận chuyển": "#4CAF50"
    }
    color = mau_sac.get(val, "#808080")
    return f'background-color: {color}; color: white; font-weight: bold; text-align: center; padding: 8px; border-radius: 5px;'

def render_order_management(df):
    st.title("📦 Quản lý Đơn hàng Thêu")
    
    # Thống kê
    tong_don = len(df)
    da_xong = len(df[df['Trạng thái'] == 'Đã gửi vận chuyển'])
    col1, col2, col3 = st.columns(3)
    col1.metric("📊 Tổng đơn", tong_don)
    col2.metric("✅ Đã xong", da_xong)
    col3.metric("🚀 Đang xử lý", tong_don - da_xong)

    # Form tạo đơn mới (AI-Powered)
    with st.expander("➕ Tạo đơn hàng mới - AI Input Hub"):
        if 'form_data' not in st.session_state:
            st.session_state.form_data = {"ten_khach_hang": "", "so_dien_thoai": "", "dia_chi": "", "san_pham": "Áo thun thêu logo", "so_luong": 1, "tong_tien": 0, "yeu_cau_theu": "", "sku": "TS-DEN-M"}
        
        text_chat = st.text_area("💬 Dán chat chốt đơn")
        if st.button("🪄 Tự động trích xuất"):
            res = xuly_ai_gemini(text_chat)
            if res:
                st.session_state.form_data = res
                st.rerun()

        with st.form("tao_don"):
            c1, c2 = st.columns(2)
            ten = c1.text_input("Tên khách", st.session_state.form_data["ten_khach_hang"])
            sdt = c1.text_input("SĐT", st.session_state.form_data["so_dien_thoai"])
            sku = c2.text_input("Mã SKU", st.session_state.form_data["sku"])
            tt = c2.selectbox("Trạng thái", ["New", "Đang thiết kế", "Đang sản xuất"])
            if st.form_submit_button("💾 Lưu đơn hàng"):
                new_id = f"DH{str(len(df)+1).zfill(3)}"
                # Lấy các thông tin từ form
                san_pham_ten = st.session_state.form_data.get("san_pham", "Áo thun")
                tong_tien_format = f"{st.session_state.form_data.get('tong_tien', 0):,}đ"
                
                new_row = pd.DataFrame({"Mã đơn hàng": [new_id], "Khách hàng": [ten], "Sản phẩm": [san_pham_ten], "Số lượng": [1], "Mã SKU": [sku], "Trạng thái": [tt], "Ngày tạo": [datetime.now().strftime("%d/%m/%Y")], "Tổng tiền": [tong_tien_format]})
                st.session_state.df_don_hang = pd.concat([st.session_state.df_don_hang, new_row], ignore_index=True)
                
                if luu_du_lieu_csv(st.session_state.df_don_hang):
                    st.success(f"Đã lưu đơn {new_id}")
                    # Gửi thông báo Telegram khi tạo đơn mới thành công
                    msg = f"🚀 <b>ĐƠN HÀNG MỚI!</b>\n Mã: {new_id}\n Khách: {ten}\n SP: {san_pham_ten}\n Tổng: {tong_tien_format}"
                    send_telegram_notification(msg)
                    st.rerun()

    # Bảng danh sách
    st.write("### 📋 Danh sách đơn hàng")
    df_disp = df.drop(columns=['Anh_Pet', 'Anh_Design'], errors='ignore')
    st.dataframe(df_disp.style.applymap(tao_mau_nen_trang_thai, subset=['Trạng thái']), use_container_width=True)

    # Tra cứu chi tiết
    st.markdown("---")
    st.markdown("### 🔍 Tra cứu chi tiết")
    ma_don = st.selectbox("Chọn mã đơn", df['Mã đơn hàng'].tolist())
    row = df[df['Mã đơn hàng'] == ma_don].iloc[0]
    
    c_p, c_d = st.columns(2)
    with c_p:
        st.write("#### 📷 Ảnh Pet Gốc")
        if check_file_exists(row['Anh_Pet']):
            st.image(row['Anh_Pet'])
        else:
            up = st.file_uploader("Upload ảnh pet", key=f"up_{ma_don}")
            if up:
                path = luu_anh_pet(up, ma_don)
                df.at[df[df['Mã đơn hàng']==ma_don].index[0], 'Anh_Pet'] = path
                luu_du_lieu_csv(df)
                st.rerun()

    with c_d:
        st.write("#### 🎨 Mẫu Thêu AI")
        if check_file_exists(row['Anh_Design']):
            st.image(row['Anh_Design'])
            with open(row['Anh_Design'], 'rb') as f:
                st.download_button("Tải về", f, file_name=f"design_{ma_don}.png")
        
        if st.button("🎨 Gen thiết kế", key=f"gen_{ma_don}"):
            if check_file_exists(row['Anh_Pet']):
                st.session_state.is_processing_ai = True
                st.session_state.processing_ma_don = ma_don
                with st.spinner("AI đang xử lý..."):
                    pet_img = Image.open(row['Anh_Pet'])
                    style_img = Image.open("assets/style_ref.jpg")
                    data = gen_anh_mau_theu(pet_img, style_img)
                    if data:
                        path = luu_anh_design(data, ma_don)
                        df.at[df[df['Mã đơn hàng']==ma_don].index[0], 'Anh_Design'] = path
                        if luu_du_lieu_csv(df):
                            # Gửi thông báo Telegram khi thiết kế xong
                            msg = f"🎨 <b>THIẾT KẾ XONG!</b>\n Đã có mẫu thêu cho đơn <code>{ma_don}</code>. Mời sếp vào kiểm tra và duyệt!"
                            send_telegram_notification(msg)
                            
                        st.session_state.is_processing_ai = False
                        st.rerun()
            else: st.warning("Cần upload ảnh pet trước")

def render_ai_design(df):
    st.title("🎨 Trợ lý AI Design")
    ma_don = st.selectbox("Chọn đơn hàng", df['Mã đơn hàng'].tolist())
    row = df[df['Mã đơn hàng'] == ma_don].iloc[0]
    
    col_l, col_r = st.columns(2)
    with col_l:
        st.write("### 1️⃣ Ảnh gốc")
        if check_file_exists(row['Anh_Pet']): st.image(row['Anh_Pet'])
        else: st.info("Chưa có ảnh pet")
    
    with col_r:
        st.write("### 2️⃣ Kết quả AI")
        if st.button("🎨 Gen ảnh mẫu thêu", type="primary"):
            if check_file_exists(row['Anh_Pet']):
                st.session_state.is_processing_ai = True
                st.session_state.processing_ma_don = ma_don
                with st.spinner("AI đang vẽ..."):
                    pet_img = Image.open(row['Anh_Pet'])
                    style_img = Image.open("assets/style_ref.jpg")
                    data = gen_anh_mau_theu(pet_img, style_img)
                    if data:
                        path = luu_anh_design(data, ma_don)
                        df.at[df[df['Mã đơn hàng']==ma_don].index[0], 'Anh_Design'] = path
                        if luu_du_lieu_csv(df):
                            # Gửi thông báo Telegram khi thiết kế xong
                            msg = f"🎨 <b>THIẾT KẾ XONG!</b>\n Đã có mẫu thêu cho đơn <code>{ma_don}</code>. Mời sếp vào kiểm tra và duyệt!"
                            send_telegram_notification(msg)
                            
                        st.session_state.is_processing_ai = False
                        st.rerun()
            else: st.error("Thiếu ảnh gốc")
        
        if check_file_exists(row['Anh_Design']):
            st.image(row['Anh_Design'])

