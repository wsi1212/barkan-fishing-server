---
name: npc-skins
description: >-
  마을/지역 NPC에 어울리는 스킨을 NameMC에서 찾아 골라 서버(prod)에 실제로 적용한다.
  "NPC 스킨 찾아줘", "이 NPC들 스킨 바꿔줘", "마을별로 어울리는 스킨 넣어줘",
  "이 NPC 스킨 겹치나 확인해줘" 같은 요청에 쓴다. 핵심은 겹치지 않게(중복 방지) +
  테마-지역 일치(사막 스킨이 유럽마을에 새면 어색함) + 실제 텍스처 해시로 검증
  (NameMC 페이지 id는 텍스처 해시가 아니라 다른 페이지가 같은 텍스처일 수 있음).
  Codex 브라우저 제어(실제 크롬, WebFetch/서버curl은 스킨사이트 403) + 오라클 SSH
  (MineSkin API 해시 검증) + AIBuilder MCP 또는 콘솔 npc skin --url(적용) 3단 파이프라인.
---

# NPC 스킨 소싱 파이프라인

목표는 "적당히 어울리는 스킨을 빠르게 찾기"가 아니라 **겹치지 않는다는 걸 실제로 증명**하는
것. NameMC 인기 태그의 스킨은 이미 우리 서버 어딘가에서 쓰고 있을 확률이 높다(실측: 인기
태그에서 뽑은 후보 4개 중 2개가 기존 NPC와 완전히 같은 텍스처였음). 페이지 id만 보고 "다른
스킨이겠지" 하고 넘어가면 틀린다.

## 0. 사전 조건

- **Codex 브라우저 제어 연결 필수** — WebFetch/서버 curl은 NameMC 등 스킨 사이트에서 403.
  실제 크롬 확장(로그인된 브라우저)만 통과한다. 연결 안 돼 있으면 사용자에게 먼저 확장
  설치+로그인 요청.
- **오라클(prod) SSH 접근** — MineSkin API 해시 검증 + 기존 NPC 해시 추출에 필요.
  `ssh -i ~/.ssh/oracle-mc.key ubuntu@168.107.8.107`. (로컬에서 직접 MineSkin
  호출하면 이것도 막힐 수 있음 — 오라클에서 curl.)
- **적용 도구**: `mcp__minecraft-ai-builder__mc_npc_set_skin`(url 모드) 또는 AIBuilder
  브릿지가 죽었으면 콘솔 `npc skin --url <PNG주소>`(tmux 세션 등 상태 유지되는 sender로).
  **texture+signature 직접 붙여넣기는 절대 금지** — Citizens가 리로드마다 재검증 시도 →
  실패 → skindb.net 랜덤 스티브/알렉스 스킨으로 스왑되는 버그가 있다(왕도 NPC 26명 전원이
  이걸로 날아간 전례 있음). url 모드나 인게임 `/npc skin`만 안전.

## 1. 기존 서버 스킨 해시 전량 추출 (한 번만, 대조 기준선)

```bash
ssh -i ~/.ssh/oracle-mc.key ubuntu@168.107.8.107 'python3 -c "
import re, base64, json
with open(\"/home/ubuntu/mcserver/plugins/Citizens/saves.yml\") as f:
    content = f.read()
raws = re.findall(r\"textureRaw: (\S+)\", content)
hashes = set()
for r in raws:
    try:
        pad = r + \"=\" * (-len(r) % 4)
        data = json.loads(base64.b64decode(pad))
        hashes.add(data[\"textures\"][\"SKIN\"][\"url\"].rsplit(\"/\",1)[-1])
    except Exception:
        pass
print(len(hashes), \"unique hashes\")
for h in sorted(hashes): print(h)
"'
```

이 해시 목록(현재 118개)이 "이미 쓰는 스킨" 기준선이다. 이후 모든 후보를 이 목록과 대조한다.

## 2. NameMC 태그 브라우징 + 콘택트시트 (Codex 브라우저 제어)

한 장 한 장 스킨 페이지를 열어보는 건 느리고, 기본 페이지 렌더는 등각(isometric) 축소판이라
얼굴/색을 오판하기 쉽다(예: 초록 로브인 줄 알았는데 실제론 크리퍼 얼굴 스킨). **정면 풀바디
콘택트시트**로 한 번에 비교한다:

