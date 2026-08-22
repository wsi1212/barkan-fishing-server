# 발주 — `/수리` 장비·통발 수리창

## 화면 계약

`RepairGui`는 27칸(3행) 상자 GUI다. 배경은 제목 글리프로 조립되며, 실제 아이템은 아래 슬롯에 코드가 올린다.

| 슬롯 | 역할 | 실제 내용 |
|---:|---|---|
| 11·12·13·14 | 개별 수리 | 화면 기준 12~15번에 릴·줄·바늘·찌를 연속 배치 |
| 15 | 입력/수리 | 화면 기준 16번에 실제 통발 아이템 1스택을 직접 올리는 입력칸 |
| 11·12·13·14·15 | 슬롯 띠 | 화면 기준 12~16번 슬롯 5개에 아이템 5개를 끊김 없이 배치 |
| 22 | 수리 실행 | 장착 부품과 화면 기준 16번 입력 통발을 수리하는 `⚡ 수리 실행` |

실제 작업 판은 [src/repair/_template.png](src/repair/_template.png), 숫자와 역할이 적힌 검수 도면은 [src/repair/_guide.png](src/repair/_guide.png), 한 장짜리 발주 시트는 [src/repair/_order.png](src/repair/_order.png)다.

## 납품 규격

- 파일: `src/repair/bg_source.png`
- 캔버스: **704×672px**, RGBA 또는 RGB 모두 가능하지만 최종 알파는 255 고정
- Minecraft GUI 1px = 원화 4px. 슬롯 피치는 **72px**, 아이콘 상자는 슬롯 중앙 **64×64px**
- 제목 글자는 그림에 굽지 않는다. `GuiTitle.of()`가 런타임 제목을 얹는다.
- 11·12·13·14·15·22번 홈은 재질·프레임만 그리고 안쪽은 아이템이 읽히도록 저대비로 둔다. 11~15는 끊기지 않는 5칸 슬롯 띠다.
- 플레이어 인벤토리 영역(아트 y=336~639)은 장식을 추가하지 않는다. 이 판은 작업대 판에서 검증된 인벤토리 격자를 이미 포함하므로 `src/repair/.assembled`로 `build_plate.py`의 중복 격자 합성을 막는다.
- 슬롯의 위치·크기·피치를 바꾸지 않는다. 좌우 프레임은 슬롯 소켓 바깥으로 한쪽 **16px 이내**다.
- 투명 픽셀 0. 둥근 모서리 바깥도 어두운 재질로 채운다.

## 컨셉

강화창의 용광로보다 차분한 **정비 작업대**다. 기름 먹인 목재, 그을린 철, 청동 테두리,
낮은 주황 불빛, 숫돌·물통·공구걸이를 사용한다. 둘째 줄 화면 기준 12~15번에는
릴·줄·바늘·찌를 놓고, 바로 다음 16번에는 플레이어가 통발 실물을 올린다. 즉 12~16번이
아이템 5개가 끊기지 않는 한 줄 슬롯 띠다.
내구도 상태 색은 아이템 lore가 담당하므로 배경은 중성 톤을 유지한다.

## 검증 순서

```bash
cd "/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/Skript/scripts"
python3 gui-forge/check_align.py repair gui-forge/src/repair/bg_source.png
python3 gui-forge/audit_slots.py repair
python3 gui-forge/audit_all.py repair
python3 gui-forge/verify_repair_bg.py
python3 - <<'PY'
from PIL import Image
p = Image.open('gui-forge/src/repair/bg_source.png').convert('RGBA')
assert p.size == (704, 672)
assert p.getchannel('A').getextrema() == (255, 255)
print('repair plate: size/opacity OK')
PY
python3 gui-forge/build_plate.py repair
python3 -m json.tool "$HOME/development/barkan-resourcepack/assets/barkan/font/gui.json" >/dev/null
```

정렬 검수의 합격 기준은 모든 사용 슬롯에서 64px 아이콘 상자와 홈의 차이가 4배 원화 기준 ±1px 이내다.
텍스처가 강한 홈은 `audit_all.py`가 홈 안쪽 결을 경계로 오인할 수 있으므로, 최종 판정은
`check_align.py`의 빨간 상자 오버레이와 `verify_repair_bg.py`의 슬롯 내부·글리프·타일 검사를 함께 본다.
그 다음 [src/repair/_preview_full.png](src/repair/_preview_full.png)을 확인하고, dev에서 `/수리`를 열어
다음 4가지를 실제로 확인한다.

1. 제목이 명판 중앙에 밝게 보이고 배경 글리프가 창 밖으로 밀리지 않는가.
2. 화면 기준 12~16번에 릴·줄·바늘·찌·통발이 순서대로 정확히 앉는가.
3. 22번 수리 실행 아이콘과 입력 통발의 수량/lore가 배경 장식에 묻히지 않는가.
4. 플레이어 인벤토리 36칸 격자가 배경의 인벤토리 판과 겹쳐 두꺼워지거나 밀리지 않는가.

리소스팩은 먼저 로컬 `F3+T`로 확인하고, 승인 전에는 `~/deploy-rp.sh` 또는 서버 재시작을 실행하지 않는다.
