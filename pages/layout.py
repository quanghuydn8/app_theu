from nicegui import ui

def create_layout(on_nav):
    """
    Tạo khung sườn giao diện (Header + Left Drawer).
    on_nav: Callback function(page_name) để xử lý điều hướng.
    """
    
    # --- HEADER ---
    with ui.header().classes('bg-white text-slate-800 shadow-sm items-center h-16 px-4 no-wrap') as header:
        # Toggle button cho Left Drawer
        ui.button(on_click=lambda: left_drawer.toggle(), icon='menu').props('flat color=slate-600')
        
        # Logo & Title
        with ui.row().classes('items-center gap-2'):
            ui.icon('emergency_share', size='md', color='blue-600')
            ui.label('Xưởng Thêu 4.0').classes('text-lg font-bold text-blue-700')
            
        ui.space() 
        
        # User Info
        with ui.row().classes('items-center gap-2 cursor-pointer'):
            ui.label('Hi, Admin').classes('text-sm font-medium text-slate-600')
            ui.avatar('account_circle', color='blue-100', text_color='blue-600')

    # --- LEFT DRAWER (SIDEBAR) ---
    with ui.left_drawer(value=True).classes('bg-slate-50 border-r border-slate-200 p-4') as left_drawer:
        
        def nav_button(text, icon, page_name):
            """Helper tạo nút điều hướng"""
            # Sửa logic: Gọi callback thay vì trực tiếp xóa container
            ui.button(text, icon=icon, on_click=lambda: on_nav(page_name)).props('flat align=left text-color=slate-700').classes('w-full mb-1 hover:bg-blue-50 hover:text-blue-600 transition-colors')

        # Menu Items
        ui.label('MENU CHÍNH').classes('text-xs font-bold text-slate-400 mb-2 mt-2')
        nav_button('Quản lý Đơn hàng', 'dashboard', 'Quản lý Đơn hàng')
        nav_button('Tạo Đơn Mới', 'edit_note', 'Tạo Đơn Mới')
        nav_button('AI Edit Ảnh', 'auto_fix_high', 'AI Edit Ảnh')
        nav_button('Quản lý Khách hàng', 'groups', 'Quản lý Khách hàng')

    return header, left_drawer