```javascript
// tabId는 tabs_context_mcp로 확보한 것. 태그 페이지 이동 직후 실행.
const links = Array.from(document.querySelectorAll('a[href*="/skin/"]'));
const ids = [...new Set(links.map(a => a.getAttribute('href').split('/skin/')[1]).filter(Boolean))].slice(0,12);
document.body.innerHTML = '<div style="background:#222;padding:10px;display:flex;flex-wrap:wrap;gap:10px;">' +
  ids.map(id => `<div style="text-align:center;color:#fff;font-family:sans-serif;">
    <img src="https://s.namemc.com/3d/skin/body.png?id=${id}&scale=5&width=150&height=300" style="background:#333;"/>
    <div>${id}</div></div>`).join('') + '</div>';
ids;
```

`navigate` → 위 JS(`javascript_tool`) → 2초 대기 → `screenshot` 순서로 배치(browser_batch)하면
한 번의 왕복으로 태그당 6~12개를 눈으로 비교할 수 있다.

**태그 고르는 법**: `king`/`noble`/`wizard`/`pirate`/`knight`/`medieval`/`chef`/`arabian`/
`farmer`/`grandma`/`monk`/`villager`가 실전에서 잘 맞았다. **`girl`은 현대/애니풍이라 중세
테마에 안 맞음. `villager`는 바닐라 주민 몹 얼굴이 나온다**(그게 필요한 컨셉이면 오히려 좋음
— 예: 마을 촌장). `sailor`도 애니풍으로 치우칠 수 있으니 확인 후 판단.

**테마-지역 일치 원칙**: 사막(아라비안) 스킨은 사막 마을에만, 유럽풍은 유럽 마을에만 —
잘못 섞이면 몰입이 깨진다는 명시적 피드백이 있었다. 지역 컨셉과 태그를 먼저 맞추고 시작.

## 3. 후보 텍스처 해시 검증 (MineSkin API, 오라클에서)

콘택트시트에서 마음에 드는 id를 골랐으면, **적용 전에 반드시** 실제 텍스처 해시를 뽑아
1단계 기준선과 대조한다:

```bash
ssh -i ~/.ssh/oracle-mc.key ubuntu@168.107.8.107 \
  "curl -s -X POST https://api.mineskin.org/generate/url \
   -H 'Content-Type: application/json' \
   -d '{\"url\":\"https://s.namemc.com/i/<후보ID>.png\",\"variant\":\"classic\"}'" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['hash'])"
```

- 응답의 `hash`가 1단계 기준선 집합에 **있으면 → 중복, 다른 후보로 재시도**.
- **MineSkin은 rate limit이 있다**(연속 호출 시 "request too soon" 에러) — 호출 사이 6~8초
  간격을 둘 것. 실전에서 인기 태그 후보의 절반 가까이가 중복으로 걸렸다 — 여러 개 준비해두고
  하나씩 소거하는 식으로 진행.
- 최종 확정 후보들끼리도 서로 해시가 겹치지 않는지 교차 확인.

## 4. 적용

```
mcp__minecraft-ai-builder__mc_npc_set_skin(citizens_id=<CID>, url="https://s.namemc.com/i/<확정ID>.png")
```
브릿지가 죽었으면 콘솔(상태 유지되는 sender: tmux 세션 등)에서:
```
npc select <CID>
npc skin --url https://s.namemc.com/i/<확정ID>.png
```
적용 후 **재감사** — 1단계 스크립트를 다시 돌려서 해시가 실제로 바뀌었는지, 다른 NPC와
안 겹치는지 최종 확인한다(한 세션에서 no-op처럼 보인 사례가 있었음 — 눈으로 GUI만 보고
끝내지 말 것).

## 5. 이름/역할 배선 체크 (스킨과 별개지만 항상 같이 하게 되는 일)

Citizens 표시명(`npc rename`)과 BlockShip `npc.json`의 name(`npc이름 <id> <표시명>`)이
**색코드까지 완전히 같아야** 우클릭이 반응한다(클릭 핸들러가 이름으로 매칭, CID 아님).
개명 시 항상 둘 다 갱신. 관련 상세는 메모리 `reference_citizens_npc_console_placement`.
