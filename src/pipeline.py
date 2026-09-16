from datetime import datetime
from live_tracker import new_request_arrives, get_ip_aggregate_features, get_ip_time_features
from request_features import get_single_request_features, get_composite_features
from model_scorer import score_request, size_threshold, feature_columns


def handle_incoming_request(ip, url, status, size, user_agent, referrer, extra, protocol, method):
    now = datetime.now()

    single_features = get_single_request_features(
        url=url, status=status, method=method, protocol=protocol,
        user_agent=user_agent, extra=extra, referrer=referrer,
        size=size, timestamp=now, size_threshold=size_threshold
    )

    basic_features = new_request_arrives(
        ip, url, status, size, user_agent,
        is_client_issue=single_features['is_client_issue'],
        is_server_issue=single_features['is_server_issue'],
        is_automated_client=single_features['is_automated_client']
    )
    basic_features['is_request_first'] = basic_features.pop('is_first')
    basic_features['time_since_previous_request'] = basic_features.pop('time_gap')

    aggregate_features = get_ip_aggregate_features(ip)
    time_features = get_ip_time_features(ip)
    composite_features = get_composite_features(single_features, aggregate_features, time_features)

    all_features = {}
    all_features.update(single_features)
    all_features.update(basic_features)
    all_features.update(aggregate_features)
    all_features.update(time_features)
    all_features.update(composite_features)

    # Known simplification: requests_per_method_url and requests_per_ip_url_per_min
    # are intentionally not calculated live (low value, high cost — same conclusion as POC).
    # Everything else must match training features exactly — treat any other entry
    # in this list as a bug to fix, not a simplification.
    missing = [col for col in feature_columns if col not in all_features]
    expected_missing = {'requests_per_method_url', 'requests_per_ip_url_per_min'}
    unexpected_missing = set(missing) - expected_missing
    if unexpected_missing:
        print("🚨 UNEXPECTED missing features (real bug):", unexpected_missing)

    result = score_request(all_features)
    return result


if __name__ == "__main__":
    for i in range(10):
        result = handle_incoming_request(
            ip="9.9.9.9",
            url="/wp-login.php",
            status=404,
            size=178,
            user_agent="Mozilla/5.0 (compatible; MJ12bot/v1.4.8; http://mj12bot.com)",
            referrer="-",
            extra="-",
            protocol="HTTP/1.1",
            method="GET"
        )
        print(i, result)