import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Màu sắc đồng bộ với trang Quản lý
STATUS_COLORS = {
    "New": "#808080",
    "Đã xác nhận": "#4CAF50",
    "Đang thiết kế": "#2196F3",
    "Chờ duyệt thiết kế": "#FF9800",
    "Đã duyệt thiết kế": "#4CAF50",
    "Đang sản xuất": "#9C27B0",
    "Hoàn thành sản xuất": "#00BCD4",
    "Đang đóng gói": "#FF5722",
    "Sẵn sàng giao hàng": "#8BC34A",
    "Đang giao hàng": "#FFC107",
    "Đã gửi vận chuyển": "#2E7D32"
}

def parse_money(value):
    """Chuyển chuỗi tiền (ví dụ: '1,500,000đ') thành số nguyên"""
    try:
        return int(str(value).replace(',', '').replace('đ', '').replace('.', ''))
    except:
        return 0

def calculate_metrics(df):
    """Tính toán các chỉ số thống kê từ DataFrame"""
    # Tổng doanh thu
    total_revenue = sum(parse_money(x) for x in df['Tổng tiền'])
    
    # Tỷ lệ hoàn thành
    completed = len(df[df['Trạng thái'] == 'Đã gửi vận chuyển'])
    completion_rate = (completed / len(df) * 100) if len(df) > 0 else 0
    
    # Số thiết kế đã hoàn thành
    designs_done = df['Anh_Design'].notna().sum()
    
    # Tổng số lượng sản phẩm
    total_products = df['Số lượng'].sum()
    
    return {
        "total_revenue": total_revenue,
        "completion_rate": completion_rate,
        "completed_orders": completed,
        "total_orders": len(df),
        "designs_done": designs_done,
        "total_products": total_products
    }

def create_status_pie_chart(df):
    """Tạo biểu đồ tròn tỷ lệ trạng thái đơn hàng"""
    status_counts = df['Trạng thái'].value_counts().reset_index()
    status_counts.columns = ['Trạng thái', 'Số lượng']
    
    # Lấy màu tương ứng
    colors = [STATUS_COLORS.get(s, '#808080') for s in status_counts['Trạng thái']]
    
    fig = px.pie(
        status_counts, 
        values='Số lượng', 
        names='Trạng thái',
        color_discrete_sequence=colors,
        hole=0.4  # Donut chart
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(
        title="📊 Phân bố Trạng thái Đơn hàng",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.3),
        height=400
    )
    return fig

def create_top_products_chart(df):
    """Tạo biểu đồ cột Top 5 sản phẩm bán chạy"""
    # Nhóm theo sản phẩm và tính tổng số lượng
    product_sales = df.groupby('Sản phẩm')['Số lượng'].sum().reset_index()
    product_sales = product_sales.nlargest(5, 'Số lượng')
    
    fig = px.bar(
        product_sales,
        x='Sản phẩm',
        y='Số lượng',
        color='Số lượng',
        color_continuous_scale=['#E3F2FD', '#1976D2'],
        text='Số lượng'
    )
    fig.update_traces(texttemplate='%{text}', textposition='outside')
    fig.update_layout(
        title="🏆 Top 5 Sản phẩm Bán chạy",
        xaxis_title="",
        yaxis_title="Số lượng",
        showlegend=False,
        height=400
    )
    return fig

def create_orders_timeline_chart(df):
    """Tạo biểu đồ đường xu hướng đơn hàng theo ngày"""
    # Chuyển đổi ngày tạo
    df_copy = df.copy()
    df_copy['Ngày'] = pd.to_datetime(df_copy['Ngày tạo'], format='%d/%m/%Y', errors='coerce')
    
    # Nhóm theo ngày và đếm số đơn
    daily_orders = df_copy.groupby('Ngày').size().reset_index(name='Số đơn')
    daily_orders = daily_orders.sort_values('Ngày')
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily_orders['Ngày'],
        y=daily_orders['Số đơn'],
        mode='lines+markers',
        name='Số đơn',
        line=dict(color='#2196F3', width=3),
        marker=dict(size=10, color='#1976D2'),
        fill='tozeroy',
        fillcolor='rgba(33, 150, 243, 0.1)'
    ))
    
    fig.update_layout(
        title="📈 Xu hướng Đơn hàng theo Thời gian",
        xaxis_title="Ngày",
        yaxis_title="Số đơn hàng",
        height=350,
        hovermode='x unified'
    )
    return fig

