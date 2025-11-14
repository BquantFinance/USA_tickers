import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import ftplib
from io import BytesIO
from datetime import datetime
import base64

st.set_page_config(
    page_title="USA Stock Market Metadata - BQuant Finance", 
    layout="wide", 
    page_icon="📊",
    menu_items={
        'Get Help': 'https://bquantfinance.com',
        'Report a bug': 'https://twitter.com/Gsnchez',
        'About': "Made by @Gsnchez | bquantfinance.com"
    }
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem;
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .footer {
        text-align: center;
        padding: 2rem;
        margin-top: 3rem;
        border-top: 2px solid #e5e7eb;
    }
    .metric-card {
        background-color: #f9fafb;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #3b82f6;
    }
    .download-section {
        background-color: #f0f9ff;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=3600)
def load_all_tickers():
    """Load all ticker metadata from NASDAQ FTP"""
    ftp = ftplib.FTP("ftp.nasdaqtrader.com")
    ftp.login()
    ftp.cwd("SymbolDirectory")
    
    # NASDAQ
    r = BytesIO()
    ftp.retrbinary('RETR nasdaqlisted.txt', r.write)
    r.seek(0)
    nasdaq_df = pd.read_csv(r, sep="|")
    nasdaq_df = nasdaq_df[nasdaq_df['Symbol'].notna()].copy()
    nasdaq_df['Exchange'] = 'NASDAQ'
    
    # NYSE/AMEX
    r = BytesIO()
    ftp.retrbinary('RETR otherlisted.txt', r.write)
    r.seek(0)
    nyse_df = pd.read_csv(r, sep="|")
    nyse_df = nyse_df[nyse_df['ACT Symbol'].notna()].copy()
    nyse_df.rename(columns={'ACT Symbol': 'Symbol'}, inplace=True)
    
    # Standardize columns
    nasdaq_df['Exchange_Detail'] = 'NASDAQ'
    nyse_df['Exchange_Detail'] = nyse_df['Exchange'].map({
        'N': 'NYSE',
        'P': 'NYSE Arca',
        'A': 'NYSE American (AMEX)',
        'Z': 'BATS/CBOE'
    })
    
    ftp.close()
    
    # Combine
    all_tickers = pd.concat([
        nasdaq_df[['Symbol', 'Security Name', 'ETF', 'Exchange', 'Exchange_Detail', 'Market Category']],
        nyse_df[['Symbol', 'Security Name', 'ETF', 'Exchange', 'Exchange_Detail']]
    ], ignore_index=True)
    
    all_tickers['ETF'] = all_tickers['ETF'].fillna('N')
    all_tickers['Type'] = all_tickers['ETF'].map({'Y': 'ETF', 'N': 'Stock'})
    all_tickers['Data_Source'] = 'bquantfinance.com'
    all_tickers['Retrieved_Date'] = datetime.now().strftime('%Y-%m-%d')
    
    return all_tickers, nasdaq_df, nyse_df


def create_download_link(df, filename, file_format='csv'):
    """Create download link for dataframe"""
    if file_format == 'csv':
        data = df.to_csv(index=False)
        mime = 'text/csv'
    elif file_format == 'excel':
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Data')
        data = output.getvalue()
        mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    elif file_format == 'json':
        data = df.to_json(orient='records', indent=2)
        mime = 'application/json'
    
    return data, mime


# ==================== HEADER ====================

st.markdown("""
<div class="main-header">
    <h1>📊 USA Stock Market Metadata Explorer</h1>
    <p style="font-size: 1.2rem; margin: 0;">Complete metadata for all US-listed securities</p>
    <p style="font-size: 0.9rem; margin-top: 0.5rem;">
        Made by <strong>@Gsnchez</strong> | <a href="https://bquantfinance.com" style="color: white; text-decoration: underline;">bquantfinance.com</a>
    </p>
</div>
""", unsafe_allow_html=True)

# Load data
with st.spinner("📡 Loading ticker data from NASDAQ FTP..."):
    all_tickers, nasdaq_df, nyse_df = load_all_tickers()

st.success(f"✅ Loaded {len(all_tickers):,} securities | Data by **bquantfinance.com**")

# ==================== QUICK DOWNLOAD SECTION ====================

st.markdown('<div class="download-section">', unsafe_allow_html=True)
st.subheader("⚡ Quick Download - Complete Dataset")

col1, col2, col3, col4 = st.columns(4)

with col1:
    csv_data, _ = create_download_link(all_tickers, 'usa_tickers', 'csv')
    st.download_button(
        label="📥 Download CSV",
        data=csv_data,
        file_name=f"usa_tickers_complete_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True
    )

with col2:
    excel_data, _ = create_download_link(all_tickers, 'usa_tickers', 'excel')
    st.download_button(
        label="📥 Download Excel",
        data=excel_data,
        file_name=f"usa_tickers_complete_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

with col3:
    json_data, _ = create_download_link(all_tickers, 'usa_tickers', 'json')
    st.download_button(
        label="📥 Download JSON",
        data=json_data,
        file_name=f"usa_tickers_complete_{datetime.now().strftime('%Y%m%d')}.json",
        mime="application/json",
        use_container_width=True
    )

with col4:
    # Download only stocks (no ETFs)
    stocks_only = all_tickers[all_tickers['Type'] == 'Stock']
    stocks_csv, _ = create_download_link(stocks_only, 'usa_stocks', 'csv')
    st.download_button(
        label="📥 Stocks Only CSV",
        data=stocks_csv,
        file_name=f"usa_stocks_only_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True
    )

st.markdown('</div>', unsafe_allow_html=True)

# ==================== KEY METRICS ====================

st.header("📈 Market Overview")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Total Securities", f"{len(all_tickers):,}")
with col2:
    stocks = len(all_tickers[all_tickers['Type'] == 'Stock'])
    st.metric("Stocks", f"{stocks:,}")
with col3:
    etfs = len(all_tickers[all_tickers['Type'] == 'ETF'])
    st.metric("ETFs", f"{etfs:,}")
with col4:
    exchanges = all_tickers['Exchange_Detail'].nunique()
    st.metric("Exchanges", exchanges)
with col5:
    nasdaq_count = len(all_tickers[all_tickers['Exchange'] == 'NASDAQ'])
    st.metric("NASDAQ", f"{nasdaq_count:,}")

# ==================== VISUALIZATIONS ====================

st.header("📊 Market Distribution")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏢 By Exchange", "📦 Stock vs ETF", "🔍 NASDAQ Categories", "📋 Full Data", "💾 Downloads"])

with tab1:
    st.subheader("Securities by Exchange")
    
    exchange_counts = all_tickers['Exchange_Detail'].value_counts().reset_index()
    exchange_counts.columns = ['Exchange', 'Count']
    exchange_counts['Percentage'] = (exchange_counts['Count'] / exchange_counts['Count'].sum() * 100).round(2)
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.pie(exchange_counts, values='Count', names='Exchange',
                    title='Securities Distribution by Exchange',
                    color_discrete_sequence=px.colors.qualitative.Set3,
                    hole=0.4)
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.bar(exchange_counts, x='Exchange', y='Count',
                    title='Securities Count by Exchange',
                    color='Count',
                    color_continuous_scale='Blues',
                    text='Count')
        fig.update_traces(texttemplate='%{text:,}', textposition='outside')
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    st.dataframe(exchange_counts, use_container_width=True, hide_index=True)
    
    # Download this chart data
    csv_data, _ = create_download_link(exchange_counts, 'exchange_distribution', 'csv')
    st.download_button(
        label="📥 Download Exchange Data",
        data=csv_data,
        file_name="exchange_distribution.csv",
        mime="text/csv"
    )

with tab2:
    st.subheader("Stocks vs ETFs Analysis")
    
    type_dist = all_tickers.groupby(['Exchange_Detail', 'Type']).size().reset_index(name='Count')
    
    col1, col2 = st.columns(2)
    
    with col1:
        overall_type = all_tickers['Type'].value_counts().reset_index()
        overall_type.columns = ['Type', 'Count']
        overall_type['Percentage'] = (overall_type['Count'] / overall_type['Count'].sum() * 100).round(2)
        
        fig = px.pie(overall_type, values='Count', names='Type',
                    title='Overall: Stocks vs ETFs',
                    color_discrete_map={'Stock': '#2E86AB', 'ETF': '#A23B72'},
                    hole=0.4)
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.bar(type_dist, x='Exchange_Detail', y='Count', color='Type',
                    title='Stocks vs ETFs by Exchange',
                    color_discrete_map={'Stock': '#2E86AB', 'ETF': '#A23B72'},
                    barmode='group')
        st.plotly_chart(fig, use_container_width=True)
    
    pivot = type_dist.pivot(index='Exchange_Detail', columns='Type', values='Count').fillna(0).astype(int)
    pivot['Total'] = pivot.sum(axis=1)
    pivot['Stock %'] = (pivot['Stock'] / pivot['Total'] * 100).round(1)
    pivot['ETF %'] = (pivot['ETF'] / pivot['Total'] * 100).round(1)
    
    st.dataframe(pivot, use_container_width=True)
    
    # Download
    csv_data, _ = create_download_link(pivot.reset_index(), 'stock_vs_etf', 'csv')
    st.download_button(
        label="📥 Download Stock vs ETF Data",
        data=csv_data,
        file_name="stock_vs_etf_analysis.csv",
        mime="text/csv"
    )

with tab3:
    st.subheader("NASDAQ Market Categories")
    
    if 'Market Category' in nasdaq_df.columns:
        market_cat = nasdaq_df['Market Category'].value_counts().reset_index()
        market_cat.columns = ['Category', 'Count']
        
        category_desc = {
            'Q': 'NASDAQ Global Select Market',
            'G': 'NASDAQ Global Market',
            'S': 'NASDAQ Capital Market'
        }
        market_cat['Description'] = market_cat['Category'].map(category_desc)
        market_cat['Percentage'] = (market_cat['Count'] / market_cat['Count'].sum() * 100).round(2)
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.pie(market_cat, values='Count', names='Description',
                        title='NASDAQ Market Categories Distribution',
                        color_discrete_sequence=px.colors.qualitative.Pastel,
                        hole=0.3)
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.bar(market_cat, x='Description', y='Count',
                        title='Securities by Market Category',
                        color='Count',
                        color_continuous_scale='Teal',
                        text='Count')
            fig.update_traces(texttemplate='%{text:,}', textposition='outside')
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(market_cat, use_container_width=True, hide_index=True)
        
        st.info("""
        **NASDAQ Market Categories:**
        - **Global Select Market (Q)**: Highest tier, strictest listing standards
        - **Global Market (G)**: Mid-tier market
        - **Capital Market (S)**: Small cap companies
        """)
        
        # Download
        csv_data, _ = create_download_link(market_cat, 'nasdaq_categories', 'csv')
        st.download_button(
            label="📥 Download Category Data",
            data=csv_data,
            file_name="nasdaq_market_categories.csv",
            mime="text/csv"
        )

with tab4:
    st.subheader("🔍 Search and Filter Securities")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        search = st.text_input("🔎 Search by Symbol or Name", "", placeholder="e.g., AAPL or Apple")
    with col2:
        exchange_filter = st.multiselect(
            "🏢 Filter by Exchange",
            options=sorted(all_tickers['Exchange_Detail'].unique()),
            default=sorted(all_tickers['Exchange_Detail'].unique())
        )
    with col3:
        type_filter = st.multiselect(
            "📦 Filter by Type",
            options=['Stock', 'ETF'],
            default=['Stock', 'ETF']
        )
    
    # Apply filters
    filtered = all_tickers.copy()
    
    if search:
        filtered = filtered[
            filtered['Symbol'].str.contains(search, case=False, na=False) |
            filtered['Security Name'].str.contains(search, case=False, na=False)
        ]
    
    filtered = filtered[filtered['Exchange_Detail'].isin(exchange_filter)]
    filtered = filtered[filtered['Type'].isin(type_filter)]
    
    st.info(f"📊 Showing **{len(filtered):,}** of **{len(all_tickers):,}** securities")
    
    # Display table
    display_cols = ['Symbol', 'Security Name', 'Type', 'Exchange_Detail']
    if 'Market Category' in filtered.columns:
        display_cols.append('Market Category')
    
    st.dataframe(
        filtered[display_cols].sort_values('Symbol'),
        use_container_width=True,
        height=400
    )
    
    # Download filtered data
    col1, col2, col3 = st.columns(3)
    with col1:
        csv_data, _ = create_download_link(filtered, 'filtered_tickers', 'csv')
        st.download_button(
            label="📥 Download Filtered (CSV)",
            data=csv_data,
            file_name=f"filtered_tickers_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    with col2:
        excel_data, _ = create_download_link(filtered, 'filtered_tickers', 'excel')
        st.download_button(
            label="📥 Download Filtered (Excel)",
            data=excel_data,
            file_name=f"filtered_tickers_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    with col3:
        json_data, _ = create_download_link(filtered, 'filtered_tickers', 'json')
        st.download_button(
            label="📥 Download Filtered (JSON)",
            data=json_data,
            file_name=f"filtered_tickers_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True
        )

with tab5:
    st.subheader("💾 Bulk Downloads")
    st.markdown("Download pre-filtered datasets for your analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📊 Complete Datasets")
        
        # All tickers
        csv_data, _ = create_download_link(all_tickers, 'all', 'csv')
        st.download_button(
            label="📥 All Securities (CSV)",
            data=csv_data,
            file_name=f"usa_all_securities_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        excel_data, _ = create_download_link(all_tickers, 'all', 'excel')
        st.download_button(
            label="📥 All Securities (Excel)",
            data=excel_data,
            file_name=f"usa_all_securities_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
        json_data, _ = create_download_link(all_tickers, 'all', 'json')
        st.download_button(
            label="📥 All Securities (JSON)",
            data=json_data,
            file_name=f"usa_all_securities_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col2:
        st.markdown("#### 📦 Filtered Datasets")
        
        # Stocks only
        stocks_only = all_tickers[all_tickers['Type'] == 'Stock']
        stocks_csv, _ = create_download_link(stocks_only, 'stocks', 'csv')
        st.download_button(
            label=f"📥 Stocks Only ({len(stocks_only):,} securities)",
            data=stocks_csv,
            file_name=f"usa_stocks_only_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        # ETFs only
        etfs_only = all_tickers[all_tickers['Type'] == 'ETF']
        etfs_csv, _ = create_download_link(etfs_only, 'etfs', 'csv')
        st.download_button(
            label=f"📥 ETFs Only ({len(etfs_only):,} securities)",
            data=etfs_csv,
            file_name=f"usa_etfs_only_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        # NASDAQ only
        nasdaq_only = all_tickers[all_tickers['Exchange'] == 'NASDAQ']
        nasdaq_csv, _ = create_download_link(nasdaq_only, 'nasdaq', 'csv')
        st.download_button(
            label=f"📥 NASDAQ Only ({len(nasdaq_only):,} securities)",
            data=nasdaq_csv,
            file_name=f"nasdaq_tickers_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        # NYSE only
        nyse_only = all_tickers[all_tickers['Exchange_Detail'] == 'NYSE']
        nyse_csv, _ = create_download_link(nyse_only, 'nyse', 'csv')
        st.download_button(
            label=f"📥 NYSE Only ({len(nyse_only):,} securities)",
            data=nyse_csv,
            file_name=f"nyse_tickers_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )

# ==================== STATISTICS ====================

st.header("📊 Detailed Statistics")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🏆 Top Exchanges")
    top_exchanges = all_tickers['Exchange_Detail'].value_counts().head(5).reset_index()
    top_exchanges.columns = ['Exchange', 'Securities']
    top_exchanges['Share %'] = (top_exchanges['Securities'] / len(all_tickers) * 100).round(1)
    st.dataframe(top_exchanges, use_container_width=True, hide_index=True)

with col2:
    st.markdown("### 📦 ETF Breakdown")
    etf_by_exchange = all_tickers[all_tickers['Type'] == 'ETF']['Exchange_Detail'].value_counts().reset_index()
    etf_by_exchange.columns = ['Exchange', 'ETF Count']
    etf_by_exchange['% of All ETFs'] = (etf_by_exchange['ETF Count'] / etfs * 100).round(1)
    st.dataframe(etf_by_exchange, use_container_width=True, hide_index=True)

with col3:
    st.markdown("### 📈 Stock Breakdown")
    stock_by_exchange = all_tickers[all_tickers['Type'] == 'Stock']['Exchange_Detail'].value_counts().reset_index()
    stock_by_exchange.columns = ['Exchange', 'Stock Count']
    stock_by_exchange['% of All Stocks'] = (stock_by_exchange['Stock Count'] / stocks * 100).round(1)
    st.dataframe(stock_by_exchange, use_container_width=True, hide_index=True)

# ==================== INSIGHTS ====================

st.header("🎯 Market Insights")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "ETF Percentage",
        f"{(etfs / len(all_tickers) * 100):.1f}%",
        help="Percentage of all securities that are ETFs"
    )

with col2:
    nasdaq_share = len(all_tickers[all_tickers['Exchange'] == 'NASDAQ'])
    st.metric(
        "NASDAQ Market Share",
        f"{(nasdaq_share / len(all_tickers) * 100):.1f}%",
        help="Percentage of securities listed on NASDAQ"
    )

with col3:
    nyse_share = len(all_tickers[all_tickers['Exchange_Detail'] == 'NYSE'])
    st.metric(
        "NYSE Market Share",
        f"{(nyse_share / len(all_tickers) * 100):.1f}%",
        help="Percentage of securities listed on NYSE"
    )

with col4:
    avg_name_length = all_tickers['Security Name'].str.len().mean()
    st.metric(
        "Avg Name Length",
        f"{avg_name_length:.0f} chars",
        help="Average length of security names"
    )

# ==================== FOOTER ====================

st.markdown("---")
st.markdown("""
<div class="footer">
    <h3>📊 USA Stock Market Metadata Explorer</h3>
    <p style="font-size: 1.1rem; margin: 1rem 0;">
        <strong>Created by <a href="https://twitter.com/Gsnchez" target="_blank">@Gsnchez</a></strong><br>
        <a href="https://bquantfinance.com" target="_blank" style="color: #3b82f6; text-decoration: none; font-weight: bold;">bquantfinance.com</a>
    </p>
    <p style="color: #6b7280; font-size: 0.9rem;">
        📡 <strong>Data Source:</strong> NASDAQ Trader FTP Server<br>
        🔄 <strong>Update Frequency:</strong> Real-time (data cached for 1 hour)<br>
        📊 <strong>Coverage:</strong> All US-listed securities (NASDAQ, NYSE, NYSE Arca, NYSE American, BATS)<br>
        📅 <strong>Last Updated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </p>
    <p style="margin-top: 1rem;">
        <a href="https://twitter.com/Gsnchez" target="_blank">🐦 Twitter</a> • 
        <a href="https://bquantfinance.com" target="_blank">🌐 Website</a> • 
        <a href="https://substack.com/@bquantfinance" target="_blank">📧 Newsletter</a>
    </p>
    <p style="font-size: 0.8rem; color: #9ca3af; margin-top: 1rem;">
        Made with ❤️ for the quantitative finance community<br>
        © {datetime.now().year} BQuant Finance. All rights reserved.
    </p>
</div>
""".format(datetime=datetime), unsafe_allow_html=True)
