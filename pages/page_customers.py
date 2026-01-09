from nicegui import ui
import pandas as pd
import traceback
from backend.data_handler import (
    lay_danh_sach_khach_hang, 
    fetch_all_orders, 
    lay_lich_su_khach,
    get_order_details,
    ORDER_STATUSES,
    PRODUCTION_TAGS,
    update_order_info,
    update_item_field,
    upload_image_to_supabase,
    update_item_image
)
from pages.components import hien_thi_anh_vuong

class CustomerPage:
    def __init__(self):
        self.current_history_df = pd.DataFrame()
        self.build_ui()

    def build_ui(self):
        # ======================================================
        # PHẦN 1: DANH SÁCH KHÁCH HÀNG (TOP)
        # ======================================================
        # Remove h-[60vh] to let it grow naturally
        with ui.column().classes('w-full h-[65vh] p-0 gap-2 mb-6'):
            
            ui.label('👥 Quản lý Khách hàng').classes('text-2xl font-bold text-slate-700')

            # 1.1. FILTER
            with ui.row().classes('w-full gap-2 items-center'):
                with ui.card().classes('flex-1 p-2 shadow-sm flex-row gap-2 items-center'):
                    self.input_search = ui.input(
                        placeholder='🔍 Tìm Tên hoặc SĐT...',
                        on_change=self.load_data
                    ).props('outlined dense debounce=500').classes('flex-1')
                    
                    self.select_rank = ui.select(
                        ["Tất cả", "Bạc (< 500k)", "🥇 Vàng (500k-5tr)", "💎 Kim Cương (> 5tr)"],
                        value="Tất cả", label="Hạng", on_change=self.load_data
                    ).props('dense options-dense').classes('w-48')
                    
                    self.num_min_spend = ui.number(
                        "Chi tiêu tối thiểu", value=0, step=500000, on_change=self.load_data
                    ).props('dense').classes('w-40')

                    ui.button('Load', on_click=self.load_data).props('dense')

            # 1.2. TABLE KHÁCH HÀNG (TEST với ui.table thay vì aggrid)
            self.table_columns = [
                {'name': 'id', 'label': 'ID', 'field': 'id', 'align': 'left'},
                {'name': 'ho_ten', 'label': 'Họ Tên', 'field': 'ho_ten', 'align': 'left'},
                {'name': 'sdt', 'label': 'SĐT', 'field': 'sdt', 'align': 'left'},
                {'name': 'dia_chi', 'label': 'Địa chỉ', 'field': 'dia_chi', 'align': 'left'},
                {'name': 'tong_tieu_str', 'label': 'Tổng Tiêu', 'field': 'tong_tieu_str', 'align': 'right'},
                {'name': 'so_don_hang', 'label': 'Số Đơn', 'field': 'so_don_hang', 'align': 'center'},
                {'name': 'nguon_shop', 'label': 'Nguồn', 'field': 'nguon_shop', 'align': 'left'},
            ]
            self.table_customers = ui.table(
                columns=self.table_columns,
                rows=[],
                row_key='id',
                pagination=20,
                selection='single'
            ).classes('w-full').style('height: 500px')
            
            self.table_customers.on('selection', self.on_customer_select_table)

        # ======================================================
        # PHẦN 2: CHI TIẾT KHÁCH & LỊCH SỬ (BOTTOM - AUTO HEIGHT)
        # ======================================================
        self.detail_container = ui.column().classes('w-full bg-slate-50 border-t p-4 pb-10 gap-6')
        self.detail_container.visible = False  # Hidden by default
        
        with self.detail_container:
            # 2.1. PROFILE CARD
            ui.label('📜 Hồ sơ & Lịch sử mua hàng').classes('text-xl font-bold text-blue-800')
            
            with ui.card().classes('w-full p-4 border-l-4 border-blue-500 shadow-md bg-white'):
                with ui.row().classes('w-full justify-between items-center'):
                    # Info Left
                    with ui.column().classes('gap-1'):
                        ui.label('Khách hàng').classes('text-xs text-slate-500 uppercase font-bold')
                        with ui.row().classes('items-center gap-2'):
                            self.lbl_name = ui.label('').classes('text-3xl font-bold text-slate-800')
                            self.badge_rank = ui.label('').classes('px-3 py-1 rounded-full text-xs font-bold border shadow-sm')
                        
                        with ui.row().classes('items-center gap-2 mt-1'):
                            ui.icon('location_on', size='xs').classes('text-slate-400')
                            self.lbl_address = ui.label('').classes('text-sm text-slate-600 italic')

                    # Metrics Right
                    with ui.row().classes('gap-10'):
                        with ui.column().classes('items-end'):
                            ui.label('Tổng chi tiêu').classes('text-xs text-slate-500 uppercase font-bold')
                            self.lbl_total_spend = ui.label('').classes('text-3xl font-bold text-green-700')
                            ui.label('Real-time check').classes('text-[10px] text-green-500 bg-green-50 px-1 rounded border border-green-200')
                        
                        with ui.column().classes('items-end'):
                            ui.label('Số đơn hàng').classes('text-xs text-slate-500 uppercase font-bold')
                            self.lbl_order_count = ui.label('').classes('text-3xl font-bold text-blue-600')

            # 2.2. HISTORY TABLE (Lịch sử đơn hàng)
            ui.label('👇 Lịch sử đơn hàng (Click để xem chi tiết)').classes('font-bold text-slate-500 mt-2')
            
            self.history_columns = [
                {'name': 'ma_don', 'label': 'Mã Đơn', 'field': 'ma_don', 'align': 'left'},
                {'name': 'created_at', 'label': 'Ngày tạo', 'field': 'created_at', 'align': 'left'},
                {'name': 'thanh_tien_str', 'label': 'Giá trị', 'field': 'thanh_tien_str', 'align': 'right'},
                {'name': 'trang_thai', 'label': 'Trạng thái', 'field': 'trang_thai', 'align': 'left'},
                {'name': 'shop', 'label': 'Shop', 'field': 'shop', 'align': 'left'},
            ]
            self.table_history = ui.table(
                columns=self.history_columns,
                rows=[],
                row_key='ma_don',
                selection='single',
                pagination=10
            ).classes('w-full').style('max-height: 300px')
            
            self.table_history.on('selection', self.on_order_select_table)

            # 2.3. ORDER DETAIL (Full View)
            self.order_detail_container = ui.column().classes('w-full mt-4 bg-white border border-slate-200 rounded-lg shadow-sm')
            self.order_detail_container.visible = False

        self.load_data()

    def _clean_data(self, df):
        """Hàm làm sạch dữ liệu chuẩn để tránh lỗi JSON của Grid"""
        if df.empty: return df
        return df.astype(object).where(pd.notnull(df), "")

    def refresh_history_table(self):
        """Refresh the order history table for the currently selected customer"""
        if not hasattr(self, 'current_customer_id') or not self.current_customer_id:
            return
        
        df_hist = lay_lich_su_khach(self.current_customer_id)
        if not df_hist.empty:
            df_hist['thanh_tien_str'] = df_hist['thanh_tien'].apply(lambda x: f"{float(x or 0):,.0f} đ")
            if 'created_at' in df_hist.columns:
                df_hist['created_at'] = df_hist['created_at'].astype(str)
            
            df_hist = self._clean_data(df_hist)
            self.table_history.rows = df_hist.to_dict('records')
        else:
            self.table_history.rows = []
        
        self.table_history.update()

    def load_data(self):
        try:
            search = self.input_search.value
            df_cust = lay_danh_sach_khach_hang(search)
            df_orders = fetch_all_orders()
            
            # --- TÍNH TOÁN DỮ LIỆU ---
            if not df_orders.empty and not df_cust.empty:
                stats = df_orders.groupby("khach_hang_id").agg({
                    "thanh_tien": "sum",
                    "ma_don": "count"
                }).reset_index()
                stats.columns = ["id", "real_tong_tieu", "real_so_don"] # Rename nhanh
                
                df_cust = pd.merge(df_cust, stats, on="id", how="left")
                df_cust["tong_tieu"] = df_cust["real_tong_tieu"].fillna(0)
                df_cust["so_don_hang"] = df_cust["real_so_don"].fillna(0)
            else:
                if not df_cust.empty:
                    df_cust["tong_tieu"] = 0
                    df_cust["so_don_hang"] = 0
            
            # Filter
            min_spend = self.num_min_spend.value or 0
            if min_spend > 0 and not df_cust.empty:
                df_cust = df_cust[df_cust['tong_tieu'] >= min_spend]
                
            rank_opt = self.select_rank.value
            if rank_opt != "Tất cả" and not df_cust.empty:
                if "Bạc" in rank_opt: df_cust = df_cust[df_cust['tong_tieu'] < 500000]
                elif "Vàng" in rank_opt: df_cust = df_cust[(df_cust['tong_tieu'] >= 500000) & (df_cust['tong_tieu'] < 5000000)]
                elif "Kim Cương" in rank_opt: df_cust = df_cust[df_cust['tong_tieu'] >= 5000000]

            # --- RENDER GRID ---
            if not df_cust.empty:
                df_display = df_cust.copy()
                df_display['tong_tieu_str'] = df_display['tong_tieu'].apply(lambda x: f"{float(x or 0):,.0f} đ")
                
                df_display = self._clean_data(df_display)
                records = df_display.to_dict('records')
                
                # Update ui.table rows
                self.table_customers.rows = records
                self.table_customers.update()
                ui.notify(f"Đã tải {len(df_display)} khách hàng", type='positive')
            else:
                self.table_customers.rows = []
                self.table_customers.update()
                ui.notify("Không tìm thấy khách hàng nào.", type='warning')
        except Exception as e:
            traceback.print_exc()
            ui.notify(f"Lỗi tải dữ liệu: {e}", type='negative')

    def on_customer_select_table(self, e):
        """Xử lý khi chọn khách hàng từ bảng (ui.table selection)"""
        try:
            ui.notify("DEBUG: Selection handler triggered", type='info')
            
            # selection event: e.args contains selected rows list
            # e.selection contains the list of selected row dicts
            selected = self.table_customers.selected
            ui.notify(f"DEBUG: Selected = {selected}", type='info')
            
            if not selected:
                return
            row = selected[0]  # First selected row
            if not row: return
            
            ui.notify(f"DEBUG: Row = {row.get('ho_ten', 'N/A')}", type='positive')
            
            # UI Transitions - Use .visible property instead of CSS classes
            self.detail_container.visible = True
            self.order_detail_container.visible = False
            self.table_history.rows = []
            self.table_history.update()
            
            # Fill Profile
            self.lbl_name.text = str(row.get('ho_ten', ''))
            self.lbl_address.text = str(row.get('dia_chi', ''))
            self.lbl_total_spend.text = str(row.get('tong_tieu_str', '0 đ'))
            self.lbl_order_count.text = str(row.get('so_don_hang', 0))
            
            # Rank Style
            try: 
                total = float(row.get('tong_tieu', 0))
            except: 
                total = 0
            
            if total >= 5000000:
                self.badge_rank.text = '💎 Kim Cương'
                self.badge_rank.classes('bg-cyan-50 text-cyan-900 border-cyan-200', remove='bg-yellow-50 bg-slate-100')
            elif total >= 500000:
                self.badge_rank.text = '🥇 Vàng'
                self.badge_rank.classes('bg-yellow-50 text-yellow-800 border-yellow-200', remove='bg-cyan-50 bg-slate-100')
            else:
                self.badge_rank.text = 'Bạc'
                self.badge_rank.classes('bg-slate-100 text-slate-600 border-slate-300', remove='bg-cyan-50 bg-yellow-50')

            # Load History Table
            kid = row.get('id')
            self.current_customer_id = kid  # Store for refresh
            if kid:
                df_hist = lay_lich_su_khach(kid)
                if not df_hist.empty:
                    df_hist['thanh_tien_str'] = df_hist['thanh_tien'].apply(lambda x: f"{float(x or 0):,.0f} đ")
                    if 'created_at' in df_hist.columns:
                        df_hist['created_at'] = df_hist['created_at'].astype(str)
                    
                    df_hist = self._clean_data(df_hist)
                    self.table_history.rows = df_hist.to_dict('records')
                else:
                    self.table_history.rows = []
                
                self.table_history.update()
                ui.run_javascript(f'window.scrollTo({{ top: document.body.scrollHeight, behavior: "smooth" }});')

        except Exception as ex:
            print(f"Table Click Error: {ex}")
            traceback.print_exc()

    def on_customer_select(self, e):
        """Xử lý khi click vào bảng khách hàng"""
        # cellClicked trả về data trong e.args['data']
        try:
            row = e.args.get('data')
            if not row: return
            
            # UI Transitions
            self.detail_container.remove_classes('hidden')
            self.order_detail_container.add_classes('hidden') # Reset đơn cũ
            self.grid_history.options['rowData'] = []
            self.grid_history.update()
            
            # 1. Fill Profile
            self.lbl_name.text = str(row.get('cname', ''))
            self.lbl_address.text = str(row.get('caddr', ''))
            self.lbl_total_spend.text = str(row.get('ctotal', '0 đ'))
            self.lbl_order_count.text = str(row.get('ccount', 0))
            
            # Rank Style
            try: total = float(row.get('tong_tieu', 0)) # Cần cột gốc nếu có, ở đây lấy tạm
            except: 
                # Parse từ string "1,000,000 đ"
                s = str(row.get('ctotal', '0')).replace(',', '').replace(' đ', '')
                total = float(s) if s.replace('.','').isdigit() else 0
            
            if total >= 5000000:
                self.badge_rank.text = '💎 Kim Cương'
                self.badge_rank.classes('bg-cyan-50 text-cyan-900 border-cyan-200', remove='bg-yellow-50 bg-slate-100')
            elif total >= 500000:
                self.badge_rank.text = '🥇 Vàng'
                self.badge_rank.classes('bg-yellow-50 text-yellow-800 border-yellow-200', remove='bg-cyan-50 bg-slate-100')
            else:
                self.badge_rank.text = 'Bạc'
                self.badge_rank.classes('bg-slate-100 text-slate-600 border-slate-300', remove='bg-cyan-50 bg-yellow-50')

            # 2. Load History Grid
            kid = row.get('cid')
            if kid:
                df_hist = lay_lich_su_khach(kid)
                if not df_hist.empty:
                    df_hist['thanh_tien_str'] = df_hist['thanh_tien'].apply(lambda x: f"{float(x or 0):,.0f} đ")
                    # Ép kiểu ngày thành chuỗi để Grid không lỗi
                    if 'created_at' in df_hist.columns:
                        df_hist['created_at'] = df_hist['created_at'].astype(str)
                    
                    df_hist = self._clean_data(df_hist)
                    self.grid_history.options['rowData'] = df_hist.to_dict('records')
                
                self.grid_history.update()
                
                # Cuộn xuống phần chi tiết cho mượt
                ui.run_javascript(f'window.scrollTo({{ top: document.body.scrollHeight, behavior: "smooth" }});')

        except Exception as ex:
            print(f"Click Error: {ex}")

    def on_order_select(self, e):
        """Sự kiện click vào bảng lịch sử (old aggrid handler)"""
        try:
            row = e.args.get('data')
            if not row: return
            
            ma_don = row.get('ma_don')
            if ma_don:
                self.render_full_order_detail(ma_don)
                ui.run_javascript(f'window.scrollTo({{ top: document.body.scrollHeight, behavior: "smooth" }});')
        except: pass

    def on_order_select_table(self, e):
        """Sự kiện chọn đơn hàng từ bảng lịch sử (ui.table selection)"""
        try:
            selected = self.table_history.selected
            if not selected:
                return
            row = selected[0]
            if not row: return
            
            ma_don = row.get('ma_don')
            if ma_don:
                self.render_full_order_detail(ma_don)
                ui.run_javascript(f'window.scrollTo({{ top: document.body.scrollHeight, behavior: "smooth" }});')
        except Exception as ex:
            print(f"Order Select Error: {ex}")
            traceback.print_exc()

    def render_full_order_detail(self, ma_don):
        """Vẽ chi tiết đơn hàng (Copy từ OrderPage render_detail_view)"""
        self.order_detail_container.visible = True
        self.order_detail_container.clear()
        
        order, items = get_order_details(ma_don)
        if not order: return
        
        # Store for later use
        self.current_order = order
        self.current_items = items
        
        # Data Clean
        if not isinstance(order.get('tags'), list): order['tags'] = []
        shop = order.get('shop') or 'Inside'
        
        # Helper: Lưu Note
        def handle_save_feedback(item_obj, new_note):
            from backend.data_handler import update_item_field, update_order_info
            update_item_field(item_obj['id'], 'yeu_cau_sua', new_note)
            update_order_info(order['ma_don'], {"trang_thai": "Chờ sản xuất"})
            ui.notify('✅ Đã lưu Note và chuyển trạng thái!', type='positive')
            self.render_full_order_detail(ma_don)  # Refresh
        
        # Helper: Upload ảnh
        async def handle_image_upload_here(e, item_id, field):
            from backend.data_handler import upload_image_to_supabase, update_item_image
            try:
                # Lấy dữ liệu file từ event (Hỗ trợ e.file và e.content)
                content_obj = getattr(e, 'file', None) or getattr(e, 'content', None)
                if not content_obj and hasattr(e, 'args'):
                    content_obj = e.args.get('file') or e.args.get('content')
                
                if not content_obj:
                    raise AttributeError(f"Không tìm thấy file trong event {type(e)}")

                # Đọc dữ liệu (Hỗ trợ cả sync và async read)
                if hasattr(content_obj, 'read'):
                    res = content_obj.read()
                    if hasattr(res, '__await__'):
                        file_data = await res
                    else:
                        file_data = res
                else:
                    file_data = content_obj # Đã là bytes

                fname = f"item_{item_id}_{field}_{int(__import__('time').time())}.png"
                url = upload_image_to_supabase(file_data, fname)
                if url:
                    update_item_image(item_id, url, field)
                    ui.notify('✅ Upload thành công!', type='positive')
                    self.render_full_order_detail(ma_don)
                else:
                    ui.notify('⚠️ Lỗi upload thất bại', type='negative')
            except Exception as ex:
                print(f"ERROR UPLOAD CUSTOMER: {traceback.format_exc()}")
                ui.notify(f'Lỗi upload: {str(ex)}', type='negative')

        # Helper: Save order
        def save_order_changes():
            from backend.data_handler import update_order_info
            update_data = {
                'shop': order.get('shop'),
                'trang_thai': order.get('trang_thai'),
                'ten_khach': order.get('ten_khach'),
                'sdt': order.get('sdt'),
                'dia_chi': order.get('dia_chi'),
                'ngay_dat': order.get('ngay_dat'),
                'ngay_tra': order.get('ngay_tra'),
                'thanh_tien': order.get('thanh_tien'),
                'da_coc': order.get('da_coc'),
                'tags': order.get('tags'),
                'ghi_chu': order.get('ghi_chu'),
            }
            update_order_info(order['ma_don'], update_data)
            ui.notify('✅ Đã lưu thay đổi!', type='positive')
            
            # Refresh history table
            self.refresh_history_table()
            # Refresh detail view
            self.render_full_order_detail(ma_don)

        with self.order_detail_container:
            # HEADER
            with ui.row().classes('w-full justify-between items-center mb-2 pb-2 border-b p-4 bg-slate-50'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('search', size='md').classes('text-blue-600')
                    ui.label(f"Chi tiết đơn hàng: {order.get('ma_don')}").classes('text-xl font-bold text-blue-800')
                    if order.get('da_in'): ui.chip('Đã in', icon='print', color='green').props('dense')

                with ui.row().classes('gap-2'):
                    ui.button('Mở trang chỉnh sửa', icon='edit', 
                              on_click=lambda: ui.open(f'/print/{order.get("ma_don")}', new_tab=True)).props('flat color=blue')
                    ui.button('Lưu Thay Đổi', icon='save', on_click=save_order_changes).classes('bg-blue-600 text-white')

            # BODY
            with ui.row().classes('w-full gap-6 items-start no-wrap p-4'):
                
                # === CỘT TRÁI: THÔNG TIN KHÁCH ===
                with ui.card().classes('w-[320px] p-4 shadow-sm gap-3 shrink-0 bg-slate-50'):
                    ui.label('� Thông tin đơn hàng').classes('font-bold text-slate-700')
                    
                    # Shop & Trạng thái
                    ui.select(["Inside", "TGTĐ", "Lanh Canh"], value=shop, label="Shop").bind_value(order, 'shop').classes('w-full').props('dense')
                    
                    st_opts = list(ORDER_STATUSES)
                    if order.get('trang_thai') not in st_opts: st_opts.append(order.get('trang_thai'))
                    ui.select(st_opts, value=order.get('trang_thai'), label="Trạng thái").bind_value(order, 'trang_thai').classes('w-full').props('dense options-dense')

                    # Info
                    ui.input('Tên khách', value=order.get('ten_khach')).bind_value(order, 'ten_khach').classes('w-full').props('dense')
                    ui.input('SĐT', value=order.get('sdt')).bind_value(order, 'sdt').classes('w-full').props('dense')
                    ui.textarea('Địa chỉ', value=order.get('dia_chi')).bind_value(order, 'dia_chi').classes('w-full').props('dense rows=2')
                    
                    # Date
                    with ui.row().classes('w-full'):
                        ui.input('Ngày đặt', value=str(order.get('ngay_dat'))[:10]).bind_value(order, 'ngay_dat').props('dense type=date').classes('w-1/2')
                        ui.input('Ngày trả', value=str(order.get('ngay_tra'))[:10]).bind_value(order, 'ngay_tra').props('dense type=date').classes('w-1/2')

                    ui.separator().classes('my-2')
                    
                    # Money
                    ui.label('💰 Tài chính').classes('font-bold text-slate-700')
                    with ui.column().classes('w-full gap-1'):
                        num_tong = ui.number('Tổng tiền', value=order.get('thanh_tien'), format='%.0f').bind_value(order, 'thanh_tien').classes('w-full').props('dense')
                        num_coc = ui.number('Đã cọc', value=order.get('da_coc'), format='%.0f').bind_value(order, 'da_coc').classes('w-full').props('dense')
                        
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
                    ui.select(list(set(PRODUCTION_TAGS + order['tags'])), value=order['tags'], multiple=True, label='Tags').bind_value(order, 'tags').classes('w-full').props('use-chips dense')
                    ui.input('Ghi chú', value=order.get('ghi_chu')).bind_value(order, 'ghi_chu').classes('w-full').props('dense')
                    
                    # Footer Button - Match page_orders.py
                    ui.separator().classes('my-1')
                    with ui.row().classes('w-full gap-2'):
                        if order.get('trang_thai') in ['Mới', 'New']:
                            def confirm_order():
                                update_order_info(order['ma_don'], {"trang_thai": "Chờ sản xuất"})
                                ui.notify('✅ Đã xác nhận đơn hàng!', type='positive')
                                self.refresh_history_table()
                                self.render_full_order_detail(ma_don)
                            ui.button('Xác nhận', on_click=confirm_order).classes('flex-1 bg-green-100 text-green-800')
                        ui.button('In Phiếu', icon='print', on_click=lambda: ui.open(f'/print/{order.get("ma_don")}', new_tab=True)).props('outline').classes('flex-1')
                        ui.button('Lưu', icon='save', on_click=save_order_changes).classes('flex-1 bg-blue-600 text-white')

                # === CỘT PHẢI: SẢN PHẨM ===
                with ui.column().classes('flex-1 gap-3 min-w-0'):
                    ui.label(f"🛒 Sản phẩm ({len(items)}) - {shop}").classes('font-bold text-slate-700 text-lg')
                    
                    if not items: ui.label('Chưa có sản phẩm').classes('italic text-slate-400')

                    for item in items:
                        with ui.card().classes('w-full p-3 border shadow-sm bg-slate-50'):
                            
                            # LAYOUT PHỤ THUỘC SHOP
                            if shop == "Lanh Canh":
                                with ui.grid(columns=3).classes('w-full gap-4'):
                                    with ui.column().classes('gap-1'):
                                        ui.label(item.get('ten_san_pham')).classes('font-bold')
                                        ui.label(f"{item.get('mau')} / {item.get('size')}").classes('text-sm text-slate-500')
                                        ui.label(f"SL: {item.get('so_luong')}").classes('text-sm')
                                    with ui.column().classes('gap-1'):
                                        ui.label('📸 SP Chính').classes('text-xs font-bold')
                                        hien_thi_anh_vuong(item.get('img_main'))
                                        ui.upload(auto_upload=True, on_upload=lambda e, i=item['id']: handle_image_upload_here(e, i, 'img_main')).props('flat dense').classes('w-full h-8')
                                    with ui.column().classes('gap-1'):
                                        ui.label('📝 Mẫu sửa đổi').classes('text-xs font-bold')
                                        hien_thi_anh_vuong(item.get('img_sub1'))
                                        ui.upload(auto_upload=True, on_upload=lambda e, i=item['id']: handle_image_upload_here(e, i, 'img_sub1')).props('flat dense').classes('w-full h-8')

                            elif shop == "Inside":
                                with ui.grid(columns=4).classes('w-full gap-4'):
                                    with ui.column().classes('gap-1'):
                                        ui.label(item.get('ten_san_pham')).classes('font-bold')
                                        ui.label(f"{item.get('mau')} / {item.get('size')}").classes('text-sm text-slate-500')
                                        ui.label(f"YC: {item.get('kieu_theu')}").classes('text-xs text-red-500')
                                    with ui.column().classes('gap-1'):
                                        ui.label('1️⃣ Ảnh Chính').classes('text-xs font-bold')
                                        hien_thi_anh_vuong(item.get('img_main'))
                                        ui.upload(auto_upload=True, on_upload=lambda e, i=item['id']: handle_image_upload_here(e, i, 'img_main')).props('flat dense').classes('w-full h-8')
                                    with ui.column().classes('gap-1'):
                                        ui.label('2️⃣ Ảnh Phụ 1').classes('text-xs font-bold')
                                        hien_thi_anh_vuong(item.get('img_sub1'))
                                        ui.upload(auto_upload=True, on_upload=lambda e, i=item['id']: handle_image_upload_here(e, i, 'img_sub1')).props('flat dense').classes('w-full h-8')
                                    with ui.column().classes('gap-1'):
                                        ui.label('3️⃣ Ảnh Design').classes('text-xs font-bold')
                                        hien_thi_anh_vuong(item.get('img_design'))
                                        ui.upload(auto_upload=True, on_upload=lambda e, i=item['id']: handle_image_upload_here(e, i, 'img_design')).props('flat dense').classes('w-full h-8')
                                        if order.get('trang_thai') == "Đang thiết kế":
                                            def send_for_review():
                                                update_order_info(order['ma_don'], {"trang_thai": "Chờ duyệt thiết kế"})
                                                ui.notify('✅ Đã gửi duyệt!', type='positive')
                                                self.refresh_history_table()
                                                self.render_full_order_detail(ma_don)
                                            ui.button('🚀 Gửi duyệt', on_click=send_for_review).props('dense size=sm color=purple')

                            else: # TGTĐ
                                with ui.grid(columns=5).classes('w-full gap-4'):
                                    with ui.column().classes('gap-1'):
                                        ui.label(item.get('ten_san_pham')).classes('font-bold text-sm')
                                        ui.label(f"{item.get('mau')} / {item.get('size')}").classes('text-xs text-slate-500')
                                        ui.label(f"YC: {item.get('kieu_theu')}").classes('text-xs text-red-500 wrap')
                                    with ui.column().classes('gap-1'):
                                        ui.label('1️⃣ Ảnh Gốc').classes('text-xs font-bold')
                                        hien_thi_anh_vuong(item.get('img_main'))
                                        ui.upload(auto_upload=True, on_upload=lambda e, i=item['id']: handle_image_upload_here(e, i, 'img_main')).props('flat dense').classes('w-full h-8')
                                    with ui.column().classes('gap-1'):
                                        ui.label('2️⃣ Kết quả AI').classes('text-xs font-bold')
                                        hien_thi_anh_vuong(item.get('img_sub1'))
                                    with ui.column().classes('gap-1'):
                                        ui.label('3️⃣ Design').classes('text-xs font-bold')
                                        hien_thi_anh_vuong(item.get('img_design'))
                                        ui.upload(auto_upload=True, on_upload=lambda e, i=item['id']: handle_image_upload_here(e, i, 'img_design')).props('flat dense').classes('w-full h-8')
                                        if order.get('trang_thai') == "Đang thiết kế":
                                            def send_for_review_tgtd():
                                                update_order_info(order['ma_don'], {"trang_thai": "Chờ duyệt thiết kế"})
                                                ui.notify('✅ Đã gửi duyệt!', type='positive')
                                                self.refresh_history_table()
                                                self.render_full_order_detail(ma_don)
                                            ui.button('🚀 Duyệt', on_click=send_for_review_tgtd).props('dense size=sm color=purple')
                                    with ui.column().classes('gap-1'):
                                        ui.label('4️⃣ File Thêu').classes('text-xs font-bold')
                                        if item.get('img_sub2'): ui.link('💾 Tải File', item.get('img_sub2')).classes('text-xs')
                                        else: ui.label('Trống').classes('text-xs italic')
                                        ui.upload(auto_upload=True, on_upload=lambda e, i=item['id']: handle_image_upload_here(e, i, 'img_sub2')).props('flat dense').classes('w-full h-8')

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
                                    ui.upload(auto_upload=True, on_upload=lambda e, i=item['id']: handle_image_upload_here(e, i, 'img_sua_1')) \
                                        .props('flat dense size=sm').classes('w-full')

                                with ui.column().classes('w-[130px] border p-1 rounded bg-white items-center shrink-0'):
                                    ui.label('Feedback 2').classes('text-[10px] text-slate-400')
                                    hien_thi_anh_vuong(item.get('img_sua_2'))
                                    ui.upload(auto_upload=True, on_upload=lambda e, i=item['id']: handle_image_upload_here(e, i, 'img_sua_2')) \
                                        .props('flat dense size=sm').classes('w-full')
