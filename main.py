import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import ftplib
from io import BytesIO
from datetime import datetime

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
    nasdaq_df['Exchange_Detail'] = 'NASDAQ'
    
    # NYSE/AMEX
    r = BytesIO()
    ftp.retrbinary('RETR otherlisted.txt', r.write)
    r.seek(0)
    nyse_df = pd.read_csv(r, sep="|")
    nyse_df = nyse_df[nyse_df['ACT Symbol'].notna()].copy()
    nyse_df.rename(columns={'ACT Symbol': 'Symbol'}, inplace=True)
    nyse_df['Exchange_Detail'] = nyse_df['Exchange'].map({
        'N': 'NYSE',
        'P': 'NYSE Arca',
        'A': 'NYSE American (AMEX)',
        'Z': 'BATS/CBOE'
    }).fillna('Other')
    
    ftp.close()
    
    # Combine
    all_tickers = pd.concat([
        nasdaq_df[['Symbol', 'Security Name', 'ETF', 'Exchange', 'Exchange_Detail', 'Market Category']],
        nyse_df[['Symbol', 'Security Name', 'ETF', 'Exchange', 'Exchange_Detail']]
    ], ignore_index=True)
    
    all_tickers['ETF'] = all_tickers['ETF'].fillna('N')
    all_tickers['Type'] = all_tickers['ETF'].map({'Y': 'ETF', 'N': 'Stock'})
    all_tickers['Exchange_Detail'] = all_tickers['Exchange_Detail'].fillna('Unknown')
    all_tickers['Data_Source'] = 'bquantfinance.com'
    all_tickers['Retrieved_Date'] = datetime.now().strftime('%Y-%m-%d')
    
    return all_tickers


def create_download_link(df, file_format='csv'):
    """Create download data"""
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
    all_tickers = load_all_tickers()

st.success(f"✅ Loaded {len(all_tickers):,} securities | Data by **bquantfinance.com**")

# ==================== KEY METRICS ====================

col1, col2, col3, col4, col5 = st.columns(5)

stocks = len(all_tickers[all_tickers['Type'] == 'Stock'])
etfs = len(all_tickers[all_tickers['Type'] == 'ETF'])

with col1:
    st.metric("Total Securities", f"{len(all_tickers):,}")
with col2:
    st.metric("Stocks", f"{stocks:,}")
with col3:
    st.metric("ETFs", f"{etfs:,}")
with col4:
    nasdaq_count = len(all_tickers[all_tickers['Exchange'] == 'NASDAQ'])
    st.metric("NASDAQ", f"{nasdaq_count:,}")
with col5:
    nyse_count = len(all_tickers[all_tickers['Exchange_Detail'] == 'NYSE'])
    st.metric("NYSE", f"{nyse_count:,}")

# ==================== TICKER LIST (MAIN FOCUS) ====================

st.header("📋 All USA Tickers")

col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

with col1:
    search = st.text_input("🔎 Search by Symbol or Name", "", placeholder="e.g., AAPL or Apple")
with col2:
    exchange_options = sorted([x for x in all_tickers['Exchange_Detail'].unique() if pd.notna(x)])
    exchange_filter = st.multiselect(
        "🏢 Exchange",
        options=exchange_options,
        default=exchange_options
    )
with col3:
    type_filter = st.multiselect(
        "📦 Type",
        options=['Stock', 'ETF'],
        default=['Stock', 'ETF']
    )
with col4:
    show_rows = st.selectbox("📏 Rows", [100, 250, 500, 1000, 5000], index=1)

# Apply filters
filtered = all_tickers.copy()

if search:
    filtered = filtered[
        filtered['Symbol'].str.contains(search, case=False, na=False) |
        filtered['Security Name'].str.contains(search, case=False, na=False)
    ]

filtered = filtered[filtered['Exchange_Detail'].isin(exchange_filter)]
filtered = filtered[filtered['Type'].isin(type_filter)]

st.info(f"📊 Showing **{len(filtered):,}** securities")

# Display table
display_cols = ['Symbol', 'Security Name', 'Type', 'Exchange_Detail']
if 'Market Category' in filtered.columns:
    display_cols.append('Market Category')

st.dataframe(
    filtered[display_cols].sort_values('Symbol').head(show_rows),
    use_container_width=True,
    height=500
)

# ==================== SINGLE DOWNLOAD SECTION ====================

st.markdown('<div class="download-section">', unsafe_allow_html=True)
st.subheader("💾 Download Data")

col1, col2, col3, col4 = st.columns(4)

with col1:
    csv_data, _ = create_download_link(filtered, 'csv')
    st.download_button(
        label=f"📥 CSV ({len(filtered):,} rows)",
        data=csv_data,
        file_name=f"usa_tickers_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True
    )

