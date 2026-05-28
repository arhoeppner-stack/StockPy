import pandas as pd
import streamlit as st
import plotly.express as px
import yfinance as yf

st.set_page_config(page_title="Portfolio Dashboard", layout="wide")

st.title("Portfolio Dashboard")
st.caption("Upload a portfolio CSV to view current values, allocation, and performance.")

uploaded = st.file_uploader("Upload portfolio CSV", type=["csv"])


@st.cache_data(ttl=300)
def load_quotes(symbols):
    symbols = [s for s in sorted(set(symbols)) if isinstance(s, str) and s.strip()]
    if not symbols:
        return pd.DataFrame(columns=["Symbol", "Current Price"])

    rows = []
    if len(symbols) == 1:
        sym = symbols[0]
        ticker = yf.Ticker(sym)
        try:
            price = ticker.fast_info.get("last_price", None)
        except Exception:
            price = None
        if price is None:
            try:
                hist = ticker.history(period="5d")
                price = float(hist["Close"].dropna().iloc[-1]) if not hist.empty else None
            except Exception:
                price = None
        rows.append({"Symbol": sym, "Current Price": price})
        return pd.DataFrame(rows)

    data = yf.download(
        symbols,
        period="1d",
        interval="1d",
        group_by="ticker",
        auto_adjust=False,
        progress=False,
        threads=True,
    )

    for sym in symbols:
        price = None
        try:
            if isinstance(data.columns, pd.MultiIndex):
                close = data[sym]["Close"].dropna()
                if not close.empty:
                    price = float(close.iloc[-1])
            else:
                if "Close" in data.columns and not data["Close"].dropna().empty:
                    price = float(data["Close"].dropna().iloc[-1])
        except Exception:
            try:
                ticker = yf.Ticker(sym)
                price = ticker.fast_info.get("last_price", None)
            except Exception:
                price = None

        rows.append({"Symbol": sym, "Current Price": price})

    return pd.DataFrame(rows)


def clean_num(series):
    return pd.to_numeric(
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace('"', "", regex=False),
        errors="coerce",
    )


if uploaded is None:
    st.info("Upload a CSV to begin.")
    st.stop()

try:
    df = pd.read_csv(uploaded)
except Exception as e:
    st.error(f"Could not read CSV: {e}")
    st.stop()

required = {"Symbol", "Portfolio", "Qty #"}
missing = required - set(df.columns)
if missing:
    st.error(f"Missing required columns: {', '.join(sorted(missing))}")
    st.stop()

for col in ["Qty #", "Price Paid $", "Value $", "Total Gain $", "Day's Gain $", "Last Price $", "Change $", "Change %", "Total Gain %"]:
    if col in df.columns:
        df[col] = clean_num(df[col])

df["Symbol"] = df["Symbol"].astype(str).str.strip()
df["Portfolio"] = df["Portfolio"].astype(str).str.strip()

quotes = load_quotes(df["Symbol"].dropna().tolist())
df = df.merge(quotes, on="Symbol", how="left")

if "Current Price" not in df.columns:
    df["Current Price"] = pd.NA

df["Market Value"] = df["Qty #"] * df["Current Price"]
fallback_value = df["Value $"] if "Value $" in df.columns else pd.Series([pd.NA] * len(df))
df["Market Value"] = df["Market Value"].fillna(fallback_value)
df["Weight %"] = df["Market Value"] / df["Market Value"].sum() * 100

if "Total Gain $" not in df.columns:
    df["Total Gain $"] = pd.NA

portfolio_total = df["Market Value"].sum()
holdings_count = len(df)
accounts_count = df["Portfolio"].nunique()
largest_symbol = df.loc[df["Market Value"].idxmax(), "Symbol"] if df["Market Value"].notna().any() else "N/A"

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Portfolio", f"${portfolio_total:,.2f}")
c2.metric("Holdings", f"{holdings_count}")
c3.metric("Accounts", f"{accounts_count}")
c4.metric("Largest Position", largest_symbol)

st.subheader("Account Summary")
account_summary = (
    df.groupby("Portfolio", dropna=False)
    .agg(
        Holdings=("Symbol", "count"),
        Market_Value=("Market Value", "sum"),
        Total_Gain=("Total Gain $", "sum"),
    )
    .reset_index()
    .rename(columns={"Market_Value": "Market Value", "Total_Gain": "Total Gain"})
)
st.dataframe(account_summary, use_container_width=True)

st.subheader("Holdings")
show_cols = [
    col
    for col in [
        "Symbol",
        "Portfolio",
        "Qty #",
        "Price Paid $",
        "Current Price",
        "Market Value",
        "Weight %",
        "Total Gain $",
    ]
    if col in df.columns
]
st.dataframe(
    df[show_cols].sort_values("Market Value", ascending=False),
    use_container_width=True,
)

left, right = st.columns(2)
with left:
    pie = px.pie(
        df,
        names="Portfolio",
        values="Market Value",
        title="Allocation by Account",
    )
    st.plotly_chart(pie, use_container_width=True)

with right:
    bar = px.bar(
        df.sort_values("Market Value", ascending=False),
        x="Symbol",
        y="Market Value",
        color="Portfolio",
        title="Positions by Value",
    )
    st.plotly_chart(bar, use_container_width=True)

st.subheader("By Account")
for portfolio_name, group in df.groupby("Portfolio"):
    with st.expander(f"{portfolio_name} ({len(group)} holdings)", expanded=False):
        st.dataframe(
            group.sort_values("Market Value", ascending=False)[show_cols],
            use_container_width=True,
        )

csv = df.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download enriched CSV",
    data=csv,
    file_name="portfolio_dashboard_enriched.csv",
    mime="text/csv",
)