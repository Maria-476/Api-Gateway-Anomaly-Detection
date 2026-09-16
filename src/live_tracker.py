from datetime import datetime

ip_notebook = {}

def new_request_arrives(ip, url, status, size, user_agent, is_client_issue, is_server_issue, is_automated_client):
    now = datetime.now()

    if ip not in ip_notebook:
        ip_notebook[ip] = []

    previous_visits = ip_notebook[ip]

    if len(previous_visits) == 0:
        time_gap = 0
        is_first = 1
    else:
        last_visit_time = previous_visits[-1]['time']
        time_gap = (now - last_visit_time).total_seconds()
        is_first = 0

    # store MORE per visit now — this is the only real change in this step
    ip_notebook[ip].append({
        'url': url,
        'time': now,
        'status': status,
        'size': size,
        'user_agent': user_agent,
        'is_client_issue': int(is_client_issue),
        'is_server_issue': int(is_server_issue),
        'is_automated': is_automated_client
    })

    total_visits = len(ip_notebook[ip])

    return {
        'total_visits': total_visits,
        'time_gap': time_gap,
        'is_first': is_first
    }

def get_ip_aggregate_features(ip):
    visits = ip_notebook[ip]

    total_requests = len(visits)
    unique_urls = len(set(v['url'] for v in visits))
    client_error_count = sum(v['is_client_issue'] for v in visits)
    server_error_count = sum(v['is_server_issue'] for v in visits)
    automated_count = sum(v['is_automated'] for v in visits)
    unique_uas = len(set(v['user_agent'] for v in visits))
    sizes = [v['size'] for v in visits]

    features = {
        'unique_urls_per_ip': unique_urls,
        'requests_per_url_per_ip': total_requests / unique_urls if unique_urls > 0 else 0,
        'unique_url_ratio_per_ip': unique_urls / total_requests,
        'total_requests_per_ip': total_requests,
        'server_errors_per_ip': server_error_count,
        'error_rate_per_ip': (client_error_count + server_error_count) / total_requests,
        'success_rate_per_ip': 1 - ((client_error_count + server_error_count) / total_requests),
        'unique_ua_per_ip': unique_uas,
        'automated_requests_per_ip': automated_count,
        'avg_size_per_ip': sum(sizes) / len(sizes),
        'max_size_per_ip': max(sizes),
    }

    return features
# -----------------

def get_ip_time_features(ip):
    visits = ip_notebook[ip]
    now = datetime.now()

    recent_min = [v for v in visits if (now - v['time']).total_seconds() <= 60]
    recent_sec = [v for v in visits if (now - v['time']).total_seconds() <= 1]

    return {
        'requests_per_min': len(recent_min),
        'requests_per_sec': len(recent_sec),
        'bytes_per_ip_per_min': sum(v['size'] for v in recent_min),
        'errors_per_ip_per_min': sum(v['is_client_issue'] for v in recent_min)
    }
# Testing

if __name__ == "__main__":
    new_request_arrives("1.2.3.4", "/home", 200, 5000, "Mozilla/5.0", False, False, 0)
    new_request_arrives("1.2.3.4", "/login", 404, 178, "Mozilla/5.0", True, False, 0)
    new_request_arrives("1.2.3.4", "/home", 200, 5200, "Mozilla/5.0", False, False, 0)

    print(get_ip_aggregate_features("1.2.3.4"))
    print(get_ip_time_features("1.2.3.4"))