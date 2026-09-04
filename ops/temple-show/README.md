# temple_show — 해저신전 필드보스 후보 전시월드

바다 필드보스가 살 «해저신전» 후보 16개를 하나의 공허 전시월드에 격자로 모았다.
`castle_show`(무료 중세성 15개)와 같은 방식이고, `/월드 temple_show` 로 들어간다.

- **dev·prod 양쪽 반영 완료** (2026-09-04). prod 는 가동 중에 `mv import` 로 넣었다 — 재시작 없음.
- 스폰 `(-24, 64, -24)` 씨렌턴 발판. `/월드` 는 `Bukkit.getWorlds()` 를 훑는 범용 명령이라
  월드만 로드돼 있으면 목록·탭완성·TP 가 자동이다(BarkanWorldWarp.jar 손댈 것 없음).
- 비OP 는 접속 시 스폰마을로 축출된다 — `RegionTracker.PLAYER_WORLDS` 허용목록에 없기 때문(의도).

## 파이프라인 (전부 헤드리스, 서버 재시작 없음)

```bash
python3.12 -m venv venv && ./venv/bin/pip install amulet-core pillow   # Amulet 1.9.45 / py3.12 고정
./fetch.sh dl                      # 원본 내려받기(URL 은 fetch.sh 안에 있다)
unzip / bsdtar 로 ex/<n>/world 로 풀기
./venv/bin/python detect4.py ex/*/world     # 월드형 소스에서 신전 위치 찾기 → boxes.py 에 반영
./venv/bin/python boxes.py                  # boxes.json
cp <castle_show>/level.dat build/temple_show/level.dat   # 공허 flat 제너레이터 템플릿
./venv/bin/python bake.py build/temple_show # 굽기 (16개 / 21초)
./venv/bin/python finalize.py build/temple_show temple_show -24 66 -24
./venv/bin/python render_map.py build/temple_show map.png   # 위에서 본 검수용 지도
cp -R build/temple_show <서버루트>/ && rm <서버루트>/temple_show/session.lock
mv import temple_show normal && mv setspawn temple_show:-24,66,-24
python signs.py plots.json                  # 표지판 명령 생성 → pre / 8초 / post
```

prod 는 tar+scp → `~/mcserver/` 에 풀고 `session.lock`·`uid.dat` 삭제 → 같은 RCON 절차.
**재시작 불필요**(`mv import` 는 가동 중에 먹는다). 실측: 접속자 5명, TPS 20.0 유지, 메모리 변화 없음.

## 함정 (다시 하면 또 밟는다)

- **Amulet 은 대상 레벨을 열어 둔 채 소스 레벨을 열면 세션락을 잃고 `save()` 가 통째로 실패한다.**
  그래서 `bake.py` 는 «소스 열기→볼륨 추출→소스 닫기→대상 열기→붙여넣기→저장→닫기» 를 후보마다 반복한다.
  실패해도 청크는 일부 써져 있어서 «된 것처럼» 보인다 — 마지막 `완료 N개` 줄이 없으면 실패다.
- **가동 중인 서버의 월드를 Amulet 으로 열면 session.lock 때문에 그냥 멈춘다**(에러도 안 난다). 항상 사본에서 작업.
- **물은 전부 공기로 치환한다**(`tlib.STRIP`). 안 그러면 잘라낸 상자 가장자리에서 물이 공허로 쏟아져
  유체 틱이 폭주한다. 미역·켈프·기포기둥도 같이 지운다(물 없으면 즉시 파괴돼 아이템 스팸).
  → 산호는 남겨 뒀으니 죽은 산호로 변한다. 전시용이라 그대로 둠.
- **PMC 컨테스트 맵은 «바닷물» 을 파랑/청록 스테인드글라스+양털로 만든다.** 안 지우면 위에서 봐도
  속에서 봐도 파란 덩어리다 → `manifest.FAKE_SEA` 로 후보별로 지운다(13·17·19).
- **월드형 소스는 어디가 신전인지 자동으로 모른다.** `level.dat` 의 `Data.Player.Pos`(제작자 마지막
  위치)가 1차 힌트지만 빗나가는 게 있다(11번은 마을, 16번은 로비였다) → `detect4.py` 로
  prismarine/sea_lantern/conduit 밀도 최대 청크를 씨앗 삼아 flood-fill 하는 쪽이 정확했다.
- **universal 팔레트 이름은 `oak_leaves` 가 아니라 `leaves[material=oak]` 처럼 «일반명+속성»** 이다.
  자연/인공 분류 정규식을 바닐라 아이디로 쓰면 나무가 전부 «인공» 으로 잡혀 숲을 신전으로 오인한다.
- **★이름표를 text_display 로 만들면 안 된다.** `NpcDialogueManager.sweepOrphanBubbles` 가
  `EntitiesLoad` 마다 «탈것 없는 persistent TextDisplay» 를 **월드 불문 전부** 지운다(말풍선 고아 청소).
  소환 직후엔 멀쩡히 보이다가 청크가 한 번 언로드되면 없어진다 → 블록엔티티인 **표지판**을 쓴다(`signs.py`).
  이 서버에서는 홀로그램류를 세울 수 없다는 뜻이기도 하다.
