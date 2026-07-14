# 카지노 폴리시 2차 — 실행 계획서 (Sonnet 위임용)

> 2026-07-13 작성. 유저 요청 8건. 각 항목에 **원인 코드 위치를 이미 특정**해뒀으니
> 탐색부터 다시 하지 말고 아래 앵커에서 시작할 것. 소스 루트:
> `/Users/user/development/blockship-plugin/src/main/java/com/blockship/casino/`
> RP: `~/development/barkan-resourcepack/` · 스크립트: 이 repo `casino-tools/`

---

## 공통 규약 (위반 금지)

1. **병렬 세션 WIP 주의**: blockship 트리에 다른 세션 미커밋 변경이 수십 파일 있음.
   **내가 만진 파일만 `git add <파일>` 단위로 커밋**. `git add -A` 금지.
   jar는 통째 빌드라 배포 시 트리 전체가 나감 — 배포 직전 `git status` 확인하고,
   타 세션 WIP가 컴파일 깨져 있으면 유저에게 보고(내 커밋만으로 빌드 불가).
2. **prod 배포 순서**: `sudo systemctl stop mcserver` → jar `scp` → `start`.
   (실행 중 jar 덮어쓰기/plugman reload 절대 금지 — CNFE 부분 고장.)
   SSH: `ssh -i ~/.ssh/oracle-mc.key ubuntu@134.185.113.25`, jar 목적지
   `~/mcserver/plugins/BlockShip-1.0.0-SNAPSHOT.jar`.
3. **`~/deploy-blockship.sh` 사용 금지** — jar 외 JSON 6종을 dev→prod로 덮어써
   prod측 편집을 클로버함. jar만 수동 scp.
4. **재시작은 모아서 한 번**: jar + RP + casino-tables.json 수정을 전부 끝낸 뒤
   재시작 1회에 태움. 재시작 전 유저에게 물어볼 것(접속자 0명/wsi1212 혼자면 즉시 가능).
5. **RP 배포**: 텍스처 수정 후 `~/deploy-rp.sh` (zip→GitHub release→prod sha1 갱신).
   클라 적용은 서버 재시작 후 재접속+RP 재다운.
6. **§l/&l 볼드 금지**(전역 훅이 차단), OP 명령에 영타 별칭 금지.
7. **PIL**: 시스템 python3에 PIL 없음. `python3 -m venv <scratchpad>/ptenv &&
   pip install Pillow` 후 그 venv python으로 생성기 실행.
8. **검증**: GUI/물리버튼은 봇 클릭 desync — 봇은 `/카지노 액션 <토큰>` 채팅 명령
   경로(TableInputService.sendClickableLine의 백업 경로)로 테스트. 육안 확인은 유저 몫.
9. dev 먼저 배포·확인(`~/deploy-dev.sh`), prod는 유저 승인 또는 혼자일 때.

---

## 작업 1 — 좌석 위치 교정 (모든 게임)

**현상**: 착석 위치가 물리 테이블 의자와 어긋남.
**구조**: 좌석 = prod `~/mcserver/plugins/BlockShip/casino-tables.json`의 `seats[]`
(Spot x/y/z/yaw). 착석은 `TableSeatService`가 그 좌표에 투명 ArmorStand + CE
bar_stool 의자를 스폰해 태움 — 즉 **JSON 좌표가 곧 앉는 자리**. yaw 의미는
"그 자리에서 테이블 중앙을 바라보는 방향"(TableDef.java:27).

**절차**:
1. prod JSON을 scp로 내려받아 테이블 7개(홀덤2·섯다2·블랙잭3·쓰리카드2·룰렛1·슬롯 제외
   — 실제 목록은 JSON이 권위)의 seats 좌표 덤프.
2. MCP(`mc_inspect_volume`, prod 터널 25599)로 각 테이블 주변 실물(의자/테이블 블록)
   스캔. **측량 범위 = 게임 지역 "카지노"(regions.json 등록, world):
   x −479~−424, y 37~51, z 227~262 (box)** — 이 박스 안만 보면 됨. 실물 층은
   y 40~42 부근. forceload 되어 있음(-478 227 ~ -424 262).
3. 각 좌석을 **실물 의자 블록 중심(x.5, z.5) 위**로 스냅, y는 기존 값 유지,
   yaw = 좌석→테이블 중앙 벡터의 yaw(계산: `yaw = atan2(-(dx), dz)` in degrees).
4. 의자가 없는 테이블(맨바닥 착석)은 테이블 가장자리에서 0.7~1.0블록 떨어진 지점에
   균등 배치.
