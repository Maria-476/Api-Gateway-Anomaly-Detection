import random
import pandas as pd
from paths import get_path

RAW_PATH = get_path('data', 'raw', 'web_server_access_logs.csv')
MODEL_PATH = get_path('models', 'isolation_forest_v1.joblib')

with open(RAW_PATH, encoding='utf-8') as f:
    total_rows = sum(1 for _ in f) - 1

random_line = random.randint(1, total_rows)

df_sample = pd.read_csv(RAW_PATH, skiprows=range(1, random_line), nrows=1)
row = df_sample.iloc[0]
print("Testing row:", row['ip'], row['url'], row['time'])

from live_tracker import new_request_arrives, get_ip_aggregate_features, get_ip_time_features
from request_features import get_single_request_features, get_composite_features
from model_scorer import score_request, size_threshold, feature_columns
from feature_engineering import build_features
def build_live_features(row):
    timestamp = pd.to_datetime(row['time'])

    single = get_single_request_features(
        url=row['url'], status=row['status'], method=row['method'],
        protocol=row['protocol'], user_agent=row['user_agent'],
        extra=row['extra'], referrer=row['referrer'], size=row['size'],
        timestamp=timestamp, size_threshold=size_threshold
    )

    basic = new_request_arrives(
        row['ip'], row['url'], row['status'], row['size'], row['user_agent'],
        is_client_issue=single['is_client_issue'],
        is_server_issue=single['is_server_issue'],
        is_automated_client=single['is_automated_client']
    )
    basic['is_request_first'] = basic.pop('is_first')
    basic['time_since_previous_request'] = basic.pop('time_gap')

    aggregate = get_ip_aggregate_features(row['ip'])
    time_feats = get_ip_time_features(row['ip'])
    composite = get_composite_features(single, aggregate, time_feats)

    all_feats = {}
    all_feats.update(single)
    all_feats.update(basic)
    all_feats.update(aggregate)
    all_feats.update(time_feats)
    all_feats.update(composite)
    return all_feats

print("\n--- COMPARISON ---")
df_batch_features = build_features(df_sample.copy(), size_threshold=size_threshold)
batch_result = df_batch_features.drop(columns=['label', 'type']).iloc[0].to_dict()

live_result = build_live_features(row)

mismatches = 0
for key in sorted(set(batch_result) | set(live_result)):
    b, l = batch_result.get(key, "MISSING"), live_result.get(key, "MISSING")
    if isinstance(b, (int, float)) and isinstance(l, (int, float)):
        if abs(b - l) > 0.0001:
            print(f"❌ {key}: batch={b} vs live={l}")
            mismatches += 1
    elif b != l:
        print(f"❌ {key}: batch={b} vs live={l}")
        mismatches += 1

print("✅ All match!" if mismatches == 0 else f"\n{mismatches} mismatches found")