def create_sku_analysis_chart(df):
    """Tạo biểu đồ phân tích SKU (Màu sắc và Size)"""
    # Trích xuất màu và size từ SKU (TS-MAU-SIZE)
    df_copy = df.copy()
    df_copy['Màu'] = df_copy['Mã SKU'].apply(lambda x: x.split('-')[1] if len(str(x).split('-')) > 1 else 'N/A')
    df_copy['Size'] = df_copy['Mã SKU'].apply(lambda x: x.split('-')[2] if len(str(x).split('-')) > 2 else 'N/A')
    
    # Nhóm theo màu
    color_counts = df_copy['Màu'].value_counts().reset_index()
    color_counts.columns = ['Màu sắc', 'Số lượng']
    
    fig = px.bar(
        color_counts,
        x='Màu sắc',
        y='Số lượng',
        color='Màu sắc',
        color_discrete_map={
            'DO': '#F44336', 'TRANG': '#FAFAFA', 'DEN': '#212121', 
            'XANH': '#4CAF50', 'XANHLA': '#8BC34A', 'XANHDUONG': '#2196F3',
            'VANG': '#FFEB3B', 'HONG': '#E91E63', 'CAM': '#FF9800',
            'TIM': '#9C27B0', 'NAU': '#795548', 'XAM': '#9E9E9E'
        },
        text='Số lượng'
    )
    fig.update_traces(textposition='outside')
    fig.update_layout(
        title="🎨 Phân bố Màu sắc Sản phẩm",
        xaxis_title="",
        yaxis_title="Số đơn",
        showlegend=False,
        height=350
    )
    return fig

def format_currency(value):
    """Format số tiền thành dạng dễ đọc"""
    if value >= 1_000_000_000:
        return f"{value/1_000_000_000:.1f}B VNĐ"
    elif value >= 1_000_000:
        return f"{value/1_000_000:.1f}M VNĐ"
    else:
        return f"{value:,.0f}đ"

