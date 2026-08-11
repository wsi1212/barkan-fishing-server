"""
insights.py — 리스팅 테이블에 "뭐가 좋고 뭐가 구린지" 자동 배지를 붙이는 경량 헬퍼.

queries.py는 숫자만 뱉는다(순수 쿼리 쿡북 — 웹/CLI 공유라 판단 로직을 넣으면 안 됨, §10-3).
숫자만 늘어놔서는 사람이 한눈에 좋음/나쁨을 못 읽는다는 피드백(2026-07-28)에 따라, 여기서
표시 직전 단계(app.py)가 컬럼 하나를 기준으로 상위/하위나 이상치에 배지를 붙인다.

통계적으로 거창한 이상치 탐지(z-score 등)가 아니라 "정렬해서 양끝/이탈값에 표시"하는 단순한
방식 — 표본이 작은 사이드박스/초기 prod 데이터에서도 과적합(허수 이상치) 없이 안정적으로 동작한다.
모든 함수는 rows(list of dict)를 in-place로 변경하고 그대로 반환한다(체이닝 편의).
"""


def flag_extremes(rows, key, good_label=None, bad_label=None, n=2, min_rows=4, good="high"):
    """key 기준 상위/하위 n개에 배지. good='high'면 큰 값이 좋음(성공률 등), 'low'면 작은 값이
    좋음(소요시간 등). good_label/bad_label 중 하나를 None으로 두면 그쪽은 배지를 안 붙인다.
    표본이 min_rows 미만이면(우연한 극값을 "이상치"로 오인하기 쉬워) 아무 배지도 안 붙인다."""
    valid = [r for r in rows if r.get(key) is not None]
    if len(valid) < min_rows:
        return rows
    ordered = sorted(valid, key=lambda r: r[key])
    lo, hi = ordered[:n], ordered[-n:]
    good_rows, bad_rows = (hi, lo) if good == "high" else (lo, hi)
    if good_label:
        for r in good_rows:
            r["_flag"], r["_flag_cls"] = good_label, "good"
    if bad_label:
        for r in bad_rows:
            r.setdefault("_flag", bad_label)
            r.setdefault("_flag_cls", "bad")
    return rows


def flag_deviation(rows, actual_key, expected_key, label="⚠️ 명목과 괴리", n=2, min_rows=4, threshold=0.05):
    """actual vs expected 차이가 큰 순으로 상위 n개에 배지(RNG 실측 vs 명목 확률 등).
    threshold 미만 편차는 표본이 커도 배지 안 붙임(사소한 노이즈까지 이상치로 부풀리지 않게)."""
    valid = [r for r in rows if r.get(actual_key) is not None and r.get(expected_key) is not None]
    if len(valid) < min_rows:
        return rows
    devs = [(r, abs(r[actual_key] - r[expected_key])) for r in valid]
    devs.sort(key=lambda t: -t[1])
    for r, dev in devs[:n]:
        if dev >= threshold:
            r["_flag"], r["_flag_cls"] = label, "bad"
    return rows


def flag_band(rows, key, good_range, good_label="✅ 정상 범위", low_label=None, high_label=None):
    """key 값이 (lo, hi) 범위 안이면 good, 밖이면 방향에 따라 low_label/high_label(카지노 RTP 등
    "정답 구간"이 있는 지표용 — 상대적 극값이 아니라 절대 기준으로 판정)."""
    lo, hi = good_range
    for r in rows:
        v = r.get(key)
        if v is None:
            continue
        if v < lo and low_label:
            r["_flag"], r["_flag_cls"] = low_label, "bad"
        elif v > hi and high_label:
            r["_flag"], r["_flag_cls"] = high_label, "bad"
        elif lo <= v <= hi and good_label:
            r["_flag"], r["_flag_cls"] = good_label, "good"


def delta_badge(today, avg):
    """오늘 값 vs 최근 평균 대비 등락 % 배지(접속자·플레이타임·어획·퀘스트 등 항상 0 이상인 카운트류
    전용). avg가 0/None이면 배지 없음. 부호가 있어 0 근처를 오가는 지표(순발행·카지노 net)는
    기준값이 0에 가까우면 %가 왜곡되므로 delta_badge_abs를 대신 써야 한다."""
    if not avg:
        return ""
    pct = (today - avg) / avg * 100
    if abs(pct) < 5:
        return f'<span class="badge" style="background:#22252d;color:var(--muted)">≈{pct:+.1f}%</span>'
    cls = "ok" if pct > 0 else "warn"
    return f'<span class="badge {cls}">{pct:+.1f}%</span>'


def delta_badge_abs(today, avg, fmt):
    """부호 있는 지표(순발행·카지노 net 등) 전용 — 기준값이 0 근처면 %가 왜곡되기 쉬워(분모가 0에
    가까워짐) 절대 증감을 그대로 보여준다. 늘어난 게 좋은 건지 나쁜 건지는 지표마다 다르므로
    (순발행 증가=유저활동 증가일 수도, 인플레 가속일 수도) 색은 중립으로 둔다 — 판단은 사람 몫."""
    diff = today - avg
    return f'<span class="badge" style="background:#22252d;color:var(--muted)">{fmt(diff)} (평균 대비)</span>'
