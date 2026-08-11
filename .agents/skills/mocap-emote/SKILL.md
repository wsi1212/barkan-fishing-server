---
name: mocap-emote
description: >-
  CMU Graphics Lab 오픈 모션캡처 데이터베이스(mocap.cs.cmu.edu, 자유재배포 라이선스)에서
  진짜 사람 동작을 받아 steve.bbmodel(BetterModel 13본 플레이어 리그)의 이모트/춤
  애니메이션으로 리타게팅한다. "이모트 더 역동적으로", "진짜 춤 동작처럼", "모션캡처로
  교체", "다른 게임 움직임 참고해서 만들어줘" 같은 요청에 쓴다. 손으로 키프레임 찍는 것보다
  훨씬 자연스러운 비대칭/체중이동이 나온다 — 단 소스 클립에서 정적인 구간을 고르면
  실패하니 자동 에너지탐색이 핵심. 오프라인 스틱피규어 렌더로 자기검수까지 마친 뒤에만
  bbmodel에 반영한다.
---

# 모션캡처 이모트 리타게팅

다른 게임/댄서의 "좋은 움직임"을 우리 눈으로 직접 보고 베끼는 건 안 된다(저작권 있는
안무 raw 데이터 복제는 리스크). 대신 **CMU Graphics Lab Motion Capture Database**
(mocap.cs.cmu.edu)를 쓴다 — FAQ에 명시: *"The motion capture data may be copied,
modified, or redistributed without permission."* 완전 자유. 140명+ 피험자의 댄스·
스포츠·일상동작 수천 클립이 ASF(스켈레톤)+AMC(모션) 포맷으로 공개돼 있다.

## 파이프라인 한눈에

```
CMU 사이트에서 subject/trial 탐색(브라우저로 search.php?subjectnumber=N)
  -> 다운로드 전 유저에게 파일명/용량 고지(다운로드 정책)
  -> curl로 <N>.asf + <N>_<trial>.amc 받기
  -> scripts/retarget.py scan  : 클립 전체에서 가장 동적인 구간 자동 탐색
  -> scripts/retarget.py preview : 그 구간을 렌더만(파일 안 씀) — 반드시 육안 확인
  -> scripts/retarget.py bake : 확정본을 steve.bbmodel 타겟 애니에 굽기
  -> dev는 파일 직접수정+/bm reload, prod는 scp+/bm reload (재시작 불필요, 순수 리소스)
```

## ★ 왜 "정적 구간" 함정에 걸리는지 (직접 겪은 실패)

클립의 **첫 2초를 그냥 쓰면 안 된다.** 캡처 시작은 대개 피험자가 준비자세로 가만히
서있는 구간이라, 리타게팅 자체는 완벽히 맞아도 결과물이 "제대로 안 된 것처럼" 보인다
(실제로 유저가 "제대로 넣은거 아닌거같은데?"라고 지적한 사례 — 원인은 파이프라인
버그가 아니라 소스 윈도우 선택 실수였음). `retarget.py scan`이 주요 관절(어깨/엉덩이/
무릎)의 raw 값 range를 슬라이딩 윈도우로 훑어 가장 동적인 구간을 자동으로 찾아준다.
**scan 결과를 신뢰하고, 절대 start=0을 기본값으로 쓰지 말 것.**

## ★ 리타게팅 핵심 원리 (그래서 루트 캘리브레이션이 이상해도 상관없다)

ASF 본의 `local_rot = C @ Rdof @ Cinv` (C=axis 라인에서 나온 상수 변환행렬, Rdof=그
프레임의 실제 애니메이션 값)는 **부모 기준 로컬 회전 델타**다. 조상의 회전이 아무리
이상해도(실제로 subject 60 salsa의 root 회전이 -95/86/-103도처럼 캘리브레이션
특이값을 가짐) 수학적으로 상쇄되어 하위 관절의 리타게팅엔 전혀 영향 없다 — **전체
forward-kinematics는 검증용 렌더에나 필요하지 리타게팅 자체엔 불필요**하다는 뜻.
(`asf_amc.py Skeleton.local_rot()`가 이걸 구현, `.fk()`는 원본 CMU 골격을 그대로
렌더해서 "우리 리타게팅이 이상한지 원본 자체가 이런 동작인지" 비교할 때만 쓴다.)

## ★ 짐벌락 함정 — 팔꿈치/무릎은 절대 decompose 하지 말 것

다관절 본(어깨 rhumerus/lhumerus, 엉덩이 rfemur/lfemur, 척추 lowerback/upperback,
머리 head)은 Euler XYZ decompose(`asf_amc.decompose_xyz`)가 안전하다(ry가 ±90 근처만
아니면). 하지만 **팔꿈치(rradius/lradius)와 무릎(rtibia/ltibia)은 ASF에서 원래 단일
DOF(대개 `dof rx` 하나)** 인데, 이걸 decompose 해보면 ry가 하필 ±90 근처에 걸려서
rx/rz가 -180~180 사이로 미친듯이 요동치는 가짜 신호가 나온다(직접 겪음 — rradius rx
range가 무려 180이었는데 실제 팔꿈치 굽힘은 그 정도로 안 움직임). **해결: 단일 DOF
본은 반드시 `sk.raw_dof(frame, bone_name, 0)`으로 원본 채널 값을 직접 쓴다.**
`find_best_window`도 이 raw 값 기준으로 에너지를 계산한다.

