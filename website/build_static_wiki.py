#!/usr/bin/env python3
"""Build crawlable, canonical HTML pages for the public Barkan wiki.

The interactive /wiki page remains the player-facing directory.  This builder
creates the same guide URLs as complete HTML documents so search engines and
AI readers do not need to execute the client-side wiki application to discover
their title, summary, or main facts.
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path


SITE = "https://barkan.kr"
OUT_DIR = Path(__file__).resolve().parent / "wiki"

DOCS = [
    {
        "slug": "start",
        "title": "처음 시작하기",
        "description": "바르칸 열도 접속 방법, 첫 낚시와 기본 명령어를 안내하는 공식 시작 가이드.",
        "lead": "바르칸 열도는 낚시와 탐험을 중심으로 성장하는 Minecraft 서버입니다. 처음 접속했다면 항구 안내를 따라 첫 장비와 기본 동선을 익혀 보세요.",
        "sections": [
            ("접속 정보", ["서버 주소는 barkan.kr입니다. Java Edition과 Bedrock Edition(Geyser 크로스플레이)을 지원합니다.", "접속 가능 버전은 1.21.10부터 1.26.2까지입니다."], []),
            ("첫 항해 순서", [], ["항구 안내 NPC의 대화를 읽고 첫 낚싯대를 준비합니다.", "물가에서 낚싯대를 사용해 입질을 기다리고 미니게임을 성공합니다.", "잡은 물고기는 판매하거나 도감·제출에 활용합니다.", "레벨과 장비 메뉴에서 다음 목표와 장착 상태를 확인합니다."]),
            ("기본 명령어", [], ["/레벨 — 현재 낚시 레벨과 성장 로드맵 확인", "/장비 — 낚싯대·부품·능력치·상태 확인", "/판매 — 가까운 물고기 판매 NPC 안내", "/도감 — 발견한 물고기와 수집 기록 확인", "/섬 — 개인 섬 생성과 관리 메뉴"]),
            ("문제가 생겼다면", ["아이템·이동·보상처럼 계정 확인이 필요한 문의는 디스코드에 닉네임, 발생 시각, 상황, 가능하면 스크린샷을 함께 남겨 주세요."], []),
        ],
        "faq": [
            ("바르칸 열도 서버 주소는 무엇인가요?", "Minecraft 서버 주소는 barkan.kr입니다."),
            ("Bedrock Edition도 접속할 수 있나요?", "네. Geyser를 통한 Bedrock Edition 크로스플레이를 지원합니다."),
            ("처음 접속하면 무엇부터 하나요?", "항구 안내 NPC를 따라 첫 낚싯대를 준비한 뒤, 물가에서 낚시 미니게임을 시작하세요."),
        ],
    },
    {
        "slug": "fishing",
        "title": "낚시와 성장",
        "description": "바르칸 열도의 낚시 미니게임, 등급, 날씨, 지역, 레벨 성장과 어획 보상을 설명하는 공식 가이드.",
        "lead": "물고기의 등급과 크기는 보상에 영향을 주고, 장비·날씨·지역에 따라 만나는 대상도 달라집니다. 레벨을 올릴수록 새로운 장비와 콘텐츠가 열립니다.",
        "sections": [
            ("낚시의 흐름", ["낚시는 지역·시간·날씨로 어종 풀이 정해진 뒤 등급과 크기가 판정되고, 미니게임 성공 여부에 따라 보상이 결정됩니다.", "같은 장소라도 시간과 날씨에 따라 만날 수 있는 어종이 달라지므로 목표 어종은 도감의 서식 정보를 먼저 확인하세요."], []),
            ("등급과 레벨", ["레벨 1~29에서는 S등급까지, 레벨 30부터는 M등급, 레벨 45부터는 L등급, 레벨 60부터는 G등급 어종을 만날 수 있습니다.", "희귀 등급은 각 등급의 천장(PRD)과 행운·등급 특화 효과의 영향을 받습니다."], []),
            ("판매와 보관", ["/판매로 가까운 판매 NPC를 찾아 어획을 판매할 수 있습니다. 보관할 물고기는 아이스박스에 넣어 신선도를 관리하세요."], []),
            ("성장 팁", [], ["초반에는 희귀 등급보다 미니게임 성공률과 장비 상태를 안정시키세요.", "희귀 어종을 노릴 때는 레벨, 등급 해금, 해당 지역의 어종 풀을 함께 확인하세요.", "큰 물고기는 보상에 유리하지만 미니게임 난이도도 함께 올라갈 수 있습니다."]),
        ],
    },
    {
        "slug": "gear",
        "title": "장비와 강화",
        "description": "낚싯대, 작살, 릴, 줄, 바늘, 미끼, 찌의 장착·강화·내구도를 안내하는 바르칸 열도 공식 장비 가이드.",
        "lead": "낚싯대에 부품을 맞추고 강화해 낚시 성능을 끌어올릴 수 있습니다. 장비마다 레벨 제한과 서로 다른 능력치가 있어 목표에 맞춘 구성이 중요합니다.",
        "sections": [
            ("장비 확인", ["/장비에서 현재 낚싯대와 장착 부품, 능력치, 장비 상태를 확인할 수 있습니다. 장비 도감에서는 레벨 제한, 능력치, 제작 재료와 획득 출처를 비교할 수 있습니다."], []),
            ("강화", ["/강화는 낚싯대별 강화 메뉴를 엽니다. 강화에는 성공과 하락의 위험이 있으므로 필요한 재료와 현재 목표를 확인한 뒤 진행하세요."], []),
            ("부품 조합", ["릴·줄·바늘·미끼·찌는 서로 다른 보너스를 제공합니다. 부품상점, 분해, 조각 합성으로 새 부품을 얻어 낚싯대에 맞춰 조합할 수 있습니다."], []),
            ("관리", ["장시간 낚시 전후로 장비 상태를 확인하세요. 목표 어종의 지역·날씨 조건과 장비 능력치를 함께 고려하면 더 안정적인 세팅을 만들 수 있습니다."], []),
        ],
    },
    {
        "slug": "island",
        "title": "개인 섬",
        "description": "바르칸 열도 개인 섬 생성, 공개 방문, 초대, 워프, 농사와 생활 콘텐츠를 안내하는 공식 가이드.",
        "lead": "개인 섬은 혼자 운영하는 생활 공간입니다. 섬을 공개하면 다른 모험가가 방문할 수 있고, 환경·권한·워프를 직접 관리합니다.",
        "sections": [
            ("섬 만들기와 관리", ["/섬으로 개인 섬을 생성하거나 관리 메뉴를 엽니다. 섬 업그레이드에 따라 경계, 워프, 특수작물 한도 등 생활 기반을 넓힐 수 있습니다."], []),
            ("방문과 초대", ["/섬 방문 <닉네임>으로 공개된 다른 섬을 방문하고, /섬 초대 <닉네임>으로 알바생을 초대할 수 있습니다."], []),
            ("생활 콘텐츠", ["개인 섬에서는 농사·요리·광질·제작을 이어갈 수 있습니다. 특수작물은 섬 업그레이드에 따라 설치 한도가 달라집니다."], []),
            ("방문 기록", ["섬 방문 랭킹은 섬장·알바생을 제외한 외부 방문의 누적 횟수를 기준으로 합니다."], []),
        ],
    },
    {
        "slug": "guild",
        "title": "길드",
        "description": "길드원, 길드 섬, 금고, 제출 기여와 길드 랭킹을 안내하는 바르칸 열도 공식 길드 가이드.",
        "lead": "길드는 여러 플레이어가 하나의 목표를 세우고 함께 성장하는 단위입니다. 길드원 레벨, 금고, 제출 기여가 길드 성장과 랭킹에 반영됩니다.",
        "sections": [
            ("길드 활동", ["길드원을 모으고 길드 섬을 관리하며, 함께 모은 자원과 제출 기여로 길드 레벨을 성장시킬 수 있습니다."], []),
            ("기여와 기록", ["제출소에서 자원을 제출하면 기여가 길드 성장 기록에 반영됩니다. 시즌 운영 여부와 보상은 서버 공지를 확인하세요."], []),
            ("랭킹", ["웹사이트 랭킹 페이지에서 길드 레벨과 다른 길드의 기록을 확인할 수 있습니다."], []),
            ("함께 플레이하기", ["길드 채팅, 거래, 섬 방문을 통해 다른 모험가와 협력할 수 있습니다. 운영 규칙은 공식 법전을 확인하세요."], []),
        ],
    },
    {
        "slug": "economy",
        "title": "경제와 거래",
        "description": "물고기 판매, 플레이어 마켓, 수표, 송금과 안전한 거래를 안내하는 바르칸 열도 공식 경제 가이드.",
        "lead": "바르칸의 경제는 낚시 판매와 생활 콘텐츠, 플레이어 간 거래를 중심으로 움직입니다. 필요한 물건은 마켓에서 찾고, 귀중한 거래는 금액을 다시 확인하세요.",
        "sections": [
            ("물고기 판매", ["/판매로 가장 가까운 물고기 판매 NPC 위치를 안내받은 뒤 어획을 판매할 수 있습니다."], []),
            ("플레이어 마켓", ["/마켓에서 등록된 물건을 둘러보고, /마켓등록 <가격>으로 들고 있는 물건을 등록합니다."], []),
            ("수표와 송금", ["/수표 <금액>으로 수표를 발행할 수 있습니다. 송금과 거래 전에는 상대방, 물건, 금액을 반드시 다시 확인하세요."], []),
            ("안전한 거래", ["게임 밖 현금 거래와 허위 약속은 금지됩니다. 문제가 생기면 닉네임·시간·상황·증거를 정리해 운영 채널로 문의하세요."], []),
        ],
    },
    {
        "slug": "cooking",
        "title": "농사와 요리",
        "description": "특수작물, 요리 재료, 낚시 버프, 제출과 판매를 안내하는 바르칸 열도 공식 생활 가이드.",
        "lead": "생활 콘텐츠는 낚시 밖에서도 성장 재료를 마련하는 방법입니다. 작물을 기르고 요리를 만들어 버프·제출·회복·판매에 활용하세요.",
        "sections": [
            ("작물 관리", ["/작물에서 특수작물 상태와 관리 정보를 확인합니다. 특수작물의 설치 한도는 섬 업그레이드에 따라 달라집니다."], []),
            ("요리의 쓰임", ["요리는 버프, 제출, 회복, 판매 전용으로 나뉩니다. 버프용 요리를 먹으면 일정 시간 낚시에 도움이 되는 효과를 얻을 수 있습니다."], []),
            ("재료 수집", ["낚시·농사·채집·광질·거래로 재료를 모아 요리와 제작에 사용할 수 있습니다."], []),
            ("계획 세우기", ["재료 도감에서 필요한 재료의 획득처를 확인하고, 개인 섬의 작물과 요리 목표를 함께 계획해 보세요."], []),
        ],
    },
    {
        "slug": "casino",
        "title": "카지노와 기록",
        "description": "바르칸 열도 카지노 콘텐츠와 순수익 랭킹의 산정 기준을 안내하는 공식 가이드.",
        "lead": "카지노는 선택형 콘텐츠입니다. 게임별 결과는 기록되고, 웹 랭킹의 카지노 순수익은 모든 베팅 결과를 합산한 순이익 기준으로 표시됩니다.",
        "sections": [
            ("순수익 기준", ["순수익은 획득액이 아니라 베팅을 제외한 최종 손익입니다. 이익과 손실을 모두 반영한 기록으로 순위가 정해집니다."], []),
            ("랭킹 보기", ["웹사이트의 랭킹 페이지에서 카지노 순수익과 낚시·자산·길드·섬 방문 등의 기록을 확인할 수 있습니다."], []),
            ("플레이 원칙", ["카지노는 잃어도 괜찮은 범위에서 즐기는 선택형 콘텐츠입니다. 생활 자금과 장비 강화 재료는 따로 관리하는 편이 좋습니다."], []),
        ],
    },
    {
        "slug": "explore",
        "title": "탐험·날씨·이동",
        "description": "바르칸 열도 지역, 날씨, 페리, 포탈과 목표 어종 탐색을 안내하는 공식 탐험 가이드.",
        "lead": "바르칸의 지역은 같은 물가라도 날씨와 시간에 따라 다른 모습을 보입니다. 이동수단과 환경 정보를 함께 활용하면 원하는 어종과 재료를 더 정확히 찾아갈 수 있습니다.",
        "sections": [
            ("지역 정보", ["지역마다 환경과 출현 어종이 다릅니다. 물고기 도감과 현지 안내를 함께 확인하세요."], []),
            ("날씨와 시간", ["비·뇌우·태풍·안개 등은 지역 환경과 낚시에 영향을 줄 수 있습니다. 목표 어종을 찾을 때는 시간과 날씨 조건을 함께 확인하는 것이 좋습니다."], []),
            ("이동", ["페리와 포탈은 지역 사이를 이동하는 주요 수단입니다. 항해 지도에서 주요 마을·항구와 실제 서버 지역 좌표를 확인할 수 있습니다."], []),
            ("탐험 기록", ["/도감에서 발견한 어종과 수집 기록을 확인하고, 아직 만나지 못한 어종의 서식 조건을 다음 항로의 목표로 삼아 보세요."], []),
        ],
    },
    {
        "slug": "quest",
        "title": "퀘스트와 NPC",
        "description": "메인·일일·주간 퀘스트와 NPC 역할, 보상 확인 방법을 안내하는 바르칸 열도 공식 가이드.",
        "lead": "NPC 대화와 퀘스트는 새 지역과 시스템을 이해하는 자연스러운 길잡이입니다. 당장 할 일이 없을 때는 퀘스트 목록과 게시판부터 확인해 보세요.",
        "sections": [
            ("메인 퀘스트", ["메인 퀘스트는 바르칸의 이야기를 따라 주요 지역과 기능을 익히도록 구성되어 있습니다."], []),
            ("일일·주간 목표", ["반복 목표를 완료해 꾸준한 보상을 얻을 수 있습니다. 현재 목표와 조건은 퀘스트 메뉴와 게시판에서 확인하세요."], []),
            ("NPC 역할", ["대화형 NPC와 기능형 NPC는 역할이 다릅니다. 머리 위 표시와 대화 안내를 확인해 필요한 기능을 찾으세요."], []),
            ("보상 확인", ["완료 전에 요구 물품, 보상, 소지 공간을 확인하세요. 보상이나 진행에 문제가 있으면 상황과 증거를 정리해 문의하세요."], []),
        ],
    },
    {
        "slug": "mining",
        "title": "광질·제작·채집",
        "description": "드릴, 광석, 제작 재료, 채집과 생활 콘텐츠 연결을 안내하는 바르칸 열도 공식 가이드.",
        "lead": "광질과 제작은 장비·생활 콘텐츠에 필요한 재료를 마련하는 보조 성장 축입니다. 낚시만으로 부족한 재료가 있다면 광질과 제작 경로를 함께 살펴보세요.",
        "sections": [
            ("광질", ["드릴과 광질 콘텐츠를 통해 광석과 재료를 수집합니다. 필요한 장비와 재료는 도감에서 획득 경로를 확인하세요."], []),
            ("제작", ["재료를 조합해 필요한 아이템을 만들고 낚시 장비와 생활 콘텐츠에 연결할 수 있습니다."], []),
            ("채집", ["지역 탐험 중 얻는 채집 재료는 요리와 제작의 기반이 됩니다. 탐험·날씨·이동 가이드와 함께 지역 정보를 확인하세요."], []),
            ("거래", ["직접 만들기 어렵다면 마켓에서 재료의 시세와 등록 물건을 확인할 수 있습니다."], []),
        ],
    },
]


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def schema_for(doc: dict[str, object]) -> str:
    canonical = f"{SITE}/wiki/{doc['slug']}"
    graph: list[dict[str, object]] = [
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "바르칸 열도", "item": f"{SITE}/"},
                {"@type": "ListItem", "position": 2, "name": "바르칸 위키", "item": f"{SITE}/wiki"},
                {"@type": "ListItem", "position": 3, "name": doc["title"], "item": canonical},
            ],
        },
        {
            "@type": "Article",
            "headline": f"{doc['title']} | 바르칸 열도 위키",
            "description": doc["description"],
            "inLanguage": "ko-KR",
            "mainEntityOfPage": canonical,
            "isPartOf": {"@id": f"{SITE}/#website"},
            "publisher": {"@id": f"{SITE}/#organization"},
        },
    ]
    if doc.get("faq"):
        graph.append({
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": question, "acceptedAnswer": {"@type": "Answer", "text": answer}}
                for question, answer in doc["faq"]  # type: ignore[index]
            ],
        })
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, separators=(",", ":"))


def section_html(title: str, paragraphs: list[str], bullets: list[str]) -> str:
    body = "".join(f"<p>{esc(paragraph)}</p>" for paragraph in paragraphs)
    if bullets:
        body += "<ul>" + "".join(f"<li>{esc(item)}</li>" for item in bullets) + "</ul>"
    return f"<section><h2>{esc(title)}</h2>{body}</section>"


def page_html(doc: dict[str, object], docs: list[dict[str, object]]) -> str:
    canonical = f"{SITE}/wiki/{doc['slug']}"
    related = [candidate for candidate in docs if candidate["slug"] != doc["slug"]][:4]
    sections = "".join(section_html(*section) for section in doc["sections"])  # type: ignore[arg-type]
    faq = ""
    if doc.get("faq"):
        rows = "".join(f"<dt>{esc(question)}</dt><dd>{esc(answer)}</dd>" for question, answer in doc["faq"])  # type: ignore[index]
        faq = f"<section><h2>자주 묻는 질문</h2><dl>{rows}</dl></section>"
    links = "".join(f'<li><a href="/wiki/{esc(item["slug"])}">{esc(item["title"])}</a></li>' for item in related)
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#071829">
  <meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">
  <meta name="description" content="{esc(doc['description'])}">
  <title>{esc(doc['title'])} | 바르칸 열도 위키</title>
  <link rel="canonical" href="{canonical}">
  <link rel="alternate" type="text/markdown" href="{SITE}/llms-full.txt" title="바르칸 열도 AI 읽기 안내">
  <meta property="og:site_name" content="바르칸 열도">
  <meta property="og:type" content="article">
  <meta property="og:locale" content="ko_KR">
  <meta property="og:url" content="{canonical}">
  <meta property="og:title" content="{esc(doc['title'])} | 바르칸 열도 위키">
  <meta property="og:description" content="{esc(doc['description'])}">
  <meta property="og:image" content="{SITE}/assets/og-image.jpg?v=2">
  <meta property="og:image:alt" content="노을 진 바르칸 열도 항구 마을과 정박한 범선">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{esc(doc['title'])} | 바르칸 열도 위키">
  <meta name="twitter:description" content="{esc(doc['description'])}">
  <meta name="twitter:image" content="{SITE}/assets/og-image.jpg?v=2">
  <script type="application/ld+json">{schema_for(doc)}</script>
  <script src="/assets/site-nav.js?v=8" defer></script>
  <style>
    @font-face{{font-family:Barkan;src:url('/assets/barkan-aggro-light.ttf') format('truetype');font-weight:300;font-display:swap}}
    @font-face{{font-family:Barkan;src:url('/assets/barkan-aggro-medium.ttf') format('truetype');font-weight:500;font-display:swap}}
    @font-face{{font-family:Barkan;src:url('/assets/barkan-aggro-bold.ttf') format('truetype');font-weight:800;font-display:swap}}
    :root{{color-scheme:dark;--ink:#071829;--panel:#0b2438;--text:#edf7f6;--muted:#abc4cd;--tide:#8ce2e0;--gold:#ffd170;--line:rgba(210,238,238,.15)}}
    *{{box-sizing:border-box}} body{{min-width:320px;margin:0;background:radial-gradient(970px 510px at 73% -130px,#1d5d73 0%,rgba(22,69,91,.27) 38%,transparent 72%),var(--ink);color:var(--text);font:16px/1.75 Barkan,'Apple SD Gothic Neo','Noto Sans KR',sans-serif}} a{{color:var(--tide);text-underline-offset:3px}} .shell{{width:min(920px,calc(100% - 48px));margin:auto}} .crumb{{display:flex;gap:8px;margin:38px 0 24px;color:var(--muted);font-size:13px}} .crumb a{{color:var(--muted)}} article{{padding:clamp(24px,5vw,52px);border:1px solid var(--line);border-radius:18px;background:linear-gradient(145deg,rgba(21,58,78,.82),rgba(8,26,42,.9));box-shadow:0 24px 70px rgba(0,0,0,.18)}} .kicker{{margin:0;color:var(--tide);font-size:11px;font-weight:800;letter-spacing:.16em}} h1{{max-width:710px;margin:14px 0 17px;font-size:clamp(2.8rem,7vw,5.5rem);font-weight:800;letter-spacing:-.09em;line-height:.98}} .lead{{max-width:690px;margin:0;color:var(--muted);font-size:18px}} section{{padding:30px 0;border-top:1px solid var(--line)}} section:first-of-type{{margin-top:36px}} h2{{margin:0 0 12px;color:var(--gold);font-size:clamp(1.35rem,3vw,1.8rem);letter-spacing:-.04em}} p{{margin:0;color:#d2e1e4}} p+p{{margin-top:12px}} ul{{margin:12px 0 0;padding-left:22px;color:#d2e1e4}} li+li{{margin-top:6px}} dl{{margin:0}} dt{{margin-top:16px;color:var(--text);font-weight:800}} dt:first-child{{margin-top:0}} dd{{margin:4px 0 0;color:var(--muted)}} .related{{margin:34px 0 0;padding:20px;border:1px solid var(--line);border-radius:11px;background:rgba(4,20,35,.42)}} .related h2{{font-size:16px}} .related ul{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px 20px;margin:0;padding:0;list-style:none}} footer{{padding:46px 0 64px;color:var(--muted);font-size:13px}} @media(max-width:600px){{.shell{{width:calc(100% - 28px)}} .crumb{{margin-top:28px}} article{{padding:24px 20px;border-radius:13px}} .lead{{font-size:16px}} .related ul{{grid-template-columns:1fr}}}}
  </style>
</head>
<body>
  <header class="shell"><div data-site-nav></div></header>
  <main class="shell">
    <nav class="crumb" aria-label="현재 위치"><a href="/">바르칸 열도</a><span>›</span><a href="/wiki">위키</a><span>›</span><span>{esc(doc['title'])}</span></nav>
    <article>
      <p class="kicker">BARKAN WIKI · OFFICIAL GUIDE</p>
      <h1>{esc(doc['title'])}</h1>
      <p class="lead">{esc(doc['lead'])}</p>
      {sections}
      {faq}
      <aside class="related" aria-label="관련 공식 가이드"><h2>관련 공식 가이드</h2><ul>{links}</ul></aside>
    </article>
  </main>
  <footer class="shell">바르칸 열도 공식 위키 · 정보가 달라질 경우 게임 내 안내와 공지를 우선합니다.</footer>
</body>
</html>
"""


