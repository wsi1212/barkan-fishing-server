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
    """세로 막대 차트. labels/values 길이 동일. 음수 허용(0선 기준 위/아래).
    막대에 마우스를 올리면 값 라벨이 막대 위/아래에 뜬다(네이티브 <title> 툴팁 + CSS 표시 라벨 병행,
    2026-07-28 피드백 — 호버해도 아무것도 안 뜬다는 지적에 scatter_chart와 동일한 패턴 적용)."""
    if not values:
        return '<div class="chart-empty">데이터 없음</div>'
    fmt = value_fmt or (lambda v: f"{v:,.1f}")
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
        label_txt = f"{escape(str(label))}: {escape(fmt(v))}"
        # 막대가 거의 꽉 차면(길이가 비슷비슷한 값들) 라벨이 위쪽 제목과 겹치므로 최소 y를 clamp.
        label_y = max(y - 6, pad_t + 12) if v >= 0 else (y + bar_h + 14)
        parts.append(f'<g class="bar-pt">')
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{max(bar_h,1):.1f}" class="{cls}"><title>{label_txt}</title></rect>')
        parts.append(f'<text x="{x + bw/2:.1f}" y="{label_y:.1f}" class="bar-hover-label" text-anchor="middle">{label_txt}</text>')
        parts.append('</g>')
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
            label_txt = f"{escape(name)}: {escape(fmt(v))}"
            parts.append(f'<g class="bar-pt">')
            parts.append(f'<rect x="{x:.1f}" y="{y_cursor:.1f}" width="{bw:.1f}" height="{h:.1f}" class="chart-series-{si % 6}"><title>{label_txt}</title></rect>')
            parts.append(f'<text x="{x + bw/2:.1f}" y="{y_cursor - 4:.1f}" class="bar-hover-label" text-anchor="middle">{label_txt}</text>')
            parts.append('</g>')
        parts.append(f'<text x="{x + bw/2:.1f}" y="{height - pad_b + 16}" class="chart-label" text-anchor="middle">{escape(str(labels[i]))[:10]}</text>')
    legend_x = pad_l
    for si, name in enumerate(names):
        parts.append(f'<rect x="{legend_x}" y="{height - 14}" width="10" height="10" class="chart-series-{si % 6}"/>')
        parts.append(f'<text x="{legend_x + 14}" y="{height - 5}" class="chart-legend">{escape(name)}</text>')
        legend_x += 16 + len(name) * 7 + 14
    parts.append(f'<text x="{pad_l - 6}" y="{pad_t + 4}" class="chart-tick" text-anchor="end">{fmt(vmax)}</text>')
    parts.append('</svg>')
    return "".join(parts)


