"""
charts.py — 서버사이드 SVG 차트 생성기 (외부 JS 라이브러리 0개, CDN 미의존).

stats-system-plan.md §10-5는 Chart.js를 동봉(vendored)하는 안을 제시했지만, 이 환경에서는
파일을 새로 내려받을 수 없어(§10-5 "CDN 미의존" 요건은 유지하되) 대신 순수 SVG를 서버에서
직접 그려 넣는 방식을 택했다 — 결과물은 동일(자체 완결·오프라인 렌더)하고, JS 없이도 렌더되어
오히려 더 견고하다. 다크/라이트 테마는 CSS 변수로 색만 참조하고 좌표계는 파이썬이 계산한다.
"""
from html import escape


def _svg_open(width, height):
    return f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" xmlns="http://www.w3.org/2000/svg" role="img">'


def bar_chart(labels, values, width=640, height=280, value_fmt=None, title=None):
    """세로 막대 차트. labels/values 길이 동일. 음수 허용(0선 기준 위/아래)."""
    if not values:
        return '<div class="chart-empty">데이터 없음</div>'
    fmt = value_fmt or (lambda v: f"{v:,.0f}")
    pad_l, pad_r, pad_t, pad_b = 50, 16, 24, 40
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    vmax = max(max(values), 0)
    vmin = min(min(values), 0)
    span = (vmax - vmin) or 1
    zero_y = pad_t + plot_h * (vmax / span)
    n = len(values)
    bw = plot_w / n * 0.65
    gap = plot_w / n
    parts = [_svg_open(width, height)]
    if title:
        parts.append(f'<text x="{pad_l}" y="16" class="chart-title">{escape(title)}</text>')
    parts.append(f'<line x1="{pad_l}" y1="{zero_y:.1f}" x2="{width - pad_r}" y2="{zero_y:.1f}" class="chart-axis"/>')
    for i, (label, v) in enumerate(zip(labels, values)):
        x = pad_l + i * gap + (gap - bw) / 2
        bar_h = abs(v) / span * plot_h
        y = zero_y - bar_h if v >= 0 else zero_y
        cls = "chart-bar-pos" if v >= 0 else "chart-bar-neg"
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{max(bar_h,1):.1f}" class="{cls}"><title>{escape(str(label))}: {fmt(v)}</title></rect>')
        lx = x + bw / 2
        parts.append(f'<text x="{lx:.1f}" y="{height - pad_b + 16}" class="chart-label" text-anchor="middle">{escape(str(label))[:10]}</text>')
    parts.append(f'<text x="{pad_l - 6}" y="{pad_t + 4}" class="chart-tick" text-anchor="end">{fmt(vmax)}</text>')
    parts.append(f'<text x="{pad_l - 6}" y="{height - pad_b + 4}" class="chart-tick" text-anchor="end">{fmt(vmin)}</text>')
    parts.append('</svg>')
    return "".join(parts)


def stacked_bar_chart(labels, series, width=680, height=300, value_fmt=None, title=None):
    """series: {name: [values...]} 양수만 가정(순발행 소스 스택 등). 색은 CSS 클래스 순환(최대 6종)."""
    if not labels:
        return '<div class="chart-empty">데이터 없음</div>'
    fmt = value_fmt or (lambda v: f"{v:,.0f}")
    pad_l, pad_r, pad_t, pad_b = 60, 16, 32, 40
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    totals = [sum(s[i] for s in series.values()) for i in range(len(labels))]
    vmax = max(totals) or 1
    n = len(labels)
    gap = plot_w / n
    bw = gap * 0.65
    parts = [_svg_open(width, height)]
    if title:
        parts.append(f'<text x="{pad_l}" y="16" class="chart-title">{escape(title)}</text>')
    names = list(series.keys())
    for i in range(n):
        x = pad_l + i * gap + (gap - bw) / 2
        y_cursor = pad_t + plot_h
        for si, name in enumerate(names):
            v = series[name][i]
            if v <= 0:
                continue
            h = v / vmax * plot_h
            y_cursor -= h
            parts.append(f'<rect x="{x:.1f}" y="{y_cursor:.1f}" width="{bw:.1f}" height="{h:.1f}" class="chart-series-{si % 6}"><title>{escape(name)}: {fmt(v)}</title></rect>')
        parts.append(f'<text x="{x + bw/2:.1f}" y="{height - pad_b + 16}" class="chart-label" text-anchor="middle">{escape(str(labels[i]))[:10]}</text>')
    legend_x = pad_l
    for si, name in enumerate(names):
        parts.append(f'<rect x="{legend_x}" y="{height - 14}" width="10" height="10" class="chart-series-{si % 6}"/>')
        parts.append(f'<text x="{legend_x + 14}" y="{height - 5}" class="chart-legend">{escape(name)}</text>')
        legend_x += 16 + len(name) * 7 + 14
    parts.append(f'<text x="{pad_l - 6}" y="{pad_t + 4}" class="chart-tick" text-anchor="end">{fmt(vmax)}</text>')
    parts.append('</svg>')
    return "".join(parts)


