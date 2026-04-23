"""
analysis.py
-----------
Event study and OLS regression analysis.

Tests whether Trump tweet sentiment predicts market returns.

Run:
    python src/analysis.py

Output:
    results/figures/score_vs_return.png
    results/figures/category_returns.png
    results/figures/sentiment_over_time.png
    results/ols_results.txt
    results/ols_coefficients.csv
"""

import os
import yaml
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import statsmodels.api as sm
from scipy import stats

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED = os.path.join(ROOT, "data", "processed")
RESULTS   = os.path.join(ROOT, "results")
FIGURES   = os.path.join(RESULTS, "figures")
os.makedirs(FIGURES, exist_ok=True)

with open(os.path.join(ROOT, "config.yaml"), "r") as f:
    CONFIG = yaml.safe_load(f)

plt.rcParams.update({
    "figure.dpi": 150,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "font.size": 10,
})
RED  = "#C8102E"
BLUE = "steelblue"
GREY = "#6B6B6B"


# ── 1. Load data ──────────────────────────────────────────────────────────────
def load_data() -> pd.DataFrame:
    path = os.path.join(PROCESSED, "merged_dataset.csv")
    df = pd.read_csv(path, parse_dates=["created_at", "event_date"])
    print(f"  Loaded {len(df)} tweets")
    # Focus on market-relevant tweets for regression
    df_relevant = df[df["market_relevant"] == True].copy()
    print(f"  Market-relevant tweets: {len(df_relevant)}")
    return df, df_relevant


# ── 2. Plot: Sentiment score over time ────────────────────────────────────────
def plot_sentiment_over_time(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(14, 4))

    # Monthly average sentiment
    df["month"] = df["created_at"].dt.to_period("M").dt.to_timestamp()
    monthly = df.groupby("month")["score"].mean()

    ax.plot(monthly.index, monthly.values, color=BLUE, linewidth=1.5)
    ax.fill_between(monthly.index, monthly.values, 5,
                    where=(monthly.values >= 5), alpha=0.2, color=BLUE)
    ax.fill_between(monthly.index, monthly.values, 5,
                    where=(monthly.values < 5), alpha=0.2, color=RED)
    ax.axhline(5, color=GREY, linewidth=0.8, linestyle="--", label="Neutral (5)")

    ax.set_title("Trump Tweet Sentiment Score Over Time (Monthly Average)",
                 fontsize=12, fontweight="bold")
    ax.set_ylabel("Average Sentiment Score (1-10)")
    ax.set_ylim(1, 10)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.xticks(rotation=45, ha="right")
    ax.legend()

    plt.tight_layout()
    path = os.path.join(FIGURES, "sentiment_over_time.png")
    plt.savefig(path)
    plt.close()
    print(f"  Saved -> {path}")


# ── 3. Plot: Score vs Market Return ──────────────────────────────────────────
def plot_score_vs_return(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    for ax, (col, label) in zip(axes, [
        ("SP500_ret_1d", "S&P 500 Return +1 Day"),
        ("SP500_ret_3d", "S&P 500 Return +3 Days"),
    ]):
        data = df[["score", col]].dropna()
        if len(data) == 0:
            continue

        # Scatter
        ax.scatter(data["score"], data[col],
                   alpha=0.3, color=BLUE, s=15)

        # OLS trend line
        m, b, r, p, _ = stats.linregress(data["score"], data[col])
        x_line = np.linspace(1, 10, 100)
        ax.plot(x_line, m * x_line + b, color=RED, linewidth=2,
                label=f"slope={m:.3f}, p={p:.3f}")

        ax.axhline(0, color=GREY, linewidth=0.8, linestyle=":")
        ax.set_xlabel("Tweet Sentiment Score (1=Negative, 10=Positive)")
        ax.set_ylabel("Market Return (%)")
        ax.set_title(label, fontweight="bold")
        ax.legend(fontsize=9)

    plt.suptitle("Trump Tweet Sentiment vs S&P 500 Returns",
                 fontsize=13, fontweight="bold", y=1.02)
    plt.tight_layout()
    path = os.path.join(FIGURES, "score_vs_return.png")
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    print(f"  Saved -> {path}")


# ── 4. Plot: Average return by category ──────────────────────────────────────
def plot_category_returns(df: pd.DataFrame) -> None:
    categories = df["category"].unique()
    col = "SP500_ret_1d"
    data = df[["category", col]].dropna()

    means = data.groupby("category")[col].mean().sort_values()
    counts = data.groupby("category")[col].count()

    fig, ax = plt.subplots(figsize=(8, 5))
    colors = [RED if v < 0 else BLUE for v in means.values]
    bars = ax.barh(means.index, means.values, color=colors, alpha=0.8)

    # Add count labels
    for bar, cat in zip(bars, means.index):
        ax.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height()/2,
                f"n={counts[cat]}", va="center", fontsize=9)

    ax.axvline(0, color=GREY, linewidth=0.8)
    ax.set_xlabel("Average S&P 500 Return Next Day (%)")
    ax.set_title("Average Market Return by Tweet Category",
                 fontsize=12, fontweight="bold")

    plt.tight_layout()
    path = os.path.join(FIGURES, "category_returns.png")
    plt.savefig(path)
    plt.close()
    print(f"  Saved -> {path}")


# ── 5. OLS regression ─────────────────────────────────────────────────────────
def run_ols(df: pd.DataFrame) -> None:
    results_text = []

    for ret_col, label in [
        ("SP500_ret_1d", "S&P 500 +1 Day"),
        ("SP500_ret_3d", "S&P 500 +3 Days"),
        ("VIX_ret_1d",   "VIX +1 Day"),
    ]:
        if ret_col not in df.columns:
            continue

        data = df[["score", "category", ret_col]].dropna()
        if len(data) < 30:
            continue

        # Dummies for category
        dummies = pd.get_dummies(data["category"], drop_first=True, dtype=float)
        X = pd.concat([data[["score"]], dummies], axis=1)
        X = sm.add_constant(X)
        y = data[ret_col]

        model = sm.OLS(y, X).fit(cov_type="HC3")

        header = f"\n{'='*60}\nOLS: {label}\n{'='*60}"
        results_text.append(header)
        results_text.append(model.summary().as_text())

        print(f"\n{header}")
        print(f"  N={int(model.nobs)}, R²={model.rsquared:.4f}, "
              f"F-stat p={model.f_pvalue:.4f}")
        print(f"  Score coef: {model.params['score']:.4f} "
              f"(p={model.pvalues['score']:.4f})")

    # Save full OLS output
    path = os.path.join(RESULTS, "ols_results.txt")
    with open(path, "w") as f:
        f.write("\n".join(results_text))
    print(f"\n  Full OLS results saved -> {path}")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Loading data...")
    df_all, df_relevant = load_data()

    print("\nGenerating plots...")
    plot_sentiment_over_time(df_all)
    plot_score_vs_return(df_relevant)
    plot_category_returns(df_relevant)

    print("\nRunning OLS regressions...")
    run_ols(df_relevant)

    print("\nAnalysis complete. Check results/figures/ for plots.")