def line_chart(points, width=680, height=280, value_fmt=None, title=None, x_fmt=None,
               x_label=None, y_label=None, reference_diagonal=False):
    """points: [(x_label, y), ...] — x축은 순서상 인덱스로 균등 배치(범주형).
    reference_diagonal=True면 "이론상 x=y여야 정상"인 비교용 점선을 그려준다(RNG 검증 페이지처럼
    구간이 대략 균등 간격일 때만 의미 있음 — x축이 진짜 비례축이 아니라 인덱스 배치라 완벽한
    y=x는 아니고 근사치). 호버 시 값 라벨 표시는 bar_chart/scatter_chart와 동일한 패턴."""
    if not points:
        return '<div class="chart-empty">데이터 없음</div>'
    fmt = value_fmt or (lambda v: f"{v:,.1f}")
    xfmt = x_fmt or (lambda v: str(v))
    pad_l, pad_r, pad_t, pad_b = 54, 16, 24, 50
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
    if reference_diagonal:
        # x_bucket 값 자체(라벨)를 y축과 같은 스케일(vmin~vmax)로 매핑해 "이론값" 점선을 그린다.
        ref_coords = []
        for i, (label, _) in enumerate(points):
            try:
                xv = float(label)
            except (TypeError, ValueError):
                xv = None
            if xv is None:
                continue
            px = coords[i][0]
            py = pad_t + plot_h - (xv - vmin) / span * plot_h
            ref_coords.append((px, py))
        if ref_coords:
            ref_path = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(ref_coords))
            parts.append(f'<path d="{ref_path}" class="chart-reference-line" fill="none"/>')
            rx, ry = ref_coords[-1]
            parts.append(f'<text x="{rx:.1f}" y="{ry - 6:.1f}" class="chart-reference-label" text-anchor="end">이론값(명목=실측)</text>')
    parts.append(f'<path d="{path}" class="chart-line" fill="none"/>')
    for (px, py), (label, y) in zip(coords, points):
        label_txt = f"{escape(xfmt(label))}: {escape(fmt(y))}"
        parts.append(f'<g class="line-pt">')
        parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="8" fill="transparent"/>')
        parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="2.5" class="chart-dot"><title>{label_txt}</title></circle>')
        parts.append(f'<text x="{px:.1f}" y="{py - 10:.1f}" class="line-hover-label" text-anchor="middle">{label_txt}</text>')
        parts.append('</g>')
    step_label = max(1, n // 8)
    for i, (label, _) in enumerate(points):
        if i % step_label == 0:
            parts.append(f'<text x="{coords[i][0]:.1f}" y="{height - pad_b + 16}" class="chart-label" text-anchor="middle">{escape(xfmt(label))}</text>')
    parts.append(f'<text x="{pad_l - 6}" y="{pad_t + 4}" class="chart-tick" text-anchor="end">{fmt(vmax)}</text>')
    parts.append(f'<text x="{pad_l - 6}" y="{height - pad_b + 4}" class="chart-tick" text-anchor="end">{fmt(vmin)}</text>')
    if x_label:
        parts.append(f'<text x="{pad_l + plot_w / 2:.1f}" y="{height - 6}" class="chart-axis-label" text-anchor="middle">{escape(x_label)} →</text>')
    if y_label:
        ly = pad_t + plot_h / 2
        parts.append(f'<text x="12" y="{ly:.1f}" class="chart-axis-label" text-anchor="middle" transform="rotate(-90 12 {ly:.1f})">{escape(y_label)} →</text>')
    parts.append('</svg>')
    return "".join(parts)


def scatter_chart(points, width=640, height=380, x_fmt=None, y_fmt=None, title=None,
                   x_label=None, y_label=None, colors=None):
    """points: [(x, y, label), ...]. colors(옵션): points와 같은 길이의 'good'/'bad'/None 리스트 —
    좋음/나쁨 인사이트가 있으면 점 색으로도 구분(파란 점만 잔뜩 있으면 뭐가 뭔지 안 보인다는
    2026-07-28 피드백). x_label/y_label로 축 자체에 뭘 나타내는지 명시(제목만으론 부족했음).
    호버 시 값 라벨은 네이티브 <title> 툴팁 + CSS만으로 보이는 텍스트 라벨을 같이 제공(JS 없이도
    동작 — 순수 SVG+CSS 원칙 유지, §10-5)."""
    if not points:
        return '<div class="chart-empty">데이터 없음</div>'
    xfmt = x_fmt or (lambda v: f"{v:,.1f}")
    yfmt = y_fmt or (lambda v: f"{v:,.1f}")
    pad_l, pad_r, pad_t, pad_b = 66, 16, 24, 56
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
    for i, (x, y, label) in enumerate(points):
        px = pad_l + (x - xmin) / xspan * plot_w
        py = pad_t + plot_h - (y - ymin) / yspan * plot_h
        cls = "chart-dot"
        c = colors[i] if colors else None
        if c == "good":
            cls = "chart-dot-good"
        elif c == "bad":
            cls = "chart-dot-bad"
        label_txt = f"{escape(str(label))} — x={escape(xfmt(x))}, y={escape(yfmt(y))}"
        parts.append(f'<g class="scatter-pt">')
        # 실제 보이는 점(r=4)보다 훨씬 큰 투명 히트영역(r=11) — 작은 점을 정확히 조준 안 해도 호버됨.
        parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="11" fill="transparent"/>')
        parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" class="{cls}"><title>{label_txt}</title></circle>')
        anchor = "end" if px > pad_l + plot_w * 0.7 else "start"
        lx = px + (-8 if anchor == "end" else 8)
        parts.append(f'<text x="{lx:.1f}" y="{py - 8:.1f}" class="scatter-hover-label" text-anchor="{anchor}">{label_txt}</text>')
        parts.append('</g>')
    parts.append(f'<text x="{pad_l - 8}" y="{pad_t + 4}" class="chart-tick" text-anchor="end">{yfmt(ymax)}</text>')
    parts.append(f'<text x="{pad_l - 8}" y="{height - pad_b + 4}" class="chart-tick" text-anchor="end">{yfmt(ymin)}</text>')
    parts.append(f'<text x="{pad_l}" y="{height - pad_b + 16}" class="chart-tick">{xfmt(xmin)}</text>')
    parts.append(f'<text x="{width - pad_r}" y="{height - pad_b + 16}" class="chart-tick" text-anchor="end">{xfmt(xmax)}</text>')
    if x_label:
        parts.append(f'<text x="{pad_l + plot_w / 2:.1f}" y="{height - 6}" class="chart-axis-label" text-anchor="middle">{escape(x_label)} →</text>')
    if y_label:
        ly = pad_t + plot_h / 2
        parts.append(f'<text x="14" y="{ly:.1f}" class="chart-axis-label" text-anchor="middle" transform="rotate(-90 14 {ly:.1f})">{escape(y_label)} →</text>')
    parts.append('</svg>')
    return "".join(parts)
