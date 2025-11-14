import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import ftplib
from io import BytesIO

st.set_page_config(page_title="USA Stock Market Metadata", layout="wide", page_icon="📊")


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
    
    return all_tickers, nasdaq_df, nyse_df


# ==================== APP ====================

st.title("📊 USA Stock Market Metadata Explorer")
st.markdown("### Complete metadata for all US-listed securities (NASDAQ, NYSE, AMEX)")

# Load data
with st.spinner("Loading ticker data from NASDAQ FTP..."):
    all_tickers, nasdaq_df, nyse_df = load_all_tickers()

st.success(f"✅ Loaded {len(all_tickers):,} securities")

# ==================== KEY METRICS ====================

st.header("📈 Market Overview")

col1, col2, col3, col4 = st.columns(4)

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

# ==================== VISUALIZATIONS ====================

st.header("📊 Market Distribution")

tab1, tab2, tab3, tab4 = st.tabs(["🏢 By Exchange", "📦 Stock vs ETF", "🔍 NASDAQ Categories", "📋 Full Data"])

with tab1:
    # Exchange distribution
    exchange_counts = all_tickers['Exchange_Detail'].value_counts().reset_index()
    exchange_counts.columns = ['Exchange', 'Count']
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.pie(exchange_counts, values='Count', names='Exchange',
                    title='Securities by Exchange',
                    color_discrete_sequence=px.colors.qualitative.Set3)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.bar(exchange_counts, x='Exchange', y='Count',
                    title='Securities Count by Exchange',
                    color='Exchange',
                    color_discrete_sequence=px.colors.qualitative.Set3)
        st.plotly_chart(fig, use_container_width=True)
    
    st.dataframe(exchange_counts, use_container_width=True)

with tab2:
    # Stock vs ETF by exchange
    type_dist = all_tickers.groupby(['Exchange_Detail', 'Type']).size().reset_index(name='Count')
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Overall pie chart
        overall_type = all_tickers['Type'].value_counts().reset_index()
        overall_type.columns = ['Type', 'Count']
        
        fig = px.pie(overall_type, values='Count', names='Type',
                    title='Overall: Stocks vs ETFs',
                    color_discrete_map={'Stock': '#2E86AB', 'ETF': '#A23B72'})
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Stacked bar by exchange
        fig = px.bar(type_dist, x='Exchange_Detail', y='Count', color='Type',
                    title='Stocks vs ETFs by Exchange',
                    color_discrete_map={'Stock': '#2E86AB', 'ETF': '#A23B72'})
        st.plotly_chart(fig, use_container_width=True)
    
    # Detailed table
    pivot = type_dist.pivot(index='Exchange_Detail', columns='Type', values='Count').fillna(0).astype(int)
    pivot['Total'] = pivot.sum(axis=1)
    pivot['Stock %'] = (pivot['Stock'] / pivot['Total'] * 100).round(1)
    pivot['ETF %'] = (pivot['ETF'] / pivot['Total'] * 100).round(1)
    
    st.dataframe(pivot, use_container_width=True)

with tab3:
    # NASDAQ Market Categories
    if 'Market Category' in nasdaq_df.columns:
        market_cat = nasdaq_df['Market Category'].value_counts().reset_index()
        market_cat.columns = ['Category', 'Count']
        
        # Add descriptions
        category_desc = {
            'Q': 'NASDAQ Global Select Market',
            'G': 'NASDAQ Global Market',
            'S': 'NASDAQ Capital Market'
        }
        market_cat['Description'] = market_cat['Category'].map(category_desc)
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.pie(market_cat, values='Count', names='Description',
                        title='NASDAQ Market Categories',
                        color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.bar(market_cat, x='Description', y='Count',
                        title='Securities by Market Category',
                        color='Description',
                        color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(market_cat, use_container_width=True)
        
        st.info("""
        **NASDAQ Market Categories:**
        - **Global Select Market (Q)**: Highest tier, strictest standards
        - **Global Market (G)**: Mid tier
        - **Capital Market (S)**: Small cap companies
        """)

with tab4:
    # Full data table with filters
    st.subheader("🔍 Search and Filter")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        search = st.text_input("Search by Symbol or Name", "")
    with col2:
        exchange_filter = st.multiselect(
            "Filter by Exchange",
            options=all_tickers['Exchange_Detail'].unique(),
            default=all_tickers['Exchange_Detail'].unique()
        )
    with col3:
        type_filter = st.multiselect(
            "Filter by Type",
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
    
    st.info(f"Showing {len(filtered):,} of {len(all_tickers):,} securities")
    
    # Display table
    display_cols = ['Symbol', 'Security Name', 'Type', 'Exchange_Detail']
    if 'Market Category' in filtered.columns:
        display_cols.append('Market Category')
    
    st.dataframe(
        filtered[display_cols].sort_values('Symbol'),
        use_container_width=True,
        height=400
    )
    
    # Download button
    csv = filtered.to_csv(index=False)
    st.download_button(
        label="📥 Download Filtered Data (CSV)",
        data=csv,
        file_name="usa_tickers_metadata.csv",
        mime="text/csv"
    )

# ==================== STATISTICS ====================

st.header("📊 Detailed Statistics")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Top 10 Exchanges")
    top_exchanges = all_tickers['Exchange_Detail'].value_counts().head(10).reset_index()
    top_exchanges.columns = ['Exchange', 'Securities']
    st.dataframe(top_exchanges, use_container_width=True, hide_index=True)

with col2:
    st.subheader("ETF Concentration")
    etf_by_exchange = all_tickers[all_tickers['Type'] == 'ETF']['Exchange_Detail'].value_counts().reset_index()
    etf_by_exchange.columns = ['Exchange', 'ETF Count']
    st.dataframe(etf_by_exchange, use_container_width=True, hide_index=True)

# ==================== INTERESTING FACTS ====================

st.header("🎯 Market Insights")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "ETF Percentage",
        f"{(etfs / len(all_tickers) * 100):.1f}%",
        help="Percentage of all securities that are ETFs"
    )

with col2:
    nasdaq_only = len(all_tickers[all_tickers['Exchange'] == 'NASDAQ'])
    st.metric(
        "NASDAQ Market Share",
        f"{(nasdaq_only / len(all_tickers) * 100):.1f}%",
        help="Percentage of securities listed on NASDAQ"
    )

with col3:
    nyse_only = len(all_tickers[all_tickers['Exchange_Detail'] == 'NYSE'])
    st.metric(
        "NYSE Market Share",
        f"{(nyse_only / len(all_tickers) * 100):.1f}%",
        help="Percentage of securities listed on NYSE"
    )

# ==================== FOOTER ====================

st.markdown("---")
st.markdown("""
**Data Source:** NASDAQ Trader FTP Server  
**Update Frequency:** Real-time (data refreshed every hour)  
**Coverage:** All US-listed securities (NASDAQ, NYSE, NYSE Arca, NYSE American, BATS)
""")
