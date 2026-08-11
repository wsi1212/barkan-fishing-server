# NPC dialogue profile pack

BetterHUD의 `portrait-grandfather-hud.png`를 스타일 기준으로 삼고, `npc.json`의 159개 NPC와 각 NPC의 `dialogue.json` 대사를 읽어 만든 128×128 RGBA 프로필 PNG 묶음이다.

- `out/`: `{citizensId}_{npc}__{표정}.png`
- `manifest.json`: NPC별 원본 스킨 stem, 역할, 대사 줄 수, 표정, 파일 목록
- `review/base-contact-sheet.png`: 159개 기본 프로필 전체 시트
- `review/report.json`: 크기·RGBA·투명 모서리·빈 이미지·변형 차이 QA 결과
- `build_profiles.py`: 스킨/대사 데이터에서 재생성
- `review_profiles.py`: 재생성 후 QA 및 연락시트 생성

기본 표정은 모든 NPC에 제공한다. 대사가 있는 NPC는 말투 키워드에 따라 `talk`, `happy`, `worried`, `stern`, `surprised` 중 필요한 변형을 추가하며, 대사가 없는 기능형 NPC는 직업 소품이 포함된 `base`만 만든다.