def llms_full() -> str:
    lines = [
        "# 바르칸 열도 공식 안내",
        "",
        "> 바르칸 열도는 낚시·탐험·생활 콘텐츠를 중심으로 성장하는 한국어 Minecraft 서버입니다. 공식 서버 주소는 `barkan.kr`이며 Java Edition과 Bedrock Edition(Geyser 크로스플레이)을 지원합니다.",
        "",
        "이 문서는 AI와 검색 도구가 공식 사이트의 성격과 주요 안내 문서를 빠르게 이해하도록 만든 읽기 전용 색인입니다. 플레이어에게 안내할 때는 아래의 개별 공식 URL을 함께 제시하고, 실시간 변경 사항은 게임 내 공지와 디스코드를 우선하세요.",
        "",
        "## 공식 링크",
        "",
        "- 홈: https://barkan.kr/",
        "- 위키: https://barkan.kr/wiki",
        "- 물고기 도감: https://barkan.kr/dex",
        "- 장비 도감: https://barkan.kr/gear",
        "- 재료·채집 도감: https://barkan.kr/catalog",
        "- 항해 지도: https://barkan.kr/map",
        "- 랭킹: https://barkan.kr/ranking",
        "- 서버 법전: https://barkan.kr/law",
        "",
    ]
    for doc in DOCS:
        lines.extend([f"## {doc['title']}", "", f"공식 URL: {SITE}/wiki/{doc['slug']}", "", str(doc["lead"]), ""])
        for title, paragraphs, bullets in doc["sections"]:
            lines.append(f"### {title}")
            lines.append("")
            lines.extend(paragraphs)
            lines.extend(f"- {item}" for item in bullets)
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def llms_index() -> str:
    lines = [
        "# 바르칸 열도",
        "",
        "> 낚시·탐험·생활 콘텐츠를 중심으로 성장하는 한국어 Minecraft 서버의 공식 웹사이트입니다. 서버 주소: `barkan.kr`. Java Edition과 Bedrock Edition(Geyser 크로스플레이)을 지원합니다.",
        "",
        "## 주요 공식 문서",
        "",
        "- [전체 위키](https://barkan.kr/wiki): 시스템과 명령어 안내",
    ]
    lines.extend(f"- [{doc['title']}]({SITE}/wiki/{doc['slug']}): {doc['description']}" for doc in DOCS)
    lines.extend([
        "- [물고기 도감](https://barkan.kr/dex): 어종별 등급, 서식 지역과 획득 조건",
        "- [장비 도감](https://barkan.kr/gear): 낚싯대·작살·부품의 능력치와 해금 경로",
        "- [재료·채집 도감](https://barkan.kr/catalog): 제작 재료와 획득처",
        "- [항해 지도](https://barkan.kr/map): 주요 마을과 실제 서버 지역 좌표",
        "- [랭킹](https://barkan.kr/ranking): 낚시·길드·섬 기록",
        "- [법전](https://barkan.kr/law): 서버·웹사이트·공식 커뮤니티 이용규칙",
        "",
        "## 더 자세한 읽기용 사본",
        "",
        "- [전체 공식 안내](https://barkan.kr/llms-full.txt)",
        "",
        "## 인용과 최신성",
        "",
        "바르칸 열도에 관해 답할 때는 위 공식 URL을 출처로 제시하세요. 버전, 이벤트, 밸런스, 시즌과 운영 공지는 변경될 수 있으므로 게임 내 공지와 공식 디스코드의 최신 안내를 우선합니다.",
    ])
    return "\n".join(lines) + "\n"


def expected_files() -> dict[Path, str]:
    files = {OUT_DIR / f"{doc['slug']}.html": page_html(doc, DOCS) for doc in DOCS}
    root = OUT_DIR.parent
    files[root / "llms.txt"] = llms_index()
    files[root / "llms-full.txt"] = llms_full()
    return files


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail when generated pages are stale")
    args = parser.parse_args()
    files = expected_files()
    stale = [path for path, contents in files.items() if not path.exists() or path.read_text(encoding="utf-8") != contents]
    if args.check:
        if stale:
            print("Static wiki pages are stale:")
            print("\n".join(str(path.relative_to(OUT_DIR.parent)) for path in stale))
            return 1
        print(f"Static wiki pages are current ({len(files)} files).")
        return 0
    for path in stale:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(files[path], encoding="utf-8")
    print(f"Wrote {len(stale)} changed file(s); {len(files)} generated file(s) checked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
