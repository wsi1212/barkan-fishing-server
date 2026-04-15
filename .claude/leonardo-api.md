# Leonardo AI 이미지 생성 가이드

## API Key
```
ecf564a9-81a8-4dc6-8b01-aecc70cb58ea
```

## 사용법

### 이미지 생성 요청
```bash
curl -X POST "https://cloud.leonardo.ai/api/rest/v1/generations" \
  -H "Authorization: Bearer ecf564a9-81a8-4dc6-8b01-aecc70cb58ea" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "프롬프트 내용",
    "width": 512,
    "height": 512,
    "num_images": 1,
    "modelId": "e71a1c2f-4f80-4800-934f-2c68979d8cc8",
    "transparency": "foreground_only"
  }'
```

### 결과 확인
```bash
curl "https://cloud.leonardo.ai/api/rest/v1/generations/{generationId}" \
  -H "Authorization: Bearer ecf564a9-81a8-4dc6-8b01-aecc70cb58ea"
```

## 주요 파라미터

| 파라미터 | 설명 | 값 |
|---------|------|-----|
| modelId | 모델 | `e71a1c2f-4f80-4800-934f-2c68979d8cc8` (Leonardo Phoenix) |
| width/height | 크기 | 512, 768, 1024 등 |
| num_images | 생성 수 | 1~4 |
| transparency | 투명 배경 | `"foreground_only"` (투명 PNG) |

## 주의사항
- `alchemy: true`는 Phoenix 모델에서 사용 불가
- 생성 후 15~30초 대기 필요 (비동기)
- status가 `COMPLETE`가 되면 `generated_images[0].url`에서 이미지 URL 확인
- 비용: 약 $0.01/장

## 마크 리소스팩용 프롬프트 팁
- "transparent background" + `"transparency": "foreground_only"` 필수
- "pixel art style" 추가하면 마크 느낌
- "viewed from behind" = 등 뒤에서 본 모습 (날개용)
- "wings only no body" = 날개만 (캐릭터 없이)
- "game asset sprite" = 게임 에셋 느낌
