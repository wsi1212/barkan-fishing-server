#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""아티팩트 본문(.html 조각) → 팀 배포용 단독 HTML.

아티팩트는 <!doctype>…<head>…<body> 스켈레톤을 «발행 시점»에 씌워 준다.
그래서 소스 파일에는 그게 없다 — 그대로 열면 리셋 CSS도 뷰포트 메타도 없다.
이 스크립트가 그 껍데기를 대신 씌우고, 호스트가 해 주던 두 가지를 손으로 채운다:
  ① 최소 리셋   ② 테마 (호스트는 data-theme 을 찍어 주지만 단독 파일엔 아무도 없다 → 토글 + localStorage)
덤으로 인쇄 스타일. 현장에서 종이로 들고 팔 사람이 있다.
"""
import io, os, re, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else "deepsea-hq.html"
DST = sys.argv[2] if len(sys.argv) > 2 else "../../../../../../home/user/barkan-fishing-server/docs/deepsea-hq-plan.html"

body = io.open(SRC, encoding="utf-8").read()
title = re.search(r"<title>(.*?)</title>", body).group(1)
body = body.replace("<title>%s</title>\n" % title, "", 1)
links = re.findall(r'<link [^>]*>\n', body)
for l in links:
    body = body.replace(l, "", 1)
body = body.lstrip("\n")

HEAD = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="description" content="바르칸 열도 · 심해교단 본부 굴착 도면 — 종단면, 층별 평면, 지역 등록, 퀘스트 배치.">
<title>{title}</title>
{links}<style>
/* ── standalone reset (아티팩트 호스트가 주던 것을 대체) ───────────── */
*,*::before,*::after{{box-sizing:border-box}}
html{{-webkit-text-size-adjust:100%}}
body,h1,h2,h3,h4,p,figure,blockquote,dl,dd,ul,ol{{margin:0}}
ul[class],ol[class]{{list-style:none;padding:0}}
img,svg,video{{max-width:100%;display:block}}
button,input,select,textarea{{font:inherit;color:inherit}}
table{{border-collapse:collapse}}
:where(a){{color:var(--cyan)}}
@media (prefers-reduced-motion:reduce){{
  *,*::before,*::after{{animation-duration:.01ms!important;transition-duration:.01ms!important}}
}}
</style>
""".format(title=title, links="".join(links))

EXTRA_CSS = """<style>
/* ── standalone 전용: 테마 토글 + 공유 머리말 + 인쇄 ──────────────── */
.theme-btn{
  position:fixed; top:14px; right:14px; z-index:20;
  display:inline-flex; align-items:center; gap:7px;
  padding:7px 13px; border:1px solid var(--rule); border-radius:2px;
  background:var(--panel); color:var(--ink-2); cursor:pointer;
  font-family:"IBM Plex Mono",ui-monospace,monospace; font-size:11px;
  letter-spacing:.1em; text-transform:uppercase;
  box-shadow:var(--shadow); transition:color .15s, border-color .15s;
}
.theme-btn:hover{color:var(--cyan); border-color:var(--cyan)}
.theme-btn:focus-visible{outline:2px solid var(--cyan); outline-offset:2px}
.theme-btn .dot{width:8px; height:8px; border-radius:50%; background:var(--cyan)}

.share-note{
  max-width:1060px; margin:0 auto; padding:11px 22px;
  font-family:"IBM Plex Mono",ui-monospace,monospace; font-size:11.5px;
  letter-spacing:.04em; color:var(--ink-3); border-bottom:1px solid var(--rule-soft);
}
.share-note b{color:var(--cyan); font-weight:600}

@media print{
  :root{--ground:#fff; --panel:#fff; --panel-2:#f2f6f7; --void:#fff}
  .theme-btn, .share-note{display:none}
  body{background:#fff}
  header{padding-top:0}
  section{padding-top:26px; break-inside:avoid}
  .sheet{break-inside:avoid; box-shadow:none}
  .grid{grid-template-columns:1fr 1fr}
  footer{margin-top:26px}
  @page{margin:14mm}
}
</style>
"""

BTN = """<button class="theme-btn" id="themeBtn" type="button" aria-label="테마 전환"><span class="dot"></span><span id="themeLbl">밝음</span></button>
<p class="share-note">바르칸 열도 · 빌드팀 공유본 &nbsp;·&nbsp; 이 파일 하나만 있으면 열린다 &nbsp;·&nbsp; <b>Ctrl/⌘+P → PDF</b> 로 현장 인쇄본</p>
"""

JS = """<script>
(function () {
  var KEY = 'barkan-deepsea-theme';
  var root = document.documentElement;
  var btn  = document.getElementById('themeBtn');
  var lbl  = document.getElementById('themeLbl');

  function stored() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
  function systemDark() {
    return !!(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
  }
  function paint() {
    var t = root.getAttribute('data-theme');
    var dark = t ? t === 'dark' : systemDark();
    lbl.textContent = dark ? '어두움' : '밝음';
    btn.setAttribute('aria-label', '테마 전환 — 현재 ' + (dark ? '어두움' : '밝음'));
  }

  var saved = stored();
  if (saved === 'dark' || saved === 'light') root.setAttribute('data-theme', saved);
  paint();

  btn.addEventListener('click', function () {
    var cur = root.getAttribute('data-theme');
    var dark = cur ? cur === 'dark' : systemDark();
    var next = dark ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    try { localStorage.setItem(KEY, next); } catch (e) {}
    paint();
  });

  if (window.matchMedia) {
    var mq = window.matchMedia('(prefers-color-scheme: dark)');
    var on = function () { if (!root.getAttribute('data-theme')) paint(); };
    if (mq.addEventListener) mq.addEventListener('change', on);
    else if (mq.addListener) mq.addListener(on);
  }
})();
</script>
"""

out = HEAD + EXTRA_CSS + "</head>\n<body>\n" + BTN + body.rstrip() + "\n" + JS + "</body>\n</html>\n"
os.makedirs(os.path.dirname(os.path.abspath(DST)), exist_ok=True)
io.open(DST, "w", encoding="utf-8").write(out)
print("→ {}  ({:,} bytes)".format(DST, os.path.getsize(DST)))
