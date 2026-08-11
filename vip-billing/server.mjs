import http from "node:http";
import process from "node:process";
import { createHash, randomBytes, randomUUID, timingSafeEqual } from "node:crypto";
import pg from "pg";

const { Pool } = pg;

const PORT = Number.parseInt(process.env.PORT ?? "3100", 10);
const BASE_URL = (process.env.PUBLIC_BASE_URL ?? "https://barkan.kro.kr/vip").replace(/\/$/, "");
// 운영 도구의 단일 진입점은 기존 Discord 인증 통계 대시보다.
const STATS_ADMIN_URL = process.env.STATS_ADMIN_URL ?? "https://barkan.kro.kr/admin/membership";
const INTERNAL_TOKEN = process.env.INTERNAL_API_TOKEN ?? "";
const TOSS_CLIENT_KEY = process.env.TOSS_CLIENT_KEY ?? "";
const TOSS_SECRET_KEY = process.env.TOSS_SECRET_KEY ?? "";
// 토스 PG 전환 전에는 계좌이체 기간권으로 운영한다. 실제 계좌 정보는 Oracle 환경변수에만 둔다.
const BANK_TRANSFER_BANK = process.env.BANK_TRANSFER_BANK ?? "";
const BANK_TRANSFER_ACCOUNT_NUMBER = process.env.BANK_TRANSFER_ACCOUNT_NUMBER ?? "";
const BANK_TRANSFER_ACCOUNT_HOLDER = process.env.BANK_TRANSFER_ACCOUNT_HOLDER ?? "";
const ADMIN_USERNAME = process.env.ADMIN_USERNAME ?? "admin";
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD ?? "";
const pool = new Pool({ connectionString: process.env.DATABASE_URL, max: 8 });

const TIERS = Object.freeze({
  VIP: { name: "VIP", price: 9900, yearlyMonthlyPrice: 4900, color: "#83e7ff", benefits: ["VIP 채팅 태그", "월간 꾸미기 보상", "멤버십 전용 소식"] },
  MVP: { name: "MVP", price: 19900, yearlyMonthlyPrice: 9900, color: "#ffd36b", benefits: ["MVP 채팅 태그", "전용 외형·칭호", "멤버십 전용 꾸미기"] },
  MVP_PLUS: { name: "MVP+", price: 29900, yearlyMonthlyPrice: 14900, color: "#ff94da", benefits: ["VIP 전체 혜택", "월간 외형 선택권", "프리미엄 프로필 꾸미기"] }
});

const MAX_MONTHS = 12;
const PURCHASE_MONTHS = Object.freeze([1, 3, 5, 12]);
const RECOMMENDED_MONTHS = 5;
const bankTransferConfigured = () => Boolean(BANK_TRANSFER_BANK && BANK_TRANSFER_ACCOUNT_NUMBER && BANK_TRANSFER_ACCOUNT_HOLDER);
const periodDays = (months) => months === MAX_MONTHS ? 365 : months * 30;
const monthsForDays = (days) => days === 365 ? MAX_MONTHS : Math.ceil(days / 30);
// 1개월은 기본가, 12개월은 약속한 최저 월 단가가 되도록 월 단가를 선형으로 낮춘다.
function periodPrice(tier, months) {
  if (months === MAX_MONTHS) return tier.yearlyMonthlyPrice * MAX_MONTHS;
  const yearlyRate = tier.yearlyMonthlyPrice / tier.price;
  const rate = 1 - (1 - yearlyRate) * ((months - 1) / (MAX_MONTHS - 1));
  return Math.round((tier.price * months * rate) / 100) * 100;
}
const monthlyPrice = (tier, months) => Math.round(periodPrice(tier, months) / months);
const periodLabel = (months) => `${periodDays(months)}일`;

