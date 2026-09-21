import requests
import pandas as pd
import time
from paths import get_path

RAW_PATH = get_path("data" , "raw" , 'web_server_access_logs.csv')
API_URL = "http://127.0.0.1:8000/check-request"


def simulate(num_requests=20, delay_seconds=1):
    df = pd.read_csv(RAW_PATH, nrows=num_requests)

    for _, row in df.iterrows():
        payload = {
            "ip": row['ip'],
            "url": row['url'],
            "status": int(row['status']),
            "size": int(row['size']),
            "user_agent": row['user_agent'],
            "referrer": row['referrer'],
            "extra": row['extra'],
            "protocol": row['protocol'],
            "method": row['method']
        }

        response = requests.post(API_URL, json=payload)
        result = response.json()

        print(f"{row['ip']} → {row['url']} | {result}")
        time.sleep(delay_seconds)


def simulate_known_anomaly(delay_seconds=1):
    df = pd.read_csv(RAW_PATH, nrows=100000)
    anomalies = df[df['type'].isin(['rce', 'scanning'])].head(5)

    for _, row in anomalies.iterrows():
        payload = {
            "ip": row['ip'], "url": row['url'], "status": int(row['status']),
            "size": int(row['size']), "user_agent": row['user_agent'],
            "referrer": row['referrer'], "extra": row['extra'],
            "protocol": row['protocol'], "method": row['method']
        }
        response = requests.post(API_URL, json=payload)
        print(f"{row['type']} | {row['ip']} → {row['url']} | {response.json()}")
        time.sleep(delay_seconds)

def simulate_repeated_attacker(delay_seconds=1):
    df = pd.read_csv(RAW_PATH, nrows=100000)
    attacker_row = df[df['type'] == 'rce'].iloc[0]

    for i in range(5):
        payload = {
            "ip": attacker_row['ip'], "url": attacker_row['url'],
            "status": int(attacker_row['status']), "size": int(attacker_row['size']),
            "user_agent": attacker_row['user_agent'], "referrer": attacker_row['referrer'],
            "extra": attacker_row['extra'], "protocol": attacker_row['protocol'],
            "method": attacker_row['method']
        }
        response = requests.post(API_URL, json=payload)
        print(i, response.json())
        time.sleep(delay_seconds)

if __name__ == "__main__":
    simulate_repeated_attacker()