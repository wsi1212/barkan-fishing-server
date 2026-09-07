import assert from "node:assert/strict";
import test from "node:test";
import { inflateSync } from "node:zlib";
import { hexRgb, rgbPng, rgbPngDataUrl } from "./pixel-png.mjs";

// 인코더가 진짜 PNG 를 뱉는지 확인하려면 다시 풀어서 픽셀을 대조하는 수밖에 없다.
// (브라우저가 못 읽는 PNG 를 만들어도 문법 오류는 안 나므로 눈으로는 못 잡는다.)
function decode(buffer) {
  assert.deepEqual([...buffer.subarray(0, 8)], [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
  const chunks = new Map();
  for (let at = 8; at < buffer.length; ) {
    const length = buffer.readUInt32BE(at);
    const type = buffer.toString("ascii", at + 4, at + 8);
    chunks.set(type, buffer.subarray(at + 8, at + 8 + length));
    at += 12 + length;
  }
  const ihdr = chunks.get("IHDR");
  const width = ihdr.readUInt32BE(0);
  assert.equal(ihdr.readUInt32BE(4), width, "정사각형이어야 한다");
  assert.equal(ihdr[8], 8);
  assert.equal(ihdr[9], 2);
  assert.ok(chunks.has("IEND"));
  const raw = inflateSync(chunks.get("IDAT"));
  assert.equal(raw.length, width * (width * 3 + 1));
  const pixels = [];
  for (let y = 0; y < width; y += 1) {
    const line = y * (width * 3 + 1);
    assert.equal(raw[line], 0, "필터는 None 뿐이다");
    for (let x = 0; x < width; x += 1) {
      const at = line + 1 + x * 3;
      pixels.push((raw[at] << 16) | (raw[at + 1] << 8) | raw[at + 2]);
    }
  }
  return { width, pixels };
}

test("굽고 다시 풀면 픽셀이 그대로다", () => {
  const size = 8;
  const values = Array.from({ length: size * size }, (_, i) => (i * 0x040507) & 0xffffff);
  const decoded = decode(rgbPng(values, size));
  assert.equal(decoded.width, size);
  assert.deepEqual(decoded.pixels, values);
});

test("엠블럼 실제 크기(128²)도 행/열 순서가 유지된다", () => {
  const size = 128;
  const values = Array.from({ length: size * size }, (_, i) => (i % size === 0 ? 0xff0000 : 0x101010));
  const { pixels } = decode(rgbPng(values, size));
  assert.deepEqual(pixels, values);
  // 첫 열만 빨강 — 행/열을 뒤집었다면 첫 행만 빨강이 된다.
  assert.equal(pixels[0], 0xff0000);
  assert.equal(pixels[1], 0x101010);
  assert.equal(pixels[size], 0xff0000);
});

test("CRC 가 청크마다 맞다", () => {
  // decode() 는 CRC 를 안 보므로 여기서 직접 검산한다.
  const buffer = rgbPng(Array(16).fill(0x123456), 4);
  const table = new Int32Array(256);
  for (let n = 0; n < 256; n += 1) {
    let c = n;
    for (let k = 0; k < 8; k += 1) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    table[n] = c;
  }
  const crc32 = (b) => {
    let crc = -1;
    for (const byte of b) crc = table[(crc ^ byte) & 0xff] ^ (crc >>> 8);
    return (crc ^ -1) >>> 0;
  };
  let seen = 0;
  for (let at = 8; at < buffer.length; ) {
    const length = buffer.readUInt32BE(at);
    assert.equal(buffer.readUInt32BE(at + 8 + length), crc32(buffer.subarray(at + 4, at + 8 + length)));
    at += 12 + length;
    seen += 1;
  }
  assert.equal(seen, 3, "IHDR·IDAT·IEND");
});

test("data URI 는 <img src> 에 바로 넣을 수 있다", () => {
  const url = rgbPngDataUrl(Array(64).fill(0xdcd9d3), 8);
  assert.match(url, /^data:image\/png;base64,[A-Za-z0-9+/=]+$/);
  assert.deepEqual(decode(Buffer.from(url.split(",")[1], "base64")).pixels, Array(64).fill(0xdcd9d3));
});

test("픽셀이 모자라면 빈 이미지를 굽지 않고 던진다", () => {
  assert.throws(() => rgbPng(Array(10).fill(0), 8), RangeError);
  assert.throws(() => rgbPng(null, 8), RangeError);
});

test("hexRgb", () => {
  assert.equal(hexRgb("#dcd9d3"), 0xdcd9d3);
  assert.equal(hexRgb("08121d"), 0x08121d);
  assert.equal(hexRgb("없음"), 0);
  assert.equal(hexRgb(undefined), 0);
});
