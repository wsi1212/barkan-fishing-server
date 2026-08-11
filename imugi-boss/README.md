# 이무기 보스 — 변환 파이프라인 + 애니메이션

블록 빌드 → 마디별 RP 모델(ItemDisplay) → BlockShip `boss/` 체인 애니메이션.

## ★렌더 레시피 (실측 2026-07-06 — 어기면 크기/방향 어긋남)
클라(1.21.4+)는 item_display의 아이템 모델을 **Y180° 회전 + 대형 모델(스팬 48유닛) 2/3 축소**로 렌더한다.
- 스폰 scale = **리그 k × 1.5** (`imugi_rig.json`의 `render_scale_multiplier`=1.5. ★정정: 초기 '0.5×→×2'는 오측 — 33% 과대였음)
- left_rotation = **목표방향 쿼터니언 × Y180** (`[0,1,0,0]`)
- k는 bake에서 최장축 스팬이 정확히 48유닛 되게 exact 값(k=최대반경×2/3, 반올림 금지)
- 부속 디스플레이(엔더체스트 눈)도 동일 배율
- ★크기 측정은 나디르 탑다운 + 같은 깊이 나란히 비교로만 (광각 가장자리 왜곡이 1.5×+ 부풀림)

## 파일
- `convert_straight.py` — **직선판→z밴드 13마디** 모델/리그 bake + 인라인 diff=0 검증 (애니메이션 정식 경로)
- `convert_imugi.py` — 감긴 원본→측지거리 마디 (동상용) + spawn_commands.txt(tag imugi_test)
- `vanilla_geom.py` — 1.20.1 클라 jar blockstate/model에서 기하 파생 (손코딩 금지)
- `verify_imugi.py` — 독립 역변환 대조 (내부 밀폐블록 컬링 면제)
- `imugi_rig.json`(감긴)/`imugi_s_rig.json`(직선) — 마디 pivot/scale/item_model. 플러그인 데이터로 복사: `plugins/BlockShip/imugi_rig.json` (부팅 캐시 — 교체 후 재시작)
- `straight_imugi_blocks.json` — 직선판 설치 기록(=소스, blockstate 포함)
- `imugi_scan.json` + `imugi_states.json` — 감긴 원본 765블록 (★hyphae axis 포함 — 결방향)

## 플러그인 (blockship `boss/`)
OP `/이무기 소환 [월드 x y z [반경]] | 수영 | 잠수루프 | 정지 | 제거 | 정보`
- 소환 = **정지(레스트 포즈)** + 기존 보스 자동 교체. 수영/잠수루프로 애니 시작
- 체인: 머리 경로 + 위치 히스토리 팔로우(관절거리), 2틱 갱신 = teleport/interpolation, 접선 ±0.9 스무딩, 잠수경로 Chaikin
- ★마디 모델은 직선 레스트 포즈에서만 bake (코일 포즈 = 체인에서 뒤엉킴, 실패 사례 있음)
- 보스 persistent=false (재시작에 안 남음) + PDC 고아 sweep
- dev 호수: flatroom (150, 수면 -60, -100) r14 — 그 구역 forceload 유지 중

## dev 실소환 마무리 순서
현재 정식 테스트 기준은 감긴 리그 `imugi_rig.json`과 `barkan:imugi/seg_00..08`이다.

1. 필요할 때만 `python3 convert_imugi.py` 실행 후 `python3 verify_imugi.py`에서 diff=0 확인.
2. 리그를 dev 데이터 폴더에 복사: `imugi-boss/imugi_rig.json` → `~/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip/imugi_rig.json`.
3. BlockShip 빌드·dev jar 배포·서버 재시작: `~/deploy-dev.sh`.
4. 리소스팩 재빌드: `cd ~/development/barkan-resourcepack && zip -rq "$HOME/Library/Application Support/minecraft/resourcepacks/barkan-resourcepack.zip" assets pack.mcmeta -x "*.DS_Store"`.
5. 클라이언트에서 F3+T 후 `spawn_commands.txt` 순서대로 dev 호수 주변 9청크를 forceload하고 `/이무기 소환 flatroom 150 -60 -100 14` → `/이무기 정보` → `/이무기 수영`을 실행. 유영/잠수 완료 후 forceload를 반드시 해제한다.

직선 `imugi_s` 리그는 별도 비교용 산출물이며, 이 정식 소환 테스트에는 복사하지 않는다.
