# File: backend/printer.py

def _get_css():
    """CSS cho phiếu in (Khổ A4 hoặc A5 tùy máy in)"""
    return """
    <style>
        @media print {
            @page { margin: 0; size: auto; }
            body { margin: 1cm; font-family: Arial, sans-serif; font-size: 14px; }
            .no-print { display: none !important; }
            .page-break { page-break-before: always; } /* Ngắt trang khi in nhiều đơn */
        }
        body { font-family: Arial, sans-serif; line-height: 1.4; color: #000; }
        .print-container { margin-bottom: 20px; }
        .header { text-align: center; border-bottom: 2px solid #000; padding-bottom: 10px; margin-bottom: 15px; }
        .title { font-size: 24px; font-weight: bold; text-transform: uppercase; }
        .info-row { display: flex; justify-content: space-between; margin-bottom: 5px; }
        .table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        .table th, .table td { border: 1px solid #000; padding: 8px; text-align: left; }
        .table th { background-color: #f0f0f0; }
        .img-box { text-align: center; padding: 5px; }
        .img-box img { max-width: 80px; max-height: 80px; object-fit: contain; }
        .note { color: red; font-weight: bold; font-style: italic; font-size: 12px; }
        .footer { margin-top: 20px; text-align: center; font-style: italic; font-size: 12px; }
    </style>
    """

def _get_single_order_body(order, items):
    """Tạo HTML body cho 1 đơn hàng"""
    # Xử lý dữ liệu an toàn
    ma_don = order.get('ma_don', 'N/A')
    ten_khach = order.get('ten_khach', 'Khách lẻ')
    sdt = order.get('sdt', '')
    dia_chi = order.get('dia_chi', '')
    ghi_chu = order.get('ghi_chu', '')
    
    # Tạo bảng sản phẩm
    rows_html = ""
    for idx, item in enumerate(items, 1):
        # Lấy ảnh ưu tiên: Design -> Main -> Sub
        img_url = item.get('img_design') or item.get('img_main') or ""
        img_html = f'<img src="{img_url}">' if img_url else ""
        
        # Note thêu
        note_theu = f"<br><span class='note'>Note: {item.get('kieu_theu', '')}</span>" if item.get('kieu_theu') else ""
        
        rows_html += f"""
        <tr>
            <td style="text-align: center;">{idx}</td>
            <td>
                <b>{item.get('ten_san_pham')}</b><br>
                Màu: {item.get('mau')} | Size: {item.get('size')}<br>
                {note_theu}
            </td>
            <td style="text-align: center;">{img_html}</td>
            <td style="text-align: center;">{item.get('so_luong')}</td>
        </tr>
        """

    return f"""
    <div class="print-container">
        <div class="header">
            <div class="title">PHIẾU SẢN XUẤT</div>
            <div>Mã đơn: <b>{ma_don}</b></div>
        </div>
        <div class="info-group">
            <div class="info-row"><span>Khách hàng: <b>{ten_khach}</b></span> <span>SĐT: {sdt}</span></div>
            <div class="info-row"><span>Địa chỉ: {dia_chi}</span></div>
            <div class="info-row"><span>Ghi chú đơn: {ghi_chu}</span></div>
        </div>
        <table class="table">
            <thead>
                <tr>
                    <th style="width: 5%">STT</th>
                    <th style="width: 45%">Sản phẩm / Note thêu</th>
                    <th style="width: 30%">Hình ảnh</th>
                    <th style="width: 20%">SL</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        <div class="footer">
            <p>Xưởng Thêu 4.0 - In ngày {order.get('created_at', '')}</p>
        </div>
    </div>
    """

def generate_print_html(order_info, items):
    """Hàm in 1 đơn hàng (Dùng cho nút In trong chi tiết đơn)"""
    if not order_info: return "<h1>Không có dữ liệu đơn hàng</h1>"
    
    css = _get_css()
    body = _get_single_order_body(order_info, items)
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>In đơn {order_info.get('ma_don')}</title>
        {css}
    </head>
    <body>
        {body}
        <script>
            // Tự động mở dialog in khi load xong
            window.onload = function() {{ window.print(); }}
        </script>
    </body>
    </html>
    """

def generate_combined_print_html(orders_data_list):
    """
    Hàm tạo mã HTML để in GỘP nhiều đơn hàng.
    orders_data_list: list các dict [{'order_info': ..., 'items': ...}, ...]
    """
    css = _get_css()
    all_bodies = ""
    
    for idx, data in enumerate(orders_data_list):
        # Thêm class page-break trước mỗi đơn (trừ đơn đầu tiên) để máy in tự ngắt trang
        page_break = '<div class="page-break"></div>' if idx > 0 else ""
        
        body = _get_single_order_body(data['order_info'], data['items'])
        all_bodies += f"{page_break}{body}"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>In danh sách đơn hàng</title>
        {css}
    </head>
    <body style="margin: 0; padding: 20px;">
        {all_bodies}
    </body>
    </html>
    """