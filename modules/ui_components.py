import streamlit as st
import pandas as pd
from datetime import datetime
import time

# Import từ các module khác
from modules.data_handler import (
    fetch_all_orders,
    get_order_details,
    save_full_order,
    update_order_status,
    tai_danh_sach_trang_thai,
    upload_image_to_supabase,
    update_item_image,
    kiem_tra_ket_noi
)
from modules.ai_logic import xuly_ai_gemini
from modules.notifier import send_telegram_notification

# --- HELPER FUNCTIONS ---
def get_status_color_map():
    df_status = tai_danh_sach_trang_thai()
    return dict(zip(df_status["Trạng thái"], df_status["Màu sắc"]))

def tao_badge_trang_thai(trang_thai):
    mau_sac_map = get_status_color_map()
    color = mau_sac_map.get(trang_thai, "#808080")
    return f'<span style="background-color: {color}; color: white; padding: 4px 10px; border-radius: 12px; font-size: 0.8em; font-weight: 600;">{trang_thai}</span>'

# ==============================================================================
# 1. FORM TẠO ĐƠN HÀNG (AUTO FILL SHOP)
# ==============================================================================
def hien_thi_form_tao_don():
    st.markdown("### 📝 Tạo Đơn Hàng Mới")

    # Khởi tạo Session State
    if 'temp_items' not in st.session_state:
        st.session_state.temp_items = [{"ten_sp": "", "mau": "", "size": "", "kieu_theu": "", "thong_tin_phu": ""}]
    
    if 'ai_order_data' not in st.session_state:
        st.session_state.ai_order_data = {}

    # --- KHU VỰC AI INPUT HUB ---
    with st.expander("✨ AI Trợ lý & Debugger", expanded=True):
        c_chat, c_btn = st.columns([4, 1])
        with c_chat:
            chat_content = st.text_area("Đoạn chat:", height=100, placeholder="Ví dụ: 'Khách Tùng... TGTD' hoặc 'IS'...", label_visibility="collapsed")
        
        with c_btn:
            st.write("")
            is_debug = st.toggle("🐞 Debug", value=True) 
            btn_extract = st.button("🪄 Trích xuất", type="primary", use_container_width=True)

        if btn_extract and chat_content:
            with st.spinner("AI đang xử lý..."):
                extracted_data, raw_text = xuly_ai_gemini(chat_content)
                
                # HIỂN THỊ DEBUG
                if is_debug:
                    st.divider()
                    d1, d2 = st.columns(2)
                    with d1:
                        st.markdown("**🔍 AI Raw Output:**")
                        st.code(raw_text, language="json")
                    with d2:
                        st.markdown("**🐍 Python Mapped Data:**")
                        st.json(extracted_data)

                if extracted_data:
                    st.session_state.ai_order_data = extracted_data
                    
                    # Lấy danh sách sản phẩm từ AI
                    ai_items = extracted_data.get("items", [])
                    
                    if ai_items and len(ai_items) > 0:
                        new_items_list = []
                        for item in ai_items:
                            new_items_list.append({
                                "ten_sp": item.get("ten_sp", ""),
                                "mau": item.get("mau", ""), 
                                "size": item.get("size", ""),
                                "kieu_theu": item.get("kieu_theu", ""),
                                "thong_tin_phu": item.get("ghi_chu_sp", "")
                            })
                        st.session_state.temp_items = new_items_list
                    else:
                        st.session_state.temp_items = [{"ten_sp": "", "mau": "", "size": "", "kieu_theu": "", "thong_tin_phu": ""}]
                    
                    if not is_debug:
                        st.success(f"✅ Đã tách {len(st.session_state.temp_items)} sản phẩm!")
                        time.sleep(0.5)
                        st.rerun()
                else:
                    st.error(f"Lỗi: {raw_text}")

    # --- FORM NHẬP LIỆU CHÍNH ---
    defaults = st.session_state.ai_order_data
    
    with st.form("form_tao_don_chinh"):
        c1, c2 = st.columns(2)
        with c1:
            ma_don = st.text_input("Mã đơn hàng", value=f"ORD-{datetime.now().strftime('%m%d-%H%M')}")
            ten_khach = st.text_input("Tên khách hàng", value=defaults.get("ten_khach_hang", ""))
            sdt = st.text_input("Số điện thoại", value=defaults.get("so_dien_thoai", ""))
            dia_chi = st.text_area("Địa chỉ giao hàng", value=defaults.get("dia_chi", ""), height=100)
        with c2:
            # --- LOGIC CHỌN SHOP (LINE) ---
            shop_options = ["TGTĐ", "Inside", "Lanh Canh"]
            
            # Lấy Shop từ AI, nếu không khớp danh sách thì mặc định Inside
            ai_shop_suggest = defaults.get("shop", "Inside")
            if ai_shop_suggest not in shop_options: 
                ai_shop_suggest = "Inside"
                
            selected_shop = st.selectbox("Shop (Line sản phẩm)", shop_options, index=shop_options.index(ai_shop_suggest))
            # ------------------------------
            
            ngay_dat = st.date_input("Ngày đặt", value=datetime.now())
            ngay_tra = st.date_input("Ngày trả dự kiến", value=datetime.now())
            httt = st.selectbox("Hình thức thanh toán", ["Ship COD", "Chuyển khoản", "Tiền mặt"])
            van_chuyen = st.selectbox("Vận chuyển", ["Thường", "Hỏa tốc", "Giao hàng tiết kiệm"])

        st.divider()
        st.markdown("#### 📦 Chi tiết sản phẩm")
        
        edited_items = st.data_editor(
            pd.DataFrame(st.session_state.temp_items),
            num_rows="dynamic",
            column_config={
                "ten_sp": st.column_config.TextColumn("Tên sản phẩm", required=True),
                "mau": "Màu",
                "size": "Size",
                "kieu_theu": "Kiểu thêu",
                "thong_tin_phu": "Ghi chú thêu"
            },
            key="editor_items_input",
            use_container_width=True
        )

        st.divider()
        c3, c4, c5 = st.columns(3)
        ai_tien = float(defaults.get("tong_tien", 0))
        ai_coc = float(defaults.get("da_coc", 0))
        
        with c3: thanh_tien = st.number_input("Tổng tiền", min_value=0.0, step=10000.0, value=ai_tien, format="%.0f")
        with c4: da_coc = st.number_input("Đã cọc", min_value=0.0, step=10000.0, value=ai_coc, format="%.0f")
        with c5: st.metric("Còn lại", f"{thanh_tien - da_coc:,.0f} đ")

        if st.form_submit_button("💾 LƯU ĐƠN HÀNG", type="primary", use_container_width=True):
            items_list = [i for i in edited_items.to_dict('records') if str(i['ten_sp']).strip() != ""]

            if not ten_khach or not ma_don:
                st.error("❌ Thiếu tên khách hoặc mã đơn!")
            else:
                order_data = {
                    "ma_don": ma_don,
                    "ten_khach": ten_khach,
                    "sdt": sdt,
                    "dia_chi": dia_chi,
                    "ngay_dat": ngay_dat.isoformat(),
                    "ngay_tra": ngay_tra.isoformat(),
                    "thanh_tien": thanh_tien,
                    "da_coc": da_coc,
                    "con_lai": thanh_tien - da_coc,
                    "httt": httt,
                    "van_chuyen": van_chuyen,
                    "shop": selected_shop,  # <--- LƯU TRƯỜNG SHOP
                    "trang_thai": "New" 
                }

                if save_full_order(order_data, items_list):
                    st.success(f"✅ Đã lưu đơn {ma_don}!")
                    msg = f"🚀 <b>ĐƠN MỚI ({selected_shop}): {ma_don}</b>\nKhách: {ten_khach}\nTổng: {thanh_tien:,.0f}đ"
                    send_telegram_notification(msg)
                    st.session_state.ai_order_data = {}
                    st.session_state.temp_items = [{"ten_sp": "", "mau": "", "size": "", "kieu_theu": "", "thong_tin_phu": ""}]
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Lỗi lưu Database!")

