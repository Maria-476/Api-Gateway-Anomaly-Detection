import joblib
import os

# Get the folder this script itself is in, no matter where it's run from
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, '..', 'models', 'isolation_forest_v1.joblib')

# Load the saved model ONCE when this file is imported
saved = joblib.load(MODEL_PATH)
model = saved['model']
threshold = saved['threshold']
feature_columns = saved['feature_columns']
size_threshold = saved['size_threshold']

import pandas as pd

def score_request(features_dict):
    row = pd.DataFrame([[features_dict.get(col, 0) for col in feature_columns]], columns=feature_columns)

    score = -model.decision_function(row)[0]
    is_anomaly = score > threshold

    return {'score': float(score), 'is_anomaly': bool(is_anomaly)}





