# Module Package for App Quản lý Đơn hàng Thêu
# Version 3.3 Modular

from .data_handler import (
    check_file_exists,
    luu_anh_pet,
    luu_anh_design,
    tai_anh_design,
    luu_du_lieu_csv,
    tai_du_lieu_csv,
    tao_du_lieu_mau,
    tao_chi_tiet_don_hang,
    sync_images_with_dataframe,
    DIR_DESIGNS,
    DIR_PETS,
    CSV_FILE
)

from .ai_logic import (
    configure_ai,
    xuly_ai_gemini,
    gen_anh_mau_theu
)

from .ui_components import (
    tao_badge_trang_thai,
    tao_mau_nen_trang_thai,
    render_order_management,
    render_ai_design
)

from .dashboard import (
    render_dashboard,
    calculate_metrics,
    create_status_pie_chart,
    create_top_products_chart,
    create_orders_timeline_chart
)

from .notifier import (
    send_telegram_notification
)

