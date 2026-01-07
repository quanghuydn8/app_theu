import streamlit as st

def _get_single_order_body(order_info, items):
    """
    Hàm helper: Tạo nội dung HTML body cho 1 đơn hàng (Layout Dọc - Compact).
    """
    shop_type = order_info.get('shop', 'Inside')
    
    # --- LOGIC TẠO LIST ITEM ---
    items_html = ""
    for i, item in enumerate(items):
        # 1. Thu thập tất cả ảnh CÓ DỮ LIỆU
        valid_images = []
        # Kiểm tra từng loại ảnh, nếu có URL thì thêm vào list
        if item.get('img_main'): valid_images.append({'url': item['img_main'], 'label': 'Ảnh Gốc'})
        if item.get('img_sub1'): valid_images.append({'url': item['img_sub1'], 'label': 'Ảnh 1'})
        if item.get('img_design'): valid_images.append({'url': item['img_design'], 'label': 'Design'})

        # 2. Tạo HTML cho phần ảnh (Nếu có)
        images_row_html = ""
        if valid_images:
            imgs_html = ""
            # Logic chia cột ảnh: Tự động chia đều chiều rộng
            width_pct = int(100 / len(valid_images)) - 1 
            for img in valid_images:
                imgs_html += f"""
                <div class="img-box" style="width: {width_pct}%;">
                    <img src="{img['url']}" />
                    <span class="label">{img['label']}</span>
                </div>
                """
            images_row_html = f'<div class="item-images">{imgs_html}</div>'
        
        # 3. Tổng hợp HTML cho 1 sản phẩm
        items_html += f"""
        <div class="item-row">
            <div class="item-header">
                <span class="stt">#{i+1}</span>
                <span class="p-name">{item.get('ten_sp')}</span>
                <span class="p-attr">Màu: <b>{item.get('mau')}</b></span>
                <span class="p-attr">Size: <b>{item.get('size')}</b></span>
                <span class="p-attr">SL: <b>{item.get('so_luong', 1)}</b></span>
            </div>
            <div class="item-note">Note: {item.get('kieu_theu')}</div>
            {images_row_html}
        </div>
        """

    # --- KHUNG NỘI DUNG ĐƠN HÀNG ---
    single_order_html = f"""
    <div class="print-container">
        <!-- HEADER COMPACT -->
        <div class="header">
            <div class="h-left">
                <div class="brand">PHIẾU SẢN XUẤT ({shop_type})</div>
                <div class="cust-info">
                    Khách: <b>{order_info.get('ten_khach')}</b> - {order_info.get('sdt')}<br>
                    Đ/c: {order_info.get('dia_chi')}
                </div>
            </div>
            <div class="h-right">
                <div class="meta-row">Mã: <b>{order_info.get('ma_don')}</b></div>
                <div class="meta-row">Ngày in: {order_info.get('ngay_dat')[:10]}</div>
                <div class="meta-row">COD: <b>{float(order_info.get('con_lai', 0)):,.0f} đ</b></div>
            </div>
        </div>

        <!-- LIST SẢN PHẨM -->
        <div class="items-list">
            {items_html}
        </div>
    </div>
    """
    return single_order_html

def _get_css():
    return """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');
        body { font-family: 'Roboto', sans-serif; font-size: 13px; color: #000; margin: 0; padding: 0; }
        
        .print-container { 
            width: 100%; max-width: 800px; margin: 0 auto; padding: 10px; 
            border-bottom: 2px dashed #999; /* Vạch cắt giữa các đơn nếu in gộp */
            page-break-inside: avoid;
        }

        /* HEADER */
        .header { display: flex; justify-content: space-between; border-bottom: 2px solid #000; padding-bottom: 5px; margin-bottom: 10px; }
        .h-left { width: 70%; }
        .h-right { width: 30%; text-align: right; }
        
        .brand { font-size: 18px; font-weight: bold; text-transform: uppercase; margin-bottom: 4px; }
        .cust-info { font-size: 13px; line-height: 1.4; }
        .meta-row { font-size: 13px; margin-bottom: 2px; }

        /* ITEMS */
        .items-list { display: flex; flex-direction: column; gap: 10px; }
        .item-row { border: 1px solid #ccc; padding: 8px; border-radius: 4px; page-break-inside: avoid; }
        
        .item-header { display: flex; align-items: center; gap: 15px; margin-bottom: 4px; flex-wrap: wrap;}
        .stt { background: #000; color: #fff; padding: 2px 6px; font-weight: bold; border-radius: 3px; font-size: 12px; }
        .p-name { font-weight: bold; font-size: 15px; }
        .p-attr { background: #eee; padding: 2px 6px; border-radius: 3px; font-size: 13px; }
        
        .item-note { color: #d00; font-weight: bold; font-style: italic; margin-bottom: 6px; font-size: 13px; }

        /* IMAGES */
        .item-images { display: flex; gap: 5px; justify-content: flex-start; }
        .img-box { text-align: center; border: 1px solid #ddd; padding: 2px; }
        .img-box img { width: 100%; height: 140px; object-fit: contain; display: block; }
        .label { display: block; font-size: 10px; color: #555; background: #f5f5f5; border-top: 1px solid #ddd; }

        @media print {
            .print-container { border-bottom: none; page-break-inside: avoid; margin-bottom: 20px; }
            .page-break { page-break-before: always; height: 0; display: block; }
        }
    </style>
    """

def generate_print_html(order_info, items):
    """
    Hàm tạo mã HTML để in phiếu sản xuất (Work Order) cho 1 đơn hàng.
    """
    body_content = _get_single_order_body(order_info, items)
    
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>{_get_css()}</head>
    <body style="margin: 0; padding: 20px;">
        {body_content}
        <script>
            window.onload = function() {{
                // Auto print dialog
                // window.print();
            }}
        </script>
    </body>
    </html>
    """
    return full_html

def generate_combined_print_html(orders_data_list):
    """
    Hàm tạo mã HTML để in GỘP nhiều đơn hàng.
    orders_data_list: list các dict [{'order_info': ..., 'items': ...}, ...]
    """
    all_bodies = ""
    for idx, data in enumerate(orders_data_list):
        # Thêm page-break trước mỗi đơn (trừ đơn đầu tiên)
        if idx > 0:
            all_bodies += '<div class="page-break"></div>'
            
        all_bodies += _get_single_order_body(data['order_info'], data['items'])
        
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>{_get_css()}</head>
    <body style="margin: 0; padding: 20px;">
        {all_bodies}
    </body>
    </html>
    """
    return full_html