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
    lay_danh_sach_khach_hang,
    update_item_field,
    mark_order_as_printed,
    STATUS_DONE,
    STATUS_CANCEL,
    supabase
)
from modules.ai_logic import xuly_ai_gemini, gen_anh_mau_theu, generate_image_from_ref
from modules.notifier import send_telegram_notification, check_order_notifications
from modules.printer import generate_print_html, generate_combined_print_html # Hàm tạo HTML in ấn
from modules.exporter import export_orders_to_excel
import base64

# --- HELPER UI COMPONENTS ---
def hien_thi_anh_vuong(data, label="Ảnh"):
    if not data:
        return
    
    # Nếu là bytes (ảnh từ AI), convert sang base64
    if isinstance(data, bytes):
        try:
            b64 = base64.b64encode(data).decode()
            url = f"data:image/png;base64,{b64}"
        except:
            return
    else:
        url = data

    st.markdown(
        f"""
        <div style="
            width: 100%;
            aspect-ratio: 1 / 1;
            background-image: url('{url}');
            background-size: cover;
            background-position: center;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
            margin-bottom: 5px;
            cursor: pointer;
        " title="{label}"></div>
        <div style="text-align: center; margin-bottom: 8px;">
            <a href="{url}" target="_blank" style="text-decoration: none; font-size: 0.8em; color: #555;">🔍 Xem Full</a>
        </div>
        """,
        unsafe_allow_html=True
    )


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
                    st.session_state.form_ghi_chu = extracted_data.get("ghi_chu", "")

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
            # [SỬA 1] Không sinh mã ngay, để trống và cho phép nhập tay nếu muốn
            ma_don_input = st.text_input("Mã đơn hàng", placeholder="Để trống = Tự sinh ", help="Nếu để trống, hệ thống sẽ tự sinh mã theo thời gian lúc bấm Lưu.")
            
            # Ten Khach Hang
            if "form_ten_khach" not in st.session_state: st.session_state.form_ten_khach = defaults.get("ten_khach_hang", "")
            ten_khach = st.text_input("Tên khách hàng", key="form_ten_khach")

            # So Dien Thoai
            if "form_sdt" not in st.session_state: st.session_state.form_sdt = defaults.get("so_dien_thoai", "")
            sdt = st.text_input("Số điện thoại", key="form_sdt")

            # Dia Chi
            if "form_dia_chi" not in st.session_state: st.session_state.form_dia_chi = defaults.get("dia_chi", "")
            dia_chi = st.text_area("Địa chỉ giao hàng", height=68, key="form_dia_chi")

            # Ghi chu (Mới)
            if "form_ghi_chu" not in st.session_state: st.session_state.form_ghi_chu = defaults.get("ghi_chu", "")
            ghi_chu = st.text_input("Ghi chú đặc biệt", key="form_ghi_chu", placeholder="Vd: Khách có 2 SĐT, ship giờ hành chính...")
        with c2:
            # --- LOGIC CHỌN SHOP (LINE) ---
            shop_options = ["TGTĐ", "Inside", "Lanh Canh"]
            ai_shop_suggest = defaults.get("shop", "Inside")
            if ai_shop_suggest not in shop_options: ai_shop_suggest = "Inside"
            selected_shop = st.selectbox("Shop (Line sản phẩm)", shop_options, index=shop_options.index(ai_shop_suggest))
            
            # --- MAP NGÀY THÁNG ---
            ai_ngay_dat_str = defaults.get("ngay_dat")
            ai_ngay_tra_str = defaults.get("ngay_tra")
            
            val_ngay_dat = datetime.now()
            val_ngay_tra = datetime.now()

            if ai_ngay_dat_str:
                try: val_ngay_dat = datetime.strptime(ai_ngay_dat_str, "%Y-%m-%d")
                except: pass
            if ai_ngay_tra_str:
                try: val_ngay_tra = datetime.strptime(ai_ngay_tra_str, "%Y-%m-%d")
                except: pass
            
            ngay_dat = st.date_input("Ngày đặt", value=val_ngay_dat, format="DD/MM/YYYY")
            
            c_date, c_check = st.columns([2, 1])
            ai_co_hen = defaults.get("co_hen_ngay", False)
            with c_date:
                ngay_tra = st.date_input("Ngày trả dự kiến", value=val_ngay_tra, format="DD/MM/YYYY")
            with c_check:
                st.write("")
                st.write("") 
                co_hen_ngay = st.checkbox("🚨 Khách hẹn?", value=ai_co_hen)
            
            # --- MAP THANH TOÁN & VẬN CHUYỂN ---
            opts_httt = ["Ship COD 💵", "0đ 📷"]
            opts_vc = ["Thường", "Xe Ôm 🏍", "Bay ✈"]
            ai_httt = defaults.get("httt", "Ship COD 💵")
            ai_vc = defaults.get("van_chuyen", "Thường")
            idx_httt = opts_httt.index(ai_httt) if ai_httt in opts_httt else 0
            idx_vc = opts_vc.index(ai_vc) if ai_vc in opts_vc else 0

            httt = st.selectbox("Hình thức thanh toán", opts_httt, index=idx_httt)
            van_chuyen = st.selectbox("Vận chuyển", opts_vc, index=idx_vc)

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

            # [SỬA 2] Logic sinh mã đơn tại thời điểm bấm nút
            final_ma_don = ma_don_input.strip()
            if not final_ma_don:
                # Nếu không nhập gì -> Tự sinh theo giờ hiện tại
                final_ma_don = f"ORD-{datetime.now().strftime('%m%d-%H%M-%S')}"

            if not ten_khach:
                st.error("❌ Thiếu tên khách hàng!")
            elif not items_list:
                st.error("❌ Đơn hàng phải có ít nhất 1 sản phẩm!")
            else:
                order_data = {
                    "ma_don": final_ma_don, # Dùng mã vừa chốt
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
                    "shop": selected_shop,
                    "trang_thai": "New",
                    "co_hen_ngay": co_hen_ngay,
                    "ghi_chu": ghi_chu
                }

                if save_full_order(order_data, items_list):
                    st.success(f"✅ Đã lưu đơn {final_ma_don}!")
                    # Bỏ rule gửi thông báo đơn mới. 
                    # check_order_notifications(final_ma_don, [], []) # Không có tag khi tạo đơn
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

    # --- LOGIC AUTO PRINT (GỘP) ---
    if "print_bulk_html" in st.session_state:
        b_html = st.session_state.pop("print_bulk_html")
        @st.dialog("🖨️ Đang in gộp...", width="large")
        def show_bulk_auto_print(html_c):
            st.success("✅ Đã cập nhật trạng thái: ĐÃ IN cho các đơn hàng được chọn.")
            final_html = html_c + "<script>window.addEventListener('load', function() { setTimeout(function() { window.print(); }, 500); });</script>"
            components.html(final_html, height=800, scrolling=True)
        show_bulk_auto_print(b_html)
    IGNORE_STATUSES = STATUS_DONE + STATUS_CANCEL 

    if not df.empty:
        df['trang_thai'] = df['trang_thai'].astype(str).str.strip()
        if 'shop' not in df.columns: df['shop'] = "Inside"
        if 'thanh_tien' in df.columns: df['thanh_tien'] = pd.to_numeric(df['thanh_tien'], errors='coerce').fillna(0)
        if 'da_coc' in df.columns: df['da_coc'] = pd.to_numeric(df['da_coc'], errors='coerce').fillna(0)
        
        # Convert Date
        if 'ngay_dat' in df.columns:
            df['ngay_dat_filter'] = pd.to_datetime(df['ngay_dat'], errors='coerce').dt.date
        if 'ngay_tra' in df.columns:
            df['ngay_tra_filter'] = pd.to_datetime(df['ngay_tra'], errors='coerce').dt.date

    # =================================================================================
    # 1. METRICS (BOX KPI) - GIỮ NGUYÊN
    # =================================================================================
    metrics_container = st.container()
    
    # Tạo khoảng cách lớn để tách biệt Metrics và phần dưới
    st.markdown("###") 

    # =================================================================================
    # 2. KHU VỰC ĐIỀU KHIỂN: NHẮC VIỆC (TRÁI) - BỘ LỌC (PHẢI)
    # =================================================================================
    c_control_left, c_control_right = st.columns([1, 2], gap="medium")

    # --- BOX TRÁI: NHẮC VIỆC ---
    with c_control_left:
        with st.container(border=True):
            st.markdown("##### 🔔 Nhắc việc quan trọng")
            
            # Tính toán dữ liệu nhắc việc
            count_urgent_today = 0
            count_due_tomorrow = 0
            df_urgent_today = pd.DataFrame()
            df_due_tomorrow = pd.DataFrame()

            if not df.empty:
                today = datetime.now().date()
                tomorrow = today + pd.Timedelta(days=1)
                
                # Lấy data chưa xong từ DF GỐC (Không bị ảnh hưởng bởi bộ lọc bên phải)
                df_pending = df[~df['trang_thai'].isin(IGNORE_STATUSES)]
                
                if not df_pending.empty and 'ngay_tra_filter' in df_pending.columns:
                    # 1. Đơn Hẹn Trả Hôm Nay
                    df_urgent_today = df_pending[
                        (df_pending['co_hen_ngay'] == True) & 
                        (df_pending['ngay_tra_filter'] == today)
                    ]
                    count_urgent_today = len(df_urgent_today)
                    
                    # 2. Đơn Trả Ngày Mai
                    df_due_tomorrow = df_pending[
                        (df_pending['ngay_tra_filter'] == tomorrow)
                    ]
                    count_due_tomorrow = len(df_due_tomorrow)
            
            # Hiển thị UI trong box nhỏ
            if count_urgent_today > 0:
                st.error(f"🔥 **HÔM NAY: {count_urgent_today} đơn hẹn gấp!**")
                with st.expander("Xem chi tiết", expanded=False):
                    for _, row in df_urgent_today.iterrows():
                        st.caption(f"• {row['ma_don']} | {row['ten_khach']}")
            else:
                st.success("✅ Hôm nay: Không có đơn hẹn gấp.", icon="👍")

            st.markdown("---") # Kẻ ngang nhỏ trong box

            if count_due_tomorrow > 0:
                st.warning(f"⏳ **NGÀY MAI: {count_due_tomorrow} đơn cần trả.**")
                with st.expander("Xem chi tiết", expanded=False):
                     for _, row in df_due_tomorrow.iterrows():
                        icon_hen = "🚨" if row.get('co_hen_ngay') else ""
                        st.caption(f"• {icon_hen} {row['ma_don']} | {row['ten_khach']}")
            else:
                st.info("☕ Ngày mai: Chưa có lịch trả hàng.", icon="✨")

    # --- BOX PHẢI: BỘ LỌC ---
    with c_control_right:
        with st.container(border=True):
            st.markdown("##### 🌪️ Bộ lọc dữ liệu")
            
            df_status = tai_danh_sach_trang_thai()
            options_status = df_status["Trạng thái"].tolist()
            
            # Hàng 1: Trạng thái, Tag & Shop
            from modules.data_handler import PRODUCTION_TAGS
            c_f1, c_f_tag, c_f2 = st.columns([1.5, 1.5, 1])
            with c_f1:
                status_filter = st.multiselect("Trạng thái:", options_status, placeholder="Chọn trạng thái...")
            with c_f_tag:
                tag_filter = st.multiselect("Nhãn (Tags):", PRODUCTION_TAGS, placeholder="Chọn Nhãn...")
            with c_f2:
                shop_filter = st.multiselect("Shop:", ["TGTĐ", "Inside", "Lanh Canh"], placeholder="Chọn Shop")
            
            # Hàng 2: Lọc ngày & Checkboxes
            c_f3, c_f4, c_f5, c_f6 = st.columns([1.5, 1.5, 0.7, 0.7])
            with c_f3:
                range_ngay_dat = st.date_input("Ngày Đặt:", value=[], format="DD/MM/YYYY")
            with c_f4:
                range_ngay_tra = st.date_input("Ngày Trả:", value=[], format="DD/MM/YYYY")
            
            with c_f5:
                st.write("") # Spacer để căn lề với date input
                st.write("")
                loc_hen_ngay = st.checkbox("🚨 Đơn hẹn", value=False)
            
            with c_f6:
                st.write("") # Spacer
                st.write("")
                loc_chua_in = st.checkbox("🖨️ Chưa in", value=False)
    # =================================================================================
    # 3. XỬ LÝ DATA (APPLY FILTER)
    # =================================================================================
    if not df.empty:
        df_show = df.copy()
        
        if status_filter: df_show = df_show[df_show['trang_thai'].isin(status_filter)]
        if tag_filter:
            # Lọc các đơn có chứa ít nhất 1 trong các tag được chọn
            def check_tag_match(order_tags):
                if not order_tags: return False
                # Nếu order_tags là string (phòng lỗi), convert về list
                if isinstance(order_tags, str): return any(x in order_tags for x in tag_filter)
                return any(x in order_tags for x in tag_filter)
            
            df_show = df_show[df_show['tags'].apply(check_tag_match)]
            
        if shop_filter: df_show = df_show[df_show['shop'].isin(shop_filter)]
        if loc_hen_ngay and 'co_hen_ngay' in df_show.columns:
            df_show = df_show[df_show['co_hen_ngay'] == True]
        if loc_chua_in:
            if 'da_in' in df_show.columns:
                # Lấy những đơn da_in là False hoặc NaN (chưa có dữ liệu)
                df_show = df_show[df_show['da_in'] != True]            
        if len(range_ngay_dat) == 2:
            s_d, e_d = range_ngay_dat
            if 'ngay_dat_filter' in df_show.columns:
                df_show = df_show[(df_show['ngay_dat_filter'] >= s_d) & (df_show['ngay_dat_filter'] <= e_d)]

        if len(range_ngay_tra) == 2:
            s_t, e_t = range_ngay_tra
            if 'ngay_tra_filter' in df_show.columns:
                df_show = df_show[(df_show['ngay_tra_filter'] >= s_t) & (df_show['ngay_tra_filter'] <= e_t)]
    else:
        df_show = pd.DataFrame()

    # =================================================================================
    # 4. ĐIỀN METRICS (LOGIC CŨ - LAYOUT 2 BOX NGANG)
    # =================================================================================
    with metrics_container:
        if not df_show.empty:
            tong_don = len(df_show)
            da_xong = len(df_show[df_show['trang_thai'].isin(STATUS_DONE)])
            da_huy = len(df_show[df_show['trang_thai'].isin(STATUS_CANCEL)])
            dang_xu_ly = tong_don - da_xong - da_huy
            
            df_rev = df_show[~df_show['trang_thai'].isin(STATUS_CANCEL)]
            dt_ban_hang = df_rev['thanh_tien'].sum()
            dt_coc = df_rev['da_coc'].sum()
            
            def tinh_thuc_nhan(row):
                if row['trang_thai'] in STATUS_DONE: return row['thanh_tien']
                else: return row['da_coc']
            
            dt_thuc_nhan = df_rev.apply(tinh_thuc_nhan, axis=1).sum()
        else:
            tong_don, da_xong, da_huy, dang_xu_ly = 0, 0, 0, 0
            dt_ban_hang, dt_coc, dt_thuc_nhan = 0, 0, 0

        # Layout Metrics (2 box ngang như yêu cầu trước)
        col_left, col_right = st.columns(2, gap="medium")
        with col_left:
            with st.container(border=True):
                st.markdown("##### 📦 Tình trạng đơn hàng")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Tổng", tong_don)
                c2.metric("Xử lý", dang_xu_ly)
                c3.metric("Xong", da_xong)
                c4.metric("Hủy", da_huy)
        with col_right:
            with st.container(border=True):
                st.markdown("##### 💰 Tài chính (Thực tế)")
                r1, r2, r3 = st.columns(3)
                r1.metric("Bán Hàng", f"{dt_ban_hang:,.0f}đ")
                r2.metric("Thực Nhận", f"{dt_thuc_nhan:,.0f}đ", delta_color="normal")
                r3.metric("Tổng Cọc", f"{dt_coc:,.0f}đ")

    # =================================================================================
    # 5. HIỂN THỊ BẢNG
    # =================================================================================
    st.divider()

    if not df_show.empty:
        # Sort & Deadline logic
        if 'co_hen_ngay' in df_show.columns:
            df_show['is_urgent_active'] = df_show.apply(
                lambda x: True if (x.get('co_hen_ngay') == True and str(x.get('trang_thai')).strip() not in IGNORE_STATUSES) else False,
                axis=1
            )
            df_show = df_show.sort_values(by=['is_urgent_active', 'created_at'], ascending=[False, False])
            
            def format_deadline(row):
                try:
                    d_obj = pd.to_datetime(row['ngay_tra'])
                    d_str = d_obj.strftime("%d/%m/%Y")
                    return f"🚨 {d_str}" if row['is_urgent_active'] else d_str
                except:
                    return str(row.get('ngay_tra', ''))

            df_show['deadline'] = df_show.apply(format_deadline, axis=1)
        else:
            def format_simple(row):
                try: return pd.to_datetime(row['ngay_tra']).strftime("%d/%m/%Y")
                except: return str(row.get('ngay_tra', ''))
            df_show['deadline'] = df_show.apply(format_simple, axis=1)

        # Display Icon
        if 'da_in' in df_show.columns:
            df_show['display_ma_don'] = df_show.apply(
                lambda x: f"🖨️ {x['ma_don']}" if x.get('da_in') == True else x['ma_don'], 
                axis=1
            )
        else:
            df_show['display_ma_don'] = df_show['ma_don']

        # Render
        def get_display_tags(tags):
            if not tags: return ""
            if isinstance(tags, str): return tags
            return ", ".join([str(t) for t in tags if t])

        df_show['display_tags'] = df_show['tags'].apply(get_display_tags)
        
        cols_to_show = ["display_ma_don", "display_tags", "ten_khach", "shop", "deadline", "thanh_tien", "trang_thai"]
        valid_cols = [c for c in cols_to_show if c in df_show.columns]
        df_display = df_show[valid_cols].reset_index(drop=True)

        # --- STYLE: Highlight Urgent ---
        def highlight_urgent(row):
            if "🚨" in str(row.get('deadline', '')):
                return ['background-color: #ffebee; color: #c62828; font-weight: bold'] * len(row)
            else:
                return [''] * len(row)

        styled_df = df_display.style.apply(highlight_urgent, axis=1)

        # --- RENDER TABLE & SELECTION ---
        # Sử dụng st.dataframe với on_select (Streamlit mới) để vừa có Style vừa có Chọn
        event = st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "display_ma_don": st.column_config.TextColumn("Mã đơn hàng", width="small"),
                "display_tags": st.column_config.TextColumn("Nhãn", width="medium"),
                "thanh_tien": st.column_config.NumberColumn("Thành tiền", format="%d đ"),
                "deadline": st.column_config.TextColumn("Hạn chót", width="medium"),
                "shop": st.column_config.TextColumn("Shop", width="small"),
                "trang_thai": st.column_config.TextColumn("Trạng thái", width="small")
            },
            on_select="rerun", # Fix: interactive -> rerun
            selection_mode="multi-row",
            key="order_table_selection"
        )
        
        # --- ACTION BUTTONS (IN / EXPORT) ---
        # Lấy các rows được chọn từ event
        selected_indices = event.selection.rows
        
        # Layout: 6 phần trống bên trái, 2 phần bên phải cho 2 nút
        # Điều chỉnh tỷ lệ tùy theo độ rộng màn hình, ví dụ [5, 1, 1] hoặc [6, 1.5, 1.5]
        # Ở đây dùng [6, 1.2, 1.3] để nút không bị quá bé
        c_spacer, c_btn_print, c_btn_excel = st.columns([5, 1.5, 1.5])

        with c_spacer:
            st.empty() # Spacer

        with c_btn_print:
            if st.button("🖨️ In đơn", type="primary", use_container_width=True, help="In các đơn đã chọn"):
                if not selected_indices:
                    st.warning("Chưa chọn!")
                else:
                    try:
                        selected_rows = df_display.iloc[selected_indices]
                        
                        # --- KIỂM TRA QUYỀN IN HÀNG LOẠT ---
                        invalid_list = []
                        for _, row in selected_rows.iterrows():
                            o_ma = str(row['display_ma_don']).replace("🖨️", "").strip()
                            o_shop = row['shop']
                            o_stt = row['trang_thai']
                            
                            if o_shop == "Lanh Canh":
                                if o_stt in ["Mới", "Đã xác nhận", "New"]:
                                    invalid_list.append(f"{o_ma} (Lanh Canh - {o_stt})")
                            else:
                                if o_stt in ["Mới", "Đã xác nhận", "Chờ sản xuất", "Đang thiết kế", "Chờ duyệt thiết kế", "New"]:
                                    invalid_list.append(f"{o_ma} ({o_shop} - {o_stt})")

                        if invalid_list:
                            st.error(f"⚠️ Có {len(invalid_list)} đơn chưa đủ điều kiện in:\n" + "\n".join([f"- {i}" for i in invalid_list]))
                        else:
                            selected_ma_don = []
                            for _, row in selected_rows.iterrows():
                                raw_ma = str(row['display_ma_don'])
                                if "🖨️" in raw_ma: raw_ma = raw_ma.replace("🖨️", "").strip()
                                selected_ma_don.append(raw_ma)
                            
                            if selected_ma_don:
                                orders_data_list = []
                                from modules.data_handler import get_order_details
                                with st.spinner(f"Xử lý {len(selected_ma_don)} đơn..."):
                                    for ma in selected_ma_don:
                                        o_info, o_items = get_order_details(ma)
                                        if o_info: orders_data_list.append({"order_info": o_info, "items": o_items})
                                
                                if orders_data_list:
                                    combined_html = generate_combined_print_html(orders_data_list)
                                    @st.dialog("🖨️ Xem trước bản in (Gộp)", width="large")
                                    def show_combined_print_preview(html_content, ma_list):
                                        st.caption("Kiểm tra kỹ các đơn trước khi bấm xác nhận.")
                                        if st.button("🚀 XÁC NHẬN & IN TẤT CẢ", type="primary", use_container_width=True):
                                            from modules.data_handler import mark_order_as_printed
                                            with st.spinner("Đang cập nhật trạng thái..."):
                                                for m in ma_list:
                                                    mark_order_as_printed(m)
                                            st.session_state["print_bulk_html"] = html_content
                                            st.rerun()
                                        components.html(html_content, height=800, scrolling=True)
                                    show_combined_print_preview(combined_html, selected_ma_don)
                    except Exception as e: st.error(f"Lỗi: {e}")

        with c_btn_excel:
            # Excel Export Button logic
            if st.button("📥 Xuất Excel", key="btn_prep_excel", use_container_width=True, help="Xuất đơn đã chọn ra Excel mẫu Nobita"):
                if not selected_indices:
                    st.warning("Chưa chọn!")
                else:
                    try:
                        selected_rows_ex = df_display.iloc[selected_indices]
                        selected_ma_don_ex = []
                        for _, row in selected_rows_ex.iterrows():
                            raw_ma = str(row['display_ma_don'])
                            if "🖨️" in raw_ma: raw_ma = raw_ma.replace("🖨️", "").strip()
                            selected_ma_don_ex.append(raw_ma)
                            
                        if selected_ma_don_ex:
                            orders_data_ex = []
                            from modules.data_handler import get_order_details
                            with st.spinner("Đang tạo..."):
                                for ma in selected_ma_don_ex:
                                    o_info, o_items = get_order_details(ma)
                                    if o_info: orders_data_ex.append({"order_info": o_info, "items": o_items})
                                    
                                    # --- LOGIC AUTOMATION: Xuất Excel -> Chờ sản xuất ---
                                    # Chỉ update nếu đơn đang ở trạng thái trước đó (Mới, Đã xác nhận) để tránh revert đơn đã làm
                                    current_st_ex = o_info.get('trang_thai', '')
                                    allow_auto_update_ex = ["Mới", "Đã xác nhận", "New"]
                                    if current_st_ex in allow_auto_update_ex:
                                        from modules.data_handler import update_order_info
                                        update_order_info(ma, {"trang_thai": "Chờ sản xuất"})

                            if orders_data_ex:
                                excel_buffer = export_orders_to_excel(orders_data_ex)
                                f_name = f"Excel_Nobita_{datetime.now().strftime('%d.%m')}.xlsx"
                                
                                # Auto download hack hoặc hiện nút download
                                st.download_button(
                                    label="⬇️ TẢI VỀ",
                                    data=excel_buffer,
                                    file_name=f_name,
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    type="primary",
                                    icon="✅"
                                )
                            else: st.error("Rỗng!")
                    except Exception as e: st.error(f"Lỗi: {e}")
    else:
        st.warning("Không tìm thấy đơn hàng phù hợp với bộ lọc.")

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

                new_ngay_dat = c_d1.date_input("Ngày đặt", value=d_dat, format="DD/MM/YYYY")
                new_ngay_tra = c_d2.date_input("Ngày trả", value=d_tra, format="DD/MM/YYYY")
                
                # Tài chính
                st.markdown("---")
                new_tong = st.number_input("Tổng tiền", value=float(order_info.get('thanh_tien', 0)), step=10000.0, format="%.0f")
                new_coc = st.number_input("Đã cọc", value=float(order_info.get('da_coc', 0)), step=10000.0, format="%.0f")
                st.caption(f"Còn lại: {new_tong - new_coc:,.0f} đ")
                
                st.markdown("---")
                
                # Load danh sách trạng thái & tags chuẩn từ data_handler
                # (Lưu ý: Bạn phải chắc chắn đã thêm PRODUCTION_TAGS vào data_handler.py như hướng dẫn trước)
                from modules.data_handler import PRODUCTION_TAGS 
                
                df_status = tai_danh_sach_trang_thai()
                options_status = df_status["Trạng thái"].tolist()
                current_st = order_info.get('trang_thai', 'New')
                if current_st not in options_status: options_status.append(current_st)
                new_trang_thai = st.selectbox("Trạng thái", options_status, index=options_status.index(current_st))
                    
                # Lấy danh sách tags hiện tại từ DB (nếu chưa có thì là list rỗng)
                current_tags = order_info.get('tags') or []
                # Ép kiểu về list nếu lỡ DB lưu dạng string (phòng lỗi)
                if isinstance(current_tags, str): current_tags = []
                
                # Gộp danh sách gợi ý + danh sách hiện có (để không bị mất các tag lạ)
                all_tag_options = list(set(PRODUCTION_TAGS + current_tags))
                
                new_tags = st.multiselect(
                    "Nhãn / Lưu ý (Tags)",
                    options=all_tag_options,
                    default=current_tags,
                    placeholder="Chọn nhãn..."
                )
                
                new_ghi_chu = st.text_input("Ghi chú đặc biệt", value=order_info.get('ghi_chu', ''))
                
                # --- NEW: Facebook ID ---
                current_fb_id = "" # TODO: Cần lấy từ bảng khach_hang, nhưng hiện tại trong order_info chưa join bảng khách.
                # Tạm thời field này để manual update nếu cần, hoặc chờ backend update order_info join khach_hang
                # new_fb_id = st.text_input("Facebook ID (Messenger)", value=current_fb_id, placeholder="ID dạng số...")

                # Nút hành động
                col_btn_1, col_btn_2 = st.columns(2)
                with col_btn_1:
                    is_new = current_st in ["Mới", "Đổi/sửa/đền"]
                    btn_confirm = st.form_submit_button("✅ Xác nhận đơn", use_container_width=True, disabled=not is_new)
                with col_btn_2:
                    btn_save = st.form_submit_button("💾 Lưu thông tin", type="primary", use_container_width=True)

                if btn_confirm or btn_save:
                    # Nếu bấm Xác nhận đơn -> auto chuyển trạng thái
                    final_status = "Đã xác nhận" if btn_confirm else new_trang_thai
                    
                    update_data = {
                        "shop": new_shop, "ten_khach": new_ten, "sdt": new_sdt, 
                        "dia_chi": new_dia_chi, "ngay_dat": new_ngay_dat.isoformat(), 
                        "ngay_tra": new_ngay_tra.isoformat(), "thanh_tien": new_tong, 
                        "da_coc": new_coc, "con_lai": new_tong - new_coc, "trang_thai": final_status,
                        "ghi_chu": new_ghi_chu,
                        "tags": new_tags
                    }
                    
                    # --- LOGIC AUTOMATION: Trigger Webhook nếu trạng thái là Chờ duyệt thiết kế ---
                    if new_trang_thai == "Chờ duyệt thiết kế" and current_st != "Chờ duyệt thiết kế":
                        st.toast("🚀 Đang gửi thông báo bản thiết kế cho khách...", icon="📨")
                        # TODO: Call webhook function here
                        # trigger_webhook_design_approval(order_info)

                    if update_order_info(ma_don, update_data):
                        # --- GỬI THÔNG BÁO THEO TAG MỚI ---
                        check_order_notifications(ma_don, current_tags, new_tags)
                        
                        st.success("Đã cập nhật!"); time.sleep(0.5); st.rerun()

            # --- NÚT IN PHIẾU (Đã cập nhật logic Đã In) ---
            st.markdown("---")
            
            # Kiểm tra trạng thái đã in để cảnh báo (Optional)
            if order_info.get('da_in'):
                st.caption("✅ Đơn này đã từng được in phiếu.")

            # --- LOGIC IN ẤN: AUTO OPEN DIALOG KHI VỪA UPDATE XONG ---
            if f"print_after_confirm_{ma_don}" in st.session_state:
                p_html = st.session_state.pop(f"print_after_confirm_{ma_don}")
                
                @st.dialog("🖨️ Đang in phiếu...", width="large")
                def show_auto_print_dialog(html_c):
                    st.success("✅ Đã cập nhật trạng thái: ĐÃ IN")
                    # Inject JS Print
                    final_html = html_c + """
                    <script>
                        window.addEventListener('load', function() {
                            setTimeout(function() { window.print(); }, 500); 
                        });
                    </script>
                    """
                    components.html(final_html, height=800, scrolling=True)
                
                show_auto_print_dialog(p_html)

            # Nút mở preview thường
            # --- LOGIC PERMISSION IN ---
            def check_print_permission(order):
                shp = order.get('shop', 'Inside')
                stt = order.get('trang_thai', '')
                
                # Danh sách trạng thái theo thứ tự process
                # Mới -> Đã xác nhận -> Chờ sản xuất -> Đang thiết kế -> Chờ duyệt thiết kế -> Đã duyệt thiết kế -> Đang sản xuất -> ...
                
                allow = False
                msg = ""
                
                if shp == "Lanh Canh":
                    # Lanh canh: Chờ sản xuất trở đi là được in
                    # Các trạng thái KHÔNG được in: Mới, Đã xác nhận
                    lbl_block = ["Mới", "Đã xác nhận", "New"]
                    if stt in lbl_block:
                        allow = False
                        msg = f"Đơn Lanh Canh phải từ 'Chờ sản xuất'. Trạng thái hiện tại: {stt}"
                    else:
                        allow = True
                else: 
                    # TGTĐ / Inside: Đã duyệt thiết kế trở đi
                    # Các trạng thái KHÔNG được in: Mới, Đã xác nhận, Chờ sản xuất, Đang thiết kế, Chờ duyệt thiết kế
                    lbl_block = ["Mới", "Đã xác nhận", "Chờ sản xuất", "Đang thiết kế", "Chờ duyệt thiết kế", "New"]
                    if stt in lbl_block:
                        allow = False
                        msg = f"Đơn Design phải từ 'Đã duyệt thiết kế'. Trạng thái hiện tại: {stt}"
                    else:
                        allow = True
                
                return allow, msg

            can_print, msg_print = check_print_permission(order_info)

            if st.button("🖨️ XEM & IN PHIẾU", use_container_width=True, key=f"btn_print_{ma_don}", disabled=not can_print, help=None if can_print else msg_print):
                html_content = generate_print_html(order_info, items)
                
                @st.dialog("🖨️ Xem trước bản in", width="large")
                def show_preview_dialog(html, m_don):
                    st.caption("Kiểm tra nội dung phiếu trước khi in.")
                    
                    # Nút GỘP: Vừa update, vừa in
                    if st.button("🚀 IN PHIẾU NGAY (Lưu & In)", key=f"btn_real_print_{m_don}", type="primary", use_container_width=True):
                        # 1. Update DB
                        mark_order_as_printed(m_don)
                        
                        # 2. Lưu HTML vào session để reopen dialog sau khi rerun
                        st.session_state[f"print_after_confirm_{m_don}"] = html
                        st.rerun()

                    components.html(html, height=800, scrolling=True)
                
                show_preview_dialog(html_content, ma_don)
                
