import streamlit as st
import pandas as pd
from datetime import datetime
import time
import requests
import io
import streamlit.components.v1 as components # Thư viện để hiện khung in

# Import từ các module khác
from modules.data_handler import (
    fetch_all_orders,
    get_order_details,
    save_full_order,
    update_order_status,
    tai_danh_sach_trang_thai,
    upload_image_to_supabase,
    update_item_image,
    kiem_tra_ket_noi,
    upload_multiple_files_to_supabase,
    update_order_info,
    lay_danh_sach_khach_hang
)
from modules.ai_logic import xuly_ai_gemini, gen_anh_mau_theu, generate_image_from_ref
from modules.notifier import send_telegram_notification
from modules.printer import generate_print_html # Hàm tạo HTML in ấn

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
                    
                    # Cập nhật luôn vào Form Inputs
                    st.session_state.form_ten_khach = extracted_data.get("ten_khach_hang", "")
                    st.session_state.form_sdt = extracted_data.get("so_dien_thoai", "")
                    st.session_state.form_dia_chi = extracted_data.get("dia_chi", "")

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

    # --- AUTOCOMPLETE LOGIC ---
    # --- AUTOCOMPLETE LOGIC (Simple Selectbox) ---
    st.markdown("##### 🕵️ Thông tin khách hàng")
    
    # Lấy danh sách khách hàng
    df_customers = lay_danh_sach_khach_hang()
    
    customer_options = []
    if not df_customers.empty:
        # Format: "SĐT | Tên (Địa chỉ)" -> Ưu tiên SĐT ở đầu để search số chính xác hơn
        customer_options = df_customers.apply(lambda x: f"{x['sdt']} | {x['ho_ten']} ({x['dia_chi']})", axis=1).tolist()
    
    def on_quick_select():
        selected_val = st.session_state.get("quick_select_box")
        if selected_val:
            # Parse: "0909xxx | Name (Addr)"
            parts = selected_val.split(" | ")
            if len(parts) >= 1:
                s_sdt = parts[0]
                found = df_customers[df_customers['sdt'] == s_sdt]
                if not found.empty:
                    st.session_state.form_ten_khach = found.iloc[0]['ho_ten']
                    st.session_state.form_sdt = found.iloc[0]['sdt']
                    st.session_state.form_dia_chi = found.iloc[0]['dia_chi']

    st.selectbox(
        "🔍 Chọn khách cũ (Gõ tên hoặc SĐT để tìm)",
        options=customer_options,
        index=None,
        placeholder="Nhập tên/SĐT...",
        key="quick_select_box",
        on_change=on_quick_select
    )

    # --- FORM NHẬP LIỆU CHÍNH ---
    defaults = st.session_state.ai_order_data
    
    with st.form("form_tao_don_chinh"):
        c1, c2 = st.columns(2)
        with c1:
            ma_don = st.text_input("Mã đơn hàng", value=f"ORD-{datetime.now().strftime('%m%d-%H%M')}")
            
            # Ten Khach Hang
            # Sử dụng key để có thể update từ code
            if "form_ten_khach" not in st.session_state: st.session_state.form_ten_khach = defaults.get("ten_khach_hang", "")
            ten_khach = st.text_input("Tên khách hàng", key="form_ten_khach")

            # So Dien Thoai
            if "form_sdt" not in st.session_state: st.session_state.form_sdt = defaults.get("so_dien_thoai", "")
            sdt = st.text_input("Số điện thoại", key="form_sdt")

            # Dia Chi
            if "form_dia_chi" not in st.session_state: st.session_state.form_dia_chi = defaults.get("dia_chi", "")
            dia_chi = st.text_area("Địa chỉ giao hàng", height=68, key="form_dia_chi")
        with c2:
            # --- LOGIC CHỌN SHOP (LINE) ---
            shop_options = ["TGTĐ", "Inside", "Lanh Canh"]
            
            # Lấy Shop từ AI, nếu không khớp danh sách thì mặc định Inside
            ai_shop_suggest = defaults.get("shop", "Inside")
            if ai_shop_suggest not in shop_options: 
                ai_shop_suggest = "Inside"
                
            selected_shop = st.selectbox("Shop (Line sản phẩm)", shop_options, index=shop_options.index(ai_shop_suggest))
            
            # --- [MỚI] MAP NGÀY THÁNG TỪ AI ---
            # Xử lý ngày trả (String -> Datetime)
            ai_ngay_tra_str = defaults.get("ngay_tra")
            val_ngay_tra = datetime.now() # Mặc định là hôm nay
            
            if ai_ngay_tra_str:
                try:
                    # Convert chuỗi "2026-01-20" thành đối tượng datetime
                    val_ngay_tra = datetime.strptime(ai_ngay_tra_str, "%Y-%m-%d")
                except:
                    pass # Nếu lỗi format thì giữ nguyên mặc định
            
            ngay_dat = st.date_input("Ngày đặt", value=datetime.now())
            # --- [MỚI] CHECKBOX HẸN NGÀY ---
            c_date, c_check = st.columns([2, 1])
            
            # Lấy giá trị từ AI (True/False)
            ai_co_hen = defaults.get("co_hen_ngay", False)
            
            with c_date:
                ngay_tra = st.date_input("Ngày trả dự kiến", value=val_ngay_tra)
            with c_check:
                st.write("") # Spacer cho thẳng hàng
                st.write("") 
                co_hen_ngay = st.checkbox("🚨 Khách hẹn?", value=ai_co_hen, help="Tích vào nếu khách yêu cầu ngày cố định/gấp")
            
            # --- [MỚI] MAP THANH TOÁN & VẬN CHUYỂN ---
            opts_httt = ["Ship COD 💵", "0đ 📷"]
            opts_vc = ["Thường", "Xe Ôm 🏍", "Bay ✈"]
            
            # Lấy giá trị từ AI
            ai_httt = defaults.get("httt", "Ship COD 💵")
            ai_vc = defaults.get("van_chuyen", "Thường")
            
            # Tìm vị trí (index) trong danh sách options
            # Nếu AI trả về "Chuyển khoản", nó sẽ tìm thấy index là 1
            idx_httt = opts_httt.index(ai_httt) if ai_httt in opts_httt else 0
            idx_vc = opts_vc.index(ai_vc) if ai_vc in opts_vc else 0

            httt = st.selectbox("Hình thức thanh toán", opts_httt, index=idx_httt) # <--- Đã map index
            van_chuyen = st.selectbox("Vận chuyển", opts_vc, index=idx_vc)         # <--- Đã map index

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
                    "trang_thai": "New",
                    "co_hen_ngay": co_hen_ngay
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

