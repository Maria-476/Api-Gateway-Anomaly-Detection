# Project Notes — API Gateway Anomaly Detection

## Dataset
- Web Server Access Logs - Labeled (Kaggle), 1M+ rows, used first 250k (100k train + 150k unseen test)
- 51 anomalies in first 100k rows: bot (43), rce (4), scanning (4)

## Key finding: bot ≠ security threat
Bots (DotBot, MJ12bot, Yahoo! Slurp etc.) are automated but not malicious — they follow
robots.txt, request reasonable sizes, don't hit sensitive paths. Redefined the real
target as "security threat" = rce + scanning only. This dramatically improved model
clarity (0.947 AUC overall → 0.992 AUC on security-only target).

## Evaluation mistakes found and fixed (documented, not hidden)
1. First AUC check used hard 0/1 predictions instead of decision_function scores →
   gave a misleading ~0.50 AUC (looked like random chance)
2. Second attempt fit and evaluated on the same full dataset → gave an inflated,
   untrustworthy 0.99+ AUC (a leakage-style mistake)
3. Fixed with repeated stratified train/test splits (20 splits) → trustworthy result:
   Overall AUC: 0.947 (std 0.020) | Security-only AUC: 0.992 (std 0.003)

## Unseen data validation
- Tested on 10k and 150k rows never touched during training
- 150k unseen batch: 0.993 AUC — consistent with training-time validation
- Confirms the model generalizes, not just memorizes

## Threshold decision
- Default threshold (best F1 balance) → 25% recall on real threats (2/8 caught)
- Lowered threshold by 15% (`threshold * 0.85`) → 100% recall (8/8 caught),
  at the cost of ~0.5% false positive rate (~800 flagged rows per 150k)
- Chose recall over precision deliberately: throttling is reversible/low-cost,
  missing a real RCE/scanning attempt is not

## Model choice
Isolation Forest over One-Class SVM/LOF — better suited for this data size and
feature count; SVM/LOF scale poorly past ~50k rows

## Known limitations
- Not validated against DDoS (distributed), SQLi, XSS — no labeled examples in
  this dataset for those attack types
- This is a decision-layer prototype, meant to plug into a real API gateway
  (Kong/AWS API Gateway/NGINX), not replace one

## Lessons Learned (mistakes found during evaluation)
- First attempt evaluated AUC using hard predictions (0/1) instead of decision_function scores → gave misleading ~0.50 AUC
- Second attempt fit the model on the full dataset then evaluated on the same data → gave inflated 0.99+ AUC (overfitting-style leakage)
- Fixed by using repeated stratified train/test splits, evaluating only on held-out folds
- Lowered the anomaly threshold by 15% to prioritize recall over precision, since throttling is a low-cost, reversible action. This increased detection of real security threats from 25% to 100% recall, at the cost of flagging ~0.5% of total traffic as false positives — an acceptable trade-off for a rate-limiting system, though not for an outright-block system.