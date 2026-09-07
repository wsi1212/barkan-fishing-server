# 웹 도감 데이터

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
