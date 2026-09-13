# src/feature_engineering.py
import pandas as pd
import numpy as np
import re
from urllib.parse import urlparse
from pandas.api.types import CategoricalDtype


def extract_ua_features(ua):
    ua = str(ua)
    ua_length = len(ua)

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

    is_mobile = int(bool(re.search(r'Mobile|Android|iPhone|iPad', ua, re.I)))
    has_bot_keyword = int(bool(re.search(r'bot|crawler|spider|slurp|archiver|crawl', ua, re.I)))
    is_automated_client = int(bool(re.search(
        r'wget|curl|python-requests|python|java|httpclient|yowai|solstice', ua, re.I)))

    return {
        "ua_length": ua_length,
        "browser_family": browser_family,
        "os_family": os_family,
        "is_mobile": is_mobile,
        "has_bot_keyword": has_bot_keyword,
        "is_automated_client": is_automated_client
    }


def extract_url_features(url):
    url = str(url)
    parsed = urlparse(url)
    path = parsed.path
    query = parsed.query

    has_query_string = int(bool(query))
    number_of_query_parameters = len(query.split('&')) if query else 0
    segment = [part for part in path.split('/') if part]

    return {
        'url_length': len(url),
        'path_length': len(path),
        'number_of_query_parameters': number_of_query_parameters,
        'has_query_string': has_query_string,
        'number_of_path_segments': len(segment),
        'has_admin': int('admin' in path.lower()),
        'has_login': int('login' in path.lower()),
        'has_api': int('api' in path.lower())
    }