# ==============================================================================
# 2. DASHBOARD QUẢN LÝ (CRM SEARCH + DYNAMIC UI)
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
    
    c_filter1, c_filter2, c_filter3 = st.columns([1, 1, 0.5]) # Chia lại cột
    
    status_filter = c_filter1.multiselect("Lọc trạng thái:", options_status)
    shop_filter = c_filter2.multiselect("Lọc Shop:", ["TGTĐ", "Inside", "Lanh Canh"])
    
    # Checkbox lọc đơn hẹn
    loc_hen_ngay = c_filter3.checkbox("🚨 Chỉ đơn hẹn", value=False)

    if not df.empty:
        df_show = df.copy()
        if status_filter: df_show = df_show[df_show['trang_thai'].isin(status_filter)]
        if shop_filter: df_show = df_show[df_show['shop'].isin(shop_filter)]
        if loc_hen_ngay:
            # Lọc những dòng co_hen_ngay == True
            if 'co_hen_ngay' in df_show.columns:
                df_show = df_show[df_show['co_hen_ngay'] == True]
        
        # Bảng hiển thị tóm tắt
        st.dataframe(
            df_show[["ma_don", "ten_khach", "shop", "sdt", "thanh_tien", "trang_thai"]],
            use_container_width=True,
            hide_index=True
        )

    # --- 3. DETAIL VIEW (CRM SEARCH ENGINE) ---
    st.markdown("---")
    st.subheader("🔍 Chi tiết & Chỉnh sửa")
    
    if not df.empty:
        # === CRM SEARCH LOGIC ===
        c_search, c_select = st.columns([1, 2])
        
        with c_search:
            search_term = st.text_input("🔎 Tìm kiếm (Tên, SĐT, Mã):", placeholder="Gõ tên khách hoặc SĐT...")
        
        # Logic lọc dữ liệu
        df_filtered = df.copy()
        if search_term:
            term = search_term.lower()
            # Lọc trên 3 trường chính
            m1 = df_filtered['ma_don'].astype(str).str.lower().str.contains(term)
            m2 = df_filtered['ten_khach'].astype(str).str.lower().str.contains(term)
            m3 = df_filtered['sdt'].astype(str).str.lower().str.contains(term)
            df_filtered = df_filtered[m1 | m2 | m3]
        
        if df_filtered.empty:
            st.warning("⚠️ Không tìm thấy đơn hàng nào phù hợp.")
            return # Dừng render nếu không có data

        # Tạo Label thông minh cho Selectbox: "ORD-XXX | Tên Khách | SĐT"
        df_filtered['display_label'] = df_filtered.apply(
            lambda x: f"{x['ma_don']} | {x.get('ten_khach', 'No Name')} | {x.get('sdt', '')}", axis=1
        )
        
        with c_select:
            # Selectbox hiển thị danh sách đã lọc
            selected_label = st.selectbox(
                f"Chọn đơn hàng ({len(df_filtered)} kết quả):", 
                df_filtered['display_label'].unique()
            )

        # Trích xuất lại mã đơn từ label đã chọn
        if selected_label:
            ma_don_select = selected_label.split(" | ")[0] # Lấy phần mã đơn đầu tiên
            
            # --- PHẦN CODE XỬ LÝ CHI TIẾT ---
            render_order_detail_view(ma_don_select)