- **로드 안 된 청크에 `setblock`/`summon` 하면 «성공» 이라 답해 놓고 유실된다.**
  `forceload add` 전부 → **8초 대기** → 명령 → `save-all flush` → `forceload remove all`.
  forceload 는 비동기라 바로 이어서 쏘면 아직 안 올라온 청크에 쓰게 된다(prod 에서 실측).
- 블록엔티티(상자·간판 내용)와 엔티티는 옮기지 않는다. 실루엣/구조 검수용이라 불필요.

## 후보 목록

`plots.json` 이 좌표 권위(그 파일이 `bake.py` 산출물이다). 출처는 `manifest.py`.

| id | 이름 | 크기(W×H×L) | 좌표 | 출처 |
|----|------|------------|------|------|
| 01 | 침몰한 신전 | 166×82×118 | `83 64 59` | Emersion of the Temple / BLUVETRO |
| 02 | 대형 해저신전 | 208×134×208 | `280 64 104` | Ocean Monument / Shadow95 |
| 04 | 제다이 해저신전 | 59×25×58 | `429 64 29` | Ocean Monument Jedi Temple / TheSmelly1998 |
| 05 | 바닐라 해저신전 원형 | 58×31×58 | `509 64 29` | Natural Ocean Temple / HalfastMC |
| 06 | 해저 도시 | 147×50×124 | `633 64 62` | Underwater city / kll |
| 07 | 아틀란티스 로비 | 151×76×151 | `75 64 299` | Mini Atlantis Lobby / Spirit_Blossom |
| 08 | 크라켄 소굴 | 63×85×61 | `191 64 254` | Kraken / pigman404 |
| 09 | 물의 기념비 | 59×29×59 | `269 64 253` | Ocean Monument Schematic |
| 13 | 오션 하트랜드 | 209×168×209 | `424 64 328` | InsaneCraft Ocean Heartlands (FREE) |
| 14 | 해저 성채 로비 | 193×190×190 | `640 64 319` | Underwater Castle Lobby 200x200 |
| 10 | 해저신전 리메이크 | 96×100×112 | `48 64 504` | Ocean Monument Redone / ParryPotter |
| 11 | 반수몰 수중궁전 | 224×101×224 | `224 64 560` | Water Palace (half submerged) / BlocksBuild |
| 16 | 컨듀잇 신전 | 144×62×128 | `424 64 512` | Temple of Conduit / Hipercreative |
| 17 | 아르타잔의 성역 | 160×123×160 | `592 64 528` | Artazan's Realm Guardian Sacred Temple |
| 18 | 씨템플 | 208×179×128 | `104 64 752` | SeaTemple / Barbarian |
| 19 | 시간의 신전 | 192×129×192 | `320 64 784` | Platreon - The Time Temple |

## 가동 중인 월드에 큰 건물을 «렉 없이» 넣기 — region 파일 투하 (2026-09-04)

17번(아르타잔의 성역)은 전시월드 플롯이 산호밭만 잘라 와서 신전이 통째로 빠져 있었다.
전체 복합체(448×125×576, 비어있지 않은 블록 610만)를 다시 떠서 **prod flatroom 5000/100/5000**
에 넣었는데, `//paste` 도 `setblock` 도 쓰지 않았다 — **아직 존재하지 않는 region 파일을 오프라인에서
구워 그냥 떨어뜨렸다.** 서버가 하는 일은 0이다(접속자 5명, TPS 20.0 내내 유지).

```bash
python place17.py            # ex/17/world → build/flatroom_patch/{region,entities}/r.{9,10}.{9,10}.mca
python render_world.py build/flatroom_patch p17.png 4992 4992 5455 5583   # 눈으로 검수
tar czf p.tgz region entities && scp … && tar xzf -C ~/mcserver/flatroom
```

- **전제: 대상 좌표의 region 파일이 없어야 한다.** 있으면 절대 덮지 말 것(서버가 그 청크를 메모리에
  들고 있으면 저장 때 되돌아가고, 최악은 손상이다). `ls region/r.<x>>5>.<z>>5>.mca` 로 먼저 확인하고,
  투하 직전에 **한 번 더** 확인한다(그 사이 누가 다녀갔을 수 있다). place17.py 를 감싼 셸이 실제로 그렇게 한다.
- **평지 지반(bedrock/dirt×2/grass, y-64..-61)을 내가 쓴 청크에 같이 넣어야 한다.** 안 그러면 새 청크는
  status=full 이라 지형이 생성되지 않고 바닥에 460×590 짜리 구멍이 뚫린다.
- 원점은 청크 정렬이 필요하니 서/북으로 패딩해서 4992 에 붙이고 콘텐츠가 5000 에서 시작하게 한다.
- 검수는 청크 몇 개만 `forceload` → `execute unless block … run time query gametime` 으로.
  **`say` 를 쓰지 말 것** — 접속자 전원 채팅에 뜬다(2026-09-04 에 두 줄 뿌렸다).
- 원본 월드 어디가 건물인지는 `render_world.py` 로 **128블록 좌표격자 지도를 뽑아 눈으로 고르는 게**
  밀도 휴리스틱보다 빠르고 정확했다.
