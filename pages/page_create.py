from nicegui import ui, run
from datetime import datetime
import json
import time

# --- IMPORT TỪ BACKEND ---
from backend.data_handler import (
    save_full_order,
    lay_danh_sach_khach_hang,
    STATUS_DONE
)
from backend.ai_logic import xuly_ai_gemini

class OrderCreatePage:
    def __init__(self):
        # 1. Khởi tạo State (Dữ liệu)
        # Thêm thong_tin_phu để match với Streamlit version
        self.items = [{"ten_sp": "", "mau": "", "size": "", "so_luong": 1, "kieu_theu": "", "thong_tin_phu": ""}]
        self.customer_list = [] # List khách hàng cho autocomplete
        
        # Load danh sách khách hàng ngay khi vào trang
        self.load_customers()
        
        # 2. Dựng giao diện
        self.build_ui()

    def load_customers(self):
        """Lấy danh sách khách hàng để gợi ý"""
        df = lay_danh_sach_khach_hang()
        if not df.empty:
            # Format: "0909xxx | Tên (Địa chỉ)"
            self.customer_list = df.apply(
                lambda x: f"{x['sdt']} | {x['ho_ten']} ({x['dia_chi']})", axis=1
            ).tolist()

    def build_ui(self):
        with ui.column().classes('w-full p-2 max-w-5xl mx-auto'): # Căn giữa, giới hạn chiều rộng cho đẹp
            ui.label('📝 Tạo Đơn Hàng Mới').classes('text-2xl font-bold text-slate-700 mb-4')

            # ======================================================
            # PHẦN 1: AI TRỢ LÝ (DẠNG CARD CỐ ĐỊNH)
            # ======================================================
            # Thay ui.expansion bằng ui.card để luôn hiển thị
            with ui.card().classes('w-full p-4 mb-4 border rounded-lg bg-blue-50 shadow-sm gap-3'):
                
                # Tiêu đề
                with ui.row().classes('w-full items-center gap-2'):
                    ui.icon('auto_awesome', size='sm').classes('text-blue-600')
                    ui.label('AI Trợ lý & Debugger').classes('font-bold text-slate-700 text-lg')

                # Ô nhập liệu (Input)
                # Thêm class 'mb-1' để tạo khoảng cách với nút bên dưới, tránh bị đè
                self.ai_input = ui.textarea(
                    placeholder="Paste đoạn chat vào đây (Ví dụ: 'Khách Tùng 090... áo trắng size L TGTD')...",
                ).classes('w-full bg-white').props('outlined rounded input-style="min-height: 80px;"') 
                
                # Hàng chứa nút bấm và Switch
                with ui.row().classes('w-full justify-between items-center'):
                    self.debug_toggle = ui.switch('Chế độ Debug').props('dense color=red')
                        
                    ui.button('🪄 Trích xuất thông tin', on_click=self.process_ai)\
                        .classes('bg-blue-600 text-white shadow-md')\
                        .props('no-caps') # no-caps để chữ không bị viết hoa toàn bộ
                
                # Khu vực hiển thị kết quả Debug
                # [FIX] Dùng bind_visibility để nó tự hiện/ẩn khi bấm Switch
                self.debug_container = ui.column().classes('w-full mt-2 p-2 border border-dashed border-slate-400 rounded bg-slate-100') \
                    .bind_visibility_from(self.debug_toggle, 'value')
            
    # ======================================================
            # PHẦN 2: THÔNG TIN (LAYOUT 2 CARD RIÊNG BIỆT)
            # ======================================================
            # Dùng ui.row để xếp 2 card nằm ngang. items-start để chúng không bị kéo giãn chiều cao
            with ui.row().classes('w-full gap-4 items-start mb-4'):
                
                # --- CARD 1: THÔNG TIN KHÁCH HÀNG (BÊN TRÁI) ---
                with ui.card().classes('flex-1 p-4 shadow-sm border border-slate-200'):
                    ui.label('1. Thông tin Khách hàng').classes('font-bold text-slate-700 mb-2')
                    
                    # Ô Tìm kiếm khách
                    ui.select(
                        options=self.customer_list,
                        with_input=True,
                        label='🔍 Tìm khách cũ (Gõ SĐT/Tên)',
                        on_change=self.on_customer_select
                    ).classes('w-full mb-3').props('clearable behavior="menu"')

                    # Các ô nhập liệu
                    self.input_ma_don = ui.input('Mã đơn (Tự sinh)').props('placeholder="Để trống tự tạo..."').classes('w-full')
                    self.input_ten = ui.input('Tên khách hàng *').classes('w-full')
                    self.input_sdt = ui.input('Số điện thoại').classes('w-full')
                    self.input_dia_chi = ui.textarea('Địa chỉ giao hàng').props('rows=3').classes('w-full')
                    self.input_ghi_chu = ui.input('Ghi chú đơn').classes('w-full')

                # --- CARD 2: THÔNG TIN ĐƠN HÀNG (BÊN PHẢI) ---
                with ui.card().classes('flex-1 p-4 shadow-sm border border-slate-200'):
                    ui.label('2. Cấu hình Đơn hàng').classes('font-bold text-slate-700 mb-2')
                    
                    with ui.column().classes('w-full gap-3'): # Dùng gap-3 để thoáng hơn
                        
                        # 1. Shop
                        self.select_shop = ui.select(["Inside", "TGTĐ", "Lanh Canh"], value="Inside", label="Shop / Line").classes('w-full')
                        
    # 2. Ngày tháng (Đặt trên 1 hàng)
                        with ui.row().classes('w-full gap-2 no-wrap'):
                            
                            # --- Input 1: Ngày Đặt ---
                            self.input_ngay_dat = ui.input('Ngày đặt').classes('flex-1')
                            self.input_ngay_dat.value = datetime.now().strftime('%Y-%m-%d')
                            
                            # 1. Tạo Slot chứa Icon
                            with self.input_ngay_dat.add_slot('append'):
                                # [FIX] Sửa .class_name() thành .classes()
                                ui.icon('event').classes('cursor-pointer').on('click', lambda: menu_dat.open())
                            
                            # 2. Tạo Menu
                            with self.input_ngay_dat:
                                with ui.menu() as menu_dat:
                                    ui.date().bind_value(self.input_ngay_dat).on('input', lambda: menu_dat.close())

                            # --- Input 2: Ngày Trả ---
                            self.input_ngay_tra = ui.input('Ngày trả').classes('flex-1')
                            self.input_ngay_tra.value = datetime.now().strftime('%Y-%m-%d')
                            
                            # 1. Tạo Slot chứa Icon
                            with self.input_ngay_tra.add_slot('append'):
                                # [FIX] Sửa .class_name() thành .classes()
                                ui.icon('event').classes('cursor-pointer').on('click', lambda: menu_tra.open())
                            
                            # 2. Tạo Menu
                            with self.input_ngay_tra:
                                with ui.menu() as menu_tra:
                                    ui.date().bind_value(self.input_ngay_tra).on('input', lambda: menu_tra.close())

                        # 3. Checkbox
                        self.chk_co_hen = ui.checkbox('🚨 Khách hẹn ngày lấy (Đơn gấp)')

                        # 4. Thanh toán & Vận chuyển
                        with ui.row().classes('w-full gap-2 no-wrap'):
                            self.select_httt = ui.select(["Ship COD 💵", "Ck trước 💳", "0đ 📷"], value="Ship COD 💵", label="Thanh toán").classes('flex-1')
                            self.select_vc = ui.select(["Thường", "Xe Ôm 🏍", "Bay ✈"], value="Thường", label="Vận chuyển").classes('flex-1')           # ======================================================
            # PHẦN 3: DANH SÁCH SẢN PHẨM (DYNAMIC LIST)
            # ======================================================
            with ui.card().classes('w-full p-4 mb-4 shadow-sm'):
                with ui.row().classes('w-full justify-between items-center mb-2'):
                    ui.label('2. Chi tiết sản phẩm').classes('font-bold text-slate-700')
                    ui.button('Thêm dòng', icon='add', on_click=self.add_item_row).props('small outline')

                # Container chứa các dòng sản phẩm
                self.items_container = ui.column().classes('w-full gap-2')
                self.render_items_list() # Vẽ lần đầu

            # ======================================================
            # PHẦN 4: TỔNG KẾT & LƯU
            # ======================================================
            with ui.card().classes('w-full p-4 shadow-md border-t-4 border-blue-600'):
                with ui.row().classes('w-full gap-4 items-center'):
                    # Tính tiền
                    self.num_tong_tien = ui.number('Tổng tiền', value=0, format='%.0f', on_change=self.calc_remaining).classes('flex-1 font-bold')
                    self.num_da_coc = ui.number('Đã cọc', value=0, format='%.0f', on_change=self.calc_remaining).classes('flex-1')
                    
                    # Label hiển thị Còn lại
                    with ui.column().classes('flex-1 items-end'):
                        ui.label('Còn lại phải thu:').classes('text-sm text-slate-500')
                        self.lbl_con_lai = ui.label('0 đ').classes('text-2xl font-bold text-red-600')

                ui.separator().classes('my-4')
                
                # Nút Lưu to bự
                ui.button('💾 LƯU ĐƠN HÀNG', on_click=self.save_order).classes('w-full h-12 text-lg bg-blue-600 text-white shadow-lg')

    # --- LOGIC XỬ LÝ GIAO DIỆN ---
    
    def render_items_list(self):
        """Vẽ lại danh sách các dòng sản phẩm"""
        self.items_container.clear()
        
        with self.items_container:
            for idx, item in enumerate(self.items):
                with ui.row().classes('w-full items-center gap-2 p-2 border rounded-md bg-slate-50'):
                    # STT
                    ui.label(f'#{idx+1}').classes('text-slate-400 w-6')
                    
                    # Các input field (Bind trực tiếp vào dict trong list self.items)
                    ui.input('Tên SP', value=item['ten_sp'], on_change=lambda e, i=item: i.update({'ten_sp': e.value})).classes('flex-1').props('dense')
                    ui.input('Màu', value=item['mau'], on_change=lambda e, i=item: i.update({'mau': e.value})).classes('w-20').props('dense')
                    ui.input('Size', value=item['size'], on_change=lambda e, i=item: i.update({'size': e.value})).classes('w-16').props('dense')
                    ui.number('SL', value=item.get('so_luong', 1), min=1, on_change=lambda e, i=item: i.update({'so_luong': int(e.value)})).classes('w-16').props('dense')
                    
                    # Kiểu thêu (Quan trọng - Note cho sản phẩm)
                    ui.input('Kiểu thêu', value=item['kieu_theu'], on_change=lambda e, i=item: i.update({'kieu_theu': e.value})).classes('flex-1').props('dense input-style="color:red"')
                    
                    # Ghi chú thêu (thông tin phụ) - Match Streamlit version
                    ui.input('Ghi chú thêu', value=item.get('thong_tin_phu', ''), on_change=lambda e, i=item: i.update({'thong_tin_phu': e.value})).classes('flex-1').props('dense')

                    # Nút xóa dòng
                    if len(self.items) > 1: # Giữ ít nhất 1 dòng
                        ui.button(icon='delete', on_click=lambda _, i=idx: self.remove_item_row(i)).props('flat dense color=red')

    def add_item_row(self):
        self.items.append({"ten_sp": "", "mau": "", "size": "", "so_luong": 1, "kieu_theu": "", "thong_tin_phu": ""})
        self.render_items_list()

    def remove_item_row(self, index):
        if 0 <= index < len(self.items):
            self.items.pop(index)
            self.render_items_list()

    def calc_remaining(self):
        """Tính tiền còn lại"""
        try:
            tong = float(self.num_tong_tien.value or 0)
            coc = float(self.num_da_coc.value or 0)
            con_lai = tong - coc
            self.lbl_con_lai.text = f"{con_lai:,.0f} đ"
        except:
            pass

    def on_customer_select(self, e):
        """Xử lý khi chọn khách từ dropdown autocomplete"""
        val = e.value
        if not val: return
        
        # Parse chuỗi "SĐT | Tên (Địa chỉ)"
        try:
            parts = val.split(" | ")
            sdt_part = parts[0]
            
            # Tìm trong list gốc (Logic này có thể tối ưu bằng dict lookup)
            # Ở đây làm đơn giản là tách chuỗi vì thông tin đã có sẵn trong string
            ten_part = parts[1].split(" (")[0]
            dia_chi_part = parts[1].split(" (")[1].replace(")", "")
            
            # Điền vào form
            self.input_ten.value = ten_part
            self.input_sdt.value = sdt_part
            self.input_dia_chi.value = dia_chi_part
            
            ui.notify(f'Đã điền thông tin khách: {ten_part}')
        except:
            pass

    # --- LOGIC AI ---
    async def process_ai(self):
        text = self.ai_input.value
        if not text:
            ui.notify('Vui lòng nhập đoạn chat', type='warning')
            return

        ui.notify('AI đang phân tích...', type='info', spinner=True)
        
        # [FIX] Dùng run.io_bound để không chặn Event Loop, tránh lỗi "Lost connection"
        extracted_data, raw_text = await run.io_bound(xuly_ai_gemini, text)

        # Hiển thị Debug (Luôn cập nhật nội dung, việc hiện/ẩn đã có bind_visibility lo)
        self.debug_container.clear()
        with self.debug_container:
            with ui.row().classes('w-full gap-4'):
                with ui.column().classes('flex-1'):
                    ui.label('🔍 AI Raw Output:').classes('font-bold text-sm')
                    ui.code(str(raw_text), language='json').classes('text-xs')
                with ui.column().classes('flex-1'):
                    ui.label('🐍 Python Mapped Data:').classes('font-bold text-sm')
                    ui.code(json.dumps(extracted_data, ensure_ascii=False, indent=2) if extracted_data else '{}', language='json').classes('text-xs')

        if extracted_data:
            # Điền vào form (Mapping data)
            self.input_ten.value = extracted_data.get("ten_khach_hang", "")
            self.input_sdt.value = extracted_data.get("so_dien_thoai", "")
            self.input_dia_chi.value = extracted_data.get("dia_chi", "")
            self.input_ghi_chu.value = extracted_data.get("ghi_chu", "")
            self.select_shop.value = extracted_data.get("shop", "Inside")
            
            # Tiền
            self.num_tong_tien.value = extracted_data.get("tong_tien", 0)
            self.num_da_coc.value = extracted_data.get("da_coc", 0)
            self.calc_remaining()
            
            # Ngày tháng (nếu AI trả về)
            if extracted_data.get("ngay_dat"):
                self.input_ngay_dat.value = extracted_data.get("ngay_dat")
            if extracted_data.get("ngay_tra"):
                self.input_ngay_tra.value = extracted_data.get("ngay_tra")
            if extracted_data.get("co_hen_ngay"):
                self.chk_co_hen.value = extracted_data.get("co_hen_ngay", False)

            # Items - bao gồm thong_tin_phu
            ai_items = extracted_data.get("items", [])
            if ai_items:
                self.items = [] # Xóa cũ
                for item in ai_items:
                    self.items.append({
                        "ten_sp": item.get("ten_sp", ""),
                        "mau": item.get("mau", ""),
                        "size": item.get("size", ""),
                        "so_luong": item.get("so_luong", 1),
                        "kieu_theu": item.get("kieu_theu", ""),
                        "thong_tin_phu": item.get("ghi_chu_sp", "") or item.get("thong_tin_phu", "")
                    })
                self.render_items_list()
                
            ui.notify('✅ Đã trích xuất thông tin thành công!')
        else:
            ui.notify('❌ AI không trả về kết quả hợp lệ', type='negative')

    # --- LOGIC LƯU ---
    def save_order(self):
        # 1. Validation
        if not self.input_ten.value:
            ui.notify('Thiếu tên khách hàng!', type='negative')
            return
        
        valid_items = [i for i in self.items if i['ten_sp'].strip()]
        if not valid_items:
            ui.notify('Đơn hàng cần ít nhất 1 sản phẩm có tên', type='negative')
            return

        # 2. Chuẩn bị data
        # Mã đơn: Nếu trống -> Tự sinh
        final_ma_don = self.input_ma_don.value.strip()
        if not final_ma_don:
            final_ma_don = f"ORD-{datetime.now().strftime('%m%d-%H%M-%S')}"

        order_data = {
            "ma_don": final_ma_don,
            "ten_khach": self.input_ten.value,
            "sdt": self.input_sdt.value,
            "dia_chi": self.input_dia_chi.value,
            "ghi_chu": self.input_ghi_chu.value,
            "shop": self.select_shop.value,
            "trang_thai": "Mới",
            
            # Properly get dates from bound inputs
            "ngay_dat": self.input_ngay_dat.value if self.input_ngay_dat.value else datetime.now().strftime('%Y-%m-%d'),
            "ngay_tra": self.input_ngay_tra.value if self.input_ngay_tra.value else datetime.now().strftime('%Y-%m-%d'),
            
            "thanh_tien": self.num_tong_tien.value,
            "da_coc": self.num_da_coc.value,
            "con_lai": (self.num_tong_tien.value or 0) - (self.num_da_coc.value or 0),
            
            "httt": self.select_httt.value,
            "van_chuyen": self.select_vc.value,
            "co_hen_ngay": self.chk_co_hen.value
        }

        # 3. Gọi Backend
        success = save_full_order(order_data, valid_items)
        
        if success:
            ui.notify(f'🎉 Đã tạo đơn {final_ma_don} thành công!', type='positive')
            
            # Reset Form
            self.input_ma_don.value = ""
            self.input_ten.value = ""
            self.input_sdt.value = ""
            self.input_dia_chi.value = ""
            self.input_ghi_chu.value = ""
            self.num_tong_tien.value = 0
            self.num_da_coc.value = 0
            self.items = [{"ten_sp": "", "mau": "", "size": "", "so_luong": 1, "kieu_theu": "", "thong_tin_phu": ""}]
            self.render_items_list()
            self.calc_remaining()
        else:
            ui.notify('Lỗi khi lưu vào Database', type='negative')