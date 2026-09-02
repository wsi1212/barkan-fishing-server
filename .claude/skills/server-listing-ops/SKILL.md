---
name: server-listing-ops
description: 마인리스트(minelist.kr) 등 마크 서버 목록 사이트의 운영 작업을 대신 처리한다. "끌어올리기 눌러줘", "서버 끌어올려", "범프 해줘", "마인리스트 인증코드 넣어줘", "MOTD에 인증코드 넣고 재시작", "인증 끝났으니 MOTD 복구해줘", "마인리스트 등록 좀", "베드락도 등록할건데 포트 뭐야" 같은 요청에 쓴다. 인앱 브라우저로 끌어올리기 버튼을 누르고(쿨타임 확인 포함), prod MOTD 에 인증코드를 넣고 재시작·검증·복구까지 한다. 리소스팩·jar 배포는 이 스킬이 아니다(deploy-prod).
---

# 서버 목록 사이트 운영

바르칸 열도의 목록 사이트 등록·유지 작업. **마인리스트 서버 페이지 =
`https://minelist.kr/servers/17441-barkan.kr`** (서버 id `17441-barkan.kr`, 2026-09-01 등록).

## 1. 서버 끌어올리기 — 되묻지 말고 한 번에

"끌어올리기 눌러줘" / "범프" / "서버 끌어올려" 를 들으면 **중간에 아무 것도 묻지 말고** 아래를
끝까지 실행하고 결과만 보고한다. 확인 질문은 유저가 이미 요청한 동작을 두 번 묻는 것이다.

★**버튼이 페이지에 없다.** `관리` 모달 안에 있다. `find` 로 ref 는 잡히지만 화면에 렌더되지
않은 상태라, 모달을 열지 않고 그 ref 를 클릭하면 실패한다. 모달 열기가 1단계다.

```
① navigate  https://minelist.kr/servers/17441-barkan.kr
② find "관리"          → ref 확보  (같은 batch 안의 find 결과는 뒤 항목에서 못 쓴다)
③ browser_batch [ computer:left_click(ref=관리), computer:screenshot ]
④ 스크린샷에서 "서버 끌어올리기" 행을 읽는다
     · "HH:MM부터 다시 가능"  → 쿨타임. 클릭하지 말고 남은 분을 계산해 보고하고 끝.
     · 그 문구가 없으면       → ⑤
⑤ find "서버 끌어올리기" → ref
   browser_batch [ computer:left_click(ref), computer:screenshot ]
⑥ 스크린샷으로 결과 확인(성공 토스트 / 순위 변화) → 보고
```

- 로그인 여부는 ③ 스크린샷 우상단으로 판별된다(`wsi1212` 가 보이면 로그인). 로그인 화면이면
  "패널 열고(Ctrl+]) 로그인해 주세요" 하고 멈춘다.
- 패널이 숨겨져 있으면 `read_page` 가 `(empty page) Viewport: 0x0` 을 낸다. 텍스트는
  `get_page_text` 로 읽히지만 클릭은 패널이 떠 있어야 좌표가 잡힌다.
- ref 를 쓸 것. 좌표는 광고 배너 때문에 레이아웃이 흔들린다. 부득이하면 800×806 기준
  `관리` 는 대략 `(228, 277)` 이었다(2026-09-01).
- 쿨타임 계산은 `date` 로 현재 KST 를 읽어서 뺀다. 모달 문구는 종료 «시각»만 준다.

모달의 다른 항목: `서버 정보 관리` · `Votifier 관리` · `대시보드` · `추천 목록` ·
`서버 피드백 보기` · `서버 인증(MOTD로 서버 관리 권한 인증)`.

## 2. MOTD 인증코드 (신규 목록 사이트 등록)

목록 사이트는 MOTD 에 코드를 넣게 해서 서버 소유를 증명시킨다. 여러 사이트를 **동시에** 인증할
수 있다 — MOTD 두 줄에 하나씩 넣으면 된다.

```bash
# 1) 백업 + 코드 삽입 (prod)
ssh -i ~/.ssh/oracle-mc.key ubuntu@168.107.8.107 python3 - <<'PY'
import io, re, shutil, time
p = "/home/ubuntu/mcserver/server.properties"
shutil.copy2(p, p + ".motd-bak-" + time.strftime("%Y%m%d-%H%M%S"))
src = io.open(p, encoding="utf-8").read()
old = re.search(r"^motd=.*$", src, re.M).group(0)
new = "motd=§b<코드1>\\n§e<코드2>"
io.open(p, "w", encoding="utf-8").write(src.replace(old, new))
print("new:", new)
PY
# 2) 접속자 확인 → 예고 → 재시작
#    python3 scripts/rcon.py list  /  rcon.py "say §e[공지] 30초 후 재시작"
#    sudo systemctl restart mcserver
# 3) 검증: 자바·베드락 양쪽 핑 (아래 스크립트)
```

### ★함정 3개 (전부 2026-09-01 실측)

**① § 색코드를 빼면 안 된다.** 색코드 없는 순수 텍스트 MOTD 는 Paper 가 레거시 컴포넌트로
파싱하지 못해서, Geyser 가 **JSON 문자열째로**(`"코드1\ncode2"` — 따옴표·백슬래시 포함) 베드락
line1 에 밀어넣고 line2 는 Geyser 기본값 `Another Geyser server.` 로 떨어진다. 각 줄 앞에
`§b`/`§e` 같은 색코드를 반드시 붙일 것.