5. 수정한 JSON을 prod에 다시 scp. **부팅 시 로드라 재시작 필요** — 최종 재시작에 묶기.
   dev에도 동일 파일이 있으면(경로: dev `plugins/BlockShip/casino-tables.json`) 함께.

**검증**: 재시작 후 봇 `/카지노 참가 <id>` → `mc_player_position`으로 봇 위치가
의자 좌표와 일치하는지. 시선 방향은 유저 육안.

---

## 작업 2 — 카드가 플레이어 반대(180°)를 봄

**원인 위치**: `CardDisplayService.flatRotation(yaw)` (CardDisplayService.java:87-91)
`rotationY(-yaw)·rotateX(-90)`. 호출부는 좌석 yaw를 그대로 전달
(PokerTableRuntime.java:511→526·529, HouseTableRuntime도 동일 패턴).
좌석 yaw = 테이블 중앙을 보는 방향인데, 이 조합에서 카드 글자 상단이 플레이어
쪽을 향해(= 앉은 사람 눈엔 상하 뒤집힘) 보이는 상태.

**수정**: `flatRotation` 한 곳만 고치면 홀카드·보드·플립 전부 일괄 수정됨:
`rotationY(-yaw)` → `rotationY((float) Math.toRadians(-yaw + 180))` 형태로 180° 보정.
**단, 부호/오프셋은 반드시 실측으로 확정**: dev에서 좌석 하나에 봇 앉히고 카드 스폰
→ `mc_screenshot`(dev 렌더)으로 글자 방향 확인 → 180 또는 -yaw 부호 반전 중 맞는 쪽 적용.
추측으로 두 번 뒤집지 말 것(과거 룰렛 마커에서 이 실수 반복됨).
보드 카드(boardYaw, PokerTableRuntime.java:773)와 딜링 애니(deal의 +140f 비틀기,
CardDisplayService.java:121)도 같은 함수 경유라 자동 반영 — 스크린샷으로 같이 확인.

---

## 작업 3 — 바이인 개념 삭제 (홀덤·섯다)

**현행**: `TableGameManager.join` L156-166 — `bank.buyIn(p, 100만)` 즉시 차감,
스택 = 바이인 고정(`PokerTableRuntime.HOLDEM_BUYIN/SEOTDA_BUYIN` L47-48,
`buyInAmount()` L99, `addPlayer(seat, p, buyIn)` L115). 하차 시 `TableBank.cashOut`.

**목표 모델(하우스 게임과 동일한 즉시순액정산)**:
- 착석 시 차감 없음. **핸드 시작 시점 스택 = 지갑 잔액 스냅샷**(1만 단위 내림 권장).
- 핸드 종료 시 `CasinoLedger.applyNet(playerId, name, 종료스택 − 시작스택)`.
  (CasinoLedger.java:235/246. `snapshotStack`/`settleStack` L150/L185가 이미 있음 —
  용도 확인 후 재사용 가능하면 그쪽 우선.)
- 핸드 사이마다 스택 재스냅샷(밖에서 돈 벌면 다음 핸드에 반영).
- 참가 최소 자격: 홀덤 BB(1만)·섯다 앤티(1만) 이상. 핸드 시작 때 미달 좌석은 sit-out.
- `TableBank` 의존 제거(클래스는 남겨도 됨 — 다른 참조 grep 확인).
- **문구 정리**: CasinoHubGui.java blurb "바이인 100만" 줄과 참가 버튼 lore
  "바이인이 소지금에서 빠집니다"(L84-87 부근), join 메시지 "바이인 …원",
  **CasinoRuleBook.java HOLDEM 페이지 "바이인 100만" 줄** — 전부 새 모델로 수정.
- 주의: 홀덤 엔진은 핸드 중 스택 권위를 자기(HoldemTableEngine)가 가짐 — 시작
  스냅샷만 바꾸면 엔진은 무수정. 정산 지점은 PokerTableRuntime의 HandEnded 처리부.

**검증**: 봇 2명 dev에서 홀덤 1핸드 — 시작 전/후 `moneyoffline` 잔액 비교로
net만 반영됐는지, 중도 퇴장(스핀 중 하차 아님)·서버 shutdown 경로도 잔액 보존 확인.

---

## 작업 4 — "올인이 전 재산의 1/4" 원인 제거 (블랙잭·쓰리카드)

**원인(확정)**: `HouseTableRuntime.maxBet` L101-105 = `잔액 / reserveMultiplier()`,
`reserveMultiplier()` L96 = 블랙잭 4(더블+스플릿 최악 4×), 쓰리카드 2(Play 1×).
즉 올인 버튼(L276 `next = max`)이 잔액/4로 캡 → 유저가 본 "전재산 1/4".

