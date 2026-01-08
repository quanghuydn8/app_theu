from nicegui import ui
from backend.data_handler import get_order_details
from backend.printer import generate_print_html

# Đăng ký trang in với đường dẫn động /print/{ma_don}
@ui.page('/print/{ma_don}')
def print_page(ma_don: str):
    # 1. Lấy dữ liệu
    order, items = get_order_details(ma_don)
    
    if not order:
        ui.label(f"❌ Không tìm thấy đơn hàng: {ma_don}").classes('text-red-500 text-xl p-4')
        return

    # 2. Sinh HTML phiếu in
    html_content = generate_print_html(order, items)
    
    # 3. Hiển thị HTML full màn hình
    ui.html(html_content).classes('w-full')

    # 4. Nút in trôi nổi (Floating Action Button)
    with ui.button('🖨️ In Ngay', on_click=lambda: ui.run_javascript('window.print()')) \
            .classes('fixed bottom-8 right-8 shadow-lg no-print z-50') \
            .props('icon=print color=blue size=lg'):
        pass