# 플레이어 코호트·로드아웃 지표

## 코호트 축

- 낚시 레벨: 1, 10, 30, 45, 60, 70, 100을 고정 샘플로 두고, 콘텐츠 해금 레벨 전후를 추가한다.
- 지역: 실제 `regions.json`에 등록된 지역과 `fish.json`의 지역 풀을 대조한다. 부모 지역 상속을 포함한다.
- 목표: `money`, `xp`, `safety`, 필요하면 수집/도감 목표를 별도 추가한다.
- 입력: 요구 레벨 이하의 부품만, 개발자/OP 아이템은 제외, 레시피/상점/퀘스트 경로를 별도 라벨링한다.

## 로드아웃 평가

각 후보는 다음을 같은 입력으로 평가한다.

```text
expected_money/h
expected_xp/h
expected_catches/h
grade_distribution
quality_mean
failure_or_hit_rate
equipment_cost / material_cost
payback_hours = acquisition_cost / max(1, incremental_money_per_hour)
```

`incremental_money_per_hour`는 “아무 장비 없음”이 아니라 바로 전 단계에서 실제로 사용할 수 있는 최선의 대체품 대비 델타다. 가격이 0이어도 무상으로 간주하지 않고, source/획득경로를 표기한다.

## 지배(dominance)

빌드 A가 B보다 골드/h와 XP/h가 모두 높고, 비용·실패·사용 가능 레벨이 더 나쁘지 않으면 A가 B를 지배한다고 표시한다. 지배받는 장비가 많으면 등급별 비교가 아니라 선택지 붕괴 문제다.

반대로 골드/h가 낮아도 XP/h·안전성·도감 접근성이 높으면 “다른 목표의 합리적 선택”으로 남긴다. 하나의 종합 점수로 모든 플레이어를 정렬하지 않는다.
