# 작살 밸런스 감사 데이터 소스

작살은 낚싯대의 미니게임을 재사용하지 않는다. 따라서 등급 분포만 복사해 비교하면 실제 선택 비용을 놓친다. 아래 소스가 권위다.

| 축 | 권위 소스 | 확인할 값 |
|---|---|---|
| 작살 카탈로그 | `plugins/BlockShip/parts.json`의 `작살` | 가격·내구·요구 레벨·공격력·공격속도·수중호흡·수영속도·공통 수입 스탯 |
| 획득경로 | `plugins/BlockShip/recipes.json`의 `resultPartType=작살` + 상점/퀘스트 코드 | 제작 재료·레시피 해금·실제 공급 여부 |
| 물고기·지역 | `plugins/BlockShip/fish.json` + `HarpoonManager` 지역 풀 상속 | 지역별 어종·등급·크기 범위·지역 부모 상속 |
| 등급 롤 | `fishing/GradeRoller.java` | PRD base·pity·레벨 게이트·지역 풀에 없는 등급 skip |
| 스폰/처리량 | `harpoon/HarpoonManager.java` | 최대 물고기 수·스폰 쿨다운·캐치 쿨다운·HP·공격력·공격속도·돌진 |
| 보상 | `harpoon/HarpoonListener.java` | 품질 70~100·크리·크기·더블/트리플·판매보너스·XP·내구/재료/보물상자 여부 |
| 행동계측 | `telemetry/TeleTypes.java`, `HarpoonListener.java`, `HarpoonManager.java` | 스윙·명중·미스·대미지·캐치·돌진·세션 시간 |

## 해석 규칙

- `parts.json` 행은 존재하는 장비 정의이지 곧바로 획득 가능한 장비라는 뜻이 아니다. `catalog.py`는 레시피 미연결을 표시하고, 상점·퀘스트·OP 전용 경로를 별도로 확인한다.
- `GradeRoller`는 현재 지역 풀에 없는 희귀 등급을 롤에서 건너뛴다. 전 서버 등급 분포를 그대로 작살 지역에 넣지 않는다.
- `HarpoonListener`의 품질 고정 범위와 `HarpoonManager`의 쿨다운은 낚싯대의 150캐스트/h 가정과 다른 자연 처리량이다.
- 현재 작살은 낚싯대의 젖은 보물상자/재료 롤과 내구 소모 경로가 다르므로, “소득”과 “보상 다양성/소모”를 분리해 기록한다.
