# 리소스팩 문서

## 개요

바르칸 열도 서버 전용 리소스팩. 플레이어가 접속 시 자동 설치됨.

## 파일 구조

```
barkan-resourcepack/
  pack.mcmeta                          # 팩 메타 (format 46 = 1.21.4+)
  assets/minecraft/
    items/
      cod.json                         # 대구 아이템 모델 정의 (CMD 분기)
    models/item/fish/
      *.json                           # 각 물고기 모델 (텍스처 참조)
    textures/item/fish/
      *.png                            # 물고기 텍스처 (256x256, 투명 배경)
```

## 1.21.4+ 커스텀 아이템 포맷

기존 `CustomModelData` (정수) 방식이 아닌 **문자열 기반 선택** 사용:

### items/cod.json (아이템 모델 정의)
```json
{
  "model": {
    "type": "minecraft:select",
    "property": "minecraft:custom_model_data",
    "index": 0,
    "cases": [
      {
        "when": "test_sardine",
        "model": {"type": "minecraft:model", "model": "minecraft:item/fish/test_sardine"}
      }
    ],
    "fallback": {"type": "minecraft:model", "model": "minecraft:item/cod"}
  }
}
```

### 인게임 아이템 지급
```
/give @s cod[custom_model_data={strings:["test_sardine"]}]
```

### Skript에서 아이템 생성
```skript
set {_fish} to cod
set custom model data of {_fish} to custom model data with strings ("test_sardine")
```

## 텍스처 제작 가이드

### AI 생성 (Leonardo.ai API)
- API Key: Leonardo.ai 대시보드에서 발급
- 모델: `e71a1c2f-4f80-4800-934f-2c68979d8cc8` (Anime XL)
- 프롬프트 템플릿:
```
simple illustration of a single [물고기이름] fish, horizontal side view facing left,
dark charcoal gray outline, body color is [색상설명],
very small black dot for eye, minimal simple dark fins,
[체형] natural fish body shape, flat color fill with minimal shading,
cute simple Korean illustration style, soft pink pastel background,
clean lines, no detail on scales, sticker-like flat art, no text
```

### 후처리
1. 배경 제거 (플러드필 방식 — 물고기 내부 흰색 보존)
2. 세로 1.6배 확대 (살집)
3. 35도 회전 (대각선 배치)
4. 256x256 캔버스 중앙 배치
5. 반투명 픽셀 → 불투명 강제
6. 테두리 1px 검은 아웃라인 추가

### 등급별 스케일 (모델 JSON display)

| 등급 | scale | 크기 | 예시 |
|------|-------|------|------|
| E~D | 1.0 | 기본 | 피라미, 붕어 |
| C~B | 1.5 | 1.5블록 | 잉어, 메기 |
| A~S | 2.0 | 2블록 | 연어, 쏘가리 |
| S+~M | 3.0 | 3블록 | 철갑상어 |
| L | 4.0 | 4블록 | 황금잉어, 고래 |
| G | 5.0 | 5블록 | 강의수호자 |

## 호스팅 및 배포

| 항목 | 값 |
|------|-----|
| GitHub | https://github.com/wsi1212/minecraft-fish-resource-pack |
| 파일명 | barkan-resourcepack.zip (같은 release `latest`에 CraftEngine 가구팩 `barkan-furniture.zip`도 별도 자산으로 공존 — `gh release delete` 절대 금지, `--clobber` 업로드만) |
| SHA1 | 배포마다 바뀜 — `~/deploy-rp.sh`가 자동 갱신하므로 여기 고정값을 적어두지 않음 |
| 서버 설정 | server.properties → resource-pack, resource-pack-sha1 |
| 강제 적용 | require-resource-pack=true |

## 업데이트 절차

★소스 위치는 **`~/development/barkan-resourcepack`**다 (`~/Downloads/barkan-resourcepack/`는 2026-06-06 TCC 권한 문제로 이동해 더 이상 존재하지 않음).

1. `~/development/barkan-resourcepack/` 내 텍스처/모델 수정
2. 배포는 한 줄: `~/deploy-rp.sh` (ZIP 생성 → GitHub Release 업로드(`--clobber`) → SHA1 계산 → server.properties 갱신까지 전부 자동)
3. 서버 재시작 (접속자에게 자동 적용)

수동으로 해야 할 때만:
```bash
cd ~/development/barkan-resourcepack && zip -r /tmp/barkan-resourcepack.zip . -x ".*"
gh release upload latest /tmp/barkan-resourcepack.zip --repo wsi1212/minecraft-fish-resource-pack --clobber
shasum /tmp/barkan-resourcepack.zip   # → server.properties의 resource-pack-sha1에 반영
```

## 작업 파이프라인

```
1. AI 생성 (Leonardo API) — 물고기별 프롬프트로 이미지 생성
2. 후처리 — 배경 제거(플러드필), 살집 1.6배, 35도 회전, 아웃라인
3. 로컬 리소스팩 반영 — textures/item/fish/ + models + items/cod.json
4. 클라이언트 테스트 — resourcepacks에 복사 → F3+T로 확인
5. 승인 — 유저가 인게임에서 확인 후 OK
6. ZIP 압축 — barkan-resourcepack.zip 재생성
7. GitHub 푸시 — /tmp/minecraft-fish-resource-pack에서 commit + push
8. SHA1 갱신 — shasum → server.properties 업데이트
9. 서버 재시작 — 접속 플레이어에게 자동 적용
```

1~4는 자동, 5는 유저 확인, 6~9는 승인 후 자동.

## 현재 등록된 물고기 텍스처

| ID | 이름 | CMD 문자열 | 상태 |
|----|------|-----------|------|
| 1 | 테스트 정어리 | test_sardine | 완료 |

총 274종 중 1종 완료. Leonardo API로 일괄 생성 예정.
