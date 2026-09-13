## Two architectures

**Basic:**
```
api-gateway-anomaly-engine/
├── data/
│   ├── raw/
│   └── processed/
├── models/
├── src/
│   ├── ml/
│   │   ├── train.py
│   │   ├── feature_eng.py
│   │   └── predictor.py
│   ├── gateway/
│   │   └── main.py          # FastAPI + WebSocket + rate limiting, all-in-one
│   └── dashboard/
│       └── index.html       # Simple frontend: live chart + IP table, no framework needed yet
├── notes/
│   └── NOTES.md
├── requirements.txt
├── ARCHITECTURE.md
└── README.md
```


**Advanced (target)**
```
api-gateway-anomaly-engine/
├── .github/workflows/         # CI: lint + test on push
├── config/
│   └── settings.yaml          # thresholds, sensitivity, Redis config
├── data/
│   ├── raw/
│   └── processed/
├── models/
│   └── isolation_forest_v1.joblib
├── src/
│   ├── ml/
│   │   ├── train.py
│   │   ├── feature_eng.py
│   │   └── predictor.py
│   ├── gateway/
│   │   ├── main.py
│   │   ├── middleware.py
│   │   └── schemas.py
│   ├── services/
│   │   ├── redis_service.py   # rate limiting, IP blocklist
│   │   └── websocket.py
│   └── admin/
│       └── routes.py          # NEW: endpoints for unblock IP / change sensitivity
├── dashboard/                  # NEW: separate frontend app (React or plain JS)
│   ├── src/
│   │   ├── components/
│   │   │   ├── LiveChart.jsx
│   │   │   ├── TrafficTable.jsx
│   │   │   └── AdminPanel.jsx  # unblock IP / sensitivity slider UI
│   │   └── App.jsx
│   └── package.json
├── tests/
├── notes/
│   └── NOTES.md
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── ARCHITECTURE.md
└── README.md
