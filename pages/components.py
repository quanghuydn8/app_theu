from nicegui import ui
import base64

def hien_thi_anh_vuong(data, label="Ảnh"):
    """
    Hiển thị ảnh vuông (aspect-ratio 1:1) với chế độ object-cover.
    Hỗ trợ input là URL string hoặc Bytes.
    Tương đương với hàm cũ trong Streamlit nhưng dùng Native NiceGUI.
    """
    if not data:
        return

    # --- 1. XỬ LÝ DỮ LIỆU (Giữ nguyên logic cũ) ---
    url = data
    if isinstance(data, bytes):
        try:
            b64 = base64.b64encode(data).decode()
            url = f"data:image/png;base64,{b64}"
        except Exception as e:
            print(f"❌ Lỗi convert ảnh bytes: {e}")
            return

    # --- 2. RENDER UI (NiceGUI Style) ---
    # Thay vì viết HTML string, ta dùng component của NiceGUI
    with ui.column().classes('w-full gap-1 mb-2'):
        
        # Ảnh vuông:
        # - w-full: Rộng 100% container cha
        # - aspect-square: Tỷ lệ 1:1 (Vuông)
        # - object-cover: Cắt ảnh vừa khung không bị méo (giống background-size: cover)
        ui.image(url).classes('w-full aspect-square object-cover rounded-lg border border-slate-200 cursor-pointer shadow-sm') \
            .tooltip(label) \
            .on('click', lambda: ui.open(url, new_tab=True)) # Click vào ảnh mở tab mới

        # Link bên dưới (giống thẻ <a> cũ)
        with ui.row().classes('w-full justify-center'):
            ui.link('🔍 Xem Full', url, new_tab=True).classes('text-xs text-slate-500 no-underline hover:text-blue-600')