def line_chart(points, width=680, height=280, value_fmt=None, title=None, x_fmt=None):
    """points: [(x_label, y), ...] — x축은 순서상 인덱스로 균등 배치(범주형)."""
    if not points:
        return '<div class="chart-empty">데이터 없음</div>'
    fmt = value_fmt or (lambda v: f"{v:,.1f}")
    xfmt = x_fmt or (lambda v: str(v))
    pad_l, pad_r, pad_t, pad_b = 50, 16, 24, 36
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    ys = [p[1] for p in points]
    vmax = max(ys) if ys else 1
    vmin = min(ys) if ys else 0
    span = (vmax - vmin) or 1
    n = len(points)
    step = plot_w / max(n - 1, 1)
    coords = []
    for i, (_, y) in enumerate(points):
        px = pad_l + i * step
        py = pad_t + plot_h - (y - vmin) / span * plot_h
        coords.append((px, py))
    path = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(coords))
    parts = [_svg_open(width, height)]
    if title:
        parts.append(f'<text x="{pad_l}" y="16" class="chart-title">{escape(title)}</text>')
    parts.append(f'<path d="{path}" class="chart-line" fill="none"/>')
    for (px, py), (label, y) in zip(coords, points):
        parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="2.5" class="chart-dot"><title>{escape(xfmt(label))}: {fmt(y)}</title></circle>')
    step_label = max(1, n // 8)
    for i, (label, _) in enumerate(points):
        if i % step_label == 0:
            parts.append(f'<text x="{coords[i][0]:.1f}" y="{height - pad_b + 16}" class="chart-label" text-anchor="middle">{escape(xfmt(label))}</text>')
    parts.append(f'<text x="{pad_l - 6}" y="{pad_t + 4}" class="chart-tick" text-anchor="end">{fmt(vmax)}</text>')
    parts.append(f'<text x="{pad_l - 6}" y="{height - pad_b + 4}" class="chart-tick" text-anchor="end">{fmt(vmin)}</text>')
    parts.append('</svg>')
    return "".join(parts)


def scatter_chart(points, width=640, height=360, x_fmt=None, y_fmt=None, title=None):
    """points: [(x, y, label), ...]."""
    if not points:
        return '<div class="chart-empty">데이터 없음</div>'
    xfmt = x_fmt or (lambda v: f"{v:,.0f}")
    yfmt = y_fmt or (lambda v: f"{v:,.2f}")
    pad_l, pad_r, pad_t, pad_b = 60, 16, 24, 40
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    xmax, xmin = max(xs), min(xs)
    ymax, ymin = max(ys), min(ys)
    xspan = (xmax - xmin) or 1
    yspan = (ymax - ymin) or 1
    parts = [_svg_open(width, height)]
    if title:
        parts.append(f'<text x="{pad_l}" y="16" class="chart-title">{escape(title)}</text>')
    for x, y, label in points:
        px = pad_l + (x - xmin) / xspan * plot_w
        py = pad_t + plot_h - (y - ymin) / yspan * plot_h
        parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" class="chart-dot"><title>{escape(str(label))}: x={xfmt(x)} y={yfmt(y)}</title></circle>')
    parts.append(f'<text x="{pad_l - 6}" y="{pad_t + 4}" class="chart-tick" text-anchor="end">{yfmt(ymax)}</text>')
    parts.append(f'<text x="{pad_l - 6}" y="{height - pad_b + 4}" class="chart-tick" text-anchor="end">{yfmt(ymin)}</text>')
    parts.append(f'<text x="{pad_l}" y="{height - 6}" class="chart-tick">{xfmt(xmin)}</text>')
    parts.append(f'<text x="{width - pad_r}" y="{height - 6}" class="chart-tick" text-anchor="end">{xfmt(xmax)}</text>')
    parts.append('</svg>')
    return "".join(parts)
