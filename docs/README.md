# 공유용 HTML — 팀원 배포본

셋 다 **단일 HTML 파일**이다. 서버도 빌드도 필요 없다 — 그냥 브라우저로 열면 된다.
슬랙·디스코드에 파일째 올리거나, 링크를 주려면 아래 아티팩트 URL을 쓴다.

| 파일 | 내용 | 링크 |
|---|---|---|
| [`barkan-story.html`](barkan-story.html) | **1부 전 7장 이야기** (산문). 팀원에게 처음 보여줄 것 | [열기](https://claude.ai/code/artifact/ad2b7c9d-dfe1-4c2a-9340-a1c207957155) |
| [`barkan-quests.html`](barkan-quests.html) | **퀘스트 전문** — 메인 147 + 사이드 146, 목표·수여자·설명·난이도 바 | [열기](https://claude.ai/code/artifact/80c6a6c4-09a2-4822-ac88-fd746ce5b07e) |
| [`ch7-script.html`](ch7-script.html) | 7챕터 대본 + 강하 도해 | [열기](https://claude.ai/code/artifact/6338ebb5-d26d-4340-aa5d-a579032b21b3) |

★**다크모드 자동 대응**이고 모바일에서도 읽힌다. 외부 리소스를 안 쓰므로 오프라인에서도 열린다.

## 갱신하는 법

`barkan-story.html`은 손으로 쓴 문서다 — 스토리가 바뀌면 직접 고친다.
`barkan-quests.html`은 **생성물**이다. `quests.json` 파이프라인을 돌린 뒤
스크래치패드의 `mkfull.py` → `mkpage.py` 순으로 다시 뽑는다.

★파일을 고쳤으면 **아티팩트도 같이 다시 올릴 것** — 링크만 받은 팀원은 파일 쪽 변경을 못 본다.