def render_dashboard(df):
    """Render trang Dashboard chính"""
    st.title("📊 Dashboard - Trung tâm Điều hành Xưởng Thêu")
    
    # Nút làm mới dữ liệu
    col_refresh, col_time = st.columns([1, 4])
    with col_refresh:
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with col_time:
        st.caption(f"📅 Cập nhật lần cuối: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    st.markdown("---")
    
    # Tính toán metrics
    metrics = calculate_metrics(df)
    
    # === ROW 1: METRICS CARDS ===
    st.markdown("### 🎯 Chỉ số Quan trọng")
    m1, m2, m3, m4 = st.columns(4)
    
    with m1:
        st.metric(
            label="💰 Tổng Doanh thu Dự kiến",
            value=format_currency(metrics['total_revenue']),
            delta=None
        )
    
    with m2:
        st.metric(
            label="📦 Tổng Đơn hàng",
            value=f"{metrics['total_orders']} đơn",
            delta=f"{metrics['completed_orders']} đã hoàn thành"
        )
    
    with m3:
        st.metric(
            label="✅ Tỷ lệ Hoàn thành",
            value=f"{metrics['completion_rate']:.1f}%",
            delta=None
        )
    
    with m4:
        st.metric(
            label="🎨 Thiết kế Đã Gen",
            value=f"{metrics['designs_done']} / {metrics['total_orders']}",
            delta=f"{metrics['total_orders'] - metrics['designs_done']} còn lại"
        )
    
    # === ROW 2: PROGRESS BARS ===
    st.markdown("---")
    st.markdown("### 📈 Tiến độ Tổng thể")
    
    prog1, prog2 = st.columns(2)
    with prog1:
        st.markdown("**Tiến độ Hoàn thành Đơn hàng**")
        st.progress(metrics['completion_rate'] / 100)
        st.caption(f"{metrics['completed_orders']}/{metrics['total_orders']} đơn đã giao")
    
    with prog2:
        design_rate = (metrics['designs_done'] / metrics['total_orders'] * 100) if metrics['total_orders'] > 0 else 0
        st.markdown("**Tiến độ Thiết kế AI**")
        st.progress(design_rate / 100)
        st.caption(f"{metrics['designs_done']}/{metrics['total_orders']} thiết kế đã hoàn thành")
    
    # === ROW 3: MAIN CHARTS ===
    st.markdown("---")
    st.markdown("### 📊 Phân tích Chi tiết")
    
    chart1, chart2 = st.columns(2)
    
    with chart1:
        # Biểu đồ tròn trạng thái
        fig_pie = create_status_pie_chart(df)
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with chart2:
        # Biểu đồ cột top sản phẩm
        fig_bar = create_top_products_chart(df)
        st.plotly_chart(fig_bar, use_container_width=True)
    
    # === ROW 4: TIMELINE & SKU ===
    chart3, chart4 = st.columns(2)
    
    with chart3:
        # Biểu đồ xu hướng theo thời gian
        fig_line = create_orders_timeline_chart(df)
        st.plotly_chart(fig_line, use_container_width=True)
    
    with chart4:
        # Biểu đồ phân tích màu sắc
        fig_sku = create_sku_analysis_chart(df)
        st.plotly_chart(fig_sku, use_container_width=True)
    
    # === ROW 5: DETAILED TABLE ===
    st.markdown("---")
    st.markdown("### 📋 Chi tiết Trạng thái Đơn hàng")
    
    # Tạo bảng tổng hợp trạng thái
    status_summary = df['Trạng thái'].value_counts().reset_index()
    status_summary.columns = ['Trạng thái', 'Số lượng']
    status_summary['Tỷ lệ'] = (status_summary['Số lượng'] / len(df) * 100).round(1).astype(str) + '%'
    
    # Hiển thị dạng horizontal metrics
    cols = st.columns(len(status_summary))
    for idx, row in status_summary.iterrows():
        with cols[idx % len(cols)]:
            color = STATUS_COLORS.get(row['Trạng thái'], '#808080')
            st.markdown(f"""
                <div style="background-color: {color}; padding: 15px; border-radius: 10px; text-align: center; color: white; margin: 5px 0;">
                    <h4 style="margin: 0;">{row['Số lượng']}</h4>
                    <p style="margin: 0; font-size: 12px;">{row['Trạng thái']}</p>
                </div>
            """, unsafe_allow_html=True)
    
    # === INSIGHTS ===
    st.markdown("---")
    st.markdown("### 💡 Insights & Gợi ý")
    
    insight1, insight2 = st.columns(2)
    
    with insight1:
        # Đơn hàng cần ưu tiên
        pending_design = df[(df['Anh_Design'].isna()) & (df['Trạng thái'].isin(['New', 'Đã xác nhận', 'Đang thiết kế']))]
        if len(pending_design) > 0:
            st.warning(f"⚠️ **{len(pending_design)} đơn hàng** đang chờ thiết kế AI. Hãy vào trang 'Trợ lý AI Design' để xử lý!")
        else:
            st.success("✅ Tất cả đơn hàng đã có thiết kế!")
    
    with insight2:
        # Sản phẩm bán chạy nhất
        top_product = df.groupby('Sản phẩm')['Số lượng'].sum().idxmax()
        st.info(f"🏆 Sản phẩm bán chạy nhất: **{top_product}**")

