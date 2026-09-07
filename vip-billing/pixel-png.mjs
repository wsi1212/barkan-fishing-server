// 픽셀아트를 <img> 로 내보내기 위한 최소 PNG 인코더 (truecolour 8bit, 무손실).
//
// ★왜 필요한가 — 길드 엠블럼(최대 128²)을 «픽셀 하나 = <i> 하나» 로 깔면
//   CSS 그리드 트랙이 1px 아래로 내려간다. 브라우저는 트랙 경계를 장치 픽셀에
//   반올림하므로 행·열이 통째로 사라지거나 두 배로 굵어지고, 배경에는 이음매가
//   격자 무늬로 남는다(= 「엠블럼이 뭉개진다」). 진짜 이미지로 넘기면 확대·축소를
//   브라우저 이미지 필터가 처리하고, DOM 도 16,384개 대신 1개면 된다.
//
// 의존성을 늘리지 않으려고 node 내장 zlib 만 쓴다 — PNG 의 IDAT 는 zlib 스트림
// 그대로라 deflateSync 결과를 그대로 실으면 된다.
import { deflateSync } from "node:zlib";

const CRC_TABLE = (() => {
  const table = new Int32Array(256);
  for (let n = 0; n < 256; n += 1) {
    let c = n;
    for (let k = 0; k < 8; k += 1) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    table[n] = c;
  }
  return table;
})();

function crc32(buffer) {
  let crc = -1;
  for (let i = 0; i < buffer.length; i += 1) crc = CRC_TABLE[(crc ^ buffer[i]) & 0xff] ^ (crc >>> 8);
  return (crc ^ -1) >>> 0;
}

// PNG 청크 = 길이(4) + 타입(4) + 본문 + CRC(4). CRC 는 타입부터 본문 끝까지.
function chunk(type, body) {
  const head = Buffer.alloc(8);
  head.writeUInt32BE(body.length, 0);
  head.write(type, 4, "ascii");
  const tail = Buffer.alloc(4);
  tail.writeUInt32BE(crc32(Buffer.concat([head.subarray(4), body])), 0);
  return Buffer.concat([head, body, tail]);
}

/**
 * 0xRRGGBB 정수 배열(size×size, 행 우선)을 PNG 버퍼로 굽는다.
 * 범위를 벗어난 값은 검정으로 떨어진다 — 호출부가 팔레트를 이미 풀어서 넘긴다.
 */
export function rgbPng(values, size) {
  const width = Math.max(1, Math.trunc(size));
  if (!Array.isArray(values) || values.length < width * width) {
    throw new RangeError(`픽셀 ${width * width}개가 필요한데 ${Array.isArray(values) ? values.length : "배열이 아님"}`);
  }
  // 스캔라인마다 필터 바이트가 하나씩 앞에 붙는다(0 = None).
  const raw = Buffer.alloc(width * (width * 3 + 1));
  let at = 0;
  for (let y = 0; y < width; y += 1) {
    raw[at] = 0;
    at += 1;
    for (let x = 0; x < width; x += 1) {
      const rgb = Number(values[y * width + x]) | 0;
      raw[at] = (rgb >> 16) & 255;
      raw[at + 1] = (rgb >> 8) & 255;
      raw[at + 2] = rgb & 255;
      at += 3;
    }
  }
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(width, 4);
  ihdr[8] = 8; // bit depth
  ihdr[9] = 2; // colour type 2 = truecolour
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk("IHDR", ihdr),
    // 기본 압축(6). 128² 엠블럼 기준 0.2ms·740B 인데 level 9 는 2.2ms 를 써서
    // 663B 를 만든다 — data URI 로 인라인되는 크기라 그 77바이트는 값이 없다.
    chunk("IDAT", deflateSync(raw)),
    chunk("IEND", Buffer.alloc(0))
  ]);
}

/** 같은 결과를 <img src> 에 바로 넣을 수 있는 data URI 로. */
export function rgbPngDataUrl(values, size) {
  return `data:image/png;base64,${rgbPng(values, size).toString("base64")}`;
}

/** "#rrggbb" → 0xRRGGBB. 못 읽으면 검정. */
export function hexRgb(color) {
  const parsed = Number.parseInt(String(color ?? "").replace("#", ""), 16);
  return Number.isFinite(parsed) ? parsed & 0xffffff : 0;
}