# ================= CỘT PHẢI: SẢN PHẨM (DYNAMIC SHOP) =================
        with c_items:
            st.markdown(f"#### 🛒 Sản phẩm ({len(items)}) - {current_shop}")
            

            # --- 1. CALLBACK CHO 1 FILE ---
            def auto_upload_callback(uploader_key, item_id, file_suffix, db_column):
                uploaded_file = st.session_state.get(uploader_key)
                if uploaded_file:
                    url = upload_image_to_supabase(uploaded_file, f"item_{item_id}_{file_suffix}.png")
                    if url:
                        update_item_image(item_id, url, db_column)
                        st.toast(f"✅ Đã lưu {db_column}!", icon="💾")

            # --- 2. CALLBACK CHO NHIỀU FILE ---
            def auto_upload_multiple_callback(uploader_key, item_id, db_column, version_key):
                uploaded_files = st.session_state.get(uploader_key)
                if uploaded_files:
                    str_urls = upload_multiple_files_to_supabase(uploaded_files, item_id)
                    if str_urls:
                        update_item_image(item_id, str_urls, db_column)
                        if version_key in st.session_state:
                            st.session_state[version_key] += 1
                        st.toast(f"✅ Đã ghi đè {len(uploaded_files)} file mới!", icon="📂")

            if items:
                for item in items:
                    with st.container(border=True):
                        
                        # =========================================================
                        # CASE 1: LANH CANH (2 ẢNH: CHÍNH, SỬA ĐỔI)
                        # =========================================================
                        if current_shop == "Lanh Canh":
                            # Layout: [Info 1.2] | [Chính 1] | [Sửa đổi 1]
                            cols = st.columns([1.2, 1, 1])
                            
                            # Cột 0: Info
                            with cols[0]:
                                st.write(f"**{item.get('ten_sp')}**")
                                st.caption(f"{item.get('mau')} / {item.get('size')}")
                            
                            # Cột 1: Sản phẩm chính (img_main)
                            with cols[1]:
                                st.write("📸 SP Chính")
                                hien_thi_anh_vuong(item.get('img_main'), "SP Chính")
                                k_lc_main = f"u_lc_m_{item.get('id')}"
                                st.file_uploader("Up Chính", key=k_lc_main, label_visibility="collapsed",
                                                 on_change=auto_upload_callback,
                                                 args=(k_lc_main, item.get('id'), "main", "img_main"))
                            
                            # Cột 2: Mẫu sửa đổi (Lưu vào img_sub1)
                            with cols[2]:
                                st.write("📝 Mẫu sửa đổi")
                                hien_thi_anh_vuong(item.get('img_sub1'), "Mẫu sửa đổi")
                                k_lc_sub = f"u_lc_s_{item.get('id')}"
                                st.file_uploader("Up Sửa đổi", key=k_lc_sub, label_visibility="collapsed",
                                                 on_change=auto_upload_callback,
                                                 args=(k_lc_sub, item.get('id'), "fix_sample", "img_sub1"))

                        # =========================================================
                        # CASE 2: INSIDE (3 ẢNH: CHÍNH, PHỤ 1, PHỤ 2)
                        # =========================================================
                        elif current_shop == "Inside":
                            cols = st.columns([1.2, 1, 1, 1])
                            
                            with cols[0]:
                                st.write(f"**{item.get('ten_sp')}**")
                                st.caption(f"{item.get('mau')} / {item.get('size')}")
                                st.caption(f"YC: {item.get('kieu_theu')}")
                            
                            with cols[1]:
                                st.write("1️⃣ Ảnh Chính")
                                hien_thi_anh_vuong(item.get('img_main'), "Ảnh Chính")
                                k_in_main = f"u_in_m_{item.get('id')}"
                                st.file_uploader("Up Chính", key=k_in_main, label_visibility="collapsed",
                                                 on_change=auto_upload_callback,
                                                 args=(k_in_main, item.get('id'), "main", "img_main"))
                            
                            with cols[2]:
                                st.write("2️⃣ Ảnh Phụ 1")
                                hien_thi_anh_vuong(item.get('img_sub1'), "Ảnh Phụ 1")
                                k_in_sub1 = f"u_in_s1_{item.get('id')}"
                                st.file_uploader("Up Phụ 1", key=k_in_sub1, label_visibility="collapsed",
                                                 on_change=auto_upload_callback,
                                                 args=(k_in_sub1, item.get('id'), "sub1", "img_sub1"))

                            with cols[3]:
                                st.write("3️⃣ Ảnh Phụ 2")
                                hien_thi_anh_vuong(item.get('img_design'), "Ảnh Phụ 2")
                                k_in_sub2 = f"u_in_s2_{item.get('id')}"
                                st.file_uploader("Up Phụ 2", key=k_in_sub2, label_visibility="collapsed",
                                                 on_change=auto_upload_callback,
                                                 args=(k_in_sub2, item.get('id'), "sub2", "img_design"))
                                
                                # --- NÚT GỬI DUYỆT (INSIDE) ---
                                can_approve = order_info.get('trang_thai') == "Đang thiết kế"
                                if st.button("🚀 Gửi duyệt", key=f"btn_send_approval_in_{item.get('id')}", use_container_width=True, disabled=not can_approve):
                                    if update_order_info(ma_don, {"trang_thai": "Chờ duyệt thiết kế"}):
                                        st.success("Đã chuyển sang Chờ duyệt thiết kế!"); time.sleep(0.5); st.rerun()

                        # =========================================================
                        # CASE 3: TGTĐ (VÀ MẶC ĐỊNH)
                        # =========================================================
                        else:
                            cols = st.columns([1.2, 1, 1, 1, 1])
                            
                            with cols[0]:
                                st.write(f"**{item.get('ten_sp')}**")
                                st.caption(f"{item.get('mau')} / {item.get('size')}")
                                st.caption(f"YC: {item.get('kieu_theu')}")

                            with cols[1]:
                                st.write("1️⃣ Ảnh Gốc")
                                hien_thi_anh_vuong(item.get('img_main'), "Ảnh Gốc")
                                k_main = f"u_m_{item.get('id')}"
                                st.file_uploader("Up gốc", key=k_main, label_visibility="collapsed",
                                                 on_change=auto_upload_callback,
                                                 args=(k_main, item.get('id'), "main", "img_main"))

                            with cols[2]:
                                st.write("2️⃣ Kết quả AI")
                                hien_thi_anh_vuong(item.get('img_sub1'), "Kết quả AI")
                                if st.button("✨ Gen AI", key=f"ai_{item.get('id')}", type="primary"):
                                    try:
                                        input_bytes = None
                                        up_obj = st.session_state.get(k_main)
                                        if up_obj: input_bytes = up_obj.getvalue()
                                        elif item.get('img_main'):
                                            input_bytes = requests.get(item.get('img_main')).content
                                        
                                        if input_bytes:
                                            with st.spinner("AI đang vẽ..."):
                                                ai_bytes = gen_anh_mau_theu(input_bytes, f"{item.get('ten_sp')} {item.get('kieu_theu')}")
                                                if ai_bytes:
                                                    url = upload_image_to_supabase(ai_bytes, f"item_{item.get('id')}_ai.png")
                                                    if url and update_item_image(item.get('id'), url, "img_sub1"): st.rerun()
                                                else: st.error("AI lỗi")
                                        else: st.warning("Cần ảnh gốc!")
                                    except: pass

                            with cols[3]:
                                st.write("3️⃣ Ảnh Design")
                                hien_thi_anh_vuong(item.get('img_design'), "Ảnh Design")
                                if not item.get('img_design'): st.info("Chưa có")
                                k_des = f"u_des_{item.get('id')}"
                                st.file_uploader("Up Design", key=k_des, label_visibility="collapsed",
                                                 on_change=auto_upload_callback,
                                                 args=(k_des, item.get('id'), "design", "img_design"))
                                
                                # --- NÚT GỬI DUYỆT (CHỈ TGTĐ/INSIDE) ---
                                can_approve = order_info.get('trang_thai') == "Đang thiết kế"
                                if st.button("🚀 Gửi duyệt", key=f"btn_send_approval_{item.get('id')}", use_container_width=True, disabled=not can_approve):
                                    if update_order_info(ma_don, {"trang_thai": "Chờ duyệt thiết kế"}):
                                        st.success("Đã chuyển sang Chờ duyệt thiết kế!"); time.sleep(0.5); st.rerun()

                            with cols[4]:
                                st.write("4️⃣ File Thêu")
                                if item.get('img_sub2'):
                                    links = item.get('img_sub2').split(' ; ')
                                    for i, l in enumerate(links): st.markdown(f"💾 [Tải File {i+1}]({l})")
                                else: st.caption("Trống")
                                
                                ver_key = f"uploader_ver_{item.get('id')}"
                                if ver_key not in st.session_state: st.session_state[ver_key] = 0
                                k_files_dynamic = f"u_f_{item.get('id')}_v{st.session_state[ver_key]}"
                                
                                st.file_uploader("Up Files (Ghi đè)", key=k_files_dynamic, accept_multiple_files=True, 
                                                 label_visibility="collapsed", on_change=auto_upload_multiple_callback,
                                                 args=(k_files_dynamic, item.get('id'), "img_sub2", ver_key))

                        # =========================================================
                        # PHẦN DƯỚI: YÊU CẦU SỬA (CHUNG CHO TẤT CẢ SHOP)
                        # =========================================================
                        st.divider()
                        st.markdown("🛠️ **Yêu cầu sửa / Feedback khách hàng**")
                        c_fix1, c_fix2, c_fix3 = st.columns([2, 1, 1])
                        
                        with c_fix1:
                            curr_note = item.get('yeu_cau_sua') if item.get('yeu_cau_sua') else ""
                            new_note = st.text_area("Nội dung sửa:", value=curr_note, height=100, key=f"txt_fix_{item.get('id')}")
                            if st.button("💾 Lưu Note", key=f"btn_save_fix_{item.get('id')}"):
                                from modules.data_handler import update_item_field 
                                if update_item_field(item.get('id'), "yeu_cau_sua", new_note):
                                    # --- AUTO CHUYỂN TRẠNG THÁI ---
                                    update_order_info(ma_don, {"trang_thai": "Chờ sản xuất"})
                                    st.success("Đã lưu note và chuyển đơn sang Chờ sản xuất!"); time.sleep(0.5); st.rerun()
                        
                        with c_fix2:
                            st.caption("Ảnh feedback 1")
                            hien_thi_anh_vuong(item.get('img_sua_1'), "Feedback 1")
                            k_fix1 = f"u_fix1_{item.get('id')}"
                            st.file_uploader("Up ảnh 1", key=k_fix1, label_visibility="collapsed",
                                             on_change=auto_upload_callback,
                                             args=(k_fix1, item.get('id'), "fix1", "img_sua_1"))

                        with c_fix3:
                            st.caption("Ảnh feedback 2")
                            hien_thi_anh_vuong(item.get('img_sua_2'), "Feedback 2")
                            k_fix2 = f"u_fix2_{item.get('id')}"
                            st.file_uploader("Up ảnh 2", key=k_fix2, label_visibility="collapsed",
                                             on_change=auto_upload_callback,
                                             args=(k_fix2, item.get('id'), "fix2", "img_sua_2"))
            else:
                st.warning("Đơn này chưa có sản phẩm.")
