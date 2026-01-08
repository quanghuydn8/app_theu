# File: modules/__init__.py

# 1. Export các hàm từ data_handler
from .data_handler import (
    supabase,
    fetch_all_orders,
    get_order_details,
    save_full_order,
    update_order_status,
    tai_danh_sach_trang_thai,
    upload_image_to_supabase, # <--- Hàm mới
    update_item_image,        # <--- Hàm mới
    update_item_field,
    mark_order_as_printed,
    kiem_tra_ket_noi
)


# 3. Export các hàm từ ai_logic
from .ai_logic import (
    gen_anh_mau_theu,
    xuly_ai_gemini
)

# 4. Export hàm thông báo
from .notifier import send_telegram_notification, check_order_notifications

from .printer import generate_print_html