# ... (Phần Import và hàm hien_thi_form_tao_don GIỮ NGUYÊN không sửa) ...

# ==============================================================================
# 2. DASHBOARD QUẢN LÝ (EDITABLE + DYNAMIC SHOP UI)
# ==============================================================================
def render_order_management(df):
    st.markdown("<h2 style='text-align: center;'>📊 Dashboard Điều Hành</h2>", unsafe_allow_html=True)

    # --- 1. METRICS LOGIC ---
    if not df.empty:
        df['trang_thai'] = df['trang_thai'].astype(str).str.strip()
        
        tong_don = len(df)
        doanh_thu = df['thanh_tien'].sum() if 'thanh_tien' in df.columns else 0
        
        STATUS_DONE = ['Hoàn thành', 'Done', 'Đã giao', 'Completed', 'Success']
        STATUS_CANCEL = ['Đã hủy', 'Cancelled', 'Hủy', 'Fail', 'Aborted']
        
        da_xong = len(df[df['trang_thai'].isin(STATUS_DONE)])
        da_huy = len(df[df['trang_thai'].isin(STATUS_CANCEL)])
        dang_xu_ly = tong_don - da_xong - da_huy
    else:
        tong_don, doanh_thu, da_xong, dang_xu_ly, da_huy = 0, 0, 0, 0, 0

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Tổng đơn", tong_don)
    m2.metric("Đang xử lý", dang_xu_ly)
    m3.metric("Đã xong", da_xong)
    m4.metric("Đã hủy", da_huy)
    m5.metric("Doanh thu", f"{doanh_thu:,.0f}đ")
    
    st.divider()

    # --- 2. TABLE & FILTER ---
    df_status = tai_danh_sach_trang_thai()
    options_status = df_status["Trạng thái"].tolist()
    
    # Check cột shop
    if not df.empty and 'shop' not in df.columns: df['shop'] = "Inside"
    
    c_filter1, c_filter2 = st.columns([1, 1])
    status_filter = c_filter1.multiselect("Lọc trạng thái:", options_status)
    shop_filter = c_filter2.multiselect("Lọc Shop (Line):", ["TGTĐ", "Inside", "Lanh Canh"])

    if not df.empty:
        df_show = df.copy()
        if status_filter: df_show = df_show[df_show['trang_thai'].isin(status_filter)]
        if shop_filter: df_show = df_show[df_show['shop'].isin(shop_filter)]
        
        # Bảng hiển thị tóm tắt (chỉ xem, muốn sửa thì bấm chọn bên dưới)
        st.dataframe(
            df_show[["ma_don", "ten_khach", "shop", "sdt", "thanh_tien", "trang_thai"]],
            use_container_width=True,
            hide_index=True
        )

    # --- 3. DETAIL VIEW (EDITABLE) ---
    st.markdown("---")
    st.subheader("🔍 Chi tiết & Chỉnh sửa")
    
    if not df.empty:
        # Chọn đơn hàng
        ma_don_select = st.selectbox("Chọn mã đơn để xử lý:", df['ma_don'].unique())
        
        # Lấy dữ liệu tươi từ DB
        order_info, items = get_order_details(ma_don_select)
        
        if order_info:
            current_shop = order_info.get("shop", "Inside")
            
            # CHIA LAYOUT: TRÁI (INFO KHÁCH) - PHẢI (SẢN PHẨM)
            c_info, c_items = st.columns([1, 2], gap="large")
            
            # ================= CỘT TRÁI: EDIT THÔNG TIN KHÁCH =================
            with c_info:
                st.info("📝 **Thông tin đơn hàng**")
                
                with st.form(key="form_edit_info"):
                    # Các trường thông tin có thể sửa
                    new_shop = st.selectbox("Shop (Line)", ["TGTĐ", "Inside", "Lanh Canh"], index=["TGTĐ", "Inside", "Lanh Canh"].index(current_shop) if current_shop in ["TGTĐ", "Inside", "Lanh Canh"] else 1)
                    new_ten = st.text_input("Tên khách", value=order_info.get('ten_khach', ''))
                    new_sdt = st.text_input("SĐT", value=order_info.get('sdt', ''))
                    new_dia_chi = st.text_area("Địa chỉ", value=order_info.get('dia_chi', ''))
                    
                    c_d1, c_d2 = st.columns(2)
                    # Xử lý ngày tháng (chuyển str -> date)
                    try: 
                        d_dat = datetime.strptime(order_info.get('ngay_dat', ''), "%Y-%m-%d").date()
                    except: d_dat = datetime.now()
                    
                    try:
                        d_tra = datetime.strptime(order_info.get('ngay_tra', ''), "%Y-%m-%d").date()
                    except: d_tra = datetime.now()

                    new_ngay_dat = c_d1.date_input("Ngày đặt", value=d_dat)
                    new_ngay_tra = c_d2.date_input("Ngày trả", value=d_tra)
                    
                    # Tài chính
                    st.markdown("---")
                    st.caption("💰 Tài chính")
                    new_tong = st.number_input("Tổng tiền", value=float(order_info.get('thanh_tien', 0)), step=10000.0, format="%.0f")
                    new_coc = st.number_input("Đã cọc", value=float(order_info.get('da_coc', 0)), step=10000.0, format="%.0f")
                    st.markdown(f"**Còn lại: {new_tong - new_coc:,.0f} đ**")
                    
                    # Trạng thái & Vận chuyển
                    st.markdown("---")
                    current_st = order_info.get('trang_thai', 'New')
                    if current_st not in options_status: options_status.append(current_st)
                    new_trang_thai = st.selectbox("Trạng thái", options_status, index=options_status.index(current_st))
                    
                    # Nút Lưu
                    if st.form_submit_button("💾 Lưu thông tin", type="primary", use_container_width=True):
                        # Gói dữ liệu update
                        update_data = {
                            "shop": new_shop,
                            "ten_khach": new_ten,
                            "sdt": new_sdt,
                            "dia_chi": new_dia_chi,
                            "ngay_dat": new_ngay_dat.isoformat(),
                            "ngay_tra": new_ngay_tra.isoformat(),
                            "thanh_tien": new_tong,
                            "da_coc": new_coc,
                            "con_lai": new_tong - new_coc,
                            "trang_thai": new_trang_thai
                        }
                        
                        # Gọi hàm update từ data_handler (cần import thêm)
                        from modules.data_handler import update_order_info
                        if update_order_info(ma_don_select, update_data):
                            st.success("Đã cập nhật!")
                            send_telegram_notification(f"✏️ UPDATE {ma_don_select} ({new_shop}): {new_trang_thai}")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Lỗi cập nhật DB")

            # ================= CỘT PHẢI: SẢN PHẨM (DYNAMIC SHOP) =================
            with c_items:
                st.markdown(f"#### 🛒 Sản phẩm ({len(items)}) - {current_shop}")
                
                # Logic hiển thị sản phẩm giữ nguyên như cũ, chỉ thay đổi data đầu vào
                if items:
                    for item in items:
                        with st.container(border=True):
                            # 1. LINE LANH CANH: Chỉ hiện Text
                            if current_shop == "Lanh Canh":
                                st.write(f"**{item.get('ten_sp')}**")
                                st.caption(f"Màu: {item.get('mau')} | Size: {item.get('size')}")
                            
                            # 2. LINE TGTĐ & INSIDE
                            else:
                                cols = st.columns([1.5, 1, 1, 1])
                                with cols[0]:
                                    st.write(f"**{item.get('ten_sp')}**")
                                    st.caption(f"{item.get('mau')} / {item.get('size')}")
                                    st.caption(f"Yêu cầu: {item.get('kieu_theu')}")

                                # CỘT 1: ẢNH CHÍNH
                                with cols[1]:
                                    st.write("🖼️ Ảnh chính")
                                    if item.get('img_main'): st.image(item.get('img_main'), use_container_width=True)
                                    
                                    c_up, c_gen = st.columns([1, 1])
                                    with c_up:
                                        up_main = st.file_uploader("Up", key=f"up_main_{item.get('id')}", label_visibility="collapsed")
                                    
                                    with c_gen:
                                        if current_shop == "TGTĐ":
                                            if st.button("✨", key=f"gen_{item.get('id')}", help="AI Vẽ"):
                                                with st.spinner("AI Vẽ..."):
                                                    from modules.ai_logic import gen_anh_mau_theu
                                                    img_bytes = gen_anh_mau_theu(f"{item.get('ten_sp')} {item.get('kieu_theu')}")
                                                    if img_bytes:
                                                        url = upload_image_to_supabase(img_bytes, f"item_{item.get('id')}_main_ai.png")
                                                        if url and update_item_image(item.get('id'), url, "img_main"): st.rerun()

                                    if up_main:
                                        if st.button("☁️ Lưu", key=f"btn_main_{item.get('id')}"):
                                            url = upload_image_to_supabase(up_main, f"item_{item.get('id')}_main.png")
                                            if url and update_item_image(item.get('id'), url, "img_main"): st.rerun()

                                # CỘT 2: ẢNH PHỤ 1
                                with cols[2]:
                                    st.write("📸 Ảnh phụ 1")
                                    if item.get('img_sub1'): st.image(item.get('img_sub1'), use_container_width=True)
                                    up_sub1 = st.file_uploader("Up", key=f"up_sub1_{item.get('id')}", label_visibility="collapsed")
                                    if up_sub1:
                                        if st.button("☁️ Lưu", key=f"btn_sub1_{item.get('id')}"):
                                            url = upload_image_to_supabase(up_sub1, f"item_{item.get('id')}_sub1.png")
                                            if url and update_item_image(item.get('id'), url, "img_sub1"): st.rerun()

                                # CỘT 3: ẢNH PHỤ 2
                                with cols[3]:
                                    st.write("📂 Ảnh phụ 2")
                                    if item.get('img_sub2'): st.image(item.get('img_sub2'), use_container_width=True)
                                    up_sub2 = st.file_uploader("Up", key=f"up_sub2_{item.get('id')}", label_visibility="collapsed")
                                    if up_sub2:
                                        if st.button("☁️ Lưu", key=f"btn_sub2_{item.get('id')}"):
                                            url = upload_image_to_supabase(up_sub2, f"item_{item.get('id')}_sub2.png")
                                            if url and update_item_image(item.get('id'), url, "img_sub2"): st.rerun()
                else:
                    st.warning("Đơn này chưa có sản phẩm.")