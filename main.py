from nicegui import ui
from pages.layout import create_layout
from pages.page_orders import OrderPage
import pages.page_print  # Import để đăng ký route /print
import os
from dotenv import load_dotenv
from pages.page_create import OrderCreatePage
from pages.page_ai import AIEditPage
from pages.page_customers import CustomerPage

# --- CHECK ENV ---
load_dotenv()
# In ra console để kiểm tra xem đã đọc được biến môi trường chưa
print(f"Check Env: URL={os.getenv('SUPABASE_URL')}")

# --- TRANG CHỦ (INDEX PAGE) ---
# Quy tắc: Khi App có nhiều trang (ví dụ /print), trang chủ bắt buộc phải dùng @ui.page('/')
@ui.page('/') 
def index_page():
    # 1. Cấu hình CSS (Xóa padding mặc định của browser để full màn hình)
    ui.query('.nicegui-content').classes('p-0') 

    # 2. Main Container (Nơi chứa nội dung sẽ thay đổi khi bấm Menu)
    # Dùng min-h-screen để đảm bảo background phủ kín màn hình
    content_area = ui.column().classes('w-full p-6 bg-slate-50 min-h-screen gap-4')

    # 3. Hàm điều hướng (Router)
    # Hàm này nằm trong scope của index_page để truy cập được content_area
    def navigate_to(page_name):
        content_area.clear() # Xóa nội dung cũ
        
        if page_name == 'Quản lý Đơn hàng':
            with content_area:
                OrderPage() # Gọi class OrderPage để vẽ giao diện bảng
        
        elif page_name == 'Tạo Đơn Mới': # <--- SỬA ĐOẠN NÀY
            with content_area:
                OrderCreatePage()   
                
        elif page_name == 'AI Edit Ảnh':
            with content_area:
                AIEditPage()
                
        elif page_name == 'Quản lý Khách hàng':
            with content_area:
                CustomerPage()
        
        else:
            with content_area:
                ui.label(f'Không tìm thấy trang: {page_name}').classes('text-red-500')

    # 4. Khởi tạo Layout (Header + Menu bên trái)
    # Truyền hàm navigate_to vào để các nút trong menu có thể gọi nó
    create_layout(on_nav=navigate_to)

    # 5. Mặc định vào trang Quản lý đơn khi vừa mở App
    navigate_to('Quản lý Đơn hàng')

# --- KHỞI CHẠY APP ---
if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title='Xưởng Thêu 4.0',
        port=8080,
        favicon='🧵',
        reload=True # Tự động reload khi sửa code (Dev mode)
    )