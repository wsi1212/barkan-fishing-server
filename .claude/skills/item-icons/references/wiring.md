# RP·플러그인 연결 — 아이콘을 실제 아이템에 입히기

카지노 카드(`assets/barkan/items/card/*.json`)로 이미 prod 검증된 규약을 그대로 쓴다.
클라 게이트가 1.21.4+라서 `items/` 정의(item_model 컴포넌트) 방식이 전 유저에게 안전.

## 1. 파일 3종 세트 (id당)

`icon-forge/build.py --install`이 자동 생성. 수동으로 만들 때의 정답:

```
# 텍스처 (★ minecraft 네임스페이스 item/ 아래 — 아틀라스 규약, 메모리 교훈)
assets/minecraft/textures/item/barkan_icon/<id>.png
assets/minecraft/textures/item/barkan_icon/<id>.png.mcmeta   # 애니메이션일 때만

# 모델
assets/barkan/models/barkan_icon/<id>.json
{"parent":"minecraft:item/generated","textures":{"layer0":"minecraft:item/barkan_icon/<id>"}}

# 아이템 정의 (item_model 컴포넌트 타깃)
assets/barkan/items/barkan_icon/<id>.json
{"model":{"type":"minecraft:model","model":"barkan:barkan_icon/<id>"}}
```

`.mcmeta` 내용: `{"animation":{"frametime":3}}` — 텍스처 PNG는 16×(16×프레임수) 세로 스트립.

## 2. 플러그인 쪽 (BlockShip)

아이템 스택에 한 줄:

```java
meta.setItemModel(new NamespacedKey("barkan", "barkan_icon/rod_barkan"));
```

- **부품(장비) 롤아웃**: `parts.json` 스펙 문자열에 8번째 필드로 모델 id를 추가하거나
  (`이름|등급|가격|내구|스탯|레벨제한|출처|모델id`), 코드에서 이름→id 슬러그 테이블.
  PartLoader 파싱 + 아이템 생성 지점(EquipmentManager)에 setItemModel 추가.
  ★ jar 변경 = 풀 재시작 필수 → 다른 jar 작업과 모아서(잦은 재시작 금지).
- **GUI 전용(스킬 트리 아이콘 등)**: GUI 아이템 빌더에서 setItemModel만 하면 끝.
  재질(Material) 바꿀 필요 없음 — 정의가 모델을 완전히 덮는다.
- 낚싯대는 실제 FISHING_ROD 아이템이라 내구도 바 등 기존 동작 그대로 유지됨.

## 3. 배포

- **RP만 바뀐 경우 jar 재시작 불필요.** dev: `~/dev-rp-serve.sh` 서빙(127.0.0.1:8801) +
  RP 재빌드 + server.properties sha1 동기화 → 유저는 재접속으로 수신.
  sha1 갱신에 서버 재시작이 필요하면 **몰아서, 물어보고**.
- prod: `~/deploy-rp.sh` (GitHub Release + sha1 + server.properties) — **명시 요청 시에만**.
- 확인: 인게임에서 해당 부품 지급(`/부품상점` 또는 지급 명령) → 인벤토리 열고
  `mc_screenshot`. ★ MCP mc_* 툴은 prod에 붙어있음 주의 — dev 확인은 dev 봇/RCON 경로.

## 4. 함정 모음

- 텍스처를 `assets/barkan/textures/...`에 두면 item/generated가 못 찾는다 —
  반드시 `assets/minecraft/textures/item/` 아래(카드도 이렇게 되어 있음).
- 경로 전부 소문자(★CE 가구 사고와 동일 규칙 — 대문자 1개가 조용히 깨뜨림).
- 반투명 픽셀: GUI는 잘 나오지만 지면 드롭/액자에서 다르게 보일 수 있다 —
  글로우 외 반투명 금지(lint가 감사).
- pack.mcmeta `supported_formats` 이미 [46,99] — 새 포맷 필드 추가 불필요.
