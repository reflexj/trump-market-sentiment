"""
fetch_tweets.py
---------------
Downloads Trump tweets from MarkHershey/CompleteTrumpTweetsArchive on GitHub.
Contains all tweets including deleted ones, pre-split by "in office" period.

Source: https://github.com/MarkHershey/CompleteTrumpTweetsArchive

Run:
    python src/fetch_tweets.py
"""

import os
import yaml
import requests
import pandas as pd
from io import StringIO

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW  = os.path.join(ROOT, "data", "raw")
os.makedirs(RAW, exist_ok=True)

with open(os.path.join(ROOT, "config.yaml"), "r") as f:
    CONFIG = yaml.safe_load(f)

URLS = {
    "term1": "https://raw.githubusercontent.com/MarkHershey/CompleteTrumpTweetsArchive/master/data/realDonaldTrump_in_office.csv",
    "pre_office": "https://raw.githubusercontent.com/MarkHershey/CompleteTrumpTweetsArchive/master/data/realDonaldTrump_bf_office.csv",
}


# ── 1. Download CSV ───────────────────────────────────────────────────────────
def fetch_csv(url: str, label: str) -> pd.DataFrame:
    print(f"  Downloading {label} (this may take 20-30 seconds)...")
    response = requests.get(url, timeout=120)
    response.raise_for_status()

    # Use python engine + on_bad_lines='skip' to handle tweets with commas/newlines
    df = pd.read_csv(
        StringIO(response.text),
        engine="python",
        on_bad_lines="skip",
        quoting=0,          # QUOTE_MINIMAL
        encoding="utf-8",
    )
    print(f"  {label}: {len(df):>6} rows loaded")
    print(f"  Columns: {list(df.columns)}")
    return df


# ── 2. Clean and standardise ─────────────────────────────────────────────────
def clean(df: pd.DataFrame, term_label: str) -> pd.DataFrame:
    df.columns = [c.lower().strip() for c in df.columns]

    # Find timestamp column
    time_col = next((c for c in df.columns if any(k in c for k in ["time", "date", "created"])), None)
    if time_col is None:
        raise ValueError(f"No timestamp column found. Columns: {list(df.columns)}")
    df = df.rename(columns={time_col: "created_at"})
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
    df = df.dropna(subset=["created_at"])

    # Find text column
    # Prioritise exact matches first, then partial - avoids matching 'tweet url'
    text_col = next((c for c in df.columns if c in ["text", "tweet text", "full_text", "content"]), None)
    if text_col is None:
        text_col = next((c for c in df.columns if "text" in c and "url" not in c), None)
    if text_col is None:
        raise ValueError(f"No text column found. Columns: {list(df.columns)}")
    df = df.rename(columns={text_col: "text"})

    # Retweet flag
    rt_col = next((c for c in df.columns if "retweet" in c and "count" not in c), None)
    if rt_col:
        df = df.rename(columns={rt_col: "is_retweet"})
    else:
        df["is_retweet"] = df["text"].str.startswith("RT @", na=False)

    # Keep only essential columns
    keep = ["created_at", "text", "is_retweet"]
    optional = ["id_str", "id", "retweet_count", "favorite_count", "likes"]
    for col in optional:
        if col in df.columns:
            keep.append(col)

    df = df[keep].copy()
    df["term"] = term_label
    df = df.sort_values("created_at").reset_index(drop=True)
    return df


# ── 3. Filter to presidential terms ──────────────────────────────────────────
def filter_to_terms(df: pd.DataFrame) -> pd.DataFrame:
    periods = CONFIG["data"]["periods"]
    masks = []
    for p in periods:
        start = pd.to_datetime(p["start"], utc=True)
        end   = pd.to_datetime(p["end"],   utc=True)
        masks.append((df["created_at"] >= start) & (df["created_at"] <= end))

    combined = masks[0]
    for m in masks[1:]:
        combined = combined | m

    return df[combined].reset_index(drop=True)


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Fetching Trump tweets from CompleteTrumpTweetsArchive...")
    dfs = []

    for label, url in URLS.items():
        try:
            df = fetch_csv(url, label)
            df = clean(df, label)
            dfs.append(df)
        except Exception as e:
            print(f"  WARNING: Could not fetch {label}: {e}")

    if not dfs:
        raise RuntimeError("No data loaded. Check your internet connection.")

    print("\nMerging and filtering to presidential terms...")
    df_all = pd.concat(dfs, ignore_index=True)
    df_filtered = filter_to_terms(df_all)

    # Summary
    print(f"\nTotal tweets downloaded:          {len(df_all):>6}")
    print(f"Tweets during presidential terms: {len(df_filtered):>6}")
    original = df_filtered[df_filtered["is_retweet"] == False]
    print(f"Original tweets (no retweets):    {len(original):>6}")
    print("\nTweets per term:")
    print(df_filtered["term"].value_counts().to_string())
    print(f"\nDate range:")
    print(f"  From: {df_filtered['created_at'].min()}")
    print(f"  To:   {df_filtered['created_at'].max()}")

    path = os.path.join(RAW, "tweets_raw.csv")
    df_filtered.to_csv(path, index=False)
    print(f"\nSaved -> {path}")
    print("Next step: python src/fetch_market.py")