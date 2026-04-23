"""
sentiment.py
------------
Scores each Trump tweet for market sentiment using the Anthropic Claude API.

Scoring schema per tweet:
    score:    1-10  (1=very negative for markets, 10=very positive)
    category: economy / trade / geopolitics / domestic_politics / other
    market_relevant: true / false

Run:
    python src/sentiment.py --test 20   # test with 20 tweets
    python src/sentiment.py             # score all tweets

Output:
    data/raw/sentiment_scores.csv
"""

import os
import json
import time
import yaml
import pandas as pd
import anthropic
from dotenv import load_dotenv

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW   = os.path.join(ROOT, "data", "raw")
CACHE = os.path.join(RAW, "sentiment_cache.csv")

load_dotenv(os.path.join(ROOT, ".env"))

with open(os.path.join(ROOT, "config.yaml"), "r") as f:
    CONFIG = yaml.safe_load(f)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL  = "claude-haiku-4-5-20251001"   # fastest + cheapest, perfect for scoring

SYSTEM_PROMPT = """You are a financial analyst scoring tweets by Donald Trump for their likely impact on financial markets.

Respond with ONLY a JSON object in this exact format, nothing else:
{"score": <1-10>, "category": "<category>", "market_relevant": <true/false>}

Scoring rules:
- score 1-3: Negative for markets (trade war threats, protectionism, geopolitical conflict, attacking business)
- score 4-6: Neutral or unclear market impact
- score 7-10: Positive for markets (tax cuts, deregulation, trade deals, economic optimism)

Categories (pick one): economy, trade, geopolitics, domestic_politics, other

market_relevant: true if the tweet could plausibly move financial markets, false for personal attacks, sports, entertainment etc.

Respond ONLY with the JSON. No explanation."""


# ── 1. Load tweets ────────────────────────────────────────────────────────────
def load_tweets() -> pd.DataFrame:
    path = os.path.join(RAW, "tweets_raw.csv")
    df = pd.read_csv(path, parse_dates=["created_at"])
    if CONFIG["sentiment"]["filter_retweets"]:
        df = df[df["is_retweet"] == False].copy()
    print(f"  Tweets to score: {len(df)}")
    return df.reset_index(drop=True)


# ── 2. Load cache ─────────────────────────────────────────────────────────────
def load_cache() -> pd.DataFrame:
    if os.path.exists(CACHE):
        df = pd.read_csv(CACHE)
        print(f"  Cache found: {len(df)} tweets already scored")
        return df
    print("  No cache found, starting fresh")
    return pd.DataFrame(columns=["created_at", "score", "category", "market_relevant"])


# ── 3. Score a single tweet ───────────────────────────────────────────────────
def score_tweet(text: str) -> dict:
    message = client.messages.create(
        model=MODEL,
        max_tokens=100,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Tweet: {text[:500]}"}]
    )
    raw = message.content[0].text.strip()

    # Strip markdown fences if present
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    result = json.loads(raw)
    result["score"] = int(result["score"])
    result["market_relevant"] = bool(result["market_relevant"])
    assert 1 <= result["score"] <= 10
    return result


# ── 4. Score all tweets with caching ─────────────────────────────────────────
def score_all(df_tweets: pd.DataFrame, df_cache: pd.DataFrame) -> pd.DataFrame:
    if len(df_cache) > 0:
        scored_times = set(df_cache["created_at"].astype(str))
        df_todo = df_tweets[~df_tweets["created_at"].astype(str).isin(scored_times)]
    else:
        df_todo = df_tweets

    total   = len(df_todo)
    skipped = len(df_tweets) - total
    print(f"  To score: {total}  |  Already cached: {skipped}")

    if total == 0:
        print("  All tweets already scored!")
        return df_cache

    results = []
    errors  = 0

    for i, (_, row) in enumerate(df_todo.iterrows()):
        try:
            result = score_tweet(str(row["text"]))
            result["created_at"] = str(row["created_at"])
            results.append(result)

            # Print first 3 results so you can verify quality
            if i < 3:
                print(f"\n  Tweet: {str(row['text'])[:80]}...")
                print(f"  → score={result['score']} | category={result['category']} | relevant={result['market_relevant']}")

            # Checkpoint every 100 tweets
            if (i + 1) % 100 == 0:
                df_new   = pd.DataFrame(results)
                df_cache = pd.concat([df_cache, df_new], ignore_index=True)
                df_cache.to_csv(CACHE, index=False)
                results  = []
                pct      = (i + 1) / total * 100
                print(f"  Progress: {i + 1}/{total} ({pct:.0f}%) — checkpoint saved")

            # Haiku rate limit: ~50 req/min → 1.5s between requests
            time.sleep(1.5)

        except Exception as e:
            errors += 1
            print(f"  WARNING tweet {i}: {e}")
            time.sleep(3)

    # Save remainder
    if results:
        df_new   = pd.DataFrame(results)
        df_cache = pd.concat([df_cache, df_new], ignore_index=True)
        df_cache.to_csv(CACHE, index=False)

    print(f"\n  Scoring complete. Errors: {errors}/{total}")
    return df_cache


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", type=int, default=0,
                        help="Score only N tweets for testing (0 = score all)")
    args = parser.parse_args()

    print("Loading tweets...")
    df_tweets = load_tweets()

    if args.test > 0:
        df_tweets = df_tweets.head(args.test)
        print(f"  TEST MODE: scoring only {args.test} tweets")

    print("\nLoading cache...")
    df_cache = load_cache()

    print("\nScoring via Claude API (Haiku)...")
    df_scored = score_all(df_tweets, df_cache)

    # Merge scores back onto tweets
    df_tweets["created_at"] = df_tweets["created_at"].astype(str)
    df_scored["created_at"] = df_scored["created_at"].astype(str)
    df_final = df_tweets.merge(df_scored, on="created_at", how="inner")

    print(f"\nFinal scored dataset: {len(df_final)} tweets")
    print(f"\nScore distribution:")
    print(df_final["score"].value_counts().sort_index().to_string())
    print(f"\nCategory distribution:")
    print(df_final["category"].value_counts().to_string())
    print(f"\nMarket relevant: {df_final['market_relevant'].sum()} / {len(df_final)}")

    path = os.path.join(RAW, "sentiment_scores.csv")
    df_final.to_csv(path, index=False)
    print(f"\nSaved -> {path}")
    print("Next step: python src/merge.py")