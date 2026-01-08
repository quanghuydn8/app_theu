from nicegui import ui
import asyncio
import time
import io
from pages.components import hien_thi_anh_vuong

# --- IMPORT BACKEND ---
from backend.data_handler import upload_image_to_supabase
from backend.ai_logic import generate_image_from_ref

class AIEditPage:
    def __init__(self):
        # Khởi tạo state
        self.input_url = None
        self.result_url = None
        self.input_bytes = None  # Lưu bytes để gửi cho AI
        self.prompt = "đổi màu áo sang màu xanh..." # Default prompt
        
        self.build_ui()

    def build_ui(self):
        # 1. HEADER
        with ui.column().classes('w-full items-center mb-6'):
            ui.label('🎨 AI Edit Ảnh (Beta)').classes('text-3xl font-bold text-slate-700')
            ui.label("Sử dụng model 'gemini-3-pro-image-preview' để chỉnh sửa ảnh dựa trên Prompt.") \
                .classes('text-slate-500 italic')

        # 2. MAIN LAYOUT (3 Cột: Input | Output | Prompt)
        # Sử dụng flex-row để chia cột, gap-6 để tạo khoảng cách
        with ui.row().classes('w-full gap-6 items-stretch'):
            
            # --- CỘT 1: ẢNH GỐC (Width ~ 25%) ---
            with ui.card().classes('w-full md:w-1/4 p-4 flex flex-col gap-3 border-t-4 border-blue-500'):
                ui.label('📸 1. Ảnh gốc').classes('font-bold text-lg text-slate-700')
                
                # Khu vực hiển thị ảnh
                self.img_input_container = ui.column().classes('w-full aspect-square bg-slate-50 rounded border-2 border-dashed border-slate-300 items-center justify-center')
                with self.img_input_container:
                    ui.label('Chưa có ảnh').classes('text-slate-400')

                # Nút Upload
                ui.upload(
                    label='Tải ảnh lên',
                    auto_upload=True,
                    max_files=1,
                    on_upload=self.handle_upload
                ).props('accept=.jpg,.png,.jpeg flat dense color=blue').classes('w-full')

            # --- CỘT 2: KẾT QUẢ AI (Width ~ 25%) ---
            with ui.card().classes('w-full md:w-1/4 p-4 flex flex-col gap-3 border-t-4 border-purple-500'):
                ui.label('✨ 2. Kết quả AI').classes('font-bold text-lg text-slate-700')
                
                # Khu vực hiển thị kết quả
                self.img_result_container = ui.column().classes('w-full aspect-square bg-slate-50 rounded border-2 border-dashed border-slate-300 items-center justify-center')
                with self.img_result_container:
                    ui.label('Chưa có kết quả').classes('text-slate-400')

                # Nút Download (Ban đầu disable)
                self.btn_download = ui.button('⬇️ Tải Ảnh Về', on_click=self.download_result) \
                    .props('disabled color=green icon=download').classes('w-full')

            # --- CỘT 3: PROMPT & ACTION (Width ~ 50% - Flex 1) ---
            with ui.card().classes('flex-1 p-4 flex flex-col gap-3 border-t-4 border-indigo-500'):
                ui.label('📝 3. Nhập yêu cầu (Prompt)').classes('font-bold text-lg text-slate-700')
                
                # Text Area Prompt
                self.txt_prompt = ui.textarea(
                    placeholder='Ví dụ: Đổi màu áo sang đỏ, thêm logo...',
                    value=self.prompt
                ).props('outlined rounded input-class="text-lg"').classes('w-full flex-1 text-lg').bind_value(self, 'prompt')
                
                # Nút Generate to bự
                ui.button('🚀 XỬ LÝ ẢNH (GENERATE)', on_click=self.handle_generate) \
                    .props('color=indigo icon=auto_fix_high size=lg').classes('w-full h-16 text-xl font-bold shadow-lg')

    # --- HANDLERS ---

    async def handle_upload(self, e):
        """Xử lý khi user upload ảnh gốc"""
        ui.notify('Đang tải ảnh lên...', type='info', spinner=True)
        try:
            # 1. Đọc bytes từ file upload
            self.input_bytes = e.content.read()
            
            # 2. Upload lên Supabase (Folder ai_temp) để lấy URL hiển thị
            # Cần bọc bytes vào BytesIO vì hàm upload backend dùng Image.open()
            file_obj = io.BytesIO(self.input_bytes)
            fname = f"ai_input_{int(time.time())}.png"
            
            # Chạy async để không đơ UI
            url = await asyncio.to_thread(upload_image_to_supabase, file_obj, fname, "ai_temp")
            
            if url:
                self.input_url = url
                # Update UI
                self.img_input_container.clear()
                with self.img_input_container:
                    hien_thi_anh_vuong(self.input_url, "Ảnh gốc")
                ui.notify('✅ Upload thành công!')
            else:
                ui.notify('❌ Lỗi upload lên server', type='negative')
                
        except Exception as ex:
            ui.notify(f'Lỗi: {str(ex)}', type='negative')

    async def handle_generate(self):
        """Gọi Gemini AI để sửa ảnh"""
        if not self.input_bytes:
            ui.notify('⚠️ Vui lòng upload ảnh gốc trước!', type='warning')
            return
        if not self.prompt.strip():
            ui.notify('⚠️ Vui lòng nhập yêu cầu (Prompt)!', type='warning')
            return

        ui.notify('🎨 AI đang vẽ... (Vui lòng đợi 10-20s)', type='info', spinner=True, timeout=20000)
        
        try:
            # 1. Gọi hàm AI (IO Bound -> chạy trong thread)
            result_bytes = await asyncio.to_thread(generate_image_from_ref, self.input_bytes, self.prompt)
            
            if result_bytes:
                # 2. Upload kết quả lên Supabase
                fname_res = f"ai_res_{int(time.time())}.png"
                file_obj = io.BytesIO(result_bytes)
                res_url = await asyncio.to_thread(upload_image_to_supabase, file_obj, fname_res, "ai_temp")
                
                if res_url:
                    self.result_url = res_url
                    
                    # Update UI Kết quả
                    self.img_result_container.clear()
                    with self.img_result_container:
                        hien_thi_anh_vuong(self.result_url, "Kết quả AI")
                    
                    # Bật nút download
                    self.btn_download.enable()
                    ui.notify('✅ AI xử lý thành công!', type='positive')
                else:
                    ui.notify('❌ Lỗi lưu ảnh kết quả', type='negative')
            else:
                ui.notify('❌ AI không trả về ảnh. Hãy thử prompt khác.', type='negative')
                
        except Exception as e:
            ui.notify(f'Lỗi AI: {str(e)}', type='negative')

    def download_result(self):
        if self.result_url:
            ui.open(self.result_url, new_tab=True)