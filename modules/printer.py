import streamlit as st

def generate_print_html(order_info, items):
    """
    Hàm tạo mã HTML để in phiếu sản xuất (Work Order).
    Tự động chọn mẫu in dựa trên loại Shop.
    """
    shop_type = order_info.get('shop', 'Inside')
    
    # CSS CHUNG CHO TRANG IN (Khổ A4)
    css_style = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');
        body { font-family: 'Roboto', sans-serif; font-size: 14px; color: #000; }
        .print-container { width: 100%; max-width: 800px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; }
        .header { display: flex; justify-content: space-between; border-bottom: 2px solid #000; padding-bottom: 10px; margin-bottom: 20px; }
        .brand { font-size: 24px; font-weight: bold; text-transform: uppercase; }
        .meta { text-align: right; }
        .customer-box { border: 1px solid #000; padding: 10px; margin-bottom: 20px; border-radius: 4px; }
        .item-row { display: flex; border-bottom: 1px dashed #999; padding: 15px 0; page-break-inside: avoid; }
        .item-info { width: 30%; padding-right: 10px; }
        .item-images { width: 70%; display: flex; gap: 10px; }
        .img-box { border: 1px solid #ccc; width: 32%; text-align: center; }
        .img-box img { max-width: 100%; max-height: 150px; object-fit: contain; }
        .label { font-weight: bold; font-size: 12px; color: #555; display: block; margin-bottom: 4px; }
        .note { color: red; font-weight: bold; margin-top: 5px; }
        
        /* Chỉ hiện nút in trên màn hình, ẩn khi in ra giấy */
        @media print {
            .no-print { display: none !important; }
            .print-container { border: none; padding: 0; }
        }
    </style>
    """

    # --- LOGIC TẠO HTML THEO SHOP ---
    
    # 1. TEMPLATE TGTĐ (Form nhiều ảnh chi tiết)
    if shop_type == "TGTĐ":
        items_html = ""
        for i, item in enumerate(items):
            # Xử lý ảnh: Ưu tiên Ảnh AI (img_sub1) hoặc Ảnh gốc (img_main)
            img_goc = f"<img src='{item.get('img_main')}'/>" if item.get('img_main') else "<div style='height:100px; display:flex; align-items:center; justify-content:center;'>Không có ảnh</div>"
            img_ai = f"<img src='{item.get('img_sub1')}'/>" if item.get('img_sub1') else "<div style='height:100px; display:flex; align-items:center; justify-content:center;'>Chưa Gen AI</div>"
            
            # Tách link file design nếu có
            design_links = ""
            if item.get('img_sub2'):
                design_links = "<div style='font-size:10px; margin-top:5px;'>📂 Có file thiết kế</div>"

            items_html += f"""
            <div class="item-row">
                <div class="item-info">
                    <div style="font-size: 16px; font-weight: bold;">#{i+1}. {item.get('ten_sp')}</div>
                    <div>Màu: <b>{item.get('mau')}</b></div>
                    <div>Size: <b>{item.get('size')}</b></div>
                    <div style="margin-top:10px;">Yêu cầu:</div>
                    <div class="note">{item.get('kieu_theu')}</div>
                    {design_links}
                </div>
                <div class="item-images">
                    <div class="img-box"><span class="label">ẢNH GỐC</span>{img_goc}</div>
                    <div class="img-box"><span class="label">KẾT QUẢ AI / MẪU</span>{img_ai}</div>
                    <div class="img-box" style="border:1px dashed #000; display:flex; align-items:center; justify-content:center;">
                        <span style="color:#ccc;">Dán mẫu chỉ / Note</span>
                    </div>
                </div>
            </div>
            """

    # 2. TEMPLATE LANH CANH (Dạng bảng danh sách - Tiết kiệm giấy)
    elif shop_type == "Lanh Canh":
        rows = ""
        for i, item in enumerate(items):
            rows += f"""
            <tr>
                <td style="border:1px solid #000; padding:8px; text-align:center;">{i+1}</td>
                <td style="border:1px solid #000; padding:8px;"><b>{item.get('ten_sp')}</b></td>
                <td style="border:1px solid #000; padding:8px; text-align:center;">{item.get('mau')}</td>
                <td style="border:1px solid #000; padding:8px; text-align:center;">{item.get('size')}</td>
                <td style="border:1px solid #000; padding:8px;">{item.get('kieu_theu')}</td>
                <td style="border:1px solid #000; padding:8px; text-align:center;">{item.get('so_luong', 1)}</td>
            </tr>
            """
        
        items_html = f"""
        <table style="width:100%; border-collapse:collapse; margin-top:10px;">
            <tr style="background:#eee;">
                <th style="border:1px solid #000; padding:8px;">STT</th>
                <th style="border:1px solid #000; padding:8px;">Tên SP</th>
                <th style="border:1px solid #000; padding:8px;">Màu</th>
                <th style="border:1px solid #000; padding:8px;">Size</th>
                <th style="border:1px solid #000; padding:8px;">Ghi chú</th>
                <th style="border:1px solid #000; padding:8px;">SL</th>
            </tr>
            {rows}
        </table>
        """

    # 3. TEMPLATE INSIDE (Mặc định)
    else:
        items_html = ""
        for i, item in enumerate(items):
            img_main = f"<img src='{item.get('img_main')}'/>" if item.get('img_main') else ""
            items_html += f"""
            <div class="item-row">
                <div class="item-info">
                    <div style="font-size: 16px; font-weight: bold;">#{i+1}. {item.get('ten_sp')}</div>
                    <div>{item.get('mau')} / {item.get('size')}</div>
                    <div class="note">{item.get('kieu_theu')}</div>
                </div>
                <div class="item-images">
                    <div class="img-box" style="width: 48%;"><span class="label">HÌNH ẢNH</span>{img_main}</div>
                    <div class="img-box" style="width: 48%; border:1px dashed #000;"></div>
                </div>
            </div>
            """

    # --- GHÉP KHUNG HTML TỔNG ---
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>{css_style}</head>
    <body>
        <div class="print-container">
            <div class="no-print" style="text-align:right; margin-bottom:10px;">
                <button onclick="window.print()" style="background-color:#2563eb; color:white; padding:10px 20px; border:none; border-radius:5px; cursor:pointer; font-weight:bold;">🖨️ IN PHIẾU NGAY</button>
            </div>

            <div class="header">
                <div class="brand">PHIẾU SẢN XUẤT - {shop_type}</div>
                <div class="meta">
                    <div>Mã đơn: <b>{order_info.get('ma_don')}</b></div>
                    <div>Ngày in: {order_info.get('ngay_dat')[:10]}</div>
                </div>
            </div>

            <div class="customer-box">
                <div>Khách hàng: <b>{order_info.get('ten_khach')}</b> - {order_info.get('sdt')}</div>
                <div>Địa chỉ: {order_info.get('dia_chi')}</div>
                <div>Giao hàng: <b>{order_info.get('van_chuyen')}</b> | Thu hộ (COD): <b>{float(order_info.get('con_lai', 0)):,.0f} đ</b></div>
            </div>

            <div class="items-list">
                {items_html}
            </div>
            
            <div style="margin-top:30px; border-top:2px solid #000; padding-top:10px; display:flex; justify-content:space-between;">
                <div><b>Người kiểm hàng</b><br><br><br></div>
                <div><b>Thợ nhận việc</b><br><br><br></div>
            </div>
        </div>
    </body>
    </html>
    """
    return full_html