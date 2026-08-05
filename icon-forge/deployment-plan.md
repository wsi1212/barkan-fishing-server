# 낚시 아이템 아이콘 배포 계획

## 범위

- 낚싯대 64종
- 부품 90종: 릴 18, 줄 18, 바늘 18, 미끼 18, 찌 18
- 작살 52종
- 통발 48종: 12지역 × 표준/튼튼/속성/행운
- 총 254종

## 생성 및 검수 게이트

1. `catalog_build.py`가 `BlockShip/parts.json`과 `TrapSpecs.java`를 읽어 고유 ID와 이미지를 생성한다.
2. 이미지 출력은 등급에 따라 E/D/C=64×64, B=128×128, A·특수 통발=256×256, S/G=512×512를 사용한다. 모든 아이콘은 투명 배경 PNG이며, 인벤토리 16×16 슬롯에서 실루엣이 읽혀야 한다.
3. 카테고리별 접촉 시트와 전체 슬롯 미리보기로 낚싯대·작살·통발의 실루엣, 등급 상승, 같은 시리즈 팔레트를 확인한다.
4. Python과 Java의 ID 규칙(UTF-8, NUL 구분, SHA-1 앞 10자리)이 일치하는지 확인한다.
5. 리소스팩의 PNG/model/item 정의 개수가 각각 254개이고 ID 중복이 없어야 한다.

## 적용 순서

### Dev

```bash
cd /Users/user/development/blockship-plugin
~/deploy-dev.sh
```

`deploy-dev.sh`가 빌드 → dev jar 배포 → dev 서버 재시작을 수행한다. 이후 dev 서버의 `25565` 포트와 RCON `25575`에서 `list`를 확인한다.

### Resource pack 및 Prod

```bash
cd /Users/user/development/barkan-resourcepack
~/deploy-rp.sh
ssh -i ~/.ssh/oracle-mc.key ubuntu@168.107.8.107 \
  'sudo systemctl restart mcserver'
```

`deploy-rp.sh`가 ZIP 생성, GitHub 최신 릴리스 교체, SHA-1 갱신을 담당한다. 운영 서버 재시작 뒤 `systemctl is-active mcserver`, `25565` 리스닝, 온라인 플레이어 수, 최신 로그의 예외를 확인한다.

## 런타임 적용

- 신규 아이템 생성 경로는 `ItemIconModel.apply(...)`를 통해 `minecraft:item_model`을 부여한다.
- 기존 보유 아이템은 `ItemIconMigrationListener`가 접속 후 PDC/로어/통발 메타데이터를 기준으로 같은 모델 ID로 보정한다.
- Python 생성기와 Java 런타임이 같은 이름·지역·변형을 사용하므로 재시작 후에도 모델 ID가 바뀌지 않는다.

## 롤백

- 리소스팩 문제가 발생하면 직전 ZIP 릴리스와 직전 SHA-1을 복구한 뒤 prod를 재시작한다.
- Java 문제가 발생하면 `deploy-dev.sh` 이전의 BlockShip jar를 복원하고 dev/prod를 각각 재시작한다.
- 플레이어 데이터와 월드 폴더는 배포 대상에 포함하지 않는다.

## 현재 적용 증거

- 생성기 검증: `254개 / 고유 ID 254개`
- 해상도 검증: `64px 85개 / 128px 54개 / 256px 110개 / 512px 5개`
- 신규 `catalog_*` 세트: PNG 254개, model 254개, item 정의 254개(기존 아이콘 포함 디렉터리 전체는 545개)
- Dev: `25565`, `25575` 리스닝 및 RCON `list` 응답 확인
- Prod: `mcserver` active, 리소스팩 SHA-1 `9ad44a5f8900a5911a5e69bb4a3d5377436ddba3` 적용 확인
