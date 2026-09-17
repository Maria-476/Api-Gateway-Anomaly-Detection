from datetime import datetime, timedelta

throttled_ips = {}
violation_history = {}


def is_currently_throttled(ip):
    if ip not in throttled_ips:
        return False

    expires_at = throttled_ips[ip]['expires_at']
    now = datetime.now()

    if now >= expires_at:
        del throttled_ips[ip]
        return False

    return True


def throttle_ip(ip, duration_seconds=60):
    now = datetime.now()
    throttled_ips[ip] = {
        'throttled_since': now,
        'expires_at': now + timedelta(seconds=duration_seconds)
    }


def record_violation(ip):
    if ip not in violation_history:
        violation_history[ip] = []
    violation_history[ip].append(datetime.now())


def get_recent_violation_count(ip, window_minutes=30):
    if ip not in violation_history:
        return 0
    cutoff = datetime.now() - timedelta(minutes=window_minutes)
    recent = [v for v in violation_history[ip] if v >= cutoff]
    violation_history[ip] = recent
    return len(recent)


def make_decision(ip, model_result, threshold=0.0856, threshold_duration=60):
    if is_currently_throttled(ip):
        return {'action': 'already_throttled', 'ip': ip}

    if not model_result['is_anomaly']:
        return {'action': 'allow', 'ip': ip, 'score': model_result['score']}

    record_violation(ip)
    violations = get_recent_violation_count(ip)
    severity = model_result['score'] - threshold

    if violations >= 3:
        throttle_ip(ip, duration_seconds=threshold_duration * 4)
        return {'action': 'temporary_block', 'ip': ip, 'score': model_result['score'], 'violations': violations}

    elif severity > 0.02:
        throttle_ip(ip, duration_seconds=threshold_duration)
        return {'action': 'rate_limit', 'ip': ip, 'score': model_result['score'], 'violations': violations}

    else:
        return {'action': 'monitor', 'ip': ip, 'score': model_result['score'], 'violations': violations}


if __name__ == "__main__":
    import time

    fake_result_high = {'score': 0.15, 'is_anomaly': True}

    for i in range(4):
        result = make_decision("3.3.3.3", fake_result_high, threshold_duration=2)  # short 2-second throttle for testing
        print(i, result)
        time.sleep(3)   # wait past the throttle so we can test again