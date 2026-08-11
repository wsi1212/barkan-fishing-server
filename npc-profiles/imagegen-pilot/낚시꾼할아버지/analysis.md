# 낚시꾼할아버지 — ImageGen pilot

## Data basis

- Citizens ID: `1`
- Display name: `&a[Q] 낚시꾼할아버지`
- Region: 바르칸 연안의 강 / 민물 낚시 지점
- Current skin: `skin-forge/out/cm_old_angler.png`
- NPC quest IDs: 현재 `npc.json`에는 직접 연결된 퀘스트 ID 없음
- Dialogue states: `인사`, `진행중`, `근처소개`, `퀘스트완료`

## Required image states

| 파일 | 근거 대사 | 감정/연출 |
|---|---|---|
| `base.png` | “오, 자네가 새로 온 낚시꾼인가?” / 주변소개 대사 | 따뜻한 환영, 편안한 미소, 낚싯대와 물고기 |
| `progress.png` | “아직 끝나지 않은 모양이군.” / “서두르지 말고 차근차근 해보게.” | 걱정 섞인 격려, 살짝 모인 눈썹, 낚싯대를 낮춘 자세 |
| `quest_complete.png` | “오! 해냈구먼!” / “역시 자네라면 할 줄 알았어.” | 자랑스러운 기쁨, 눈썹을 올리고 물고기를 들어 올린 자세 |

All three were generated separately with ImageGen from the BetterHUD portrait as style reference and the current Minecraft skin as identity/costume reference. The green chroma-key source was removed locally and the final files are RGBA PNGs.
