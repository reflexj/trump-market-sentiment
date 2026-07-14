# Results

## 1. Sentiment Over Time

![Trump Tweet Sentiment Score Over Time](results/figures/sentiment_over_time.png)

The monthly average sentiment score remained close to neutral (5.0) throughout Trump's first term, with the score moving in a narrow band of roughly 4.7 to 5.9. This stability masks important variation that becomes visible when aligned with key political events.

The following three events could be used to explain why the sentiment was below the average in the second half of the term:

- **2019-Q4 (Impeachment):** The first impeachment inquiry, formally launched in September 2019 and voted on in December 2019, coincides with the first sustained drop below neutral.
- **2020-Q1 (Covid-19):** The onset of the Covid-19 pandemic and the associated market crash in February-March 2020 deepens the negative trend. This period marks the most sustained deviation below neutral in the entire sample.
- **2020-Q4 (Election and Capitol):** The period surrounding the November 2020 election loss and the January 6, 2021 Capitol events produces the final and sharpest negative reading in the sample, with the score reaching approximately 4.5.

The pattern suggests that aggregate tweet sentiment reflects broader political turbulence rather than any single event. The relative stability of 2017-2019 contrasts sharply with the volatility of the final year of the term.

---

## 2. Sentiment and Market Returns: OLS Results

### Specification

All regressions use HC3 heteroscedasticity-robust standard errors. The independent variable of interest is the tweet-level sentiment score (1-10). Category dummies (economy, geopolitical, geopolitics, trade, other) are included as controls. The sample is restricted to market-relevant tweets (N = 1,529-1,532 depending on the return window).

### S&P 500

![Trump Tweet Sentiment vs S&P 500 Returns](results/figures/score_vs_return.png)

| Horizon | Score Coefficient | 95% CI | p-value | R² | N |
|---------|------------------|--------|---------|-----|---|
| +1 Day | -0.107 | [-0.163, -0.050] | 0.0002 | 0.014 | 1,529 |
| +3 Days | -0.197 | [-0.289, -0.104] | <0.0001 | 0.019 | 1,532 |

A one-unit increase in the sentiment score (i.e., a more positive tweet) is associated with a **0.107 percentage point lower** S&P 500 return the following day, and a **0.197 percentage point lower** cumulative return over the following three days. Both estimates are statistically significant at the 0.1% level. The effect strengthens over the three-day horizon, suggesting the market response is not fully immediate.

No category dummy reaches conventional significance in either specification, indicating that the score rather than tweet topic drives the result.

### VIX

| Horizon | Score Coefficient | 95% CI | p-value | R² | N |
|---------|------------------|--------|---------|-----|---|
| +1 Day | +0.345 | [0.085, 0.604] | 0.009 | 0.017 | 1,529 |

More positive tweets are associated with **higher** next-day VIX returns. The geopolitics category dummy is also significant (coef = 1.58, p = 0.038), while the other category is strongly negative (coef = -5.45, p < 0.001).

### Example Tweets with the Largest Market Impact

The table below shows the market-relevant original tweets (retweets and link-only posts excluded, one tweet per trading day) with the largest absolute next-day S&P 500 return in the sample:

| Date | Tweet | Score | Category | S&P +1d | S&P +3d | VIX +1d |
|------|-------|-------|----------|---------|---------|---------|
| 2020-03-13 | "...the Secretary of the Treasury and the Secretary of Labor to issue regulations that will provide flexibility so that in no way will Small Businesses be hurt..." | 7 | economy | −11.98% | −11.54% | +43.0% |
| 2020-03-22 | "CHINESE VIRUS FACT CHECK" | 2 | geopolitics | +9.38% | +17.55% | +0.1% |
| 2020-03-12 | "I am fully prepared to use the full power of the Federal Government to deal with our current challenge of the CoronaVirus!" | 6 | economy | +9.29% | +1.96% | −23.4% |
| 2020-03-14 | "BIGGEST STOCK MARKET RISE IN HISTORY YESTERDAY!" | 8 | economy | +6.00% | +0.97% | −8.2% |
| 2020-06-10 | "Relief is on the way to Utah! I'm proud to send $187.18M in CARES Act funding to @RideUTA..." | 6 | economy | −5.89% | −3.87% | +48.0% |

Two observations stand out. First, every entry falls in the Covid-19 crash and recovery period (February–June 2020), when daily volatility was extreme for reasons unrelated to any individual tweet. The tweets coincide with, rather than cause, these moves — a tweet-level illustration of the reverse-causality caveat discussed below. Second, sentiment and subsequent returns frequently point in opposite directions: the most positive tweet in the table (score 8, celebrating a record rally) preceded a much smaller gain, while the most negative one (score 2) preceded a +9.4% rally driven by the Federal Reserve's intervention announced the following day. This mirrors the negative score coefficient in the regressions above.

### Interpretation

The negative relationship between tweet sentiment and subsequent S&P 500 returns is counterintuitive at first glance but consistent with several mechanisms:

1. **"Buy the rumor, sell the news":** When Trump posts a positively framed economic announcement, the underlying policy move is often already priced in. The tweet confirms expectations rather than conveying new information, triggering profit-taking.
2. **Reverse causality / selection bias:** Trump tended to post optimistically following positive market developments. Subsequent mean-reversion mechanically produces a negative correlation.
3. **Uncertainty amplification:** Positive policy announcements (trade deals, deregulation) increase short-term uncertainty about implementation, which is consistent with the positive VIX coefficient.