def build_features(df, size_threshold=None):
    """
    Takes raw log dataframe, returns fully engineered feature dataframe.
    label/type are kept in the output (for evaluation) — drop them
    yourself right before feeding into the model.

    size_threshold: pass the exact value from TRAINING data's
    df['size'].quantile(0.99). If None, computes it fresh on this
    data — only do that for the original training run, never for
    new/live data, or your threshold will silently drift.
    """
    df = df.copy()

    # ---- proxy / referrer ----
    df['has_proxy_ip'] = (df['extra'] != '-').astype(int)
    df['has_referrer'] = (df['referrer'] != '-').astype(int)

    # ---- user agent features ----
    ua_features = df['user_agent'].apply(extract_ua_features)
    df = pd.concat([df, ua_features.apply(pd.Series)], axis=1)
    df = pd.get_dummies(df, columns=['browser_family', 'os_family'], dtype=int)

    # ---- time features ----
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values(['ip', 'time']).reset_index(drop=True)
    df['minute'] = df['time'].dt.floor('min')
    df['hour_of_day'] = df['time'].dt.hour
    df['is_weekend'] = df['time'].dt.dayofweek.isin([5, 6]).astype(int)
    df['is_night_time'] = df['hour_of_day'].between(0, 5).astype(int)

    # ---- url features ----
    url_features = df['url'].apply(extract_url_features).apply(pd.Series)
    df = pd.concat([df, url_features], axis=1)

    # ---- status categories ----
    success_codes = [200, 201, 202, 204]
    redirect_codes = [301, 302, 303, 307, 308]
    client_issue_codes = [400, 401, 403, 404, 405, 408, 409, 410, 411, 413, 415, 422, 429]
    server_issue_codes = [500, 501, 502, 503, 504, 505]

    df['is_success'] = df['status'].isin(success_codes).astype(int)
    df['is_redirect'] = df['status'].isin(redirect_codes).astype(int)
    df['is_client_issue'] = df['status'].isin(client_issue_codes).astype(int)
    df['is_server_issue'] = df['status'].isin(server_issue_codes).astype(int)

    # ---- method (fixed categories — ensures same dummy columns every time) ----
    all_possible_methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS', 'CONNECT', 'TRACE']
    original_method = df['method'].astype(str).str.upper().str.strip()
    df['is_unknown_method'] = (~original_method.isin(all_possible_methods)).astype(int)
    method_type = CategoricalDtype(categories=all_possible_methods, ordered=False)
    df['method'] = original_method.astype(method_type)
    df = pd.get_dummies(df, columns=['method'], prefix='method', dtype=int)

    # ---- protocol features ----
    standard_protocols = ['HTTP/1.1', 'HTTP/1.0', 'HTTP/2', 'HTTP/3']
    clean_protocol = df['protocol'].astype(str).str.strip()
    df['extracted_http_version'] = clean_protocol.str.extract(r'(HTTP/\d\.\d)', expand=False).fillna('UNKNOWN')
    df['is_malformed_protocol'] = (~clean_protocol.isin(standard_protocols)).astype(int)
    command_keywords = r'wget|curl|chmod|bin|bash|sh|/tmp/|;'
    df['has_command_injection'] = clean_protocol.str.contains(command_keywords, case=False, regex=True).astype(int)
    df['is_legacy_protocol'] = (clean_protocol == 'HTTP/1.0').astype(int)

    # ---- size features ----
    df['size_log'] = np.log1p(df['size'])
    df['is_zero_size'] = (df['size'] == 0).astype(int)
    if size_threshold is None:
        size_threshold = df['size'].quantile(0.99)   # ⚠️ only safe during training
    df['is_large_size'] = (df['size'] > size_threshold).astype(int)

    # ---- per-ip aggregates: ip+time ----
    df['requests_per_min'] = df.groupby([df['time'].dt.floor('min'), 'ip'])['ip'].transform('count')
    df['requests_per_sec'] = df.groupby([df['time'].dt.floor('s'), 'ip'])['ip'].transform('count')
    df['time_since_previous_request'] = df.groupby('ip')['time'].diff().dt.total_seconds()
    df['is_request_first'] = df['time_since_previous_request'].isna().astype(int)
    df['time_since_previous_request'] = df['time_since_previous_request'].fillna(0)

    # ---- per-ip aggregates: ip+url ----
    df['unique_urls_per_ip'] = df.groupby('ip')['url'].transform('nunique')
    df['requests_per_url_per_ip'] = df.groupby(['ip', 'url'])['url'].transform('count')
    df['unique_url_ratio_per_ip'] = df['unique_urls_per_ip'] / df.groupby('ip')['url'].transform('count')

    # ---- per-ip aggregates: ip+status ----
    df['total_requests_per_ip'] = df.groupby('ip')['ip'].transform('count')
    df['client_errors_per_ip'] = df.groupby('ip')['is_client_issue'].transform('sum')
    df['server_errors_per_ip'] = df.groupby('ip')['is_server_issue'].transform('sum')
    df['success_requests_per_ip'] = df.groupby('ip')['is_success'].transform('sum')
    df['error_rate_per_ip'] = (df['client_errors_per_ip'] + df['server_errors_per_ip']) / df['total_requests_per_ip']
    df['success_rate_per_ip'] = df['success_requests_per_ip'] / df['total_requests_per_ip']

    # ---- per-ip aggregates: ip+user_agent ----
    df['unique_ua_per_ip'] = df.groupby('ip')['user_agent'].transform('nunique')
    df['automated_requests_per_ip'] = df.groupby('ip')['is_automated_client'].transform('sum')

    # ---- per-ip aggregates: ip+size ----
    df['total_size_per_ip'] = df.groupby('ip')['size'].transform('sum')
    df['avg_size_per_ip'] = df.groupby('ip')['size'].transform('mean').round(2)
    df['max_size_per_ip'] = df.groupby('ip')['size'].transform('max')

    # ---- method+url ----
    method_columns = [c for c in df.columns if c.startswith('method_') and c != 'method_recovered']
    df['method_recovered'] = df[method_columns].idxmax(axis=1).str.replace('method_', '', regex=False)
    df['method_url'] = df['method_recovered'] + '_' + df['url'].astype(str)
    df['requests_per_method_url'] = df.groupby('method_url')['method_url'].transform('count')

    # ---- ip+time+url / size / status ----
    df['requests_per_ip_url_per_min'] = df.groupby([df['time'].dt.floor('min'), 'ip', 'url'])['url'].transform('count')
    df['bytes_per_ip_per_min'] = df.groupby([df['time'].dt.floor('min'), 'ip'])['size'].transform('sum')
    df['errors_per_ip_per_min'] = df.groupby([df['time'].dt.floor('min'), 'ip'])['is_client_issue'].transform('sum')

    # ---- interaction / composite features ----
    df['scanner_threat_score'] = df['unique_urls_per_ip'] * df['error_rate_per_ip']
    df['sensitive_endpoint_attack'] = (
        (df['has_admin'] | df['has_api'] | df['has_login']) &
        (df['has_command_injection'] | (df['number_of_query_parameters'] > 3))
    ).astype(int)
    df['high_rate_automated_traffic'] = df['is_automated_client'] * df['requests_per_sec']

    # ---- drop raw/text columns ----
    drop_cols = [
        'ip', 'time', 'url', 'protocol', 'status', 'referrer', 'user_agent',
        'extra', 'no', 'minute', 'size', 'method_recovered', 'method_url',
        'extracted_http_version'
    ]
    df_clean = df.drop(columns=drop_cols)

    # ---- drop redundant (from correlation analysis) ----
    drop_redundant = [
        'success_requests_per_ip', 'client_errors_per_ip', 'url_length',
        'is_automated_client', 'total_size_per_ip', 'is_mobile'
    ]
    df_clean = df_clean.drop(columns=drop_redundant)

    # ---- drop known-constant columns (fixed list from training, NOT recalculated per batch) ----
    constant_cols = [
        'is_weekend', 'is_night_time', 'is_unknown_method',
        'method_PUT', 'method_PATCH', 'method_DELETE', 'method_CONNECT', 'method_TRACE'
    ]
    df_clean = df_clean.drop(columns=[c for c in constant_cols if c in df_clean.columns])

    return df_clean