const hash = (value) => createHash("sha256").update(value).digest("hex");
const token = (bytes = 32) => randomBytes(bytes).toString("base64url");
const minecraftName = (value) => typeof value === "string" && /^[A-Za-z0-9_]{3,16}$/.test(value);
const validUuid = (value) => typeof value === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value);
const esc = (value = "") => String(value).replace(/[&<>'"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[c]);

function cookies(req) {
  return Object.fromEntries((req.headers.cookie ?? "").split(";").map((part) => {
    const i = part.indexOf("=");
    return i < 0 ? ["", ""] : [part.slice(0, i).trim(), decodeURIComponent(part.slice(i + 1))];
  }));
}

function send(res, status, body, type = "text/html; charset=utf-8", extra = {}) {
  res.writeHead(status, {
    "Content-Type": type,
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
    "Content-Security-Policy": "default-src 'self'; style-src 'unsafe-inline'; script-src 'self' https://js.tosspayments.com; connect-src 'self' https://api.tosspayments.com",
    ...extra
  });
  res.end(body);
}
function json(res, status, data) { send(res, status, JSON.stringify(data), "application/json; charset=utf-8"); }
function redirect(res, location, cookiesOut = []) {
  send(res, 303, "", "text/plain", { Location: location, "Set-Cookie": cookiesOut });
}
function layout(title, content) {
  content = `<style>.footer{font-size:0}.footer:after{content:"문의 및 환불: wsiwsiwsi123@gmail.com";font-size:12px}</style>${content}`;
  return `<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#0c1726"><title>${esc(title)} | 바르칸 열도</title><style>
  @font-face{font-family:"Barkan Aggro";src:url("/assets/barkan-aggro-light.ttf") format("truetype");font-weight:300;font-style:normal;font-display:swap}@font-face{font-family:"Barkan Aggro";src:url("/assets/barkan-aggro-medium.ttf") format("truetype");font-weight:400;font-style:normal;font-display:swap}@font-face{font-family:"Barkan Aggro";src:url("/assets/barkan-aggro-bold.ttf") format("truetype");font-weight:700 900;font-style:normal;font-display:swap}:root{color-scheme:dark;--ink:#0c1726;--deep:#111f31;--surface:#14253a;--line:rgba(210,226,231,.16);--text:#eef4f2;--muted:#a9b9c2;--tide:#93d8d4;--aqua:#83e7ff;--gold:#ffd36b;--pink:#ff94da;--success:#6ee7a2;--danger:#ff93a9}*{box-sizing:border-box}body,body *{font-family:"Barkan Aggro","Apple SD Gothic Neo","Noto Sans KR",sans-serif}body{min-height:100vh;margin:0;background:linear-gradient(180deg,#102238 0,#0c1726 570px);color:var(--text);font:15px/1.58 "Barkan Aggro","Apple SD Gothic Neo","Noto Sans KR",sans-serif}.wrap{width:min(1080px,calc(100% - 36px));margin:auto}.nav{height:78px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--line)}.brand{display:flex;align-items:baseline;gap:9px;color:var(--text);text-decoration:none}.brand strong{font-family:ui-serif,Georgia,"Noto Serif KR",serif;font-size:19px;letter-spacing:.1em}.brand small{color:var(--tide);font-size:10px;font-weight:800;letter-spacing:.13em}.nav span{display:flex;gap:20px}.nav a:not(.brand){color:var(--muted);font-size:13px;text-decoration:none}.nav a:not(.brand):hover{color:var(--text)}main{padding:46px 0 82px}.hero{position:relative;overflow:hidden;padding:70px 4px 54px;border-bottom:1px solid var(--line)}.hero:after,.hero:before{content:"";position:absolute;right:-125px;border:1px solid rgba(147,216,212,.14);border-radius:50%;pointer-events:none}.hero:after{top:-195px;width:450px;height:450px}.hero:before{top:-125px;right:-55px;width:310px;height:310px}.hero-kicker{position:relative;margin:0 0 14px;color:var(--tide);font-size:11px;font-weight:850;letter-spacing:.16em}.hero h1{position:relative;max-width:720px;margin:0;font-family:ui-serif,Georgia,"Noto Serif KR",serif;font-size:clamp(3rem,7vw,5.8rem);font-weight:650;letter-spacing:-.07em;line-height:.98}.hero h1 span{color:var(--tide)}.hero .muted{position:relative;max-width:510px;margin:21px 0 0;font-size:16px}.button,button{display:inline-flex;align-items:center;justify-content:center;min-height:46px;padding:11px 17px;border:1px solid transparent;border-radius:6px;background:var(--tide);color:#0c1a28;font:800 14px inherit;text-decoration:none;cursor:pointer;transition:background .15s ease,transform .15s ease}.button:hover,button:hover{background:#b2edeb;transform:translateY(-1px)}.button.alt{border-color:var(--line);background:transparent;color:var(--text)}.section-head{display:flex;justify-content:space-between;align-items:end;gap:18px;margin:42px 0 17px}.section-head h2{margin:0;font-size:22px;letter-spacing:-.04em}.section-head p{margin:5px 0 0;color:var(--muted);font-size:14px}.membership-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--line);border:1px solid var(--line)}.card{display:flex;min-height:326px;flex-direction:column;padding:26px;background:var(--deep)}.card:first-child{background:linear-gradient(160deg,#162b43,#111f31)}.card:nth-child(2){background:linear-gradient(160deg,#2c2a28,#161f2d)}.card:nth-child(3){background:linear-gradient(160deg,#2d2233,#171d2e)}.card h2{margin:0;font-family:ui-serif,Georgia,"Noto Serif KR",serif;font-size:27px;letter-spacing:-.05em}.tier-desc{min-height:43px;margin:9px 0 19px;color:var(--muted);font-size:13px}.price{font-size:27px;font-weight:850;letter-spacing:-.05em}.price small{margin-left:3px;color:var(--muted);font-size:12px;font-weight:650;letter-spacing:0}.benefits{min-height:88px;margin:22px 0 25px;padding:0;list-style:none;color:#dbe5e8;font-size:13px}.benefits li{margin:7px 0}.benefits li:before{content:"—";margin-right:8px;color:var(--tier,var(--tide));font-weight:900}.card .button{width:100%;margin-top:auto;background:transparent;border-color:rgba(238,244,242,.33);color:var(--text)}.card .button:hover{border-color:var(--tier);background:rgba(255,255,255,.07)}.notice{margin:22px 0;padding:14px 16px;border-left:2px solid var(--tide);background:rgba(147,216,212,.08);color:#dcefed}.ok{border-left-color:var(--success);background:rgba(110,231,162,.1);color:#cbf8db}.danger{border-left-color:var(--danger);background:rgba(255,125,155,.11);color:#ffd5df}.muted{color:var(--muted)}.panel{max-width:780px;margin:0 auto;padding:34px;border:1px solid var(--line);background:var(--deep);box-shadow:20px 24px 0 rgba(0,0,0,.08)}.panel h1{margin:0 0 9px;font-family:ui-serif,Georgia,"Noto Serif KR",serif;font-size:34px;font-weight:650;letter-spacing:-.06em}.panel h2{margin:28px 0 12px;font-size:18px}.choice-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;margin:24px 0;background:var(--line);border:1px solid var(--line)}.choice{display:flex;min-height:104px;flex-direction:column;justify-content:center;padding:14px;background:#102035;color:var(--text);text-decoration:none;transition:background .16s ease}.choice:hover,.choice.selected{background:#1b3950;outline:1px solid var(--tier,var(--tide));outline-offset:-1px}.choice strong{font-size:14px}.choice span{margin-top:4px;color:var(--muted);font-size:12px}.choice b{margin-top:7px;font-size:16px;letter-spacing:-.03em}input,select,textarea{width:100%;margin:7px 0 16px;padding:13px;border:1px solid var(--line);border-radius:4px;background:#0b1625;color:var(--text);font:inherit}label{font-weight:750}table{width:100%;border-collapse:collapse}td,th{padding:11px 7px;border-bottom:1px solid var(--line);text-align:left}th{color:var(--muted);font-weight:650}.footer{padding:28px 0 42px;border-top:1px solid var(--line);color:#84949e;font-size:12px}@media(max-width:800px){.wrap{width:min(100% - 28px,620px)}.hero{padding:52px 0 42px}.membership-grid{grid-template-columns:1fr}.card{min-height:auto}.choice-grid{grid-template-columns:repeat(2,1fr)}.section-head{display:block}.nav{height:66px}.nav span{gap:12px}.nav a:not(.brand){font-size:12px}}@media(max-width:420px){.choice-grid{grid-template-columns:1fr}.hero h1{font-size:44px}.nav span a:first-child{display:none}.panel{padding:24px 18px}}</style></head><body><div class="wrap"><nav class="nav"><a class="brand" href="/"><strong>BARKAN</strong><small>MEMBERSHIP</small></a><span><a href="${BASE_URL}/link">계정 연결</a><a href="${BASE_URL}/account">내 이용권</a></span></nav><main>${content}</main><footer class="footer">바르칸 열도 · 멤버십 문의 및 환불은 운영팀에 문의하세요.</footer></div></body></html>`;
}

function form(req) {
  return new Promise((resolve, reject) => {
    let raw = "";
    req.on("data", (part) => { raw += part; if (raw.length > 20_000) reject(new Error("too large")); });
    req.on("end", () => resolve(Object.fromEntries(new URLSearchParams(raw))));
    req.on("error", reject);
  });
}
function bodyJson(req) {
  return new Promise((resolve, reject) => {
    let raw = "";
    req.on("data", (part) => { raw += part; if (raw.length > 100_000) reject(new Error("too large")); });
    req.on("end", () => { try { resolve(JSON.parse(raw || "{}")); } catch { reject(new Error("invalid json")); } });
    req.on("error", reject);
  });
}
function internal(req) {
  const provided = (req.headers.authorization ?? "").replace(/^Bearer\s+/i, "");
  if (!INTERNAL_TOKEN || provided.length !== INTERNAL_TOKEN.length) return false;
  return timingSafeEqual(Buffer.from(provided), Buffer.from(INTERNAL_TOKEN));
}
function admin(req, res) {
  const encoded = (req.headers.authorization ?? "").replace(/^Basic\s+/i, "");
  let user = "", pass = "";
  try { [user, pass] = Buffer.from(encoded, "base64").toString("utf8").split(":"); } catch { /* unauthorized */ }
  const okay = ADMIN_PASSWORD && user === ADMIN_USERNAME && pass.length === ADMIN_PASSWORD.length && timingSafeEqual(Buffer.from(pass), Buffer.from(ADMIN_PASSWORD));
  if (!okay) { send(res, 401, "관리자 인증이 필요합니다.", "text/plain; charset=utf-8", { "WWW-Authenticate": 'Basic realm="Barkan VIP admin", charset="UTF-8"' }); }
  return Boolean(okay);
}

async function migrate() {
  await pool.query(`
    ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS player_name TEXT;
    ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ;
    CREATE TABLE IF NOT EXISTS link_codes (
      code_hash TEXT PRIMARY KEY, minecraft_uuid UUID NOT NULL, player_name TEXT NOT NULL,
      expires_at TIMESTAMPTZ NOT NULL, used_at TIMESTAMPTZ
    );
    CREATE INDEX IF NOT EXISTS link_codes_player_idx ON link_codes (minecraft_uuid) WHERE used_at IS NULL;
    CREATE TABLE IF NOT EXISTS web_sessions (
      token_hash TEXT PRIMARY KEY, minecraft_uuid UUID NOT NULL, csrf_token TEXT NOT NULL,
      expires_at TIMESTAMPTZ NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    ALTER TABLE web_sessions ADD COLUMN IF NOT EXISTS player_name TEXT;
    CREATE TABLE IF NOT EXISTS orders (
      order_id TEXT PRIMARY KEY, minecraft_uuid UUID NOT NULL, tier TEXT NOT NULL CHECK (tier IN ('MVP','VIP','MVP_PLUS')),
      amount_krw INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'PENDING', provider_payment_key TEXT UNIQUE,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), paid_at TIMESTAMPTZ
    );
    ALTER TABLE orders ADD COLUMN IF NOT EXISTS player_name TEXT;
    ALTER TABLE orders ADD COLUMN IF NOT EXISTS period_days INTEGER NOT NULL DEFAULT 30;
    ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_method TEXT NOT NULL DEFAULT 'TOSS';
    ALTER TABLE orders ADD COLUMN IF NOT EXISTS transfer_reference TEXT UNIQUE;
    ALTER TABLE orders ADD COLUMN IF NOT EXISTS transfer_deadline TIMESTAMPTZ;
    CREATE INDEX IF NOT EXISTS orders_transfer_pending_idx ON orders (created_at DESC)
      WHERE status = 'PENDING_TRANSFER';
    CREATE TABLE IF NOT EXISTS refund_requests (
      id UUID PRIMARY KEY, minecraft_uuid UUID NOT NULL, order_id TEXT NOT NULL REFERENCES orders(order_id),
      reason TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'PENDING', created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      decided_at TIMESTAMPTZ, decided_by TEXT
    );
  `);
}

async function session(req) {
  const value = cookies(req).vip_session;
  if (!value) return null;
  const result = await pool.query("SELECT minecraft_uuid, player_name, csrf_token FROM web_sessions WHERE token_hash=$1 AND expires_at > NOW()", [hash(value)]);
  return result.rows[0] ?? null;
}
function requireCsrf(data, current) { return current && data.csrf && data.csrf === current.csrf_token; }
async function subscription(uuid) {
  const r = await pool.query("SELECT minecraft_uuid, player_name, tier, expires_at, auto_renew, cancelled_at, expires_at > NOW() AS active FROM subscriptions WHERE minecraft_uuid=$1", [uuid]);
  return r.rows[0] ?? null;
}
async function extendSubscription(client, uuid, name, tier, days) {
  const r = await client.query(`INSERT INTO subscriptions (minecraft_uuid, player_name, tier, expires_at, auto_renew, cancelled_at)
    VALUES ($1,$2,$3,NOW()+($4::int * INTERVAL '1 day'),FALSE,NULL)
    ON CONFLICT (minecraft_uuid) DO UPDATE SET player_name=EXCLUDED.player_name, tier=EXCLUDED.tier,
      expires_at=GREATEST(subscriptions.expires_at,NOW())+($4::int * INTERVAL '1 day'), cancelled_at=NULL, updated_at=NOW()
    RETURNING tier, expires_at`, [uuid, name, tier, days]);
  return r.rows[0];
}

async function toss(path, method, payload) {
  if (!TOSS_SECRET_KEY) throw new Error("토스 시크릿 키가 설정되지 않았습니다.");
  const auth = Buffer.from(`${TOSS_SECRET_KEY}:`).toString("base64");
  const response = await fetch(`https://api.tosspayments.com${path}`, { method, headers: { Authorization: `Basic ${auth}`, "Content-Type": "application/json" }, body: payload ? JSON.stringify(payload) : undefined });
  const data = await response.json();
  if (!response.ok) throw new Error(data.message ?? "토스 요청 실패");
  return data;
}

function validMonths(value) {
  const months = Number.parseInt(value, 10);
  return PURCHASE_MONTHS.includes(months) ? months : RECOMMENDED_MONTHS;
}
function selectionFrom(tierId, months) {
  const tier = TIERS[tierId];
  return tier ? { tierId, tier, months: validMonths(months) } : null;
}
function purchaseUrl(tierId, months) { return `${BASE_URL}/buy/${encodeURIComponent(tierId)}?months=${validMonths(months)}`; }
function linkUrl(selection) { return `${BASE_URL}/link?tier=${encodeURIComponent(selection.tierId)}&months=${selection.months}`; }

function home(requestedTier, requestedMonths) {
  const tierId = TIERS[requestedTier] ? requestedTier : "VIP";
  const selected = selectionFrom(tierId, requestedMonths);
  const cashOptions = [
    { pay: 5000, cash: 5000, bonus: 0 },
    { pay: 10000, cash: 10500, bonus: 500 },
    { pay: 30000, cash: 33000, bonus: 3000 }
  ].map((product) => {
    return `<a class="store-card cash-card" href="${BASE_URL}/link"><p class="store-label">캐시 충전</p><h3>${product.cash.toLocaleString()} 캐시</h3><p class="store-copy">${product.bonus ? `${product.bonus.toLocaleString()} 보너스 캐시 포함` : "기본 충전"}</p><div class="store-price">₩${product.pay.toLocaleString()}</div><span class="store-state">${product.bonus ? `+${product.bonus.toLocaleString()} 캐시` : "1캐시 · ₩1"}</span><span class="store-action">계정 연결하기 →</span></a>`;
  }).join("");
  const packages = [
    { title: "항해 패키지", tierId: "VIP", cash: 10000, recommended: true },
    { title: "원정 패키지", tierId: "MVP", cash: 20000 },
    { title: "개척 패키지", tierId: "MVP_PLUS", cash: 35000, paidCash: 30000, best: true }
  ].map((pack) => {
    const tier = TIERS[pack.tierId]; const total = periodPrice(tier, RECOMMENDED_MONTHS) + (pack.paidCash ?? pack.cash);
    return `<a class="store-card package-card${pack.best ? " best" : ""}" style="--tier:${tier.color}" href="${BASE_URL}/link">${pack.recommended ? `<span class="recommend-badge">서버 추천</span>` : ""}${pack.best ? `<span class="value-badge">★ 최고 가성비</span>` : ""}<p class="store-label">150일 패키지</p><h3>${pack.title}</h3><ul><li><b style="color:${tier.color}">${tier.name}</b> 150일</li><li>${pack.cash.toLocaleString()} 캐시${pack.best ? " <em>+5,000 보너스</em>" : ""}</li></ul><div class="store-price">₩${total.toLocaleString()}</div><span class="store-action">이 패키지 선택 →</span></a>`;
  }).join("");
  const cards = Object.entries(TIERS).map(([key, tier]) => `<section class="card" style="--tier:${tier.color}"><h2 style="color:${tier.color}">${tier.name}</h2><div class="price">₩${tier.price.toLocaleString()} <small>30일</small></div><ul class="benefits">${tier.benefits.map((b) => `<li>${esc(b)}</li>`).join("")}</ul><a class="button" href="${BASE_URL}/?tier=${encodeURIComponent(key)}&months=1#periods">${tier.name} 선택</a></section>`).join("");
  const tierTabs = Object.entries(TIERS).map(([key, tier]) => `<a class="tier-tab${key === tierId ? " selected" : ""}" style="--tier:${tier.color}" href="${BASE_URL}/?tier=${encodeURIComponent(key)}&months=${selected.months}#periods">${tier.name}</a>`).join("");
  const options = PURCHASE_MONTHS.map((months) => `<a class="choice${months === selected.months ? " selected" : ""}" style="--tier:${selected.tier.color}" href="${BASE_URL}/?tier=${encodeURIComponent(tierId)}&months=${months}#periods"><strong>${periodLabel(months)}</strong><b>₩${periodPrice(selected.tier, months).toLocaleString()}</b><span>월 ₩${monthlyPrice(selected.tier, months).toLocaleString()}</span></a>`).join("");
  return layout("멤버십", `<style>
    main{display:flex;flex-direction:column}.hero{order:1}.section-head{order:2}.membership-grid{order:3}main>.shop-section:last-of-type{order:4}.config{order:5}main>.shop-section:not(:last-of-type){order:6}.support{display:none}.store-card{display:block;color:var(--text);text-decoration:none}.store-card:hover{transform:translateY(-3px);border-color:rgba(188,229,255,.48)}.store-action{display:block;margin-top:17px;color:var(--tide);font-size:13px;font-weight:850}.store-card.package-card{position:relative;padding-top:54px}.store-card.best{position:relative;isolation:isolate;border:1px solid #f4c75d;background:linear-gradient(145deg,rgba(105,74,20,.92),rgba(41,29,27,.96))!important;box-shadow:0 0 0 1px rgba(255,227,135,.3),0 18px 38px rgba(124,80,14,.32)}.store-card.best:before{content:"";position:absolute;z-index:-1;inset:-10px;border-radius:26px;background:radial-gradient(ellipse at 50% 0,rgba(255,215,105,.35),transparent 62%);filter:blur(9px)}.store-card.best .store-label,.store-card.best .store-action{color:#ffe49b}.store-card.best .store-price{color:#fff0b7}.value-badge,.recommend-badge{position:absolute;z-index:3;top:15px;margin:0;padding:6px 9px;border-radius:999px;font-size:11px;font-weight:950;letter-spacing:-.03em}.value-badge{right:15px;border:1px solid rgba(255,235,171,.7);background:linear-gradient(135deg,#ffedaf,#c98f27);box-shadow:0 4px 15px rgba(255,189,49,.26);color:#3c2606}.recommend-badge{left:15px;border:1px solid rgba(143,231,255,.55);background:rgba(55,142,190,.3);color:#caf4ff}
    body{background:radial-gradient(860px 530px at 8% -8%,#24386e 0,transparent 65%),radial-gradient(720px 580px at 98% 5%,#3a1f5d 0,transparent 65%),#080d1e}
    .hero{padding:68px 62px 62px;border:1px solid rgba(186,209,255,.15);border-radius:30px;background:linear-gradient(130deg,rgba(20,31,70,.96),rgba(14,20,47,.93));box-shadow:0 25px 60px rgba(0,0,0,.26)}
    .hero:after{top:-245px;right:-170px;width:430px;height:430px;border:0;background:radial-gradient(circle,rgba(114,230,255,.25),transparent 68%)}
    .hero:before{display:none}.hero h1{font-family:ui-sans-serif,system-ui,"Apple SD Gothic Neo","Noto Sans KR",sans-serif;font-weight:850}.hero h1 span{color:transparent;background:linear-gradient(100deg,#9ceeff,#c4b1ff 64%,#ffb4e2);-webkit-background-clip:text;background-clip:text}.membership-grid{gap:16px;border:0;background:none}.card{position:relative;overflow:hidden;border:1px solid rgba(186,209,255,.15);border-radius:22px;box-shadow:0 18px 34px rgba(0,0,0,.14)}.card:before{content:"";position:absolute;inset:0;background:linear-gradient(145deg,color-mix(in srgb,var(--tier) 18%,transparent),transparent 40%);pointer-events:none}.card>*{position:relative}.card:first-child{background:linear-gradient(160deg,rgba(24,35,76,.96),rgba(13,20,43,.93))}.card:nth-child(2){background:linear-gradient(160deg,rgba(48,40,62,.96),rgba(18,22,46,.93))}.card:nth-child(3){background:linear-gradient(160deg,rgba(61,32,64,.96),rgba(20,20,48,.93))}.card .button{border-radius:12px;background:rgba(255,255,255,.06)}.recommended{margin:12px 0 6px;color:#dbe8ff;font-size:12px;font-weight:800}.card .price{margin-bottom:2px}.tier-tabs{display:grid;grid-template-columns:repeat(3,1fr);gap:9px;margin:18px 0}.tier-tab{padding:12px;border:1px solid rgba(186,209,255,.16);border-radius:10px;background:rgba(8,14,34,.32);color:var(--text);font-weight:800;text-align:center;text-decoration:none}.tier-tab.selected,.tier-tab:hover{border-color:var(--tier);background:rgba(255,255,255,.08)}.config{margin-top:54px;padding:32px;border:1px solid rgba(186,209,255,.16);border-radius:22px;background:linear-gradient(150deg,rgba(23,34,74,.9),rgba(13,18,41,.92));box-shadow:0 20px 44px rgba(0,0,0,.16)}.config h2{margin:0;font-size:24px}.config p{margin:6px 0 0}.config .choice-grid{grid-template-columns:repeat(4,1fr);margin:20px 0}.config .choice{border-radius:10px}.support{margin:20px 0 0;color:var(--muted);font-size:13px}.support a{color:var(--aqua)}.shop-section{margin-top:64px}.shop-section h2{margin:0;font-size:26px;letter-spacing:-.05em}.shop-section>p{margin:7px 0 18px}.store-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}.store-card{min-height:224px;padding:25px;border:1px solid rgba(186,209,255,.15);border-radius:20px;background:linear-gradient(150deg,rgba(25,42,81,.86),rgba(13,20,46,.92));box-shadow:0 18px 34px rgba(0,0,0,.14)}.cash-card:nth-child(2){background:linear-gradient(150deg,rgba(29,57,88,.92),rgba(14,24,51,.95))}.cash-card:nth-child(3){background:linear-gradient(150deg,rgba(39,43,86,.92),rgba(18,22,53,.95))}.store-label{margin:0 0 13px;color:var(--tide);font-size:11px;font-weight:850;letter-spacing:.12em}.store-card h3{margin:0;font-size:23px;letter-spacing:-.05em}.store-copy{min-height:40px;margin:8px 0;color:var(--muted);font-size:13px}.store-price{margin-top:21px;font-size:25px;font-weight:900;letter-spacing:-.05em}.store-state{display:block;margin-top:5px;color:#a8bdd4;font-size:12px}.package-card{background:linear-gradient(150deg,color-mix(in srgb,var(--tier) 16%,#182648),#10172e)}.package-card ul{min-height:44px;margin:11px 0 0;padding:0;list-style:none;color:#dce6fa;font-size:13px}.package-card li:before{content:"+";margin-right:7px;color:var(--tier);font-weight:900}
    @media(max-width:800px){.hero{padding:42px 26px;border-radius:23px}}
    @media(max-width:800px){.store-grid{grid-template-columns:1fr}.store-card{min-height:0}}@media(max-width:620px){.config .choice-grid{grid-template-columns:repeat(2,1fr)}}
  </style><section class="hero"><p class="hero-kicker">BARKAN ISLANDS</p><h1>VIP · MVP · <span>MVP+</span></h1><p class="muted">채팅 태그, 전용 외형, 프로필 꾸미기. 원하는 혜택이 있는 등급을 선택하세요.</p></section><div class="section-head"><div><h2>이용권</h2><p>각 등급은 150일 기준으로 안내합니다.</p></div></div><div class="membership-grid">${cards}</div><section class="config" id="periods"><h2>기간 설정</h2><p class="muted">${selected.tier.name} 이용권의 기간과 금액을 선택하세요.</p><div class="tier-tabs">${tierTabs}</div><div class="choice-grid">${options}</div><div class="notice"><b style="color:${selected.tier.color}">${selected.tier.name}</b> · <b>${periodLabel(selected.months)}</b><br><span style="font-size:22px;font-weight:900">₩${periodPrice(selected.tier, selected.months).toLocaleString()}</span> <span class="muted">· 월 ₩${monthlyPrice(selected.tier, selected.months).toLocaleString()}</span></div><a class="button" href="${linkUrl(selected)}">게임 계정 연결하기</a></section><section class="shop-section"><h2>캐시 충전</h2><p class="muted">1캐시 = ₩1 · 충전한 캐시는 게임 안 <code>/캐시상점</code>에서 사용합니다.</p><div class="store-grid">${cashOptions}</div></section><section class="shop-section"><h2>패키지</h2><p class="muted">멤버십 150일과 캐시를 함께 담은 구성입니다.</p><div class="store-grid">${packages}</div><p class="support">문의 및 환불: <a href="mailto:wsiwsiwsi123@gmail.com">wsiwsiwsi123@gmail.com</a></p></section>`);
}
function accountPage(current, sub, refunds, pendingOrders, notice = "") {
  const tier = sub ? TIERS[sub.tier] : null;
  const status = sub?.active ? `<span style="color:#6bf0a2">활성</span>` : "미구독 또는 만료";
  const pending = pendingOrders.length ? `<h2>입금 확인 대기</h2><table>${pendingOrders.map((o) => `<tr><th>${esc(TIERS[o.tier].name)} · ${periodLabel(monthsForDays(o.period_days))}</th><td>₩${Number(o.amount_krw).toLocaleString()}<br><a href="${BASE_URL}/bank-transfer/orders/${encodeURIComponent(o.order_id)}">입금 안내 보기</a></td></tr>`).join("")}</table>` : "";
  return layout("내 이용권", `<div class="panel"><h1>내 이용권</h1>${notice ? `<div class="notice ok">${esc(notice)}</div>` : ""}<table><tr><th>게임 계정</th><td>${esc(sub?.player_name ?? current.player_name ?? "연결됨")}</td></tr><tr><th>상태</th><td>${status}</td></tr><tr><th>등급</th><td>${tier ? `<b style="color:${tier.color}">${tier.name}</b>` : "-"}</td></tr><tr><th>만료일</th><td>${sub?.expires_at ? new Date(sub.expires_at).toLocaleString("ko-KR", { timeZone: "Asia/Seoul" }) : "-"}</td></tr></table>${pending}${sub?.active ? `<hr><form method="post" action="${BASE_URL}/account/refund"><input type="hidden" name="csrf" value="${esc(current.csrf_token)}"><label>환불 사유</label><textarea name="reason" minlength="5" maxlength="500" required placeholder="환불 요청 사유를 입력하세요."></textarea><button style="background:#c34d5d">환불 요청하기</button></form>` : `<p class="muted">원하는 등급과 기간을 선택해 이용권을 구매하세요.</p><a class="button" href="${BASE_URL}/">이용권 보기</a>`}<h2>환불 요청</h2>${refunds.length ? `<table>${refunds.map((r) => `<tr><td>${esc(r.status)}</td><td>${esc(r.reason)}</td><td>${new Date(r.created_at).toLocaleDateString("ko-KR")}</td></tr>`).join("")}</table>` : "<p class=\"muted\">요청 내역이 없습니다.</p>"}</div>`);
}

function purchasePage(current, tierId, requestedMonths) {
  const tier = TIERS[tierId];
  if (!tier) return layout("찾을 수 없음", `<div class="panel"><h1>등급을 찾을 수 없습니다.</h1></div>`);
  const months = validMonths(requestedMonths);
  const selected = selectionFrom(tierId, months);
  const options = PURCHASE_MONTHS.map((candidate) => {
    const active = candidate === months ? " selected" : "";
    const duration = periodLabel(candidate);
    return `<a class="choice${active}" style="--tier:${tier.color}" href="${purchaseUrl(tierId, candidate)}"><strong>${duration}</strong><b>₩${periodPrice(tier, candidate).toLocaleString()}</b><span>월 ₩${monthlyPrice(tier, candidate).toLocaleString()}</span></a>`;
  }).join("");
  const action = !current
    ? `<a class="button" href="${linkUrl(selected)}">게임 계정 연결하기</a><p class="muted" style="margin:13px 0 0">다음 단계에서 게임 안에서 받은 연결 코드를 입력합니다.</p>`
    : !bankTransferConfigured()
      ? `<div class="notice">현재 입금 계좌 정보를 준비 중입니다. 계좌가 설정되면 이 선택 그대로 주문할 수 있어요.</div>`
      : `<form method="post" action="${BASE_URL}/bank-transfer/orders"><input type="hidden" name="csrf" value="${esc(current.csrf_token)}"><input type="hidden" name="tier" value="${esc(tierId)}"><input type="hidden" name="months" value="${months}"><button>이 가격으로 입금 안내 만들기</button></form>`;
  return layout(`${tier.name} 이용권`, `<div class="panel"><h1 style="color:${tier.color}">${tier.name} 이용권</h1><p class="muted">기간을 선택하면 아래 금액으로 진행합니다.</p><div class="choice-grid">${options}</div><div class="notice"><b>${periodLabel(months)}</b><br><span style="font-size:22px;font-weight:900">₩${periodPrice(tier, months).toLocaleString()}</span> <span class="muted">· 월 ₩${monthlyPrice(tier, months).toLocaleString()}</span></div>${action}</div>`);
}

function linkPage(selection, error = "") {
  const chosen = selection ? `<div class="notice"><b style="color:${selection.tier.color}">${selection.tier.name}</b> · ${periodLabel(selection.months)} · <b>₩${periodPrice(selection.tier, selection.months).toLocaleString()}</b></div>` : `<p class="muted">게임 안에서 <code>/구독</code>을 실행해 1회용 연결 코드를 받은 뒤 입력하세요.</p>`;
  const hidden = selection ? `<input type="hidden" name="tier" value="${esc(selection.tierId)}"><input type="hidden" name="months" value="${selection.months}">` : "";
  return layout("게임 계정 연결", `<div class="panel"><h1>게임 계정 연결</h1>${chosen}${error ? `<div class="notice danger">${esc(error)}</div>` : ""}<form method="post" action="${BASE_URL}/link">${hidden}<label>게임 안에서 받은 코드</label><input name="code" maxlength="16" autocomplete="one-time-code" required placeholder="예: BK-AB12CD"><button>연결하기</button></form><p class="muted">게임에서 <code>/구독</code>을 실행하면 코드가 발급됩니다. 코드는 10분 동안 사용할 수 있습니다.</p></div>`);
}

function transferReference() { return `BK${randomBytes(4).toString("hex").toUpperCase()}`; }

async function route(req, res) {
  const url = new URL(req.url, "http://localhost");
  // Caddy handle_path /vip/* strips the complete /vip/ prefix, leaving an empty path for /vip/.
  const path = url.pathname || "/";
  if (req.method === "GET" && path === "/health") { await pool.query("SELECT 1"); return json(res, 200, { ok: true, paymentConfigured: Boolean(TOSS_CLIENT_KEY && TOSS_SECRET_KEY) }); }
  if (req.method === "GET" && path === "/") return send(res, 200, home(url.searchParams.get("tier"), url.searchParams.get("months")));
  if (req.method === "GET" && path === "/link") return send(res, 200, linkPage(selectionFrom(url.searchParams.get("tier"), url.searchParams.get("months"))));
  if (req.method === "POST" && path === "/link") {
    const data = await form(req); const code = String(data.code ?? "").toUpperCase().replace(/[^A-Z0-9-]/g, ""); const selected = selectionFrom(data.tier, data.months);
    const client = await pool.connect();
    try {
      await client.query("BEGIN");
      const found = await client.query("SELECT minecraft_uuid,player_name FROM link_codes WHERE code_hash=$1 AND used_at IS NULL AND expires_at>NOW() FOR UPDATE", [hash(code)]);
      if (!found.rowCount) throw new Error("코드가 없거나 만료되었습니다. 게임에서 다시 발급하세요.");
      const webToken = token(); const csrf = token(24);
      await client.query("UPDATE link_codes SET used_at=NOW() WHERE code_hash=$1", [hash(code)]);
      await client.query("INSERT INTO web_sessions (token_hash,minecraft_uuid,player_name,csrf_token,expires_at) VALUES ($1,$2,$3,$4,NOW()+INTERVAL '30 days')", [hash(webToken), found.rows[0].minecraft_uuid, found.rows[0].player_name, csrf]);
      await client.query("COMMIT");
      return redirect(res, selected ? purchaseUrl(selected.tierId, selected.months) : `${BASE_URL}/account`, [`vip_session=${encodeURIComponent(webToken)}; Path=/vip; Max-Age=2592000; HttpOnly; Secure; SameSite=Lax`]);
    } catch (error) { await client.query("ROLLBACK"); return send(res, 400, linkPage(selected, error.message)); } finally { client.release(); }
  }
  if (req.method === "GET" && path === "/account") {
    const current = await session(req); if (!current) return redirect(res, `${BASE_URL}/link`);
    const sub = await subscription(current.minecraft_uuid);
    const refunds = await pool.query("SELECT status,reason,created_at FROM refund_requests WHERE minecraft_uuid=$1 ORDER BY created_at DESC", [current.minecraft_uuid]);
    const pending = await pool.query("SELECT order_id,tier,amount_krw,period_days FROM orders WHERE minecraft_uuid=$1 AND status='PENDING_TRANSFER' AND transfer_deadline>NOW() ORDER BY created_at DESC", [current.minecraft_uuid]);
    return send(res, 200, accountPage(current, sub, refunds.rows, pending.rows, url.searchParams.get("notice") ?? ""));
  }
  if (req.method === "POST" && path === "/account/cancel") {
    const current = await session(req); const data = await form(req); if (!requireCsrf(data, current)) return send(res, 403, "잘못된 요청입니다.");
    await pool.query("UPDATE subscriptions SET auto_renew=FALSE,cancelled_at=NOW(),updated_at=NOW() WHERE minecraft_uuid=$1", [current.minecraft_uuid]);
    return redirect(res, `${BASE_URL}/account?notice=${encodeURIComponent("자동 갱신을 취소했습니다. 이미 결제한 기간까지 혜택은 유지됩니다.")}`);
  }
  if (req.method === "POST" && path === "/account/refund") {
    const current = await session(req); const data = await form(req); if (!requireCsrf(data, current)) return send(res, 403, "잘못된 요청입니다.");
    const reason = String(data.reason ?? "").trim(); if (reason.length < 5 || reason.length > 500) return send(res, 400, "환불 사유는 5~500자로 입력하세요.");
    const order = await pool.query("SELECT order_id FROM orders WHERE minecraft_uuid=$1 AND status='PAID' ORDER BY paid_at DESC LIMIT 1", [current.minecraft_uuid]);
    if (!order.rowCount) return send(res, 400, "환불 가능한 결제 내역이 없습니다.");
    const existing = await pool.query("SELECT 1 FROM refund_requests WHERE order_id=$1 AND status IN ('PENDING','REFUNDED')", [order.rows[0].order_id]);
    if (existing.rowCount) return send(res, 409, "이미 처리 중이거나 완료된 환불 요청입니다.");
    await pool.query("INSERT INTO refund_requests (id,minecraft_uuid,order_id,reason) VALUES ($1,$2,$3,$4)", [randomUUID(), current.minecraft_uuid, order.rows[0].order_id, reason]);
    return redirect(res, `${BASE_URL}/account?notice=${encodeURIComponent("환불 요청이 접수되었습니다. 운영팀 검토 후 결과를 알려드립니다.")}`);
  }
  if (req.method === "GET" && path.startsWith("/buy/")) {
    const current = await session(req);
    return send(res, 200, purchasePage(current, path.slice(5), url.searchParams.get("months")));
  }
  if (req.method === "POST" && path === "/bank-transfer/orders") {
    const current = await session(req); const data = await form(req);
    if (!requireCsrf(data, current)) return send(res, 403, "잘못된 요청입니다.");
    if (!bankTransferConfigured()) return send(res, 503, layout("입금 계좌 준비 중", `<div class="panel"><p>운영팀이 계좌이체 정보를 설정하는 중입니다.</p></div>`));
    const tierId = String(data.tier ?? ""); const tier = TIERS[tierId];
    const months = Number.parseInt(data.months, 10);
    if (!tier || !PURCHASE_MONTHS.includes(months)) return send(res, 400, "기간 선택이 올바르지 않습니다.");
    const orderId = `BK-${randomUUID().replaceAll("-", "")}`;
    const reference = transferReference();
    await pool.query("UPDATE orders SET status='EXPIRED' WHERE minecraft_uuid=$1 AND status='PENDING_TRANSFER'", [current.minecraft_uuid]);
    await pool.query("INSERT INTO orders (order_id,minecraft_uuid,player_name,tier,amount_krw,status,period_days,payment_method,transfer_reference,transfer_deadline) VALUES ($1,$2,$3,$4,$5,'PENDING_TRANSFER',$6,'BANK_TRANSFER',$7,NOW()+INTERVAL '24 hours')", [orderId, current.minecraft_uuid, current.player_name, tierId, periodPrice(tier, months), periodDays(months), reference]);
    return redirect(res, `${BASE_URL}/bank-transfer/orders/${encodeURIComponent(orderId)}`);
  }
  if (req.method === "GET" && /^\/bank-transfer\/orders\/BK-[A-Za-z0-9]+$/.test(path)) {
    const current = await session(req); if (!current) return redirect(res, `${BASE_URL}/link`);
    const orderId = path.split("/").at(-1);
    const result = await pool.query("SELECT * FROM orders WHERE order_id=$1 AND minecraft_uuid=$2", [orderId, current.minecraft_uuid]);
    if (!result.rowCount) return send(res, 404, layout("주문을 찾을 수 없음", `<div class="panel"><p>해당 주문을 찾을 수 없습니다.</p></div>`));
    const order = result.rows[0]; const tier = TIERS[order.tier];
    if (order.status !== "PENDING_TRANSFER") return send(res, 200, layout("주문 상태", `<div class="panel"><h1>주문 상태: ${esc(order.status)}</h1><a class="button" href="${BASE_URL}/account">내 이용권</a></div>`));
    if (!bankTransferConfigured()) return send(res, 503, layout("입금 계좌 준비 중", `<div class="panel"><p>운영팀이 계좌이체 정보를 설정하는 중입니다.</p></div>`));
    const deadline = new Date(order.transfer_deadline).toLocaleString("ko-KR", { timeZone: "Asia/Seoul" });
    return send(res, 200, layout("계좌이체 안내", `<div class="panel"><h1>계좌이체 안내</h1><div class="notice">입금 확인 후 운영팀이 ${esc(current.player_name ?? "게임")} 계정에 혜택을 지급합니다.</div><table><tr><th>이용권</th><td><b style="color:${tier.color}">${tier.name}</b> · ${periodLabel(monthsForDays(order.period_days))}</td></tr><tr><th>입금 금액</th><td><b>₩${Number(order.amount_krw).toLocaleString()}</b></td></tr><tr><th>은행</th><td>${esc(BANK_TRANSFER_BANK)}</td></tr><tr><th>계좌번호</th><td><b>${esc(BANK_TRANSFER_ACCOUNT_NUMBER)}</b></td></tr><tr><th>예금주</th><td>${esc(BANK_TRANSFER_ACCOUNT_HOLDER)}</td></tr><tr><th>입금자명</th><td><b>${esc(order.transfer_reference)}</b></td></tr><tr><th>입금 기한</th><td>${deadline}</td></tr></table><p class="muted">입금자명을 정확히 입력해 주세요. 기한이 지나거나 다른 이름으로 입금했다면 운영팀에 주문번호를 알려주세요.</p><a class="button alt" href="${BASE_URL}/account">내 이용권으로</a></div>`));
  }
  if (req.method === "GET" && path.startsWith("/pay/")) {
    const current = await session(req); if (!current) return redirect(res, `${BASE_URL}/link`);
    const tierId = path.slice(5); const tier = TIERS[tierId]; if (!tier) return send(res, 404, "등급을 찾을 수 없습니다.");
    if (!TOSS_CLIENT_KEY || !TOSS_SECRET_KEY) return send(res, 503, layout("결제 준비 중", `<div class="panel"><h1>결제 준비 중</h1><p class="muted">운영팀이 결제 계약을 설정하는 중입니다. 현재는 결제를 받을 수 없습니다.</p></div>`));
    const orderId = `BK-${randomUUID().replaceAll("-", "")}`;
    await pool.query("INSERT INTO orders (order_id,minecraft_uuid,tier,amount_krw) VALUES ($1,$2,$3,$4)", [orderId, current.minecraft_uuid, tierId, tier.price]);
    const sub = await subscription(current.minecraft_uuid);
    const customerKey = `mc-${current.minecraft_uuid}`;
    const config = JSON.stringify({ clientKey: TOSS_CLIENT_KEY, customerKey, orderId, amount: tier.price, orderName: `바르칸 열도 ${tier.name} 30일 이용권`, successUrl: `${BASE_URL}/payment/success`, failUrl: `${BASE_URL}/payment/fail` }).replace(/</g, "\\u003c");
    return send(res, 200, layout("결제", `<div class="panel"><h1>${esc(tier.name)} 결제</h1><p class="price">₩${tier.price.toLocaleString()}</p><p class="muted">결제 완료 후 ${esc(sub?.player_name ?? "게임")} 계정에 30일이 추가됩니다.</p><button id="pay">카드로 결제</button><p id="error" class="notice danger" hidden></p><script src="https://js.tosspayments.com/v2/standard"></script><script>const c=${config};document.querySelector('#pay').onclick=async()=>{try{const p=TossPayments(c.clientKey).payment({customerKey:c.customerKey});await p.requestPayment({method:'CARD',amount:{currency:'KRW',value:c.amount},orderId:c.orderId,orderName:c.orderName,successUrl:c.successUrl,failUrl:c.failUrl});}catch(e){const x=document.querySelector('#error');x.hidden=false;x.textContent=e.message||'결제를 시작하지 못했습니다.';}};</script></div>`));
  }
  if (req.method === "GET" && path === "/payment/success") {
    const current = await session(req); if (!current) return redirect(res, `${BASE_URL}/link`);
    const orderId = url.searchParams.get("orderId") ?? ""; const paymentKey = url.searchParams.get("paymentKey") ?? ""; const amount = Number(url.searchParams.get("amount"));
    const order = await pool.query("SELECT * FROM orders WHERE order_id=$1 AND minecraft_uuid=$2 AND status='PENDING'", [orderId, current.minecraft_uuid]);
    if (!order.rowCount || !paymentKey || amount !== order.rows[0].amount_krw) return send(res, 400, layout("결제 확인 실패", `<div class="panel"><div class="notice danger">주문 정보가 올바르지 않습니다.</div></div>`));
    const approved = await toss("/v1/payments/confirm", "POST", { paymentKey, orderId, amount });
    const client = await pool.connect();
    try { await client.query("BEGIN"); await client.query("UPDATE orders SET status='PAID',provider_payment_key=$1,paid_at=NOW() WHERE order_id=$2", [paymentKey, orderId]); await client.query("INSERT INTO payment_events (provider,provider_event_id,minecraft_uuid,status,amount_krw,payload) VALUES ('toss',$1,$2,'DONE',$3,$4) ON CONFLICT DO NOTHING", [paymentKey, current.minecraft_uuid, amount, approved]); const sub = await extendSubscription(client, current.minecraft_uuid, current.player_name ?? "Unknown", order.rows[0].tier, 30); await client.query("COMMIT"); return send(res, 200, layout("결제 완료", `<div class="panel"><h1>결제가 완료되었습니다</h1><p class="muted">${esc(TIERS[order.rows[0].tier].name)} 혜택이 반영되었습니다. 만료일: ${new Date(sub.expires_at).toLocaleString("ko-KR", { timeZone: "Asia/Seoul" })}</p><a class="button" href="${BASE_URL}/account">내 구독 보기</a></div>`)); } catch (error) { await client.query("ROLLBACK"); throw error; } finally { client.release(); }
  }
  if (req.method === "GET" && path === "/payment/fail") return send(res, 400, layout("결제 실패", `<div class="panel"><div class="notice danger">${esc(url.searchParams.get("message") ?? "결제가 취소되었거나 승인되지 않았습니다.")}</div><a class="button" href="${BASE_URL}/">다시 선택</a></div>`));
  if (req.method === "GET" && path === "/admin") return redirect(res, STATS_ADMIN_URL);
  if (req.method === "POST" && /^\/admin\/refund\/[0-9a-f-]+$/i.test(path)) {
    return send(res, 410, layout("관리 페이지 이전", `<div class="panel"><h1>관리 페이지가 이전되었습니다</h1><p>환불 처리는 통계 대시보드의 멤버십 메뉴에서 진행하세요.</p><a class="button" href="${esc(STATS_ADMIN_URL)}">멤버십 관리 열기</a></div>`));
  }
  if (req.method === "POST" && path === "/webhooks/toss") {
    // 웹훅은 결제 권한을 부여하지 않는다. 성공 승인 경로는 주문·금액을 토스 API로 직접 검증한다.
    // 여기서는 원본 이벤트를 원장에 보존하고, 외부 취소 알림만 결제 상태에 반영한다.
    const event = await bodyJson(req); const paymentKey = event?.data?.paymentKey;
    if (!paymentKey || typeof paymentKey !== "string") return json(res, 400, { error: "invalid_event" });
    let verified = event.data;
    if (TOSS_SECRET_KEY) { try { verified = await toss(`/v1/payments/${encodeURIComponent(paymentKey)}`, "GET"); } catch (error) { console.warn("toss webhook verification failed", error.message); return json(res, 400, { error: "unverified_event" }); } }
    const order = await pool.query("SELECT order_id,minecraft_uuid,amount_krw FROM orders WHERE provider_payment_key=$1", [paymentKey]);
    const eventId = `webhook-${event.eventType ?? "UNKNOWN"}-${paymentKey}-${event.createdAt ?? ""}`;
    await pool.query("INSERT INTO payment_events (provider,provider_event_id,minecraft_uuid,status,amount_krw,payload) VALUES ('toss',$1,$2,$3,$4,$5) ON CONFLICT DO NOTHING", [eventId, order.rows[0]?.minecraft_uuid ?? null, verified.status ?? event.eventType ?? "UNKNOWN", order.rows[0]?.amount_krw ?? null, event]);
    if (order.rowCount && verified.status === "CANCELED") await pool.query("UPDATE orders SET status='REFUNDED' WHERE order_id=$1", [order.rows[0].order_id]);
    return json(res, 200, { ok: true });
  }
  if (path === "/internal/refunds" && req.method === "GET") {
    if (!internal(req)) return json(res, 401, { error: "unauthorized" });
    const r = await pool.query("SELECT rr.id,rr.reason,rr.status,rr.created_at,o.order_id,o.amount_krw,o.payment_method,COALESCE(o.player_name,s.player_name) AS player_name FROM refund_requests rr JOIN orders o ON o.order_id=rr.order_id LEFT JOIN subscriptions s ON s.minecraft_uuid=rr.minecraft_uuid ORDER BY rr.created_at DESC LIMIT 100");
    return json(res, 200, { rows: r.rows });
  }
  if (/^\/internal\/refunds\/[0-9a-f-]+$/i.test(path) && req.method === "POST") {
    if (!internal(req)) return json(res, 401, { error: "unauthorized" });
    const data = await bodyJson(req); const id = path.split("/").at(-1); const actor = String(data.decidedBy ?? "stats-admin").slice(0, 100);
    const row = await pool.query("SELECT rr.*,o.provider_payment_key,o.amount_krw,o.payment_method FROM refund_requests rr JOIN orders o ON o.order_id=rr.order_id WHERE rr.id=$1 AND rr.status='PENDING'", [id]);
    if (!row.rowCount) return json(res, 404, { error: "refund_not_found" });
    if (data.action === "reject") { await pool.query("UPDATE refund_requests SET status='REJECTED',decided_at=NOW(),decided_by=$1 WHERE id=$2", [actor, id]); return json(res, 200, { message: "환불 요청을 거절했습니다." }); }
    if (data.action !== "approve") return json(res, 400, { error: "invalid_action" });
    const request = row.rows[0];
    // 계좌이체는 PG가 돈을 보관하지 않는다. 관리자가 실제 환불 송금을 마친 뒤에만 이 액션을 누른다.
    if (request.payment_method === "BANK_TRANSFER") {
      const client = await pool.connect();
      try { await client.query("BEGIN"); await client.query("UPDATE refund_requests SET status='REFUNDED',decided_at=NOW(),decided_by=$1 WHERE id=$2", [actor, id]); await client.query("UPDATE orders SET status='REFUNDED' WHERE order_id=$1", [request.order_id]); await client.query("UPDATE subscriptions SET expires_at=NOW(),auto_renew=FALSE,cancelled_at=NOW(),updated_at=NOW() WHERE minecraft_uuid=$1", [request.minecraft_uuid]); await client.query("INSERT INTO payment_events (provider,provider_event_id,minecraft_uuid,status,amount_krw,payload) VALUES ('bank_transfer',$1,$2,'REFUNDED',$3,$4) ON CONFLICT DO NOTHING", [`refund-${request.order_id}`, request.minecraft_uuid, request.amount_krw, { refundedBy: actor }]); await client.query("COMMIT"); } catch (error) { await client.query("ROLLBACK"); throw error; } finally { client.release(); }
      return json(res, 200, { message: "수동 계좌 환불 완료로 기록하고 이용권을 종료했습니다." });
    }
    const result = await toss(`/v1/payments/${encodeURIComponent(request.provider_payment_key)}/cancel`, "POST", { cancelReason: "바르칸 열도 운영자 승인 환불" });
    const client = await pool.connect();
    try { await client.query("BEGIN"); await client.query("UPDATE refund_requests SET status='REFUNDED',decided_at=NOW(),decided_by=$1 WHERE id=$2", [actor, id]); await client.query("UPDATE orders SET status='REFUNDED' WHERE order_id=$1", [request.order_id]); await client.query("UPDATE subscriptions SET expires_at=NOW(),auto_renew=FALSE,cancelled_at=NOW(),updated_at=NOW() WHERE minecraft_uuid=$1", [request.minecraft_uuid]); await client.query("INSERT INTO payment_events (provider,provider_event_id,minecraft_uuid,status,amount_krw,payload) VALUES ('toss',$1,$2,'CANCELED',$3,$4) ON CONFLICT DO NOTHING", [`refund-${request.provider_payment_key}`, request.minecraft_uuid, request.amount_krw, result]); await client.query("COMMIT"); } catch (error) { await client.query("ROLLBACK"); throw error; } finally { client.release(); }
    return json(res, 200, { message: "전액 환불을 완료하고 구독을 종료했습니다." });
  }
  if (path === "/internal/bank-transfer/orders" && req.method === "GET") {
    if (!internal(req)) return json(res, 401, { error: "unauthorized" });
    const r = await pool.query("SELECT order_id,player_name,tier,period_days,amount_krw,transfer_reference,transfer_deadline,created_at FROM orders WHERE status='PENDING_TRANSFER' ORDER BY created_at DESC LIMIT 100");
    return json(res, 200, { rows: r.rows });
  }
  if (/^\/internal\/bank-transfer\/orders\/BK-[A-Za-z0-9]+$/.test(path) && req.method === "POST") {
    if (!internal(req)) return json(res, 401, { error: "unauthorized" });
    const data = await bodyJson(req); const orderId = path.split("/").at(-1); const actor = String(data.decidedBy ?? "stats-admin").slice(0, 100);
    if (data.action !== "confirm" && data.action !== "reject") return json(res, 400, { error: "invalid_action" });
    const client = await pool.connect();
    try {
      await client.query("BEGIN");
      const found = await client.query("SELECT * FROM orders WHERE order_id=$1 FOR UPDATE", [orderId]);
      if (!found.rowCount || found.rows[0].status !== "PENDING_TRANSFER") { await client.query("ROLLBACK"); return json(res, 404, { error: "transfer_order_not_found" }); }
      const order = found.rows[0];
      if (data.action === "reject") {
        await client.query("UPDATE orders SET status='REJECTED' WHERE order_id=$1", [orderId]);
        await client.query("COMMIT");
        return json(res, 200, { message: "입금 미확인 주문을 취소했습니다." });
      }
      const sub = await extendSubscription(client, order.minecraft_uuid, order.player_name ?? "Unknown", order.tier, order.period_days);
      await client.query("UPDATE orders SET status='PAID',paid_at=NOW() WHERE order_id=$1", [orderId]);
      await client.query("INSERT INTO payment_events (provider,provider_event_id,minecraft_uuid,status,amount_krw,payload) VALUES ('bank_transfer',$1,$2,'DONE',$3,$4) ON CONFLICT DO NOTHING", [`bank-${orderId}`, order.minecraft_uuid, order.amount_krw, { confirmedBy: actor, transferReference: order.transfer_reference, periodDays: order.period_days }]);
      await client.query("COMMIT");
      return json(res, 200, { message: `${order.player_name ?? "플레이어"}에게 ${order.period_days}일 ${order.tier} 이용권을 지급했습니다. 만료: ${new Date(sub.expires_at).toLocaleString("ko-KR", { timeZone: "Asia/Seoul" })}` });
    } catch (error) { await client.query("ROLLBACK"); throw error; } finally { client.release(); }
  }
  if (path === "/internal/link-codes" && req.method === "POST") {
    if (!internal(req)) return json(res, 401, { error: "unauthorized" }); const data = await bodyJson(req); if (!validUuid(data.uuid) || !minecraftName(data.playerName)) return json(res, 400, { error: "invalid_player" });
    const code = `BK-${randomBytes(4).toString("hex").toUpperCase()}`; await pool.query("DELETE FROM link_codes WHERE minecraft_uuid=$1 AND used_at IS NULL", [data.uuid]); await pool.query("INSERT INTO link_codes (code_hash,minecraft_uuid,player_name,expires_at) VALUES ($1,$2,$3,NOW()+INTERVAL '10 minutes')", [hash(code), data.uuid, data.playerName]); return json(res, 201, { code, expiresInSeconds: 600, url: `${BASE_URL}/link` });
  }
  if (path === "/internal/subscriptions/grant" && req.method === "POST") {
    if (!internal(req)) return json(res, 401, { error: "unauthorized" }); const data = await bodyJson(req); const days = Number.parseInt(data.days, 10); if (!validUuid(data.uuid) || !minecraftName(data.playerName) || !TIERS[data.tier] || !Number.isInteger(days) || days < 1 || days > 366) return json(res, 400, { error: "invalid_request" });
    const client = await pool.connect(); try { await client.query("BEGIN"); const sub = await extendSubscription(client, data.uuid, data.playerName, data.tier, days); await client.query("INSERT INTO payment_events (provider,provider_event_id,minecraft_uuid,status,payload) VALUES ('manual',$1,$2,'GRANTED',$3)", [`manual-${randomUUID()}`, data.uuid, { grantedBy: data.grantedBy ?? "minecraft-admin", days, tier: data.tier }]); await client.query("COMMIT"); return json(res, 201, { active: true, tier: sub.tier, expiresAt: sub.expires_at }); } catch (error) { await client.query("ROLLBACK"); throw error; } finally { client.release(); }
  }
  if (path.startsWith("/internal/subscriptions/") && req.method === "GET") {
    if (!internal(req)) return json(res, 401, { error: "unauthorized" }); const uuid = path.slice("/internal/subscriptions/".length); if (!validUuid(uuid)) return json(res, 400, { error: "invalid_uuid" }); const sub = await subscription(uuid); return json(res, 200, { active: Boolean(sub?.active), tier: sub?.active ? sub.tier : null, expiresAt: sub?.expires_at ?? null });
  }
  return send(res, 404, layout("찾을 수 없음", `<div class="panel"><h1>404</h1><a class="button" href="${BASE_URL}/">멤버십 홈</a></div>`));
}

const server = http.createServer((req, res) => route(req, res).catch((error) => { console.error(error); if (!res.headersSent) send(res, 500, layout("오류", `<div class="panel"><div class="notice danger">일시적인 오류가 발생했습니다. 잠시 후 다시 시도하세요.</div></div>`)); }));
migrate().then(() => server.listen(PORT, "127.0.0.1", () => console.log(`vip-billing listening on ${PORT}`))).catch((error) => { console.error("migration failed", error); process.exit(1); });
process.on("SIGTERM", () => server.close(() => pool.end().finally(() => process.exit(0))));
