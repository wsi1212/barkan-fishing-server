# 웹 도감 데이터

## 항해 지도 갱신

`/map`은 동적 지도 플러그인이 아니라 운영 `regions.json`과 Paper 월드의 정적
스냅샷을 사용한다. 운영 월드를 dev에 동기화한 뒤 다음 순서로 갱신한다. 지형 생성기는
Anvil 파일을 서버 프로세스 밖에서 직접 읽는다. AIBuilder `region_topdown`으로 본섬을
고해상도 스캔하면 Paper 메인 스레드가 오래 멈출 수 있으므로 사용하지 않는다.

```bash
python3 website/build_map_data.py --data <prod-regions.json이_있는_폴더>
/usr/bin/python3 tools/generate-live-terrain-map.py
```

첫 명령에는 prod에서 받은 `regions.json`을 사용한다. 두 번째 명령은 동기화된 로컬
`world/`와 `plugins/BlockShip/regions.json`을 읽어 약 8블록
해상도(`max_resolution=350`)로 `assets/terrain-data.js`를 다시 만든다. 배포할 때는
`map-data.js`, `terrain-data.js`, `map.html`을 함께 올리고 `map.html`의 두 데이터
URL 캐시 버전을 올린다.

히든 장비 62종을 웹 도감에 반영하거나 아이콘 누락을 검사할 때:

```bash
python3 website/sync_hidden_gear_icons.py
python3 website/sync_hidden_gear_icons.py --check
```

스크립트는 `icon-forge/imagegen-hidden/manifest.json`의 62종을 기준으로
현재 리소스팩의 `barkan_icon` PNG를 `assets/gear/`에 웹용으로 복사하고,
`gear-data.js`와 `catalog-data.js`를 함께 갱신한다. `--check`는 두 도감의
모든 장비 항목이 아이콘 ID를 갖고 실제로 읽을 수 있는 PNG를 가리키는지
검사하며, 누락이나 경로 불일치가 있으면 실패한다.