with col2:
    excel_data, _ = create_download_link(filtered, 'excel')
    st.download_button(
        label=f"📥 Excel ({len(filtered):,} rows)",
        data=excel_data,
        file_name=f"usa_tickers_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

with col3:
    stocks_only = all_tickers[all_tickers['Type'] == 'Stock']
    stocks_csv, _ = create_download_link(stocks_only, 'csv')
    st.download_button(
        label=f"📥 Stocks Only ({len(stocks_only):,})",
        data=stocks_csv,
        file_name=f"usa_stocks_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True
    )

with col4:
    etfs_only = all_tickers[all_tickers['Type'] == 'ETF']
    etfs_csv, _ = create_download_link(etfs_only, 'csv')
    st.download_button(
        label=f"📥 ETFs Only ({len(etfs_only):,})",
        data=etfs_csv,
        file_name=f"usa_etfs_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True
    )

st.markdown('</div>', unsafe_allow_html=True)

# ==================== VISUALIZATIONS ====================

st.header("📊 Market Distribution")

tab1, tab2, tab3 = st.tabs(["🏢 By Exchange", "📦 Stock vs ETF", "🔍 NASDAQ Categories"])

with tab1:
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

with tab2:
    type_dist = all_tickers.groupby(['Exchange_Detail', 'Type']).size().reset_index(name='Count')
    
    col1, col2 = st.columns(2)
    
    with col1:
        overall_type = all_tickers['Type'].value_counts().reset_index()
        overall_type.columns = ['Type', 'Count']
        
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

with tab3:
    nasdaq_df = all_tickers[all_tickers['Exchange'] == 'NASDAQ']
    if 'Market Category' in nasdaq_df.columns:
        market_cat = nasdaq_df['Market Category'].value_counts().reset_index()
        market_cat.columns = ['Category', 'Count']
        
        category_desc = {
            'Q': 'NASDAQ Global Select',
            'G': 'NASDAQ Global',
            'S': 'NASDAQ Capital'
        }
        market_cat['Description'] = market_cat['Category'].map(category_desc).fillna('Other')
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.pie(market_cat, values='Count', names='Description',
                        title='NASDAQ Market Categories',
                        color_discrete_sequence=px.colors.qualitative.Pastel,
                        hole=0.3)
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.bar(market_cat, x='Description', y='Count',
                        title='Securities by Category',
                        color='Count',
                        color_continuous_scale='Teal',
                        text='Count')
            fig.update_traces(texttemplate='%{text:,}', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)
        
        st.info("""
        **NASDAQ Categories:** Global Select (highest tier) • Global (mid-tier) • Capital (small cap)
        """)

# ==================== STATISTICS ====================

st.header("📊 Quick Stats")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🏆 Top 5 Exchanges")
    top_exchanges = all_tickers['Exchange_Detail'].value_counts().head(5).reset_index()
    top_exchanges.columns = ['Exchange', 'Count']
    top_exchanges['%'] = (top_exchanges['Count'] / len(all_tickers) * 100).round(1)
    st.dataframe(top_exchanges, use_container_width=True, hide_index=True)

with col2:
    st.markdown("### 📦 ETF Distribution")
    etf_by_exchange = all_tickers[all_tickers['Type'] == 'ETF']['Exchange_Detail'].value_counts().head(5).reset_index()
    etf_by_exchange.columns = ['Exchange', 'ETFs']
    st.dataframe(etf_by_exchange, use_container_width=True, hide_index=True)

with col3:
    st.markdown("### 📈 Stock Distribution")
    stock_by_exchange = all_tickers[all_tickers['Type'] == 'Stock']['Exchange_Detail'].value_counts().head(5).reset_index()
    stock_by_exchange.columns = ['Exchange', 'Stocks']
    st.dataframe(stock_by_exchange, use_container_width=True, hide_index=True)

# ==================== FOOTER ====================

st.markdown("---")
st.markdown(f"""
<div class="footer">
    <h3>📊 USA Stock Market Metadata Explorer</h3>
    <p style="font-size: 1.1rem; margin: 1rem 0;">
        <strong>Created by <a href="https://twitter.com/Gsnchez" target="_blank">@Gsnchez</a></strong><br>
        <a href="https://bquantfinance.com" target="_blank" style="color: #3b82f6; text-decoration: none; font-weight: bold;">bquantfinance.com</a>
    </p>
    <p style="color: #6b7280; font-size: 0.9rem;">
        📡 Data Source: NASDAQ Trader FTP Server<br>
        🔄 Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
        📊 Coverage: All US-listed securities (NASDAQ, NYSE, Arca, American, BATS)
    </p>
    <p style="margin-top: 1rem;">
        <a href="https://twitter.com/Gsnchez" target="_blank">🐦 Twitter</a> • 
        <a href="https://bquantfinance.com" target="_blank">🌐 Website</a> • 
        <a href="https://substack.com/@bquantfinance" target="_blank">📧 Newsletter</a>
    </p>
</div>
""", unsafe_allow_html=True)
