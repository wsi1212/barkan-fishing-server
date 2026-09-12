# dev BetterHud / CraftEngine 팩 동시 실패 조사 — 2026-09-13

## 결론

정상 CE 생성 ZIP에만 적용했던 BetterHud 셰이더 호환 오버레이가 2026-09-07 03:23 KST CE 팩 재생성으로 사라졌다. 이후 dev는 원래의 잘못된 버전 범위를 가진 ZIP을 전달했다. 1.21.11 클라이언트가 구 fog API를 사용하는 텍스트 셰이더를 컴파일하다 실패하여 CE와 BetterHud가 함께 들어 있는 팩을 해제했다.

조사 중 dev/prod 설정이나 팩은 변경하지 않았다. 로컬 로그, 클라이언트 다운로드 캐시, 설치된 CE JAR의 바이트코드, 실제 HTTP 응답을 대조했다.

## 바이트와 로그 증거

| 구분 | SHA1 | 확인 결과 |
|---|---|---|
| 마지막 정상 dev CE 캐시 | `7d9d5da7770f15aaf20b8042eaa80045bb26a6a7` | `betterhud_1_21_6=56..64`, `betterhud_bridge_65_83=65..83`. 브리지는 `SHADER_VERSION 3` 사용 |
| 9/7 03:23 생성, 9/12 실패한 CE ZIP | `2aa4b5036c3d145f6aabaf4dac23f725289a7de8` | 브리지 없음. `betterhud_1_21_6=56..83`, `SHADER_VERSION 2`, fog 분기는 `>=3` |
| 클로드가 9/12 22:47 이전 셜커 파일만 제거한 ZIP | `0ce23a5caa9f1e417886e251034650d69cdb6691` | 22:47:59 동일한 텍스트 셰이더 오류 재발 |
| 클로드가 9/12 23:00 교체한 현재 HTTP 배포 ZIP | `6b73fba38b8dd810cbb45530cc026c3825b43094` | `#version 330`, fog 분기를 `>=2`로 수정. HTTP로 받은 바이트와 CE config SHA1 일치. 클라이언트 적용은 아직 미검증 |

정상 ZIP과 실패 ZIP의 `betterhud_1_21_6/.../rendertype_text.fsh`, `betterhud_26_1/.../rendertype_text.fsh`는 각각 바이트가 동일하다. 즉 원본 셰이더가 새로 변해서 생긴 회귀가 아니라, 정상 ZIP에 추가했던 브리지와 범위 교정이 빠진 것이 차이다.

서버 로그 `logs/2026-09-07-7.log.gz`:

```text
[03:22:51] [CraftEngine] 리소스 팩 생성 중...
[03:22:56] [BetterHud] Successfully merged with CraftEngine.
[03:22:56] [CraftEngine] 리소스 팩 생성 완료 (5518ms)
[03:23:00] [CraftEngine] 리소스 팩 압축 완료 (1612ms)
[03:23:00] [CraftEngine] 리소스 팩 업로드 완료 (21 ms)
```

현재 `plugins/CraftEngine/generated/resource_pack.zip`의 mtime도 9/7 03:23:00이며 SHA1은 위 실패 ZIP과 같다.

클라이언트 로그 `~/Library/Application Support/minecraft/logs/2026-09-12-1.log.gz`:

```text
[17:31:27] Connecting to localhost, 25565
[17:31:39] Couldn't compile fragment shader (minecraft:core/rendertype_text):
  Regular non-array variable 'FogColor' may not be redeclared
  'FogColor' already declared within an interface block
  Invalid call of undeclared identifier 'linear_fog'
[17:31:39] Caught error loading resourcepacks, removing all selected resourcepacks
```

동일한 오류는 22:47:59까지 반복해서 발생했다.

클라이언트 다운로드 기록은 실패한 ZIP을 정상적으로 받았음을 보여준다. 팩 다운로드/프록시 전달 자체가 이 실패의 원인은 아니다. 9/7 03:12 접속 때는 정상 ZIP이 로드되고 셰이더 실패가 없었고, 그 이후 9/12 17:31 dev 접속에서 새 실패 ZIP을 받은 기록이 남아 있다. 로컬 기록으로 확인되는 회귀 시점은 9/7이며, 9/11에 새로 깨졌다는 증거는 없다.

## CE 생성이 멈췄다는 진단에 대한 정정

설치된 `CraftEngine.jar`(26.7.4)의 `ReloadCommand`를 `javap -c -p`로 확인했다.

- 인자가 없는 `ce reload`는 `CONFIG`가 기본값이며 `reloadPlugin(...)`만 호출한다.
- `ce reload pack`과 `ce reload all` 분기에는 `BukkitPackManager.generateResourcePack()` 호출이 있다.
- 확인한 클로드 조사 세션은 `ce reload`, `ce upload`, dev 재시작을 반복했다. `ce reload all`을 실제 실행했다는 근거는 해당 세션에 없다.

따라서 기존 ZIP의 날짜가 그대로인 현상만으로 생성기 고장이라고 단정할 수 없다. 설정 리로드/업로드를 반복해도 팩 재생성은 수행되지 않는다. 현재 공식 명령어 문서도 인자 생략 시 config라고 설명하지만 최신 문서는 workflow 체계이므로, 본 판단은 설치된 26.7.4 바이트코드를 우선했다.

참고: https://xiao-momi.github.io/craft-engine-wiki/reference/commands/

## 현재 상태와 검증 한계

- 마지막 dev 클라이언트 접속/실패: 9/12 22:47. 이후 22:48에는 prod(`barkan.kr`)로 접속했다.
- 마지막 클로드 수정: 9/12 23:00. 조사 당시 클라이언트 다운로드 기록에 수정본 `6b73fba3...`는 없다. 현재 파일이 원래 오류를 일으킨 코드 분기를 교정한 것은 확인했지만, 화면 복구를 확인한 것은 아니다.
- 9/13 00:03 BetterHud가 다시 빌드되어 현재 배포 ZIP과 HUD 폰트 JSON 40개가 다르다. 차이 예시는 동일한 문자 정의의 `text_font3_1.png` / `text_font5_1.png` 참조 번호다. 텍스처 바이트와 셰이더 좌표표는 비교 시 일치했다. 이것을 팩 전체 해제의 원인이라고 단정하지 않는다.
- `texts/hud-font.yml`과 `texts/npc-dialogue-font.yml`이 `hud_font`, `hud_original_font`를 중복 정의한다. 서버에도 collision 경고가 있다. 이는 별도 정리 대상이다.
- 현재 CraftEngine은 `auto-upload: false`, 외부 호스팅(`~/dev-rp-host/barkan-ce.zip`)이다. 팩을 새로 생성해도 이 배포 사본과 SHA1은 자동으로 갱신되지 않는다.

## 재발 방지 시 필요한 조건

생성 ZIP에만 수동 패치하고 끝내면 다음 생성에서 패치가 다시 사라진다. 생성 원본 또는 항상 실행되는 생성 후 처리에 호환 수정을 넣고, HUD 최종 빌드 → CE 팩 생성 → 버전별 셰이더 검증 → 로컬 배포 사본/해시 갱신 → 실제 클라이언트 적용 확인까지 묶어야 한다.

기존 `ops/fix-betterhud-shader-overlay.py`에도 CE 재생성 시 패치가 사라진다는 경고가 있다. 다만 현재는 클로드가 템플릿의 버전 분기 자체를 바꾼 상태이므로, 이 스크립트를 무조건 재실행하지 말고 대상 버전별 셰이더를 먼저 확인해야 한다.