def render_order_detail_view(ma_don):
    # Lấy dữ liệu tươi từ DB
    order_info, items = get_order_details(ma_don)
    
    if order_info:
        current_shop = order_info.get("shop", "Inside")
        
        # CHIA LAYOUT: TRÁI (INFO KHÁCH) - PHẢI (SẢN PHẨM)
        c_info, c_items = st.columns([1, 2], gap="large")
        
        # ================= CỘT TRÁI: EDIT THÔNG TIN KHÁCH =================
        with c_info:
            st.info("📝 **Thông tin đơn hàng**")
            
            with st.form(key=f"form_edit_info_{ma_don}"): # Thêm key động
                # Các trường thông tin có thể sửa
                shop_opts = ["TGTĐ", "Inside", "Lanh Canh"]
                idx_shop = shop_opts.index(current_shop) if current_shop in shop_opts else 1
                
                new_shop = st.selectbox("Shop (Line)", shop_opts, index=idx_shop)
                new_ten = st.text_input("Tên khách", value=order_info.get('ten_khach', ''))
                new_sdt = st.text_input("SĐT", value=order_info.get('sdt', ''))
                new_dia_chi = st.text_area("Địa chỉ", value=order_info.get('dia_chi', ''))
                
                c_d1, c_d2 = st.columns(2)
                # Xử lý ngày tháng
                try: d_dat = datetime.strptime(order_info.get('ngay_dat', '')[:10], "%Y-%m-%d").date()
                except: d_dat = datetime.now()
                try: d_tra = datetime.strptime(order_info.get('ngay_tra', '')[:10], "%Y-%m-%d").date()
                except: d_tra = datetime.now()

                new_ngay_dat = c_d1.date_input("Ngày đặt", value=d_dat)
                new_ngay_tra = c_d2.date_input("Ngày trả", value=d_tra)
                
                # Tài chính
                st.markdown("---")
                new_tong = st.number_input("Tổng tiền", value=float(order_info.get('thanh_tien', 0)), step=10000.0, format="%.0f")
                new_coc = st.number_input("Đã cọc", value=float(order_info.get('da_coc', 0)), step=10000.0, format="%.0f")
                st.caption(f"Còn lại: {new_tong - new_coc:,.0f} đ")
                
                # Trạng thái
                st.markdown("---")
                df_status = tai_danh_sach_trang_thai()
                options_status = df_status["Trạng thái"].tolist()
                
                current_st = order_info.get('trang_thai', 'New')
                if current_st not in options_status: options_status.append(current_st)
                new_trang_thai = st.selectbox("Trạng thái", options_status, index=options_status.index(current_st))
                
                # Nút Lưu Info
                if st.form_submit_button("💾 Lưu thông tin", type="primary"):
                    update_data = {
                        "shop": new_shop, "ten_khach": new_ten, "sdt": new_sdt, 
                        "dia_chi": new_dia_chi, "ngay_dat": new_ngay_dat.isoformat(), 
                        "ngay_tra": new_ngay_tra.isoformat(), "thanh_tien": new_tong, 
                        "da_coc": new_coc, "con_lai": new_tong - new_coc, "trang_thai": new_trang_thai
                    }
                    if update_order_info(ma_don, update_data):
                        st.success("Đã cập nhật!"); time.sleep(0.5); st.rerun()

            # --- NÚT IN PHIẾU (Đã thêm mới) ---
            st.markdown("---")
            if st.button("🖨️ XEM & IN PHIẾU", use_container_width=True, key=f"btn_print_{ma_don}"):
                html_content = generate_print_html(order_info, items)
                
                @st.dialog("🖨️ Xem trước bản in", width="large")
                def show_print_preview(html):
                    st.caption("Bấm nút 'IN PHIẾU NGAY' màu xanh bên dưới để kết nối máy in.")
                    components.html(html, height=800, scrolling=True)
                
                show_print_preview(html_content)

        # ================= CỘT PHẢI: SẢN PHẨM (DYNAMIC SHOP) =================
        with c_items:
            st.markdown(f"#### 🛒 Sản phẩm ({len(items)}) - {current_shop}")
            if items:
                for item in items:
                    with st.container(border=True):
                        # 1. LINE LANH CANH
                        if current_shop == "Lanh Canh":
                            st.write(f"**{item.get('ten_sp')}** | {item.get('mau')} | {item.get('size')}")
                        
                        # 2. LINE TGTĐ & INSIDE
                        else:
                            # CHIA CỘT: [Info] | [Ảnh Input] | [Ảnh Output] | [File Design]
                            cols = st.columns([1.2, 1, 1, 1])
                            
                            # --- Info ---
                            with cols[0]:
                                st.write(f"**{item.get('ten_sp')}**")
                                st.caption(f"{item.get('mau')} / {item.get('size')}")
                                st.caption(f"YC: {item.get('kieu_theu')}")

                            # --- CỘT 1: ẢNH GỐC (INPUT) ---
                            with cols[1]:
                                st.write("1️⃣ Ảnh Gốc")
                                if item.get('img_main'): st.image(item.get('img_main'), use_container_width=True)
                                
                                up_main = st.file_uploader("Up gốc", key=f"u_m_{item.get('id')}", label_visibility="collapsed")
                                if up_main and st.button("Lưu Gốc", key=f"s_m_{item.get('id')}"):
                                    url = upload_image_to_supabase(up_main, f"item_{item.get('id')}_main.png")
                                    if url and update_item_image(item.get('id'), url, "img_main"): st.rerun()

                            # --- CỘT 2: ẢNH AI / PET (OUTPUT) ---
                            with cols[2]:
                                lbl_col2 = "2️⃣ Kết quả AI" if current_shop == "TGTĐ" else "📸 Ảnh Pet"
                                st.write(lbl_col2)
                                if item.get('img_sub1'): st.image(item.get('img_sub1'), use_container_width=True)
                                
                                # Nút GEN AI chỉ hiện ở TGTĐ
                                if current_shop == "TGTĐ":
                                    if st.button("✨ Gen AI", key=f"ai_{item.get('id')}", type="primary"):
                                        input_bytes = None
                                        if up_main: input_bytes = up_main.getvalue()
                                        elif item.get('img_main'):
                                            try: input_bytes = requests.get(item.get('img_main')).content
                                            except: pass
                                        
                                        if input_bytes:
                                            with st.spinner("AI đang vẽ..."):
                                                ai_bytes = gen_anh_mau_theu(input_bytes, f"{item.get('ten_sp')} {item.get('kieu_theu')}")
                                                if ai_bytes:
                                                    url = upload_image_to_supabase(ai_bytes, f"item_{item.get('id')}_ai.png")
                                                    if url and update_item_image(item.get('id'), url, "img_sub1"): st.rerun()
                                                else: st.error("AI lỗi")
                                        else: st.warning("Cần ảnh gốc!")
                                else:
                                    # Inside: Upload thủ công
                                    up_sub1 = st.file_uploader("Up Pet", key=f"u_s1_{item.get('id')}", label_visibility="collapsed")
                                    if up_sub1 and st.button("Lưu Pet", key=f"s_s1_{item.get('id')}"):
                                        url = upload_image_to_supabase(up_sub1, f"item_{item.get('id')}_pet.png")
                                        if url and update_item_image(item.get('id'), url, "img_sub1"): st.rerun()

                            # --- CỘT 3: FILE DESIGN / KHÁC ---
                            with cols[3]:
                                lbl_col3 = "3️⃣ File Design" if current_shop == "TGTĐ" else "📂 Ảnh Khác"
                                st.write(lbl_col3)
                                
                                if current_shop == "TGTĐ":
                                    if item.get('img_sub2'):
                                        links = item.get('img_sub2').split(' ; ')
                                        for i, l in enumerate(links): st.markdown(f"⬇️ [File {i+1}]({l})")
                                    
                                    up_files = st.file_uploader("Up Files", key=f"u_f_{item.get('id')}", accept_multiple_files=True, label_visibility="collapsed")
                                    if up_files and st.button("Lưu Files", key=f"s_f_{item.get('id')}"):
                                        s = upload_multiple_files_to_supabase(up_files, item.get('id'))
                                        if s and update_item_image(item.get('id'), s, "img_sub2"): st.rerun()
                                else:
                                    if item.get('img_sub2'): st.image(item.get('img_sub2'), use_container_width=True)
                                    up_sub2 = st.file_uploader("Up Khác", key=f"u_s2_{item.get('id')}", label_visibility="collapsed")
                                    if up_sub2 and st.button("Lưu Khác", key=f"s_s2_{item.get('id')}"):
                                        url = upload_image_to_supabase(up_sub2, f"item_{item.get('id')}_other.png")
                                        if url and update_item_image(item.get('id'), url, "img_sub2"): st.rerun()
            else:
                st.warning("Đơn này chưa có sản phẩm.")