**수정**: `maxBet = 잔액`(1만 단위 내림)으로 변경하고, 최악 케이스 선확인 대신
**액션 시점 지불능력 검사**로 전환:
- `lockBets` L219의 `need = bet × mult` → `need = bet`.
- 블랙잭 더블/스플릿 버튼 노출부(L357-360)와 액션 처리부에서
  `ledger.canAfford(p, 추가필요액)` 미충족 시 버튼 숨김+액션 거부.
- 쓰리카드 "플레이"(L362, +ante 추가)도 동일하게 canAfford 검사.
- 정산은 이미 net 방식이라 나머지 무수정. actionbar의 "최대 필요 …" 문구(L288)도 정리.
- 홀덤/섯다의 올인은 작업 3 완료 시 자연히 "전 재산"이 됨(스택=지갑).

**검증**: 봇 잔액 40만 세팅 → 블랙잭 올인 → 베팅 40만 확인. 더블 불가(잔액 0) 상태에서
더블 버튼 안 뜨는지 `/chatlog`로 확인.

---

## 작업 5 — 자기 족보 실시간 표시

**목표**: 자기 차례/카드 변동 때 내 패의 족보를 본인에게만 표시(actionbar 권장 —
좌석 라벨은 공개라 부적합).

- **홀덤**: 홀 2장 + 공개 보드로 현재 최고 족보. `PokerHandEvaluator` 사용
  (5장 미만인 프리플랍은 "원페어 K" / "하이카드 A" 수준의 간이 표기 — evaluator가
  5장 미만을 못 받으면 직접 분기). 표시 시점: 홀카드 수령 직후 + 각 스트리트 공개 시
  + 턴 프롬프트 시. 구현 위치: PokerTableRuntime — StreetDealt/턴 프롬프트 처리부에
  `sendActionBar(p, "§7내 패: §f" + 족보명)` 헬퍼 추가.
- **섯다**: 2장 확정 시 `SeotdaRules.evaluate(...).displayName()` ("8땡", "갑오" 등).
  섯다는 이것만으로 완결 — 매 베팅 턴 프롬프트에 같이 붙임.
- **쓰리카드**: 3장 수령 시 `ThreeCardPokerRules.evaluate(...).category().displayName()`.
- **블랙잭**: 족보 대신 합계("17", "소프트 17", "블랙잭!") — 히트/더블 후마다 갱신.
  기존에 합계 표시가 이미 있는지 확인 후 없으면 추가.

**주의**: 남의 족보가 새면 안 됨 — 반드시 해당 플레이어 1명에게만 actionbar.
쇼다운 공개는 기존 로직 그대로.

---

## 작업 6 — 트럼프 6·9 밑줄

**위치**: 생성기 `casino-tools/gen_cards.py`(이 repo), 산출물
RP `assets/minecraft/textures/item/card/{s,h,d,c}_{6,9}.png` (8장).
**수정**: 랭크 글자 렌더 함수에서 rank가 "6"/"9"일 때 글자 폭만큼 밑줄 1획 추가
(글자 baseline 아래 2~3px, 글자색 동일, 코너 인덱스 두 곳 모두).
중앙 대형 랭크(있다면)도 동일 처리. 재생성은 **트럼프만** — 화투는 작업 8과 충돌
방지 위해 이 단계에서 건드리지 않기(생성기가 전체 재생성만 지원하면 작업 8과 묶어서
한 번에 실행). 완료 후 RP 배포(공통 규약 5).

---

## 작업 7 — 슬롯 GUI 심볼을 배당표 아트로 교체

**소스 이미지**: `~/Downloads/ChatGPT Image 2026년 7월 13일 오후 06_12_20.png`
(1024×1536, RP `assets/barkan/textures/painting/slot_paytable.png`와 동일본).
"같은 그림 3개" 섹션 각 행의 첫 심볼을 크롭: 체리/레몬/종/BAR/다이아/7 — 6종.

**절차**:
1. PIL로 각 심볼 셀 크롭(행 위치는 이미지 열어 육안 좌표 확인, 심볼당 ~130px).
   배경(짙은 초록 펠트)은 남겨도 GUI에서 자연스러우면 OK — 어색하면 원형/사각
   타일로 다듬기. 128×128로 리사이즈.
2. RP에 아이템 텍스처·모델 등록: 기존 카드 패턴 참조
   (`assets/barkan/items/card/*.json` + `assets/barkan/models/card/*.json` +
   텍스처는 `assets/minecraft/textures/item/` 아래 — **경로 전부 소문자**).
   네이밍: `barkan:slot/sym_cherry` 등 6종.
