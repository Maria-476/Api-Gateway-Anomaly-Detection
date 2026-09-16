# Batch 1: Features from a single request alone (no history needed)

from urllib.parse import urlparse

def extract_request_features(url, status, method, protocol):
    parsed = urlparse(url)
    path = parsed.path
    query = parsed.query

    features = {}

    # URL features
    features['path_length'] = len(path)
    features['number_of_query_parameters'] = len(query.split('&')) if query else 0
    features['has_query_string'] = int(bool(query))
    features['number_of_path_segments'] = len([p for p in path.split('/') if p])
    features['has_admin'] = int('admin' in path.lower())
    features['has_login'] = int('login' in path.lower())
    features['has_api'] = int('api' in path.lower())

    # status features
    success_codes = [200, 201, 202, 204]
    redirect_codes = [301, 302, 303, 307, 308]
    client_issue_codes = [400, 401, 403, 404, 405, 408, 409, 410, 411, 413, 415, 422, 429]
    server_issue_codes = [500, 501, 502, 503, 504, 505]

    features['is_success'] = int(status in success_codes)
    features['is_redirect'] = int(status in redirect_codes)
    features['is_client_issue'] = int(status in client_issue_codes)
    features['is_server_issue'] = int(status in server_issue_codes)

    # protocol features
    command_keywords = ['wget', 'curl', 'chmod', 'bin', 'bash', 'sh', '/tmp/', ';']
    features['has_command_injection'] = int(any(k in str(protocol).lower() for k in command_keywords))
    features['is_legacy_protocol'] = int(protocol == 'HTTP/1.0')
    standard_protocols = ['HTTP/1.1', 'HTTP/1.0', 'HTTP/2', 'HTTP/3']
    features['is_malformed_protocol'] = int(str(protocol).strip() not in standard_protocols)
    features['is_legacy_protocol'] = int(protocol == 'HTTP/1.0')

    return features

# Batch 2: User-agent features (also single-request, no memory needed)

import re

def extract_ua_features(ua):
    
    ua = str(ua)

    is_mobile = int(bool(re.search(r'Mobile|Android|iPhone|iPad', ua, re.I)))
    has_bot_keyword = int(bool(re.search(r'bot|crawler|spider|slurp|archiver|crawl', ua, re.I)))
    is_automated_client = int(bool(re.search(
        r'wget|curl|python-requests|python|java|httpclient|yowai|solstice', ua, re.I)))

    if re.search(r'Firefox/', ua, re.I):
        browser_family = "Firefox"
    elif re.search(r'Edg/', ua, re.I):
        browser_family = "Edge"
    elif re.search(r'Chrome/', ua, re.I):
        browser_family = "Chrome"
    elif re.search(r'Safari/', ua, re.I) and not re.search(r'Chrome/', ua, re.I):
        browser_family = "Safari"
    else:
        browser_family = "Other"

    if re.search(r'Windows', ua, re.I):
        os_family = "Windows"
    elif re.search(r'Android', ua, re.I):
        os_family = "Android"
    elif re.search(r'iPhone|iPad|iOS', ua, re.I):
        os_family = "iOS"
    elif re.search(r'Linux', ua, re.I):
        os_family = "Linux"
    elif re.search(r'Mac OS|Macintosh', ua, re.I):
        os_family = "MacOS"
    else:
        os_family = "Unknown"

    features = {
        'ua_length': len(ua),
        'is_mobile': is_mobile,
        'has_bot_keyword': has_bot_keyword,
        'is_automated_client': is_automated_client,
    }

    # one-hot encode browser/os manually, since there's no dataframe to do it for us
    for b in ['Chrome', 'Firefox', 'Other', 'Safari']:
        features[f'browser_family_{b}'] = int(browser_family == b)
    for o in ['Android', 'Linux', 'MacOS', 'Unknown', 'Windows', 'iOS']:
        features[f'os_family_{o}'] = int(os_family == o)

    return features


# Batch#3 Extract Extra Features
def extract_extra_features(extra, referrer, size, timestamp, method, size_threshold):
    features = {}

    # proxy / referrer
    features['has_proxy_ip'] = int(extra != '-')
    features['has_referrer'] = int(referrer != '-')

    # size features
    import numpy as np
    features['size_log'] = float(np.log1p(size))
    features['is_zero_size'] = int(size == 0)
    features['is_large_size'] = int(size > size_threshold)  # ← paste your real size_threshold here

    # time feature
    features['hour_of_day'] = timestamp.hour

    # method one-hot (matches your training's fixed category list)
    all_methods = ['GET', 'POST', 'HEAD', 'OPTIONS']  # only the ones that survived your constant-column drop
    method_clean = str(method).upper().strip()
    for m in all_methods:
        features[f'method_{m}'] = int(method_clean == m)

    return features

# Combine Batch#1, Batch#2 & Batch#3
def get_single_request_features(url, status, method, protocol, user_agent, extra, referrer, size, timestamp, size_threshold):
    """Combines all single-request features (no memory needed) into one call."""
    features = {}
    features.update(extract_request_features(url, status, method, protocol))
    features.update(extract_ua_features(user_agent))
    features.update(extract_extra_features(extra, referrer, size, timestamp, method, size_threshold))
    return features

# ----------------

def get_composite_features(single_features, aggregate_features, time_features):
    features = {}

    features['scanner_threat_score'] = (
        aggregate_features['unique_urls_per_ip'] * aggregate_features['error_rate_per_ip']
    )

    features['sensitive_endpoint_attack'] = int(
        (single_features['has_admin'] or single_features['has_api'] or single_features['has_login']) and
        (single_features['has_command_injection'] or single_features['number_of_query_parameters'] > 3)
    )

    features['high_rate_automated_traffic'] = (
        single_features['is_automated_client'] * time_features['requests_per_sec']
    )

    return features

# Test the combined Version
if __name__ == "__main__":
    from datetime import datetime
    from model_scorer import size_threshold   # import the value, not just the code

    features = get_single_request_features(
        url="/wp-login.php",
        status=404,
        method="GET",
        protocol="HTTP/1.1",
        user_agent="Mozilla/5.0 (compatible; MJ12bot/v1.4.8; http://mj12bot.com)",
        extra="-",
        referrer="-",
        size=178,
        timestamp=datetime.now(),
        size_threshold=size_threshold
)
    print(features)