# ==============================================================================
# 3. TRANG AI EDIT ẢNH (GEN AI)
# ==============================================================================
def render_ai_image_page():
    st.markdown("<h2 style='text-align: center;'>🎨 AI Edit Ảnh (Beta)</h2>", unsafe_allow_html=True)
    st.caption("Sử dụng model 'gemini-3-pro-image-preview' để chỉnh sửa ảnh dựa trên Prompt.")

    # Khởi tạo session state
    if 'ai_input_bytes' not in st.session_state: st.session_state.ai_input_bytes = None
    if 'ai_input_url' not in st.session_state: st.session_state.ai_input_url = None
    if 'ai_result_url' not in st.session_state: st.session_state.ai_result_url = None

    # Layout 3 cột: Gốc | Kết quả | Prompt
    c_orig, c_res, c_prompt = st.columns([1.2, 1.2, 2.5])
    
    with c_orig:
        st.info("📸 1. Ảnh gốc")
        
        # Callback xử lý upload
        def handle_ai_upload():
            f = st.session_state.uploader_ai_input
            if f:
                # 1. Lưu bytes vào session trước
                st.session_state.ai_input_bytes = f.getvalue()
                # 2. Upload lên Supabase để có URL xem full
                url = upload_image_to_supabase(f, f"ai_input_{int(time.time())}.png", folder="ai_temp")
                if url:
                    st.session_state.ai_input_url = url

        uploaded_file = st.file_uploader(
            "Upload ảnh gốc", 
            type=['png', 'jpg', 'jpeg'], 
            label_visibility="collapsed",
            key="uploader_ai_input",
            on_change=handle_ai_upload
        )
        
        # Hiển thị ảnh gốc từ URL (chuẩn nhất)
        if st.session_state.ai_input_url:
            hien_thi_anh_vuong(st.session_state.ai_input_url, "Ảnh gốc")
            
    with c_res:
        st.info("✨ 2. Kết quả AI")
        if st.session_state.ai_result_url:
            hien_thi_anh_vuong(st.session_state.ai_result_url, "Kết quả AI")
            st.link_button("⬇️ TẢI ẢNH VỀ", st.session_state.ai_result_url, type="primary", use_container_width=True)
        else:
            st.markdown(
                """
                <div style="width: 100%; aspect-ratio: 1/1; background: #f9f9f9; border: 1px dashed #ccc; border-radius: 8px;
                            display: flex; align-items: center; justify-content: center; color: #aaa; font-size: 0.9em;">
                    Chưa có kết quả
                </div>
                """, 
                unsafe_allow_html=True
            )

    with c_prompt:
        st.info("📝 3. Nhập yêu cầu chỉnh sửa (Prompt)")
        # Dùng session state cho prompt để tránh mất dữ liệu khi rerun
        if 'ai_prompt_val' not in st.session_state: st.session_state.ai_prompt_val = "đổi màu áo sang màu xanh..."
        
        prompt_input = st.text_area(
            "Mô tả thay đổi:", 
            height=130,
            placeholder="Ví dụ: Đổi màu áo sang đỏ...",
            value=st.session_state.ai_prompt_val,
            label_visibility="collapsed",
            key="ai_prompt_area"
        )
        
        if st.button("🚀 XỬ LÝ ẢNH (GENERATE)", type="primary", use_container_width=True):
            if st.session_state.ai_input_bytes and prompt_input:
                with st.spinner("AI đang xử lý..."):
                    # 1. Gọi AI bằng bytes đã lưu trong session
                    print(f"DEBUG: Processing AI image with {len(st.session_state.ai_input_bytes)} bytes of input data.")
                    result_bytes = generate_image_from_ref(st.session_state.ai_input_bytes, prompt_input)
                    
                    if result_bytes:
                        print(f"DEBUG: AI generation successful. Result size: {len(result_bytes)} bytes.")
                        # 2. Upload kết quả lên Supabase
                        res_url = upload_image_to_supabase(result_bytes, f"ai_res_{int(time.time())}.png", folder="ai_temp")
                        if res_url:
                            st.session_state.ai_result_url = res_url
                            st.success("✅ Thành công!")
                            st.rerun()
                        else:
                            st.error("❌ Lỗi lưu ảnh kết quả.")
                    else:
                        st.error("❌ AI không trả về ảnh. Hãy thử prompt khác.")
            else:
                st.warning("⚠️ Thiếu ảnh gốc hoặc yêu cầu!")
