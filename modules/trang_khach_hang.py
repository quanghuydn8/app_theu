import streamlit as st
import pandas as pd
from modules.data_handler import lay_danh_sach_khach_hang, lay_lich_su_khach, sync_all_customer_totals, fetch_all_orders
from modules.ui_components import render_order_detail_view

def render_customer_page():
    st.title("👥 Quản lý Khách hàng")
    
    # 1. SEARCH BOX (DUY NHẤT)
    search_term = st.text_input("🔍 Tìm khách (Nhập Tên hoặc SĐT và nhấn Enter)", placeholder="Ví dụ: 0909123...")
    
    # --- BỘ LỌC NÂNG CAO ---
    with st.expander("⚡ Bộ lọc nâng cao (Hạng & Chi tiêu)"):
        f_c1, f_c2 = st.columns(2)
        filter_rank = f_c1.selectbox("Hạng khách hàng", ["Tất cả", "Bạc (< 500k)", "🥇 Vàng (500k-5tr)", "💎 Kim Cương (> 5tr)"])
        filter_min_spend = f_c2.number_input("Chi tiêu tối thiểu", min_value=0, step=500000)

    # 2. LOGIC DATA
    df_customers = lay_danh_sach_khach_hang(search_term if search_term else None)
    df_orders = fetch_all_orders()

    if not df_orders.empty and not df_customers.empty:
        # Tính toán tổng hợp từ bảng Orders (Real-time)
        stats = df_orders.groupby("khach_hang_id").agg({
            "thanh_tien": "sum",
            "ma_don": "count"
        }).reset_index()
        
        # Merge
        stats.rename(columns={"thanh_tien": "real_tong_tieu", "ma_don": "real_so_don", "khach_hang_id": "id"}, inplace=True)
        df_customers = pd.merge(df_customers, stats, on="id", how="left")
        
        # FillNa
        df_customers["tong_tieu"] = df_customers["real_tong_tieu"].fillna(0)
        df_customers["so_don_hang"] = df_customers["real_so_don"].fillna(0)

    # 3. APPLY FILTERS
    if not df_customers.empty:
        if filter_min_spend > 0:
            df_customers = df_customers[df_customers['tong_tieu'] >= filter_min_spend]
        
        if filter_rank != "Tất cả":
            if "Bạc" in filter_rank:
                df_customers = df_customers[df_customers['tong_tieu'] < 500000]
            elif "Vàng" in filter_rank:
                df_customers = df_customers[(df_customers['tong_tieu'] >= 500000) & (df_customers['tong_tieu'] < 5000000)]
            elif "Kim Cương" in filter_rank:
                df_customers = df_customers[df_customers['tong_tieu'] >= 5000000]

    # 4. HIỂN THỊ LIST KHÁCH HÀNG (INTERACTIVE)
    if not df_customers.empty:
        display_df = df_customers[["id", "ho_ten", "sdt", "dia_chi", "tong_tieu", "so_don_hang", "nguon_shop"]]
        display_df.columns = ["ID", "Họ Tên", "SĐT", "Địa chỉ", "Tổng chi tiêu", "Số đơn", "Nguồn"]
        
        st.info("👆 Click vào một dòng để xem chi tiết khách hàng")
        
        # TABLE SELECT EVENT
        event = st.dataframe(
            display_df, 
            hide_index=True,
            on_select="rerun", 
            selection_mode="single-row",
            column_config={
                "Tổng chi tiêu": st.column_config.NumberColumn(format="%d đ"),
                "ID": st.column_config.TextColumn(width="small"),
            },
            use_container_width=True
        )
        
        # 5. XỬ LÝ KHI CHỌN KHÁCH HÀNG
        selected_rows = event.selection.rows
        if selected_rows:
            index = selected_rows[0]
            selected_sdt = display_df.iloc[index]["SĐT"]
            
            # GET CUSTOMER INFO
            khach = df_customers[df_customers["sdt"] == selected_sdt].iloc[0]
            khach_id = int(khach["id"])
            
            # GET HISTORY
            df_history = lay_lich_su_khach(khach_id)
            real_total = df_history["thanh_tien"].sum() if (not df_history.empty and "thanh_tien" in df_history.columns) else 0

            # RANKING UI
            rank_name = "Bạc"
            rank_color = "#C0C0C0"
            if real_total >= 5000000:
                rank_name = "💎 Kim Cương"
                rank_color = "#E0F7FA"
            elif real_total >= 500000:
                rank_name = "🥇 Vàng"
                rank_color = "#FFF9C4"

            st.markdown("---")
            st.markdown("### 📜 Hồ sơ khách hàng")
            
            with st.container(border=True):
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"""
                    <div style="font-size: 14px; color: #555;">Khách hàng</div>
                    <div style="font-size: 24px; font-weight: 600;">
                        {khach["ho_ten"]}
                        <span style="background-color: {rank_color}; color: #333; padding: 4px 8px; border-radius: 12px; font-size: 0.6em; vertical-align: middle; border: 1px solid #ddd;">
                            {rank_name}
                        </span>
                    </div>
                """, unsafe_allow_html=True)
                c2.metric("Tổng chi tiêu", f"{real_total:,.0f} đ", delta="Real-time check", delta_color="off")
                c3.metric("Số đơn hàng", len(df_history) if not df_history.empty else 0)
                st.write(f"🏠 Địa chỉ: {khach['dia_chi']}")

            # 6. HIỂN THỊ LIST ĐƠN HÀNG (INTERACTIVE)
            if not df_history.empty:
                st.write("👇 Click vào đơn hàng để xem chi tiết:")
                
                # ORDER TABLE SELECT EVENT
                event_order = st.dataframe(
                    df_history[["ma_don", "created_at", "thanh_tien", "trang_thai", "shop"]],
                    on_select="rerun",
                    selection_mode="single-row",
                    column_config={
                        "thanh_tien": st.column_config.NumberColumn("Giá trị", format="%d đ"),
                        "created_at": st.column_config.DatetimeColumn("Ngày tạo", format="D/M/Y H:mm"),
                    },
                    use_container_width=True,
                    hide_index=True
                )
                
                # 7. XỬ LÝ KHI CHỌN ĐƠN HÀNG
                sel_order_rows = event_order.selection.rows
                if sel_order_rows:
                    idx_order = sel_order_rows[0]
                    selected_ma_don = df_history.iloc[idx_order]["ma_don"]
                    
                    st.markdown("---")
                    st.markdown(f"### 🔎 Chi tiết đơn hàng: {selected_ma_don}")
                    render_order_detail_view(selected_ma_don)
            else:
                st.info("Khách này chưa có đơn hàng nào.")
    else:
        st.info("Không tìm thấy khách hàng nào.")