# ==============================================================================
# 3. TRANG AI EDIT ẢNH (GEN AI)
# ==============================================================================
def render_ai_image_page():
    st.markdown("<h2 style='text-align: center;'>🎨 AI Edit Ảnh (Beta)</h2>", unsafe_allow_html=True)
    st.caption("Sử dụng model 'gemini-3-pro-image-preview' để chỉnh sửa ảnh dựa trên Prompt.")

    c_left, c_right = st.columns([1, 2])
    
    with c_left:
        st.info("1. Chọn ảnh gốc (Input Link/Upload)")
        uploaded_file = st.file_uploader("Upload ảnh gốc", type=['png', 'jpg', 'jpeg'])
        
        if uploaded_file:
            st.image(uploaded_file, caption="Ảnh gốc", use_container_width=True)
            
    with c_right:
        st.info("2. Nhập yêu cầu chỉnh sửa (Prompt)")
        prompt_input = st.text_area(
            "Mô tả thay đổi:", 
            height=150,
            placeholder="Ví dụ:\n- Đổi màu áo sang màu xanh dương\n- Thêm họa tiết hoa văn lên tay áo\n- Biến đổi thành tranh vẽ chì...",
            value="đổi màu áo sang màu xanh..."
        )
        
        if st.button("🚀 TẠO ẢNH MỚI (GENERATE)", type="primary", use_container_width=True):
            if uploaded_file and prompt_input:
                with st.spinner("AI đang vẽ... (Có thể mất 10-20s)"):
                    # Gọi hàm xử lý
                    input_bytes = uploaded_file.getvalue()
                    result_bytes = generate_image_from_ref(input_bytes, prompt_input)
                    
                    if result_bytes:
                        st.session_state['last_ai_result'] = result_bytes
                        st.success("✅ Đã tạo ảnh thành công!")
                    else:
                        st.error("❌ Không tạo được ảnh. Vui lòng thử lại prompt khác.")
            else:
                st.warning("⚠️ Vui lòng upload ảnh và nhập prompt!")

    # HIỂN THỊ KẾT QUẢ (NẾU CÓ)
    if 'last_ai_result' in st.session_state:
        st.divider()
        st.subheader("🖼️ Kết quả AI:")
        
        c_res1, c_res2 = st.columns(2)
        with c_res1:
            if uploaded_file: st.image(uploaded_file, caption="Ảnh gốc (Original)", use_container_width=True)
        with c_res2:
            st.image(st.session_state['last_ai_result'], caption="Ảnh AI (Result)", use_container_width=True)
            
            # Download Button
            st.download_button(
                label="⬇️ Tải ảnh về máy",
                data=st.session_state['last_ai_result'],
                file_name=f"ai_gen_{int(time.time())}.png",
                mime="image/png",
                type="primary"
            )
