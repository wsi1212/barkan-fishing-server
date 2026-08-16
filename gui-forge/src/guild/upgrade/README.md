# 길드 업그레이드 GUI

- `guild_upgrade_final_704x888.png`: 최종 합성 이미지
- `verification/guild_upgrade_guide_overlay.png`: 좌표 검증용 가이드선 포함 이미지
- `sources/background_imagegen.png`: 슬롯 없는 ImageGen 배경
- `sources/central_conduit_imagegen.png`: 중앙 공백에 넣은 ImageGen 도관 원본
- `cutouts/socket_frame.png`: ImageGen 슬롯 프레임 배경 제거본
- `cutouts/central_conduit.png`: 도관 원본의 배경 제거본
- `socket_frame_72x72.png`: 합성에 사용한 72×72 슬롯 프레임
- `central_conduit_placed.png`: 중앙 공백에 배치한 도관 레이어
- `connection_effects.png`: 슬롯 뒤에 합성한 기어·광원·연결효과 레이어
- `compose_upgrade.py`: 재합성 스크립트

## 고정 레이아웃

- 캔버스: `704×888`
- 슬롯 구멍: `64×64`
- 피치: 가로·세로 `72px`
- 별도 슬롯: `(64,104)`
- 왼쪽 추가 슬롯: `(208,176)`
- 왼쪽 3×3: `x=136,208,280`, `y=248,320,392`
- 오른쪽 추가 슬롯: `(496,176)`
- 오른쪽 3×3: `x=424,496,568`, `y=248,320,392`
- 두 영역 사이: `x=352` 한 칸 공백
- 하단 패널: `x=28..676`, `y=553..856`
