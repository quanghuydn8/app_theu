from pages.components import hien_thi_anh_vuong
from nicegui import ui
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import traceback

# --- IMPORT TỪ BACKEND ---
from backend.data_handler import (
    fetch_all_orders, 
    get_order_details, 
    update_order_info, 
    update_item_field,
    update_item_image,
    upload_image_to_supabase,
    mark_order_as_printed,
    ORDER_STATUSES,
    PRODUCTION_TAGS,
    STATUS_DONE,
    STATUS_CANCEL
)
from backend.ai_logic import gen_anh_mau_theu
from backend.printer import generate_combined_print_html
from backend.exporter import export_orders_to_excel

class OrderPage:
    def check_print_permission(self, order):
        """Kiểm tra xem đơn hàng có đủ điều kiện in không"""
        if not order: return False, "Chưa chọn đơn"
        
        shp = order.get('shop', 'Inside')
        stt = order.get('trang_thai', '')
        
        # Danh sách trạng thái BỊ CHẶN in
        if shp == "Lanh Canh":
            lbl_block = ["Mới", "Đã xác nhận", "New"]
            if stt in lbl_block:
                return False, f"Đơn Lanh Canh phải từ 'Chờ sản xuất'. Trạng thái: {stt}"
        else: 
            lbl_block = ["Mới", "Đã xác nhận", "Chờ sản xuất", "Đang thiết kế", "Chờ duyệt thiết kế", "New"]
            if stt in lbl_block:
                return False, f"Đơn Design phải từ 'Đã duyệt thiết kế'. Trạng thái: {stt}"
        
        return True, "Đủ điều kiện in"
    
    def __init__(self):
        self.current_order = None 
        self.current_items = []
        self.df_original = pd.DataFrame()
        self.build_ui()

    def build_ui(self):
        # ======================================================
        # PHẦN 1: DANH SÁCH ĐƠN HÀNG (TOP - CỐ ĐỊNH CHIỀU CAO)
        # ======================================================
        with ui.column().classes('w-full h-[65vh] p-0 gap-2 mb-6'):
            
            # 1.1. METRICS (KPIs)
            with ui.row().classes('w-full gap-4'):
                with ui.card().classes('flex-1 p-2 flex-row gap-4 items-center shadow-sm'):
                    with ui.column().classes('gap-0'):
                        ui.label('📦 Đơn hàng').classes('text-xs font-bold text-slate-400 uppercase')
                        self.kpi_total = ui.label('0').classes('text-2xl font-bold text-blue-600')
                    ui.separator().props('vertical')
                    with ui.row().classes('gap-4 flex-1 justify-around'):
                        self.render_mini_kpi("Đang làm", "0", "text-orange-600", ref="kpi_processing")
                        self.render_mini_kpi("Hoàn thành", "0", "text-green-600", ref="kpi_done")
                        self.render_mini_kpi("Hủy", "0", "text-slate-400", ref="kpi_cancel")

                with ui.card().classes('flex-1 p-2 flex-row gap-4 items-center shadow-sm border-l-4 border-green-500'):
                    with ui.column().classes('gap-0'):
                        ui.label('💰 Thực nhận').classes('text-xs font-bold text-slate-400 uppercase')
                        self.kpi_thuc_nhan = ui.label('0 đ').classes('text-2xl font-bold text-green-700')
                    ui.separator().props('vertical')
                    with ui.row().classes('gap-4 flex-1 justify-around'):
                        self.render_mini_kpi("Doanh số", "0 đ", "text-slate-700", ref="kpi_ban_hang")
                        self.render_mini_kpi("Tổng cọc", "0 đ", "text-slate-700", ref="kpi_coc")

            # 1.2. FILTER & CONTROLS
            with ui.row().classes('w-full items-start gap-2'):
                with ui.card().classes('w-1/3 p-2 bg-red-50 border border-red-100 gap-1'):
                    ui.label('🔔 Nhắc việc quan trọng').classes('font-bold text-red-800 text-xs mb-1')
                    self.alert_today = ui.column().classes('w-full gap-1')
                    ui.separator().classes('my-1 bg-red-200')
                    self.alert_tomorrow = ui.column().classes('w-full gap-1')
                
                with ui.expansion('Bộ lọc dữ liệu', icon='filter_alt').classes('flex-1 border rounded bg-white shadow-sm'):
                    with ui.column().classes('p-3 gap-3 w-full'):
                        with ui.row().classes('w-full gap-2'):
                            self.filter_search = ui.input(placeholder='🔍 Tìm tên, SĐT, mã...').props('dense outlined').classes('flex-1')
                            self.filter_status = ui.select(ORDER_STATUSES, multiple=True, label="Trạng thái").props('dense options-dense').classes('w-1/4')
                            self.filter_shop = ui.select(["Inside", "TGTĐ", "Lanh Canh"], multiple=True, label="Shop").props('dense options-dense').classes('w-1/4')

                        with ui.row().classes('w-full gap-4 items-center'):
                            with ui.row().classes('items-center gap-1'):
                                ui.label('Ngày đặt:').classes('text-xs text-slate-500')
                                self.date_dat_from = ui.input().props('type=date dense').classes('w-32')
                                ui.label('-')
                                self.date_dat_to = ui.input().props('type=date dense').classes('w-32')
                            
                            with ui.row().classes('items-center gap-1'):
                                ui.label('Ngày trả:').classes('text-xs text-slate-500')
                                self.date_tra_from = ui.input().props('type=date dense').classes('w-32')
                                ui.label('-')
                                self.date_tra_to = ui.input().props('type=date dense').classes('w-32')

                        with ui.row().classes('w-full justify-between items-center'):
                            with ui.row().classes('gap-4'):
                                self.filter_tags = ui.select(PRODUCTION_TAGS, multiple=True, label="Tags").props('dense options-dense').classes('w-64')
                                self.chk_urgent = ui.checkbox('🚨 Đơn hẹn gấp')
                                self.chk_not_printed = ui.checkbox('🖨️ Chưa in')
                            
                            ui.button('Áp dụng lọc', icon='search', on_click=self.apply_filters).classes('bg-blue-600 text-white px-6')

            # 1.3. AG GRID
            # [FIXED] Dùng cellClicked thay vì rowClicked để ổn định hơn
            self.grid = ui.aggrid({
                'columnDefs': [
                    {'field': 'ma_don', 'headerName': 'Mã', 'checkboxSelection': True, 'headerCheckboxSelection': True, 'width': 110},
                    {'field': 'ten_khach', 'headerName': 'Khách Hàng', 'width': 150},
                    {'field': 'shop', 'headerName': 'Shop', 'width': 80},
                    {'field': 'trang_thai', 'headerName': 'Trạng Thái', 'width': 130, 'cellStyle': {'font-weight': 'bold'}},
                    {'field': 'deadline_str', 'headerName': 'Hạn chót', 'width': 110},
                    {'field': 'thanh_tien', 'headerName': 'Tiền', 'valueFormatter': "x ? x.toLocaleString() : 0", 'width': 100},
                    {'field': 'created_at', 'headerName': 'Ngày tạo', 'width': 110},
                ],
                'defaultColDef': {'sortable': True, 'resizable': True, 'filter': True},
                'rowSelection': 'multiple',
                'pagination': True,
                'paginationPageSize': 50,
                'rowClassRules': {
                    'bg-red-50 text-red-700 font-bold': 'data.is_urgent == true',
                    'bg-green-50': 'data.trang_thai == "Hoàn thành"',
                }
            }).classes('w-full flex-1 min-h-0 shadow-sm border border-slate-200')
            
            self.grid.on('cellClicked', self.on_row_click)  # [QUAN TRỌNG] Đã đổi về cellClicked
            self.grid.on('selectionChanged', self.update_selection_count)
            
            with ui.row().classes('w-full justify-between items-center p-1'):
                self.lbl_selected_count = ui.label('Đã chọn: 0').classes('text-sm text-slate-500 font-medium')
                with ui.row().classes('gap-2'):
                    ui.button('Xuất Excel', icon='file_download', on_click=self.bulk_export_excel).props('outline sm color=green')
                    ui.button('In Phiếu', icon='print', on_click=self.bulk_print).props('sm color=blue')

        # ======================================================
        # PHẦN 2: CHI TIẾT ĐƠN HÀNG (BOTTOM - AUTO HEIGHT)
        # ======================================================
        self.detail_container = ui.column().classes('w-full bg-white rounded-lg shadow-sm border p-4 pb-10')
        
        with self.detail_container:
            with ui.column().classes('w-full items-center justify-center py-10 opacity-50'):
                ui.icon('touch_app', size='4rem').classes('text-slate-300 mb-2')
                ui.label('Chọn đơn hàng ở bảng trên để xem chi tiết').classes('text-lg text-slate-500 font-medium')

        self.refresh_data()

    # --- SỰ KIỆN CLICK (ĐÃ KHÔI PHỤC LOGIC DEBUG) ---
    def on_row_click(self, e):
        """Xử lý khi click vào ô trong bảng"""
        # In log ra terminal để debug nếu click không ăn
        print(f"👉 CLICK: {e.args}") 

        try:
            row_data = e.args.get('data')
            if not row_data:
                print("⚠️ Row data is empty")
                return

            ma_don = row_data.get('ma_don')
            if not ma_don: return

            # Lấy data tươi
            order_info, items = get_order_details(ma_don)
            
            if order_info:
                self.current_order = order_info
                self.current_items = items
                self.render_detail_view()
                
                # Cuộn xuống phần chi tiết (Optional UX)
                # ui.run_javascript(f'document.getElementById("c{self.detail_container.id}").scrollIntoView({{behavior: "smooth"}})')
            else:
                ui.notify(f'Không tìm thấy dữ liệu: {ma_don}', type='warning')

        except Exception as ex:
            print("❌ ERROR CLICK:")
            traceback.print_exc()
            ui.notify(f'Lỗi hiển thị: {str(ex)}', type='negative')

    # --- HANDLERS UPLOAD & AI ---
    async def handle_image_upload(self, e, item_id, col_name):
        ui.notify('Đang upload ảnh...', spinner=True)
        try:
            fname = f"item_{item_id}_{col_name}_{int(datetime.now().timestamp())}.png"
            url = upload_image_to_supabase(e.content, fname)
            if url:
                update_item_image(item_id, url, col_name)
                ui.notify(f'✅ Upload thành công: {col_name}')
                
                # Cập nhật UI ngay lập tức
                for item in self.current_items:
                    if item['id'] == item_id:
                        item[col_name] = url
                        break
                self.render_detail_view()
            else:
                ui.notify('❌ Upload thất bại', type='negative')
        except Exception as ex:
            ui.notify(f'Lỗi upload: {str(ex)}', type='negative')

    async def handle_gen_ai(self, item_id, prompt_text, img_main_url):
        if not img_main_url:
            ui.notify('Cần có ảnh gốc để Gen AI!', type='warning')
            return
            
        ui.notify('🎨 AI đang vẽ...', spinner=True, timeout=10000)
        try:
            import requests
            import asyncio
            res = await asyncio.to_thread(requests.get, img_main_url)
            if res.status_code == 200:
                img_bytes = res.content
                ai_bytes = await asyncio.to_thread(gen_anh_mau_theu, img_bytes, prompt_text)
                
                if ai_bytes:
                    fname = f"item_{item_id}_ai_{int(datetime.now().timestamp())}.png"
                    url = upload_image_to_supabase(ai_bytes, fname)
                    if url:
                        update_item_image(item_id, url, "img_sub1")
                        ui.notify('✅ AI vẽ xong!')
                        _, new_items = get_order_details(self.current_order['ma_don'])
                        self.current_items = new_items
                        self.render_detail_view()
                    else:
                        ui.notify('Lỗi upload ảnh AI', type='negative')
                else:
                    ui.notify('AI không trả về kết quả', type='negative')
        except Exception as e:
            ui.notify(f'Lỗi AI: {str(e)}', type='negative')

    # --- RENDER CHI TIẾT (FULL UX) ---
    def render_detail_view(self):
        self.detail_container.clear()
        if not self.current_order: return

        o = self.current_order
        items = self.current_items
        
        # Helper: Lưu Note
        def handle_save_feedback(item_obj, new_note):
            update_item_field(item_obj['id'], 'yeu_cau_sua', new_note)
            update_order_info(o['ma_don'], {"trang_thai": "Chờ sản xuất"})
            ui.notify('✅ Đã lưu Note và chuyển trạng thái!', type='positive')
            self.refresh_data() # Làm mới bảng bên trên
            self.render_detail_view() # Vẽ lại chi tiết

        # Data Clean
        if not isinstance(o.get('tags'), list): o['tags'] = []
        shop = o.get('shop') or 'Inside'
        
        with self.detail_container:
            # HEADER
            with ui.row().classes('w-full justify-between items-center mb-2 pb-2 border-b'):
                with ui.row().classes('items-center gap-2'):
                    ui.label(f"Chi tiết: {o.get('ma_don')}").classes('text-xl font-bold text-blue-800')
                    if o.get('da_in'): ui.chip('Đã in', icon='print', color='green').props('dense')

                can_print, msg_print = self.check_print_permission(o)
                with ui.row().classes('gap-2'):
                    btn_in = ui.button('In Phiếu', icon='print', on_click=lambda: ui.open(f'/print/{o.get("ma_don")}', new_tab=True)) \
                        .props(f'outline {"disabled" if not can_print else ""}')
                    if not can_print: btn_in.tooltip(msg_print)
                    ui.button('Lưu Thay Đổi', icon='save', on_click=self.save_changes).classes('bg-blue-600 text-white')

            # BODY
            with ui.row().classes('w-full gap-6 items-start no-wrap'):
                
                # === CỘT TRÁI: THÔNG TIN KHÁCH ===
                with ui.card().classes('w-[320px] p-4 shadow-sm gap-3 shrink-0 bg-slate-50'):
                    ui.label('📝 Thông tin đơn hàng').classes('font-bold text-slate-700')
                    
                    # Shop & Trạng thái
                    ui.select(["Inside", "TGTĐ", "Lanh Canh"], value=shop, label="Shop").bind_value(o, 'shop').classes('w-full').props('dense')
                    
                    st_opts = list(ORDER_STATUSES)
                    if o.get('trang_thai') not in st_opts: st_opts.append(o.get('trang_thai'))
                    ui.select(st_opts, value=o.get('trang_thai'), label="Trạng thái").bind_value(o, 'trang_thai').classes('w-full').props('dense options-dense')

                    # Info
                    ui.input('Tên khách', value=o.get('ten_khach')).bind_value(o, 'ten_khach').classes('w-full').props('dense')
                    ui.input('SĐT', value=o.get('sdt')).bind_value(o, 'sdt').classes('w-full').props('dense')
                    ui.textarea('Địa chỉ', value=o.get('dia_chi')).bind_value(o, 'dia_chi').classes('w-full').props('dense rows=2')
                    
                    # Date
                    with ui.row().classes('w-full'):
                        ui.input('Ngày đặt', value=str(o.get('ngay_dat'))[:10]).bind_value(o, 'ngay_dat').props('dense type=date').classes('w-1/2')
                        ui.input('Ngày trả', value=str(o.get('ngay_tra'))[:10]).bind_value(o, 'ngay_tra').props('dense type=date').classes('w-1/2')

                    ui.separator().classes('my-2')
                    
                    # Money
                    ui.label('💰 Tài chính').classes('font-bold text-slate-700')
                    with ui.column().classes('w-full gap-1'):
                        num_tong = ui.number('Tổng tiền', value=o.get('thanh_tien'), format='%.0f').bind_value(o, 'thanh_tien').classes('w-full').props('dense')
                        num_coc = ui.number('Đã cọc', value=o.get('da_coc'), format='%.0f').bind_value(o, 'da_coc').classes('w-full').props('dense')
                        
                        lbl_con_lai = ui.label('Còn lại: -').classes('text-right text-red-600 font-bold text-sm w-full')
                        def update_con_lai():
                            try:
                                t = float(num_tong.value or 0)
                                c = float(num_coc.value or 0)
                                lbl_con_lai.text = f"Còn lại: {t-c:,.0f} đ"
                            except: pass
                        num_tong.on('change', update_con_lai)
                        num_coc.on('change', update_con_lai)
                        update_con_lai()

                    # Meta
                    ui.select(list(set(PRODUCTION_TAGS + o['tags'])), value=o['tags'], multiple=True, label='Tags').bind_value(o, 'tags').classes('w-full').props('use-chips dense')
                    ui.input('Ghi chú', value=o.get('ghi_chu')).bind_value(o, 'ghi_chu').classes('w-full').props('dense')
                    
                    # Footer Button
                    ui.separator().classes('my-1')
                    with ui.row().classes('w-full gap-2'):
                        if o.get('trang_thai') in ['Mới', 'New']:
                            ui.button('Xác nhận', on_click=self.confirm_order).classes('flex-1 bg-green-100 text-green-800')
                        ui.button('Lưu', icon='save', on_click=self.save_changes).classes('flex-1 bg-blue-600 text-white')

                # === CỘT PHẢI: SẢN PHẨM ===
                with ui.column().classes('flex-1 gap-3 min-w-0'):
                    ui.label(f"🛒 Sản phẩm ({len(items)}) - {shop}").classes('font-bold text-slate-700 text-lg')
                    
                    if not items: ui.label('Chưa có sản phẩm').classes('italic text-slate-400')

                    for item in items:
                        with ui.card().classes('w-full p-3 border shadow-sm bg-slate-50'):
                            
                            # LOGIC LAYOUT SHOP (TGTĐ / Inside / Lanh Canh)
                            if shop == "Lanh Canh":
                                with ui.grid(columns=3).classes('w-full gap-4'):
                                    with ui.column().classes('gap-1'):
                                        ui.label(item.get('ten_san_pham')).classes('font-bold')
                                        ui.label(f"{item.get('mau')} / {item.get('size')}").classes('text-sm text-slate-500')
                                        ui.label(f"SL: {item.get('so_luong')}").classes('text-sm')
                                    with ui.column().classes('gap-1'):
                                        ui.label('📸 SP Chính').classes('text-xs font-bold')
                                        hien_thi_anh_vuong(item.get('img_main'))
                                        ui.upload(auto_upload=True, on_upload=lambda e, i=item['id']: self.handle_image_upload(e, i, 'img_main')).props('flat dense').classes('w-full h-8')
                                    with ui.column().classes('gap-1'):
                                        ui.label('📝 Mẫu sửa đổi').classes('text-xs font-bold')
                                        hien_thi_anh_vuong(item.get('img_sub1'))
                                        ui.upload(auto_upload=True, on_upload=lambda e, i=item['id']: self.handle_image_upload(e, i, 'img_sub1')).props('flat dense').classes('w-full h-8')

                            elif shop == "Inside":
                                with ui.grid(columns=4).classes('w-full gap-4'):
                                    with ui.column().classes('gap-1'):
                                        ui.label(item.get('ten_san_pham')).classes('font-bold')
                                        ui.label(f"{item.get('mau')} / {item.get('size')}").classes('text-sm text-slate-500')
                                        ui.label(f"YC: {item.get('kieu_theu')}").classes('text-xs text-red-500')
                                    with ui.column().classes('gap-1'):
                                        ui.label('1️⃣ Ảnh Chính').classes('text-xs font-bold')
                                        hien_thi_anh_vuong(item.get('img_main'))
                                        ui.upload(auto_upload=True, on_upload=lambda e, i=item['id']: self.handle_image_upload(e, i, 'img_main')).props('flat dense').classes('w-full h-8')
                                    with ui.column().classes('gap-1'):
                                        ui.label('2️⃣ Ảnh Phụ 1').classes('text-xs font-bold')
                                        hien_thi_anh_vuong(item.get('img_sub1'))
                                        ui.upload(auto_upload=True, on_upload=lambda e, i=item['id']: self.handle_image_upload(e, i, 'img_sub1')).props('flat dense').classes('w-full h-8')
                                    with ui.column().classes('gap-1'):
                                        ui.label('3️⃣ Ảnh Design').classes('text-xs font-bold')
                                        hien_thi_anh_vuong(item.get('img_design'))
                                        ui.upload(auto_upload=True, on_upload=lambda e, i=item['id']: self.handle_image_upload(e, i, 'img_design')).props('flat dense').classes('w-full h-8')
                                        if o.get('trang_thai') == "Đang thiết kế":
                                            ui.button('🚀 Gửi duyệt', on_click=lambda: self.update_status_and_reload('Chờ duyệt thiết kế')).props('dense size=sm color=purple')

                            else: # TGTĐ
                                with ui.grid(columns=5).classes('w-full gap-4'):
                                    with ui.column().classes('gap-1'):
                                        ui.label(item.get('ten_san_pham')).classes('font-bold text-sm')
                                        ui.label(f"{item.get('mau')} / {item.get('size')}").classes('text-xs text-slate-500')
                                        ui.label(f"YC: {item.get('kieu_theu')}").classes('text-xs text-red-500 wrap')
                                    with ui.column().classes('gap-1'):
                                        ui.label('1️⃣ Ảnh Gốc').classes('text-xs font-bold')
                                        hien_thi_anh_vuong(item.get('img_main'))
                                        ui.upload(auto_upload=True, on_upload=lambda e, i=item['id']: self.handle_image_upload(e, i, 'img_main')).props('flat dense').classes('w-full h-8')
                                    with ui.column().classes('gap-1'):
                                        ui.label('2️⃣ Kết quả AI').classes('text-xs font-bold')
                                        hien_thi_anh_vuong(item.get('img_sub1'))
                                        ui.button('✨ Gen AI', on_click=lambda i=item: self.handle_gen_ai(i['id'], f"{i['ten_san_pham']} {i['kieu_theu']}", i['img_main'])).props('dense size=sm color=blue')
                                    with ui.column().classes('gap-1'):
                                        ui.label('3️⃣ Design').classes('text-xs font-bold')
                                        hien_thi_anh_vuong(item.get('img_design'))
                                        ui.upload(auto_upload=True, on_upload=lambda e, i=item['id']: self.handle_image_upload(e, i, 'img_design')).props('flat dense').classes('w-full h-8')
                                        if o.get('trang_thai') == "Đang thiết kế":
                                            ui.button('🚀 Duyệt', on_click=lambda: self.update_status_and_reload('Chờ duyệt thiết kế')).props('dense size=sm color=purple')
                                    with ui.column().classes('gap-1'):
                                        ui.label('4️⃣ File Thêu').classes('text-xs font-bold')
                                        if item.get('img_sub2'): ui.link('💾 Tải File', item.get('img_sub2')).classes('text-xs')
                                        else: ui.label('Trống').classes('text-xs italic')
                                        ui.upload(auto_upload=True, on_upload=lambda e, i=item['id']: self.handle_image_upload(e, i, 'img_sub2')).props('flat dense').classes('w-full h-8')

                            # FEEDBACK SECTION
                            ui.separator().classes('my-2')
                            ui.label('🛠️ Yêu cầu sửa / Feedback khách hàng').classes('text-sm font-bold text-slate-700')
                            
                            with ui.row().classes('w-full gap-4 items-start no-wrap'):
                                with ui.column().classes('flex-1 gap-2'):
                                    txt_feedback = ui.textarea(value=item.get('yeu_cau_sua'), placeholder='Nhập nội dung sửa...') \
                                        .classes('w-full bg-yellow-50 text-sm').props('dense rows=3 outlined')
                                    
                                    ui.button('💾 Lưu Note & Chuyển trạng thái', 
                                              on_click=lambda _, i=item, t=txt_feedback: handle_save_feedback(i, t.value)) \
                                        .props('dense no-caps color=indigo icon=save').classes('w-fit')

                                with ui.column().classes('w-[130px] border p-1 rounded bg-white items-center shrink-0'):
                                    ui.label('Feedback 1').classes('text-[10px] text-slate-400')
                                    hien_thi_anh_vuong(item.get('img_sua_1'))
                                    ui.upload(auto_upload=True, on_upload=lambda e, i=item['id']: self.handle_image_upload(e, i, 'img_sua_1')) \
                                        .props('flat dense size=sm').classes('w-full')

                                with ui.column().classes('w-[130px] border p-1 rounded bg-white items-center shrink-0'):
                                    ui.label('Feedback 2').classes('text-[10px] text-slate-400')
                                    hien_thi_anh_vuong(item.get('img_sua_2'))
                                    ui.upload(auto_upload=True, on_upload=lambda e, i=item['id']: self.handle_image_upload(e, i, 'img_sua_2')) \
                                        .props('flat dense size=sm').classes('w-full')

    # --- HELPERS CHUNG ---
    def _clean_data(self, df):
        if df.empty: return df
        return df.astype(object).where(pd.notnull(df), None)

    def render_mini_kpi(self, label, value, color_class, ref=None):
        with ui.column().classes('gap-0 items-center'):
            ui.label(label).classes('text-[10px] text-slate-500')
            lbl = ui.label(value).classes(f'text-sm font-bold {color_class}')
            if ref: setattr(self, ref, lbl)

    def refresh_data(self):
        self.df_original = fetch_all_orders()
        if self.df_original.empty:
            ui.notify('Không có dữ liệu', type='warning')
            return

        today = datetime.now().date()
        def process_row(row):
            deadline_str = ""
            is_urgent = False
            try:
                if row.get('ngay_tra'):
                    d_tra = pd.to_datetime(row['ngay_tra']).date()
                    deadline_str = d_tra.strftime("%d/%m")
                    not_done = str(row.get('trang_thai')) not in (STATUS_DONE + STATUS_CANCEL)
                    if not_done and row.get('co_hen_ngay') and d_tra <= today:
                        is_urgent = True
                        deadline_str = f"🚨 {deadline_str}"
            except: pass
            tags = row.get('tags')
            tags_str = ", ".join(tags) if isinstance(tags, list) else ""
            return pd.Series([is_urgent, deadline_str, tags_str])

        self.df_original[['is_urgent', 'deadline_str', 'tags_str']] = self.df_original.apply(process_row, axis=1)
        self.df_original['date_dat_obj'] = pd.to_datetime(self.df_original['ngay_dat'], errors='coerce').dt.date
        self.df_original['date_tra_obj'] = pd.to_datetime(self.df_original['ngay_tra'], errors='coerce').dt.date
        self.apply_filters()

    def apply_filters(self):
        df = self.df_original.copy()
        if df.empty: return
        s = self.filter_search.value
        if s:
            s = s.lower()
            df = df[df['ma_don'].str.lower().str.contains(s) | df['ten_khach'].str.lower().str.contains(s) | df['sdt'].str.contains(s)]

        if self.filter_status.value: df = df[df['trang_thai'].isin(self.filter_status.value)]
        if self.filter_shop.value: df = df[df['shop'].isin(self.filter_shop.value)]
        if self.chk_urgent.value: df = df[df['is_urgent'] == True]
        if self.chk_not_printed.value: df = df[(df['da_in'].isna()) | (df['da_in'] == False)]
        
        if self.date_dat_from.value:
            d = datetime.strptime(self.date_dat_from.value, '%Y-%m-%d').date()
            df = df[df['date_dat_obj'] >= d]
        if self.date_dat_to.value:
            d = datetime.strptime(self.date_dat_to.value, '%Y-%m-%d').date()
            df = df[df['date_dat_obj'] <= d]

        cols_to_drop = ['date_dat_obj', 'date_tra_obj']
        df_clean_export = df.drop(columns=[c for c in cols_to_drop if c in df.columns], errors='ignore')

        df_final = self._clean_data(df_clean_export)
        self.grid.options['rowData'] = df_final.to_dict('records')
        self.grid.update()
        
        self.update_kpis(df)
        self.update_reminders(df)

    def update_kpis(self, df):
        total = len(df)
        done = len(df[df['trang_thai'].isin(STATUS_DONE)])
        cancel = len(df[df['trang_thai'].isin(STATUS_CANCEL)])
        processing = total - done - cancel

        self.kpi_total.text = str(total)
        self.kpi_done.text = str(done)
        self.kpi_cancel.text = str(cancel)
        self.kpi_processing.text = str(processing)
        
        df_valid = df[~df['trang_thai'].isin(STATUS_CANCEL)]
        dt_ban_hang = df_valid['thanh_tien'].sum()
        dt_coc = df_valid['da_coc'].sum()
        self.kpi_ban_hang.text = f"{dt_ban_hang:,.0f} đ"
        self.kpi_coc.text = f"{dt_coc:,.0f} đ"
        
        def calc_thuc_nhan(row):
            if row['trang_thai'] in STATUS_DONE: return row['thanh_tien']
            return row['da_coc']
        dt_thuc_nhan = df_valid.apply(calc_thuc_nhan, axis=1).sum() if not df_valid.empty else 0
        self.kpi_thuc_nhan.text = f"{dt_thuc_nhan:,.0f} đ"

    def update_reminders(self, _=None):
        """
        Cập nhật box Nhắc việc quan trọng.
        Lưu ý: Dùng self.df_original để tính toán trên TOÀN BỘ dữ liệu, 
        không bị ảnh hưởng bởi bộ lọc search/status bên phải.
        """
        self.alert_today.clear()
        self.alert_tomorrow.clear()
        
        if self.df_original.empty: return

        # 1. Lấy data chưa xong từ DF GỐC (Logic chuẩn Streamlit cũ)
        ignore_statuses = STATUS_DONE + STATUS_CANCEL
        # Lọc các đơn chưa hoàn thành/hủy
        df_pending = self.df_original[~self.df_original['trang_thai'].isin(ignore_statuses)]
        
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        
        # 2. Tính toán
        # - Đơn Hẹn Trả Hôm Nay: Phải có hẹn ngày (True) VÀ Ngày trả = Hôm nay
        df_urgent_today = df_pending.loc[
            (df_pending['co_hen_ngay'] == True) & 
            (df_pending['date_tra_obj'] == today)
        ]
        
        # - Đơn Trả Ngày Mai: Chỉ cần Ngày trả = Mai (Không cần check có hẹn hay không)
        df_due_tomorrow = df_pending.loc[
            (df_pending['date_tra_obj'] == tomorrow)
        ]

        # 3. Render UI - BOX HÔM NAY
        with self.alert_today:
            count_today = len(df_urgent_today)
            if count_today > 0:
                # Tương đương st.error
                with ui.row().classes('w-full items-center gap-2 text-red-800 bg-red-100 p-2 rounded border border-red-200'):
                    ui.label(f"🔥 HÔM NAY: {count_today} đơn hẹn gấp!").classes('font-bold text-xs')
                
                # Tương đương st.expander
                with ui.expansion('Xem chi tiết', icon='list').classes('w-full text-xs text-red-800 bg-white border border-red-100 rounded'):
                    with ui.column().classes('gap-1 p-2'):
                        for _, row in df_urgent_today.iterrows():
                            ui.label(f"• {row['ma_don']} | {row['ten_khach']}").classes('text-[10px] ml-1')
            else:
                # Tương đương st.success
                with ui.row().classes('w-full items-center gap-2 text-green-800 bg-green-100 p-2 rounded border border-green-200'):
                    ui.icon('thumb_up', size='xs')
                    ui.label("Hôm nay: Không có đơn hẹn gấp.").classes('font-bold text-xs')

        # 4. Render UI - BOX NGÀY MAI
        with self.alert_tomorrow:
            count_tomorrow = len(df_due_tomorrow)
            if count_tomorrow > 0:
                # Tương đương st.warning
                with ui.row().classes('w-full items-center gap-2 text-orange-900 bg-orange-100 p-2 rounded border border-orange-200'):
                    ui.label(f"⏳ NGÀY MAI: {count_tomorrow} đơn cần trả.").classes('font-bold text-xs')
                
                with ui.expansion('Xem chi tiết', icon='list').classes('w-full text-xs text-orange-900 bg-white border border-orange-100 rounded'):
                    with ui.column().classes('gap-1 p-2'):
                        for _, row in df_due_tomorrow.iterrows():
                            icon_hen = "🚨" if row.get('co_hen_ngay') else ""
                            ui.label(f"• {icon_hen} {row['ma_don']} | {row['ten_khach']}").classes('text-[10px] ml-1')
            else:
                # Tương đương st.info
                with ui.row().classes('w-full items-center gap-2 text-blue-800 bg-blue-100 p-2 rounded border border-blue-200'):
                    ui.icon('coffee', size='xs')
                    ui.label("Ngày mai: Chưa có lịch trả hàng.").classes('font-bold text-xs')
    async def update_selection_count(self):
        rows = await self.grid.get_selected_rows()
        self.lbl_selected_count.text = f"Đã chọn: {len(rows)}"

    async def bulk_print(self):
        rows = await self.grid.get_selected_rows()
        if not rows:
            ui.notify('Vui lòng chọn ít nhất 1 đơn hàng!', type='warning')
            return
            
        ma_list = [r['ma_don'] for r in rows]
        data_to_print = []
        invalid_list = []
        
        ui.notify(f'Đang kiểm tra {len(ma_list)} đơn hàng...', spinner=True)
        
        for ma in ma_list:
            o, i = get_order_details(ma)
            if not o: continue
            
            can_print, msg = self.check_print_permission(o)
            if not can_print:
                invalid_list.append(f"{ma}: {msg}")
            else:
                data_to_print.append({"order_info": o, "items": i})

        # Nếu có bất kỳ đơn nào không đủ điều kiện -> Không cho in cả list
        if invalid_list:
            msg_full = "⚠️ Không thể in bulk vì có đơn chưa đủ điều kiện:\n" + "\n".join(invalid_list[:5])
            if len(invalid_list) > 5: msg_full += f"\n... và {len(invalid_list)-5} đơn khác."
            
            with ui.dialog() as dialog, ui.card():
                ui.label('⚠️ Lỗi in hàng loạt').classes('text-lg font-bold text-red-600')
                ui.label(msg_full).classes('whitespace-pre-wrap text-sm')
                ui.button('Đã hiểu', on_click=dialog.close).classes('w-full')
            dialog.open()
            return

        # Nếu tất cả hợp lệ -> Tiến hành in
        for ma in ma_list:
            mark_order_as_printed(ma)
            
        html = generate_combined_print_html(data_to_print)
        # Sử dụng base64 để tránh lỗi ký tự đặc biệt khi download HTML trực tiếp
        import base64
        b64_html = base64.b64encode(html.encode('utf-8')).decode()
        ui.download(f'data:text/html;base64,{b64_html}', f'In_Gop_{len(ma_list)}_don.html')
        ui.notify(f'🎉 Đã chuẩn bị bản in cho {len(ma_list)} đơn hàng!', type='positive')
        self.refresh_data()

    async def bulk_export_excel(self):
        rows = await self.grid.get_selected_rows()
        if not rows:
            ui.notify('Vui lòng chọn đơn hàng!', type='warning')
            return
            
        ma_list = [r['ma_don'] for r in rows]
        data = []
        allow_auto_update = ["Mới", "Đã xác nhận", "New"]
        
        ui.notify('Đang chuẩn bị dữ liệu Excel...', spinner=True)
        
        for ma in ma_list:
            o, i = get_order_details(ma)
            if o:
                data.append({"order_info": o, "items": i})
                
                # Logic: Xuất Excel -> Chuyển sang "Chờ sản xuất" (Giống bản Streamlit)
                if o.get('trang_thai') in allow_auto_update:
                    update_order_info(ma, {"trang_thai": "Chờ sản xuất"})
        
        buffer = export_orders_to_excel(data)
        if buffer:
            fname = f"Excel_Nobita_{datetime.now().strftime('%d_%m')}.xlsx"
            ui.download(buffer, fname)
            ui.notify('✅ Đã xuất Excel và cập nhật trạng thái!', type='positive')
            self.refresh_data()
        else:
            ui.notify('Lỗi khi tạo file Excel', type='negative')

    def confirm_order(self):
        self.update_status_and_reload("Đã xác nhận")

    def update_status_and_reload(self, status):
        if self.current_order:
            self.current_order['trang_thai'] = status
            self.save_changes()

    def save_changes(self):
        if not self.current_order: return
        try:
            ma = self.current_order.get('ma_don')
            tong = float(self.current_order.get('thanh_tien') or 0)
            coc = float(self.current_order.get('da_coc') or 0)
            
            update_data = {
                'shop': self.current_order.get('shop'),
                'ten_khach': self.current_order.get('ten_khach'),
                'sdt': self.current_order.get('sdt'),
                'dia_chi': self.current_order.get('dia_chi'),
                'trang_thai': self.current_order.get('trang_thai'),
                'ngay_dat': self.current_order.get('ngay_dat'),
                'ngay_tra': self.current_order.get('ngay_tra'),
                'thanh_tien': tong,
                'da_coc': coc,
                'con_lai': tong - coc,
                'tags': self.current_order.get('tags'),
                'ghi_chu': self.current_order.get('ghi_chu')
            }
            update_order_info(ma, update_data)
            
            for item in self.current_items:
                update_item_field(item['id'], 'mau', item.get('mau'))
                update_item_field(item['id'], 'size', item.get('size'))
                update_item_field(item['id'], 'so_luong', item.get('so_luong'))
                update_item_field(item['id'], 'kieu_theu', item.get('kieu_theu'))

            ui.notify('✅ Đã lưu thay đổi!')
            self.refresh_data()
            self.render_detail_view()
        except Exception as e:
            ui.notify(f'Lỗi lưu: {str(e)}', type='negative')