"""
fetch_market.py
---------------
Downloads daily market data for the presidential term period using yfinance.
Tickers defined in config.yaml.

Run:
    python src/fetch_market.py

Output:
    data/raw/market_data.csv
"""

import os
import yaml
import pandas as pd
import yfinance as yf

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW  = os.path.join(ROOT, "data", "raw")
os.makedirs(RAW, exist_ok=True)

with open(os.path.join(ROOT, "config.yaml"), "r") as f:
    CONFIG = yaml.safe_load(f)


# ── 1. Determine date range from tweets ──────────────────────────────────────
def get_date_range() -> tuple:
    tweets_path = os.path.join(RAW, "tweets_raw.csv")
    df = pd.read_csv(tweets_path, parse_dates=["created_at"])
    start = df["created_at"].min().strftime("%Y-%m-%d")
    # Add buffer: 5 days before first tweet and after last tweet
    start = (pd.to_datetime(start) - pd.Timedelta(days=5)).strftime("%Y-%m-%d")
    end   = (df["created_at"].max() + pd.Timedelta(days=5)).strftime("%Y-%m-%d")
    print(f"  Tweet period: {start} to {end}")
    return start, end


# ── 2. Download market data ───────────────────────────────────────────────────
def fetch_ticker(ticker: str, name: str, start: str, end: str) -> pd.DataFrame:
    print(f"  Fetching {name} ({ticker})...")
    raw = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)

    if raw.empty:
        print(f"    WARNING: No data returned for {ticker}")
        return pd.DataFrame()

    # Flatten MultiIndex columns if present
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)

    df = raw[["Close"]].copy()
    df.columns = [name]
    df.index.name = "date"
    print(f"    {len(df):>5} trading days")
    return df


# ── 3. Compute daily returns ──────────────────────────────────────────────────
def compute_returns(df: pd.DataFrame) -> pd.DataFrame:
    tickers = CONFIG["data"]["tickers"]
    for name in tickers.keys():
        if name in df.columns:
            df[f"{name}_ret"] = df[name].pct_change() * 100
    return df


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Fetching market data via yfinance...")

    start, end = get_date_range()
    tickers = CONFIG["data"]["tickers"]

    dfs = []
    for name, ticker in tickers.items():
        df = fetch_ticker(ticker, name, start, end)
        if not df.empty:
            dfs.append(df)

    if not dfs:
        raise RuntimeError("No market data loaded.")

    # Merge all tickers on date
    market = dfs[0]
    for df in dfs[1:]:
        market = market.join(df, how="outer")

    market = market.sort_index()
    market = compute_returns(market)
    market = market.reset_index()

    print(f"\nMarket data summary:")
    print(f"  Date range: {market['date'].min().date()} to {market['date'].max().date()}")
    print(f"  Trading days: {len(market)}")
    print(f"  Columns: {list(market.columns)}")

    path = os.path.join(RAW, "market_data.csv")
    market.to_csv(path, index=False)
    print(f"\nSaved -> {path}")
    print("Next step: python src/sentiment.py")