## ★ 자기비평 없이 유저에게 보여주지 말 것

렌더는 **팔다리를 색으로 구분**해서 만든다(`pose_render.SEGMENTS_COLORED` — 척추=노랑,
우완=파랑, 좌완=빨강, 우각=초록, 좌각=보라). 색 구분 없이 단색으로 렌더하면 팔이 앞으로
뻗은 것과 척추가 굽은 것을 헷갈려서 "몸이 계속 숙여져있다"는 오진을 내릴 수 있다(실제로
한 번 이렇게 잘못 판단해서 재확인하느라 시간을 씀 — 색 구분 후 실제로는 척추는 거의
똑바르고 팔만 뻗어있던 것으로 밝혀짐). front(X-Y)+side(Z-Y) 둘 다 봐야 한다 — 다리
킥/무릎 굽힘처럼 X축 회전이 지배적인 동작은 front view에서 거의 안 보인다(단축 투영).

`preview` 커맨드로 렌더 → **내 눈으로 직접 본다** → 이상하면(팔이 계속 한쪽으로 뻗어
있나? 다리가 실제로 스텝을 밟나? 무릎이 0도 밑으로 안 꺾이나? 루프 시작/끝이 매끄러운가?)
window나 exaggeration 배율을 조정해서 다시 preview → 통과한 것만 bake.

## ★ 바닥 동작(눕기·구르기)도 가능하다 — 단 root=몸통 전체를 피벗으로 쓰면 안 된다

"서있는 자세만 가능하다"는 예전 판단은 틀렸다. 다만 root(우리 리그 기준 골반)를 실제
윈드밀의 몸통 회전값 그대로 따라가게 하면(짐벌락을 잘 피해도) "여기저기 날아다니는"
것처럼 보인다 — 실제 윈드밀은 상체가 바닥에 거의 고정되고 **다리만** 크게 도는 동작이라,
root=몸통 전체를 회전축으로 쓰면 골반의 실제 회전이 상체까지 그대로 곱해져 과하게
휩쓸린다. **성공한 구조: root+상체는 엎드린 자세로 고정, 다리만 mocap 실제 회전을
그대로.** 어느 부위가 진짜 피벗인지 먼저 판단하고 그 기준으로 나머지를 상대운동시킬 것
— root가 항상 정답은 아니다. 세 번 실패한 시행착오 전체는
`references/cmu-catalog.md`의 "누워서 도는 동작" 섹션 참고.

## ★ 이름과 실제 춤이 안 맞는 함정 (2026-07-27, 유저 지적으로 발견)

이모트 이름(예: "셔플", "힙합")이 약속하는 실제 춤 스타일과 소스 클립이 안 맞으면
품질이 아무리 좋아도 "이거 아닌데" 소리를 듣는다. `dance_hiphop`에 찰스턴(1920년대
스윙 장르, 힙합과 스타일 완전 다름)을, `dance_shuffle`에도 찰스턴(무릎 크로스오버,
좌우 슬라이드인 셔플과 다름)을 넣었다가 둘 다 되돌림. **소스를 고를 때 "동적인가"만
보지 말고 "이 이름을 가진 실제 춤의 핵심 특징(발동작 패턴·에너지 종류)과 일치하는가"를
먼저 검증할 것.** 애매하면 스타일이 안 맞는 mocap보다 손으로 만든 버전이 이름에 더
충실할 수 있다 — 이 경우엔 손제작 원본을 유지하는 게 정답이었다.

## CMU 카탈로그 & 리그 규약은 references/ 참고

- `references/cmu-catalog.md` — 검증된 subject/trial 목록(살사/찰스턴/브레이크댄스/
  점프/휠/모던댄스), 라이선스, 검색 방법.
- `references/rig-conventions.md` — steve.bbmodel 13본 구조, z-fight 오프셋 11개
  baseline, 팔/다리 축 부호 규약, 나치경례 금지 각도, 루프 클로징 요구사항.

## 배포

steve.bbmodel 애니메이션은 **서버측 데이터**라 리소스팩 재배포 불필요 — dev는 파일이
곧 서버 파일이라 `~/dev-mc.sh cmd "bm reload"`만, prod는 scp 후 원격 RCON으로
`bm reload`만 하면 된다(재시작 불필요, jar도 안 건드림). 단, prod에 접속자가 있으면
[[feedback_prod_deploy_explicit_only]] 원칙대로 배포 전에 확인할 것(접속자 0명이면
예외적으로 바로 가능).

## 다음에 새 이모트/춤을 하나 더 뽑을 때

1. 원하는 느낌을 CMU 카테고리로 번역(예: "발랄한 스텝" → charleston, "회전" →
   whirl/spin, "점프" → Jumping subject, "바디웨이브" → modern dance의 arching/bending
   trial). `references/cmu-catalog.md`에 없는 새 느낌이면 브라우저로
   `search.php?subjectnumber=N` 또는 subject 목록 페이지에서 trial 설명 텍스트로 훑는다.
2. `retarget.py scan` → `preview` → 육안 확인(자기비평 3~4패스, 통과할 때까지 유저에게
   안 보여줌) → `bake --target <이모트id>`.
3. dev 확인 후 prod 배포. steve.bbmodel 백업은 배포 직전에 타임스탬프 붙여 스크래치패드에
   복사해두는 습관(되돌릴 일 생김).
