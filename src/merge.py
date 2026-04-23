"""
merge.py
--------
Merges sentiment scores with market data.
For each tweet, finds the market return in the following windows:
    +1 day, +3 days

Since we only have daily market data (not intraday), we match each tweet
to the same trading day if posted before market close (4pm ET),
or the next trading day if posted after.

Run:
    python src/merge.py

Output:
    data/processed/merged_dataset.csv
"""

import os
import yaml
import pandas as pd
import numpy as np

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW       = os.path.join(ROOT, "data", "raw")
PROCESSED = os.path.join(ROOT, "data", "processed")
os.makedirs(PROCESSED, exist_ok=True)

with open(os.path.join(ROOT, "config.yaml"), "r") as f:
    CONFIG = yaml.safe_load(f)


# ── 1. Load data ──────────────────────────────────────────────────────────────
def load_data():
    # Sentiment scores
    sent_path = os.path.join(RAW, "sentiment_scores.csv")
    df_sent = pd.read_csv(sent_path, parse_dates=["created_at"])
    df_sent["created_at"] = pd.to_datetime(df_sent["created_at"], utc=True)
    print(f"  Sentiment scores: {len(df_sent)} tweets")

    # Market data
    mkt_path = os.path.join(RAW, "market_data.csv")
    df_mkt = pd.read_csv(mkt_path, parse_dates=["date"])
    df_mkt["date"] = pd.to_datetime(df_mkt["date"]).dt.tz_localize("UTC")
    df_mkt = df_mkt.sort_values("date").reset_index(drop=True)
    print(f"  Market data: {len(df_mkt)} trading days")

    return df_sent, df_mkt


# ── 2. Map tweet to trading day ───────────────────────────────────────────────
def get_trading_day(tweet_time: pd.Timestamp, trading_days: pd.Series) -> pd.Timestamp:
    """
    Map tweet timestamp to relevant trading day.
    NYSE closes at 4pm ET (21:00 UTC).
    - Tweet before 21:00 UTC → same trading day
    - Tweet after 21:00 UTC → next trading day
    """
    MARKET_CLOSE_HOUR = 21  # 4pm ET in UTC

    if tweet_time.hour < MARKET_CLOSE_HOUR:
        target_date = tweet_time.normalize()
    else:
        target_date = (tweet_time + pd.Timedelta(days=1)).normalize()

    target_date = target_date.tz_localize("UTC") if target_date.tzinfo is None else target_date

    # Find nearest trading day on or after target
    future_days = trading_days[trading_days >= target_date]
    if len(future_days) == 0:
        return None
    return future_days.iloc[0]


# ── 3. Compute forward returns ────────────────────────────────────────────────
def get_forward_return(event_date: pd.Timestamp, n_days: int,
                       df_mkt: pd.DataFrame, col: str) -> float:
    """Return % change from event_date close to n trading days later."""
    trading_days = df_mkt["date"]
    idx = trading_days[trading_days == event_date].index
    if len(idx) == 0:
        return np.nan

    start_idx = idx[0]
    end_idx   = start_idx + n_days

    if end_idx >= len(df_mkt):
        return np.nan

    price_start = df_mkt.loc[start_idx, col]
    price_end   = df_mkt.loc[end_idx, col]

    if pd.isna(price_start) or pd.isna(price_end) or price_start == 0:
        return np.nan

    return (price_end - price_start) / price_start * 100


# ── 4. Build merged dataset ───────────────────────────────────────────────────
def build_dataset(df_sent: pd.DataFrame, df_mkt: pd.DataFrame) -> pd.DataFrame:
    tickers  = CONFIG["data"]["tickers"]
    windows  = [1, 3]   # trading days forward
    trading_days = df_mkt["date"]

    rows = []
    skipped = 0

    for _, tweet in df_sent.iterrows():
        event_date = get_trading_day(tweet["created_at"], trading_days)
        if event_date is None:
            skipped += 1
            continue

        row = {
            "created_at":      tweet["created_at"],
            "text":            tweet.get("text", ""),
            "score":           tweet["score"],
            "category":        tweet["category"],
            "market_relevant": tweet["market_relevant"],
            "term":            tweet.get("term", "term1"),
            "event_date":      event_date,
        }

        # Add forward returns for each ticker and window
        for name in tickers.keys():
            col = name
            if col not in df_mkt.columns:
                continue
            for n in windows:
                ret = get_forward_return(event_date, n, df_mkt, col)
                row[f"{name}_ret_{n}d"] = ret

        rows.append(row)

    df = pd.DataFrame(rows)
    print(f"  Merged: {len(df)} tweets matched to trading days ({skipped} skipped)")
    return df


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Loading data...")
    df_sent, df_mkt = load_data()

    print("\nBuilding merged dataset...")
    df = build_dataset(df_sent, df_mkt)

    # Quick summary
    print(f"\nDataset overview:")
    print(f"  Total tweets merged:    {len(df)}")
    print(f"  Market relevant tweets: {df['market_relevant'].sum()}")
    print(f"  Score mean:             {df['score'].mean():.2f}")
    print(f"  Score std:              {df['score'].std():.2f}")
    ret_cols = [c for c in df.columns if "ret" in c]
    print(f"\n  Return columns: {ret_cols}")
    print(df[ret_cols].describe().round(3).to_string())

    path = os.path.join(PROCESSED, "merged_dataset.csv")
    df.to_csv(path, index=False)
    print(f"\nSaved -> {path}")
    print("Next step: python src/analysis.py")