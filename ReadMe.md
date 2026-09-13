# API Gateway Anomaly Detection & Throttling Engine

A prototype anomaly detection and throttling decision engine that simulates live API
traffic and demonstrates how ML-based scoring could plug into an existing API gateway
(e.g. as a sidecar service or custom WAF rule) — not a replacement for a real gateway
like Kong, AWS API Gateway, or NGINX.

## Status: Phase 1 (POC) complete ✅ — Phase 2 (live system) in progress

## Problem

API gateways face automated abuse — scanning, RCE attempts, credential stuffing — that
simple rate limiting alone doesn't catch. This project explores whether an unsupervised
anomaly detection model, trained only on request metadata (no manual attack signatures),
can flag these threats in near real time, feeding into a throttling decision layer.

## Dataset

[Web Server Access Logs - Labeled](https://www.kaggle.com/) (Kaggle), 1M+ rows, 13
columns. Used a 100k-row sample for training/EDA and a separate 150k-row unseen slice
for validation.

- 51 labeled anomalies in the training sample: `bot` (43), `rce` (4), `scanning` (4)

## Approach

1. **EDA** — found each attack type has a distinct behavioral fingerprint (e.g. RCE
   attempts always return HTTP 400; scanning shows a 301/404 split; bots always hit
   `/robots.txt` with known crawler user-agents)
2. **Feature engineering** — ~55 features across UA parsing, URL structure, status code
   categories, and per-IP behavioral aggregates (request rate, error rate, unique URLs
   visited, time gaps between requests)
3. **Model** — Isolation Forest (unsupervised), chosen over One-Class SVM/LOF for
   scalability to 100k+ rows
4. **Key finding** — bot traffic, while automated, isn't a real security threat (it
   follows `robots.txt`, requests reasonable sizes, avoids sensitive paths). Redefined
   the actual detection target as **security threat = RCE + scanning only**, which
   sharply improved model clarity.

## Results

| Check | AUC |
|---|---|
| Overall anomaly detection (repeated stratified splits, n=20) | 0.947 (± 0.020) |
| Security-threat detection (RCE + scanning only) | 0.992 (± 0.003) |
| Validation on 150k rows of genuinely unseen data | 0.993 |

**Threshold**: tuned to prioritize recall over precision (100% recall on real threats,
~0.5% false positive rate) — a deliberate trade-off, since throttling is a reversible,
low-cost action, while missing a real attack is not.

## Known limitations

- Not validated against distributed DDoS, SQLi, or XSS — no labeled examples of these
  in the dataset. Per-IP features also wouldn't catch a *distributed* flood by design;
  that would need cross-IP aggregate features not yet built.
- This is a decision-layer prototype, meant to sit behind a real API gateway, not
  replace one.

## Project structure

```
├── notebooks/          exploratory analysis and POC model training
├── data/raw/            original dataset
├── data/processed/      engineered feature sets
├── src/feature_engineering.py   reusable feature pipeline
├── models/               saved model + threshold + metadata
├── notes/NOTES.md         detailed working notes and decision log
```

## Next (Phase 2)

Live FastAPI service applying this model to streaming request data, with a WebSocket
dashboard and admin controls for sensitivity/unblocking. See `notes/ROADMAP.md`.