# Architecture — Current State (Phase 2 in progress)

This replaces the earlier "Basic / Advanced" plan with what's actually built, kept up
to date as we go. Renaming existing working files is deliberately avoided — it risks
breaking tested imports for no functional benefit. New files follow this naming from
here on.

## Current structure

```
api-gateway-anomaly-engine/
├── data/
│   ├── raw/                          # original 1M+ row dataset (gitignored)
│   └── Processed/
│       └── processed_100k.csv        # engineered features from Phase 1
│
├── models/
│   └── isolation_forest_v1.joblib    # model + threshold + feature_columns + size_threshold, bundled together
│
├── notebooks/
│   ├── 01_poc_eda_model.ipynb        # EDA, feature engineering, training, evaluation (Phase 1)
│   ├── 02_testing_unseen.ipynb       # validation on unseen data
│   └── Architecture.md / gateway_anomaly_architecture_basic.png
│
├── src/
│   ├── feature_engineering.py        # build_features() — batch version, used by notebooks + parity checks
│   ├── request_features.py           # single-request feature extraction (Batches 1-3): URL, status,
│   │                                    protocol, user-agent, size, proxy/referrer, method, composite features
│   ├── live_tracker.py               # per-IP in-memory history (Module A): visit counts, time gaps,
│   │                                    per-IP aggregates (unique URLs, error rate, size stats, per-min/sec rates)
│   ├── model_scorer.py               # loads the saved model bundle, scores a feature dict (Module B)
│   ├── decision_engine.py            # tiered decision logic (Module C): allow / monitor / rate_limit /
│   │                                    temporary_block, with violation history and configurable thresholds
│   ├── pipeline.py                   # glue: calls request_features → live_tracker → model_scorer →
│   │                                    decision_engine in order, for one incoming request
│   ├── main.py                       # FastAPI app — exposes pipeline.py via POST /check-request
│   ├── simulate_traffic.py           # replays real log rows against the running API, with delay,
│   │                                    to simulate live traffic
│   ├── paths.py                      # shared helper for reliable file paths regardless of run location
│   └── validate_feature_parity.py    # one-off script confirming batch vs. live features match
│
├── notes/
│   └── NOTES.md
├── requirements.txt
├── ARCHITECTURE.md                    # this file
└── README.md
```

## Data flow (Module A → B → C, live)

```
Incoming request (via FastAPI POST /check-request)
        ↓
request_features.py    → single-request features (no memory needed)
        ↓
live_tracker.py         → updates this IP's history, returns per-IP aggregate
                           and time-window features
        ↓
pipeline.py              → combines all feature batches into one dict,
                            checks for silently-missing features
        ↓
model_scorer.py           → scores the combined features with the saved
                             Isolation Forest, returns score + is_anomaly
        ↓
decision_engine.py         → checks violation history + severity, returns
                              one of: allow / monitor / rate_limit / temporary_block
        ↓
Response returned to caller (JSON)
```

## Known simplifications (documented, not oversights)

- `requests_per_method_url` and `requests_per_ip_url_per_min` are not calculated live
  (high-cardinality, low value — same conclusion reached in Phase 1 EDA)
- Decision thresholds (`VIOLATIONS_BEFORE_BLOCK`, `SEVERITY_THRESHOLD_FOR_RATE_LIMIT`, etc.)
  currently live as named constants at the top of `decision_engine.py` — a candidate for
  moving to `config/settings.yaml` once there's a real need to tune them without code changes
- In-memory storage (`live_tracker.py`, `decision_engine.py`) does not persist across
  server restarts and does not scale across multiple server instances — acceptable for
  a single-instance prototype; Redis would be the real-world upgrade path

## Not yet built (planned)

- `dashboard/` — live chart, flagged-IP table, admin controls (sensitivity, unblock)
- WebSocket streaming of live decisions to the dashboard
- `src/train.py` as a standalone script (training currently lives in the notebook)
- Tests, CI, Docker — deferred until the above is working end-to-end