3. 슬롯 GUI 릴 아이템 교체: `CasinoManager.java` — 릴 심볼→ItemStack 매핑부를 grep
   (`Symbol` enum 스위치로 Material 만드는 곳). PAPER+`setItemModel(barkan:slot/sym_*)`
   로 교체(카드 아이템 생성부 CardDisplayService.cardItem 패턴 복사).
4. 배당표 GUI/판정 메시지에 심볼 아이콘 쓰는 곳 있으면 같이 교체.

**주의**: `item/generated` 텍스처는 `minecraft:item/` 네임스페이스 아래 있어야
아틀라스에 탐(메모리: RP 커스텀 아이템 텍스처=item/ 아틀라스). 새 텍스처 추가 후
클라에서 Missing texture면 이 규칙 위반 1순위 의심.

---

## 작업 8 — 화투 텍스처 리얼리티 개선

**대상**: 14장 — `hw_1`~`hw_10`(각 월 일반패), `hw_1g`/`hw_3g`/`hw_8g`(광),
`hw_back`. 생성기 `casino-tools/gen_cards.py` 화투 섹션.
(모델 id 규약: CardDisplayService.modelOf → `hw_<월>` / `hw_<월>g`.)

**실제 화투 도상(이대로 그릴 것)** — 배경 흰색(약간 아이보리), 테두리 검정 두껍게,
모서리 라운드, 뒷면은 무광 빨강 단색+가는 검정 테:
- 1월 송학: 소나무(진초록 붓터치)+빨간 해(광: 학 추가, "光" 글자)
- 2월 매조: 매화 가지(분홍 꽃)+꾀꼬리(노랑 새)
- 3월 벚꽃: 벚꽃 만개(연분홍)+(광: 붉은 장막(만막) 커튼, "光")
- 4월 흑싸리: 등나무 덩굴 늘어짐(검보라)+작은 새
- 5월 난초: 붓꽃(보라)+수로 다리(야츠하시)
- 6월 모란: 모란꽃(빨강/분홍 큰 꽃)+나비
- 7월 홍싸리: 싸리 덤불(붉은 기 도는 가지)+멧돼지 없음(일반패는 가지만)
- 8월 공산: 억새 언덕 검은 실루엣+(광: 보름달 크고 노랗게+기러기, "光")
- 9월 국준: 국화(노랑)+술잔
- 10월 단풍: 단풍잎(빨강·주황)+사슴 없음(일반패는 잎만)
- "光" 글자는 광 3장에만, 좌하단 빨간 원 안 흰 글자.

**품질 기준**: 현행보다 해상도 올려도 됨(기존 카드 png 크기 확인 후 2배까지).
붓터치 느낌은 PIL 폴리곤+타원 레이어링으로. 완성본을 유저에게 미리보기 이미지로
보여주고(스테이징 폴더에 몽타주 저장) 승인받은 뒤 RP 배포.
**폴백**: 절차 생성 품질이 안 나오면 중단하고 유저에게 "ChatGPT 이미지 생성으로
14장 시트 뽑아달라"고 요청(배당표 전례 — 유저가 선호하는 경로). 임의로 외부
이미지 다운로드하지 말 것(저작권 — 화투 스캔은 대부분 상표/저작권 있음).

---

## 배포 계획 (전 작업 공통)

1. 작업 2·3·4·5(자바) → 빌드 → **dev 배포**(`~/deploy-dev.sh`) → 봇 검증.
2. 작업 6·7·8(RP) → `~/deploy-rp.sh` (재시작 전 아무 때나).
3. 작업 1(JSON) → dev/prod 파일 준비.
4. 전부 끝나면 **재시작 1회**: 유저에게 물어보고(혼자면 즉시) prod stop→jar+JSON scp→start.
5. 부팅 검증: `Done (`, `Enabling BlockShip`, Exception grep. 카지노 forceload 확인.
6. 커밋: blockship(자바)·scripts(생성기/이 문서)·각각 내 파일만.

## 함정 요약 (과거 사고 재발 방지)

- 카드/휠 방향은 **실측 후 수정** — 블라인드 부호 뒤집기 반복이 최다 마찰 원인.
- ItemDisplay FIXED는 모델 z가 180° 뒤집혀 보이는 사례 있음(룰렛 마커) — 스샷 검증 필수.
- hideEntity/showEntity는 세션 단위 — 재접속 시 재적용 필요(기존 onJoin 패턴 참조).
- 룰렛 "바늘=당첨번호 정렬"은 아직 유저 미검증 상태 — 이번 작업과 무관하게 건드리지 말 것.
- casino-tables.json은 prod측이 권위(딜러 7테이블 등록돼 있음) — dev 파일로 덮지 말 것.
