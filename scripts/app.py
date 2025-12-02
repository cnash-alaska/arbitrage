# app.py
import streamlit as st
import pandas as pd
import os


def run_scripts():
    scripts = [
        "scripts/fetch_markets.py",
        "scripts/markets/bitcoin.py",
        "scripts/analysis.py"
        # Add more market scripts above as needed
    ]

    for script in scripts:
        st.write(f"Running {script}...")
        try:
            with open(script, "r") as f:
                code = f.read()
                exec(code, {})
            st.success(f"Finished {script}")
        except Exception as e:
            st.error(f"Error in {script}: {e}")

# -----------------------
# App configuration
# -----------------------
st.set_page_config(
    page_title="Arbitrage Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------
# Sidebar Navigation
# -----------------------
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Trade", "Report"])

# -----------------------
# Load trades CSV
# -----------------------
TRADES_FILE = "trades/temp/arbitrage_formula_results.csv"
MARKETS_FOLDER = "markets"

@st.cache_data
def load_trades(csv_path=TRADES_FILE):
    if os.path.exists(csv_path):
        return pd.read_csv(csv_path)
    else:
        return pd.DataFrame()

trades_df = load_trades()

# -----------------------
# Load all validity check CSVs
# -----------------------
@st.cache_data
def load_validity_checks():
    all_dfs = []
    for m in os.listdir(MARKETS_FOLDER):
        folder_path = os.path.join(MARKETS_FOLDER, m)
        if os.path.isdir(folder_path):
            csv_file = os.path.join(folder_path, f"{m}_validity_check.csv")
            if os.path.exists(csv_file):
                df = pd.read_csv(csv_file)
                df['market'] = m
                all_dfs.append(df)
    if all_dfs:
        return pd.concat(all_dfs, ignore_index=True)
    else:
        return pd.DataFrame()

validity_df = load_validity_checks()

# -----------------------
# Page: Trade
# -----------------------
# -----------------------
# Page: Trade
# -----------------------
def trade_page():
    st.title("Trade Execution")

        # -------------------------
    # Refresh & Run Scripts
    # -------------------------
    st.subheader("Refresh Market Data")
    if st.button("Run Market Scripts"):
        st.info("Running full market update... please wait.")
        run_scripts()
        st.success("All scripts completed.")
        st.stop()

    
    st.subheader("Validate Trades")

    # Load trades fresh each rerun (not cached)
    if os.path.exists(TRADES_FILE):
        trades_df = pd.read_csv(TRADES_FILE)
    else:
        trades_df = pd.DataFrame()
        st.warning("No trades CSV found. Please upload or check path.")
        return

    if validity_df.empty:
        st.warning("No validity check CSVs found.")
        return

    # Session state for tracking current row
    if 'row_index' not in st.session_state:
        st.session_state.row_index = 0

    row_idx = st.session_state.row_index
    if row_idx >= len(validity_df):
        st.success("All rows validated!")
        return

    row = validity_df.iloc[row_idx]

    st.markdown(f"### Market: {row['market']}")
    st.write("**Kalshi Rule:**")
    st.write(row['kalshi_rules_primary'])
    st.write("**Polymarket Question:**")
    st.write(row['polymarket_question'])
    st.write(f"Row {row_idx + 1} of {len(validity_df)}")
    st.write("---")

    col1, col2 = st.columns(2)

    if col1.button("Valid"):
        st.session_state.row_index += 1

    if col2.button("Invalid"):
        # Remove the corresponding row from trades_df
        mask = (trades_df['kalshi_ticker'] == row['kalshi_ticker']) & \
               (trades_df['poly_ticker'] == row['polymarket_id'])
        trades_df = trades_df[~mask]
        trades_df.to_csv(TRADES_FILE, index=False)
        st.session_state.row_index += 1

    # Instead of st.experimental_rerun(), we just display current row info
    # Streamlit will naturally rerun on the next button click
    st.info("Click Valid or Invalid to proceed to the next row.")

    st.subheader("Execute Trades")
    if st.button("Execute All Valid Trades"):
        st.info("Execution logic will go here.")

# -----------------------
# Page: Report
# -----------------------
def report_page():
    st.title("Trade Report")
    st.info("This page will display executed trades, outcomes, and balances over time.")
    if trades_df.empty:
        st.warning("No trades CSV found. Please upload or check path.")
    else:
        st.dataframe(trades_df.head())  # Replace with report table / chart later

# -----------------------
# Page Routing
# -----------------------
if page == "Trade":
    trade_page()
elif page == "Report":
    report_page()