**② 베드락은 두 줄을 따로 실어 보낸다.** UNCONNECTED_PONG 의 `motd-line1`/`motd-line2` 필드에
자바 MOTD 1·2줄이 각각 매핑된다(Geyser `passthrough-motd: true`). 검증기가 **주 MOTD(line1)만**
읽는 경우가 있어서, 마인리스트 베드락 인증은 코드가 line2 에 있을 때 실패했고 line1 로 올리자
통과했다. 실패하면 코드를 1번째 줄로 옮길 것.

**③ 베드락 포트는 19132(UDP)다.** 25565 는 자바 전용 TCP 다. 폼이 25565 로 채워져 있으면
"접속 실패"가 영원히 난다. 주소는 `barkan.kr` 그대로(A레코드 직결이라 SRV 아님 —
"SRV 사용 서버는 25565" 안내는 우리와 무관).

### 검증 스크립트

자바 상태 핑과 베드락 RakNet 핑을 둘 다 봐야 한다. 자바만 보고 통과 판정하면 ②에 걸린다.

```python
# 베드락 (UDP 19132) — line1/line2 를 그대로 뽑는다
import socket, struct, sys
host, port = sys.argv[1], int(sys.argv[2])
MAGIC = bytes.fromhex("00ffff00fefefefefdfdfdfd12345678")
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(5)
s.sendto(b"\x01" + struct.pack(">Q", 0) + MAGIC + struct.pack(">Q", 2), (host, port))
data, _ = s.recvfrom(4096)
body = data[33:]
f = body[2:2 + struct.unpack(">H", body[:2])[0]].decode("utf-8", "replace").split(";")
print("line1=", f[1], "| line2=", f[7] if len(f) > 7 else "")
```

자바는 표준 상태 핑(handshake protocol 772, next-state 1 → status request)으로 `description`
을 받아 코드 문자열이 들어 있는지 본다. 부팅에 20~40초 걸리니 성공까지 5초 간격 재시도.

### 복구

인증이 끝나면 **반드시 원래 문구로 되돌린다.** 백업은 `server.properties.motd-bak-*`.
현재 정상 MOTD:

```
motd=§b              바르칸 열도 §f| §e힐링 낚시 RPG 마인팜 서버\n§7                    ✦ 9월 1일 신규 오픈 ✦
```

가장 오래된 백업이 인증 전 원본이지만 **거기엔 옛 날짜(8월 26일 그랜드 오픈)가 들어 있다** —
복구 후 날짜 문구를 확인할 것.

## 3. 등록 정보 (사이트 폼에 넣는 값)

| 항목 | 값 |
|---|---|
| 자바 주소 | `barkan.kr` (또는 `168.107.8.107`) |
| 자바 포트 | 25565 |
| 베드락 주소 | `barkan.kr` |
| 베드락 포트 | **19132** |
| 최소 클라 버전 | **1.21.10 이상** — 마인리스트 자체 감지값도 `1.21.10 ~ 26.2`. ViaVersion `block-versions: [<1.21.9]` 인데 ServerPing 이 광고하는 이름은 `1.21.10+` 다. 소개글에는 1.21.10 으로 적는다(유저 결정) |
| Votifier 포트 | 8192 (TCP) — 공개키는 `~/mcserver/plugins/VotifierPlus/rsa/public.key` |

★도메인은 무료 서브도메인이라 **갱신 주기를 놓치면 이름만 안 풀린다.** 주소 필드에는 IP 를
직접 넣는 쪽이 안전하다.

## 4. 콘텐츠 수치 (소개글에 쓸 때)

**절대 어림짐작으로 적지 말 것.** prod 라이브 JSON 이 권위다. 2026-09-01 에 유저가 올린
소개글에 `200종이 넘는 NPC`(실제 195) · `500종의 물고기`(실제 470) · `30곳의 낚시 스팟`
(실제 어장 13) 세 곳이 과장돼 있었다.

```bash
ssh -i ~/.ssh/oracle-mc.key ubuntu@168.107.8.107 'cd ~/mcserver/plugins/BlockShip && python3 -c "
import json
print(\"NPC   :\", len(json.load(open(\"npc.json\",encoding=\"utf-8\"))[\"npcs\"]))
f=json.load(open(\"fish.json\",encoding=\"utf-8\"))
print(\"물고기:\", len(f[\"fish\"]), \"/ 어장:\", len(f[\"regions\"]))
print(\"퀘스트:\", len(json.load(open(\"quests.json\",encoding=\"utf-8\"))[\"퀘스트\"]))
print(\"칭호  :\", len(json.load(open(\"titles.json\",encoding=\"utf-8\"))[\"titles\"]))
"'
```

★**어장 ≠ 지역.** `regions.json` 의 지역은 31곳(플레이어 섬 제외)이지만 물고기 분포표가 있는
곳은 `fish.json` 의 13곳뿐이다. 왕도·설산·사막마을 같은 나머지는 마을·던전이라 낚시가 안 된다.
"낚시 스팟 30곳"이라고 쓰면 확인하는 순간 티가 난다.

도박장 게임은 실제로 5종 다 있다 — `casino/` 의 `seotda`·`blackjack`·`holdem`·`roulette`·`slot`.
표기는 **블랙잭**(블랙젝 아님). CraftEngine 가구 정의는 1,133개라 "1000가지가 넘는"은 사실.
