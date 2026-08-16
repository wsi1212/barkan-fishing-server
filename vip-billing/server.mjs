import http from "node:http";
import net from "node:net";
import process from "node:process";
import { readFile } from "node:fs/promises";
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
const DISCORD_CLIENT_ID = process.env.DISCORD_CLIENT_ID ?? "";
const DISCORD_CLIENT_SECRET = process.env.DISCORD_CLIENT_SECRET ?? "";
const COMMUNITY_BASE_URL = (process.env.COMMUNITY_BASE_URL ?? "https://barkan.kro.kr/community").replace(/\/$/, "");
const DISCORD_GUILD_ID = process.env.DISCORD_GUILD_ID ?? "972075275342983199";
const MINECRAFT_PLAYERDATA_DIR = process.env.MINECRAFT_PLAYERDATA_DIR ?? "/home/ubuntu/mcserver/plugins/BlockShip/playerdata";
const MINECRAFT_GUILDS_FILE = process.env.MINECRAFT_GUILDS_FILE ?? "/home/ubuntu/mcserver/plugins/BlockShip/guilds.json";
const MINECRAFT_ISLANDS_FILE = process.env.MINECRAFT_ISLANDS_FILE ?? "/home/ubuntu/mcserver/plugins/BlockShip/islands.json";
const MINECRAFT_ACHIEVEMENTS_FILE = process.env.MINECRAFT_ACHIEVEMENTS_FILE ?? "/home/ubuntu/mcserver/plugins/BlockShip/achievements.json";
const MINECRAFT_TITLES_FILE = process.env.MINECRAFT_TITLES_FILE ?? "/home/ubuntu/mcserver/plugins/BlockShip/titles.json";
const MC_RCON_HOST = process.env.MC_RCON_HOST ?? "127.0.0.1";
const MC_RCON_PORT = Number.parseInt(process.env.MC_RCON_PORT ?? "25575", 10);
const MC_RCON_PASSWORD = process.env.MC_RCON_PASSWORD ?? "";
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

function rconPacket(id, type, body) {
  const payload = Buffer.from(String(body), "utf8");
  const packet = Buffer.alloc(4 + 4 + 4 + payload.length + 2);
  packet.writeInt32LE(4 + 4 + payload.length + 2, 0);
  packet.writeInt32LE(id, 4);
  packet.writeInt32LE(type, 8);
  payload.copy(packet, 12);
  packet[12 + payload.length] = 0;
  packet[13 + payload.length] = 0;
  return packet;
}

function nextRconPacket(socket, state) {
  return new Promise((resolve, reject) => {
    let timer;
    const cleanup = () => {
      clearTimeout(timer);
      socket.off("data", onData);
      socket.off("error", onError);
      socket.off("close", onClose);
    };
    const take = () => {
      if (state.buffer.length < 4) return false;
      const length = state.buffer.readInt32LE(0);
      if (length < 10 || length > 1_000_000) {
        cleanup();
        reject(new Error("invalid RCON packet"));
        return true;
      }
      if (state.buffer.length < length + 4) return false;
      const packet = state.buffer.subarray(4, length + 4);
      state.buffer = state.buffer.subarray(length + 4);
      const result = { id: packet.readInt32LE(0), type: packet.readInt32LE(4), body: packet.subarray(8, packet.length - 2).toString("utf8") };
      cleanup();
      resolve(result);
      return true;
    };
    const onData = (chunk) => { state.buffer = Buffer.concat([state.buffer, chunk]); take(); };
    const onError = () => { cleanup(); reject(new Error("RCON connection failed")); };
    const onClose = () => { cleanup(); reject(new Error("RCON connection closed")); };
    socket.on("data", onData);
    socket.on("error", onError);
    socket.on("close", onClose);
    timer = setTimeout(() => { cleanup(); reject(new Error("RCON timeout")); }, 5_000);
    take();
  });
}

async function rconExecute(command) {
  if (!MC_RCON_PASSWORD) throw new Error("RCON is not configured");
  const socket = net.createConnection({ host: MC_RCON_HOST, port: MC_RCON_PORT });
  const state = { buffer: Buffer.alloc(0) };
  try {
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => { socket.destroy(); reject(new Error("RCON connect timeout")); }, 5_000);
      socket.once("connect", () => { clearTimeout(timer); resolve(); });
      socket.once("error", (error) => { clearTimeout(timer); reject(error); });
    });
    socket.write(rconPacket(1, 3, MC_RCON_PASSWORD));
    const auth = await nextRconPacket(socket, state);
    if (auth.id === -1) throw new Error("RCON authentication failed");
    socket.write(rconPacket(2, 2, command));
    const response = await nextRconPacket(socket, state);
    return response.body;
  } finally {
    socket.end();
  }
}

const base64Url = (value) => Buffer.from(String(value ?? ""), "utf8").toString("base64url");
async function submitGuildApplication(current, guildId, message) {
  const command = `guildbr webapply ${[current.minecraft_uuid, current.player_name, guildId, message].map(base64Url).join(" ")}`;
  const result = await rconExecute(command);
  return /WEBAPPLY\s+ok/i.test(result);
}

function cookies(req) {
  return Object.fromEntries((req.headers.cookie ?? "").split(";").map((part) => {
    const i = part.indexOf("=");
    return i < 0 ? ["", ""] : [part.slice(0, i).trim(), decodeURIComponent(part.slice(i + 1))];
  }));
}

function send(res, status, body, type = "text/html; charset=utf-8", extra = {}) {
  if (type.startsWith("text/html") && typeof body === "string" && body.includes('class="nav-links"') && !body.includes(`href="${COMMUNITY_BASE_URL}/guilds"`)) {
    body = body.replace('<a href="/ranking">랭킹</a>', (match) => `${match}<a href="${COMMUNITY_BASE_URL}/guilds">길드</a>`);
  }
  res.writeHead(status, {
    "Content-Type": type,
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
    "Content-Security-Policy": "default-src 'self'; img-src 'self' https://mc-heads.net https://cdn.discordapp.com; style-src 'unsafe-inline'; script-src 'self' https://js.tosspayments.com; connect-src 'self' https://api.tosspayments.com",
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
    CREATE TABLE IF NOT EXISTS discord_links (
      minecraft_uuid UUID PRIMARY KEY, player_name TEXT NOT NULL,
      discord_id TEXT NOT NULL UNIQUE, discord_name TEXT,
      linked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      verified_at TIMESTAMPTZ, reward_claimed_at TIMESTAMPTZ
    );
    ALTER TABLE discord_links ADD COLUMN IF NOT EXISTS avatar_hash TEXT;
    ALTER TABLE discord_links ADD COLUMN IF NOT EXISTS verified_at TIMESTAMPTZ;
    ALTER TABLE discord_links ADD COLUMN IF NOT EXISTS reward_claimed_at TIMESTAMPTZ;
    CREATE TABLE IF NOT EXISTS web_sessions (
      token_hash TEXT PRIMARY KEY, minecraft_uuid UUID NOT NULL, csrf_token TEXT NOT NULL,
      expires_at TIMESTAMPTZ NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    ALTER TABLE web_sessions ADD COLUMN IF NOT EXISTS player_name TEXT;
    CREATE TABLE IF NOT EXISTS community_sessions (
      token_hash TEXT PRIMARY KEY, discord_id TEXT NOT NULL, minecraft_uuid UUID NOT NULL,
      player_name TEXT NOT NULL, discord_name TEXT, avatar_hash TEXT, csrf_token TEXT NOT NULL,
      expires_at TIMESTAMPTZ NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS community_sessions_expiry_idx ON community_sessions (expires_at);
    CREATE TABLE IF NOT EXISTS community_posts (
      id UUID PRIMARY KEY, discord_id TEXT NOT NULL, minecraft_uuid UUID NOT NULL,
      player_name TEXT NOT NULL, discord_name TEXT, category TEXT NOT NULL CHECK (category IN ('공략','질문','후기','소식')),
      title TEXT NOT NULL, body TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), hidden BOOLEAN NOT NULL DEFAULT FALSE
    );
    CREATE INDEX IF NOT EXISTS community_posts_feed_idx ON community_posts (hidden, created_at DESC);
    CREATE INDEX IF NOT EXISTS community_posts_author_idx ON community_posts (minecraft_uuid, created_at DESC);
    CREATE TABLE IF NOT EXISTS community_post_likes (
      post_id UUID NOT NULL REFERENCES community_posts(id) ON DELETE CASCADE,
      minecraft_uuid UUID NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      PRIMARY KEY (post_id, minecraft_uuid)
    );
    CREATE INDEX IF NOT EXISTS community_post_likes_post_idx ON community_post_likes (post_id);
    CREATE TABLE IF NOT EXISTS community_post_views (
      post_id UUID NOT NULL REFERENCES community_posts(id) ON DELETE CASCADE,
      viewer_key TEXT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      PRIMARY KEY (post_id, viewer_key)
    );
    CREATE INDEX IF NOT EXISTS community_post_views_post_idx ON community_post_views (post_id);
    CREATE TABLE IF NOT EXISTS community_comments (
      id UUID PRIMARY KEY, post_id UUID NOT NULL REFERENCES community_posts(id) ON DELETE CASCADE,
      discord_id TEXT NOT NULL, minecraft_uuid UUID NOT NULL, player_name TEXT NOT NULL,
      discord_name TEXT, body TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), hidden BOOLEAN NOT NULL DEFAULT FALSE
    );
    CREATE INDEX IF NOT EXISTS community_comments_post_idx ON community_comments (post_id, hidden, created_at ASC);
    CREATE INDEX IF NOT EXISTS community_comments_author_idx ON community_comments (minecraft_uuid, created_at DESC);
    CREATE TABLE IF NOT EXISTS community_comment_likes (
      comment_id UUID NOT NULL REFERENCES community_comments(id) ON DELETE CASCADE,
      minecraft_uuid UUID NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      PRIMARY KEY (comment_id, minecraft_uuid)
    );
    CREATE INDEX IF NOT EXISTS community_comment_likes_comment_idx ON community_comment_likes (comment_id);
    CREATE TABLE IF NOT EXISTS community_profiles (
      minecraft_uuid UUID PRIMARY KEY, introduction TEXT NOT NULL DEFAULT '', updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
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
    -- 길드 디스코드 연동. 게임(BlockShip)이 길드 명부 전체를 주기적으로 밀어넣고(guild_mirror/guild_member_mirror),
    -- 백엔드가 직전 상태와 비교해 필요한 작업만 큐에 넣는다. 봇은 큐만 비운다.
    -- 이벤트가 아니라 스냅샷 diff 인 이유: 이벤트 한 번 유실되면 그 길드는 영원히 어긋난 채로 남는다.
    CREATE TABLE IF NOT EXISTS guild_mirror (
      guild_id TEXT PRIMARY KEY, owner_uuid UUID, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS guild_member_mirror (
      guild_id TEXT NOT NULL REFERENCES guild_mirror(guild_id) ON DELETE CASCADE,
      minecraft_uuid UUID NOT NULL, guild_rank TEXT NOT NULL,
      PRIMARY KEY (guild_id, minecraft_uuid)
    );
    CREATE INDEX IF NOT EXISTS guild_member_mirror_player_idx ON guild_member_mirror (minecraft_uuid);
    CREATE TABLE IF NOT EXISTS guild_discord (
      guild_id TEXT PRIMARY KEY, role_id TEXT, category_id TEXT,
      text_channel_id TEXT, voice_channel_id TEXT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS guild_discord_jobs (
      id BIGSERIAL PRIMARY KEY,
      kind TEXT NOT NULL CHECK (kind IN ('guild_create','guild_delete','guild_members')),
      guild_id TEXT NOT NULL, payload JSONB NOT NULL DEFAULT '{}'::jsonb,
      attempts INTEGER NOT NULL DEFAULT 0, run_after TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      claimed_at TIMESTAMPTZ, done_at TIMESTAMPTZ, last_error TEXT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS guild_discord_jobs_queue_idx ON guild_discord_jobs (run_after, id) WHERE done_at IS NULL;
    -- 같은 길드에 같은 종류의 작업이 두 번 쌓이지 않게. 재요청은 run_after 를 당기는 것으로 갈음한다.
    CREATE UNIQUE INDEX IF NOT EXISTS guild_discord_jobs_pending_idx ON guild_discord_jobs (kind, guild_id) WHERE done_at IS NULL;
  `);
}

// 게임 안 직책. 디스코드 공용 역할 이름과의 대응은 봇이 들고 있다.
const GUILD_RANKS = new Set(["MASTER", "VICE_MASTER", "OFFICER", "MEMBER"]);

async function guildDiscordRow(guildId) {
  const row = await pool.query(
    "SELECT role_id,category_id,text_channel_id,voice_channel_id FROM guild_discord WHERE guild_id=$1",
    [guildId]
  );
  if (!row.rowCount) return null;
  const found = row.rows[0];
  return {
    roleId: found.role_id, categoryId: found.category_id,
    textChannelId: found.text_channel_id, voiceChannelId: found.voice_channel_id,
  };
}

/** 길드원 중 디스코드를 연결한 사람만. 미연동자는 목록에서 빠지고, 나중에 연결하는 순간 재동기화된다. */
async function guildMemberTargets(guildId) {
  const rows = await pool.query(
    `SELECT m.minecraft_uuid, m.guild_rank, d.discord_id, d.player_name
       FROM guild_member_mirror m JOIN discord_links d ON d.minecraft_uuid = m.minecraft_uuid
      WHERE m.guild_id=$1`,
    [guildId]
  );
  return rows.rows.map((row) => ({
    minecraftUuid: row.minecraft_uuid, playerName: row.player_name,
    rank: row.guild_rank, discordId: row.discord_id,
  }));
}

/** 대기 중이면 즉시 재실행하도록 당기고, 없으면 새로 넣는다. 모든 작업은 멱등이라 중복 실행은 무해하다. */
async function enqueueGuildJob(client, kind, guildId, payload = {}) {
  await client.query(
    `INSERT INTO guild_discord_jobs (kind,guild_id,payload) VALUES ($1,$2,$3::jsonb)
     ON CONFLICT (kind,guild_id) WHERE done_at IS NULL
     DO UPDATE SET run_after=NOW(), claimed_at=NULL, payload=EXCLUDED.payload`,
    [kind, guildId, JSON.stringify(payload)]
  );
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

const COMMUNITY_CATEGORIES = Object.freeze(["공략", "질문", "후기", "소식"]);
const communityConfigured = () => Boolean(DISCORD_CLIENT_ID && DISCORD_CLIENT_SECRET);
async function communitySession(req) {
  const value = cookies(req).community_session;
  if (!value) return null;
  const result = await pool.query(
    `SELECT s.discord_id,s.minecraft_uuid,s.player_name,s.discord_name,s.avatar_hash,s.csrf_token
       FROM community_sessions s JOIN discord_links d ON d.discord_id=s.discord_id
      WHERE s.token_hash=$1 AND s.expires_at>NOW()`,
    [hash(value)]
  );
  return result.rows[0] ?? null;
}
function communityLayout(title, content) {
  content = `<style>.filter{text-decoration:none}</style>${content}`;
  return `<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#071b1a"><title>${esc(title)} · 바르칸 열도</title><style>
  @font-face{font-family:Barkan;src:url('/assets/barkan-aggro-light.ttf') format('truetype');font-weight:300;font-display:swap}@font-face{font-family:Barkan;src:url('/assets/barkan-aggro-medium.ttf') format('truetype');font-weight:500;font-display:swap}@font-face{font-family:Barkan;src:url('/assets/barkan-aggro-bold.ttf') format('truetype');font-weight:800;font-display:swap}:root{color-scheme:dark;--ink:#071b1a;--deep:#0c2825;--panel:#123733;--line:rgba(216,238,224,.18);--text:#edf3e9;--muted:#a8bdb0;--faint:#78968a;--accent:#e2ad67;--mint:#96d9c4;--danger:#ff9b9f}*{box-sizing:border-box}body{margin:0;background:radial-gradient(720px 420px at 100% -10%,rgba(31,93,77,.4),transparent 70%),var(--ink);color:var(--text);font-family:Barkan,'Apple SD Gothic Neo','Noto Sans KR',sans-serif;line-height:1.6}.wrap{width:min(1160px,calc(100% - 48px));margin:auto}.nav{height:76px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--line)}.brand{color:var(--text);text-decoration:none;line-height:1}.brand strong{display:block;font-size:20px;font-weight:800;letter-spacing:.15em}.brand small{display:block;margin-top:7px;color:var(--accent);font-family:ui-monospace,monospace;font-size:9px;letter-spacing:.18em}.nav-links{display:flex;align-items:center;gap:18px}.nav-links a{color:var(--muted);font-size:13px;text-decoration:none}.nav-links a:hover{color:var(--accent)}.nav-login{padding:9px 13px;border:1px solid rgba(150,217,196,.55);color:var(--mint)!important}.nav-login:hover{background:rgba(150,217,196,.1)}main{padding:58px 0 110px}.eyebrow{margin:0 0 12px;color:var(--mint);font:800 10px ui-monospace,monospace;letter-spacing:.18em;text-transform:uppercase}.intro{display:flex;align-items:end;justify-content:space-between;gap:30px;padding-bottom:34px;border-bottom:1px solid var(--line)}h1{max-width:700px;margin:0;font-size:clamp(3rem,7vw,6rem);font-weight:800;letter-spacing:-.12em;line-height:.95}h1 em{color:var(--accent);font-style:normal}.intro-copy{max-width:310px;margin:0;color:var(--muted);font-size:14px}.toolbar{display:flex;align-items:center;justify-content:space-between;gap:16px;margin:30px 0 16px}.filters{display:flex;flex-wrap:wrap;gap:7px}.filter{padding:8px 12px;border:1px solid var(--line);background:transparent;color:var(--muted);font:500 12px Barkan;cursor:pointer}.filter.active,.filter:hover{border-color:var(--accent);color:var(--accent);background:rgba(226,173,103,.08)}.button{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:10px 15px;border:1px solid var(--accent);background:var(--accent);color:#25180b;font-weight:800;text-decoration:none;cursor:pointer}.button:hover{background:#f0c783;transform:translateY(-1px)}.button.ghost{border-color:var(--line);background:transparent;color:var(--text)}.feed{border-top:1px solid var(--line)}.post{display:grid;grid-template-columns:95px minmax(0,1fr) 130px;gap:24px;align-items:start;padding:25px 0;border-bottom:1px solid var(--line);text-decoration:none}.post:hover .post-title{color:var(--accent)}.post-category{padding-top:5px;color:var(--mint);font:800 10px ui-monospace,monospace;letter-spacing:.08em}.post-title{margin:0;font-size:24px;font-weight:500;letter-spacing:-.07em;transition:color .15s}.post-excerpt{display:-webkit-box;overflow:hidden;margin:8px 0 0;color:var(--muted);font-size:13px;-webkit-box-orient:vertical;-webkit-line-clamp:2}.post-meta{padding-top:5px;color:var(--faint);font-size:11px;text-align:right}.empty{padding:62px 0;border-bottom:1px solid var(--line);color:var(--muted)}.notice{margin:18px 0;padding:13px 15px;border-left:2px solid var(--mint);background:rgba(150,217,196,.08);color:#d8eee2}.notice.danger{border-left-color:var(--danger);background:rgba(255,155,159,.1);color:#ffd9d9}.panel{max-width:800px;margin:auto;padding:35px;border:1px solid var(--line);background:linear-gradient(145deg,rgba(18,55,51,.95),rgba(8,30,29,.95))}.panel h2{margin:0 0 7px;font-size:28px;letter-spacing:-.08em}label{display:block;margin:20px 0 7px;font-size:13px;font-weight:800}input,select,textarea{width:100%;padding:13px 14px;border:1px solid var(--line);background:#071b1a;color:var(--text);font:inherit;border-radius:0}textarea{min-height:310px;resize:vertical}small.help{display:block;margin-top:-2px;color:var(--faint);font-size:11px}.detail{max-width:820px;margin:auto}.detail-head{padding-bottom:30px;border-bottom:1px solid var(--line)}.detail h1{font-size:clamp(2.6rem,6vw,5rem)}.detail-meta{margin:17px 0 0;color:var(--muted);font-size:12px}.detail-body{padding:36px 0;color:#d7e5dc;font-size:16px;white-space:pre-wrap}.back{display:inline-block;margin-top:20px;color:var(--accent);font-size:13px;text-underline-offset:4px}.footer{padding:28px 0 40px;border-top:1px solid var(--line);color:var(--faint);font-size:12px}.footer-links{display:flex;flex-wrap:wrap;gap:18px;margin-top:10px}.footer-links a{color:var(--muted);text-decoration:none}@media(max-width:720px){.wrap{width:min(100% - 30px,620px)}.nav{height:68px}.nav-links{gap:11px}.nav-links a:not(.nav-login){display:none}.intro{display:block;padding-bottom:27px}.intro-copy{margin-top:22px}.toolbar{display:block}.filters{margin-bottom:14px}.post{grid-template-columns:70px minmax(0,1fr);gap:12px;padding:20px 0}.post-meta{grid-column:2;padding-top:0;text-align:left}.post-title{font-size:19px}.panel{padding:25px 19px}}
  </style><script src="/assets/site-nav.js" defer></script></head><body><div class="wrap"><div data-site-nav></div>${content}<footer class="footer"><div>바르칸 열도 · 공략과 항해 기록을 함께 쌓는 공간</div><div class="footer-links"><a href="https://discord.gg/fWVGGEbBsd" target="_blank" rel="noopener noreferrer">디스코드</a><a href="/vip/">멤버십 상점</a><a href="mailto:wsiwsiwsi123@gmail.com">문의 및 환불</a></div></footer></div></body></html>`;
}
async function communityPosts(category = "") {
  const selected = COMMUNITY_CATEGORIES.includes(category) ? category : "";
  const stats = `
    COALESCE((SELECT COUNT(*) FROM community_post_likes l WHERE l.post_id=p.id), 0)::int AS like_count,
    COALESCE((SELECT COUNT(*) FROM community_post_views v WHERE v.post_id=p.id), 0)::int AS view_count,
    COALESCE((SELECT COUNT(*) FROM community_comments c WHERE c.post_id=p.id AND c.hidden=FALSE), 0)::int AS comment_count`;
  const result = selected
    ? await pool.query(`SELECT p.id,p.category,p.title,p.body,p.player_name,p.minecraft_uuid,p.created_at,${stats} FROM community_posts p WHERE p.hidden=FALSE AND p.category=$1 ORDER BY p.created_at DESC LIMIT 60`, [selected])
    : await pool.query(`SELECT p.id,p.category,p.title,p.body,p.player_name,p.minecraft_uuid,p.created_at,${stats} FROM community_posts p WHERE p.hidden=FALSE ORDER BY p.created_at DESC LIMIT 60`);
  return result.rows;
}
async function communityPost(id, current = null) {
  if (!validUuid(id)) return null;
  const result = await pool.query(`
    SELECT p.id,p.category,p.title,p.body,p.player_name,p.minecraft_uuid,p.created_at,
      COALESCE((SELECT COUNT(*) FROM community_post_likes l WHERE l.post_id=p.id), 0)::int AS like_count,
      COALESCE((SELECT COUNT(*) FROM community_post_views v WHERE v.post_id=p.id), 0)::int AS view_count,
      COALESCE((SELECT COUNT(*) FROM community_comments c WHERE c.post_id=p.id AND c.hidden=FALSE), 0)::int AS comment_count,
      ($2::uuid IS NOT NULL AND EXISTS (
        SELECT 1 FROM community_post_likes l WHERE l.post_id=p.id AND l.minecraft_uuid=$2::uuid
      )) AS liked
    FROM community_posts p
    WHERE p.id=$1::uuid AND p.hidden=FALSE`, [id, current?.minecraft_uuid ?? null]);
  return result.rows[0] ?? null;
}
function communityCount(value) {
  return Number(value ?? 0).toLocaleString("ko-KR");
}
function communityPostStats(post, includeLike = false) {
  const likeLabel = includeLike ? `${post.liked ? "♥" : "♡"} ${communityCount(post.like_count)}` : `♥ ${communityCount(post.like_count)}`;
  return `<span class="post-stat${post.liked ? " liked" : ""}">${likeLabel}</span><span class="post-stat">조회 ${communityCount(post.view_count)}</span><span class="post-stat">댓글 ${communityCount(post.comment_count)}</span>`;
}
async function communityComments(postId, current = null) {
  if (!validUuid(postId)) return [];
  const result = await pool.query(`
    SELECT c.id,c.post_id,c.discord_id,c.minecraft_uuid,c.player_name,c.discord_name,c.body,c.created_at,
      COALESCE((SELECT COUNT(*) FROM community_comment_likes l WHERE l.comment_id=c.id), 0)::int AS like_count,
      ($2::uuid IS NOT NULL AND EXISTS (
        SELECT 1 FROM community_comment_likes l WHERE l.comment_id=c.id AND l.minecraft_uuid=$2::uuid
      )) AS liked
    FROM community_comments c
    WHERE c.post_id=$1::uuid AND c.hidden=FALSE
    ORDER BY c.created_at ASC
    LIMIT 200`, [postId, current?.minecraft_uuid ?? null]);
  return result.rows;
}
async function communityComment(id, current = null) {
  if (!validUuid(id)) return null;
  const result = await pool.query(`
    SELECT c.id,c.post_id,c.discord_id,c.minecraft_uuid,c.player_name,c.discord_name,c.body,c.created_at,
      COALESCE((SELECT COUNT(*) FROM community_comment_likes l WHERE l.comment_id=c.id), 0)::int AS like_count,
      ($2::uuid IS NOT NULL AND EXISTS (
        SELECT 1 FROM community_comment_likes l WHERE l.comment_id=c.id AND l.minecraft_uuid=$2::uuid
      )) AS liked
    FROM community_comments c
    WHERE c.id=$1::uuid AND c.hidden=FALSE`, [id, current?.minecraft_uuid ?? null]);
  return result.rows[0] ?? null;
}
async function readMinecraftJson(file, fallback) {
  try { return JSON.parse(await readFile(file, "utf8")); } catch { return fallback; }
}
async function minecraftProfileData(uuid) {
  if (!validUuid(uuid)) return {};
  return readMinecraftJson(`${MINECRAFT_PLAYERDATA_DIR}/${uuid}.json`, {});
}
async function minecraftGuildFor(uuid) {
  const guild = (await minecraftGuildList()).find((candidate) => candidate.members.some((member) => member.uuid === uuid));
  if (!guild) return null;
  const member = guild.members.find((candidate) => candidate.uuid === uuid);
  return { id: guild.id, name: guild.name, role: member?.role ?? "MEMBER", memberCount: guild.members.length };
}
async function minecraftIslandFor(uuid) {
  const islands = await readMinecraftJson(MINECRAFT_ISLANDS_FILE, {});
  const island = Object.values(islands).find((candidate) => candidate && typeof candidate === "object" && candidate.ownerUuid === uuid);
  if (!island) return null;
  return { name: island.id?.replace(/^개인섬_/, "") || "개인 섬", visitCount: Number(island.visitCount ?? 0), isPublic: Boolean(island.isPublic) };
}
function minecraftColorless(value) {
  return String(value ?? "").replace(/[&§][0-9a-fk-or]/gi, "").trim();
}
async function minecraftAchievementDefinitions() {
  const root = await readMinecraftJson(MINECRAFT_ACHIEVEMENTS_FILE, {});
  return Array.isArray(root.achievements) ? root.achievements : [];
}
async function minecraftTitleDefinitions() {
  const root = await readMinecraftJson(MINECRAFT_TITLES_FILE, {});
  const source = root.titles && typeof root.titles === "object" ? root.titles : {};
  const order = Array.isArray(root.order) ? root.order : Object.keys(source);
  return order.map((id) => ({ id, ...(source[id] && typeof source[id] === "object" ? source[id] : {}) }));
}
function normalizeGuild(key, guild) {
  const source = guild && typeof guild === "object" ? guild : {};
  const members = source.members && typeof source.members === "object" ? Object.entries(source.members).map(([uuid, member]) => ({
    uuid,
    name: String(member?.name ?? "알 수 없음"),
    role: String(member?.role ?? "MEMBER"),
    joinedAt: Number(member?.joinedAt ?? 0),
    contributed: Number(member?.contributed ?? 0)
  })) : [];
  const applications = source.pendingApplications && typeof source.pendingApplications === "object"
    ? Object.entries(source.pendingApplications).map(([uuid, application]) => ({ uuid, name: String(application?.name ?? "알 수 없음") }))
    : [];
  let emblemPixels = Array.isArray(source.emblemPixels) && source.emblemPixels.length === 64
    ? source.emblemPixels.map((value) => Number.isInteger(Number(value)) && Number(value) >= -1 && Number(value) < 12 ? Number(value) : -1)
    : Array(64).fill(-1);
  // 64×64 논리 캔버스와 구버전 128×128 캔버스 모두 웹 미리보기로 복원한다.
  const rawLargePixels = Array.isArray(source.emblemCanvasPixels)
    ? (source.emblemCanvasPixels.length === 64 * 64 || source.emblemCanvasPixels.length === 128 * 128 ? source.emblemCanvasPixels : null)
    : null;
  const largeSize = rawLargePixels ? Math.sqrt(rawLargePixels.length) : 0;
  const largePixels = rawLargePixels
    ? rawLargePixels.map((value) => Number.isInteger(Number(value)) && Number(value) >= -1 && Number(value) < 12 ? Number(value) : -1)
    : null;
  if (largePixels && emblemPixels.every((value) => value < 0)) {
    emblemPixels = Array.from({ length: 64 }, (_, index) => {
      const gx = index % 8, gy = Math.floor(index / 8);
      const counts = Array(12).fill(0);
      const cell = largeSize / 8;
      for (let y = 0; y < cell; y++) for (let x = 0; x < cell; x++) {
        const value = largePixels[(gy * cell + y) * largeSize + gx * cell + x];
        if (value >= 0) counts[value]++;
      }
      let best = -1, bestCount = 0;
      counts.forEach((count, color) => { if (count > bestCount) { best = color; bestCount = count; } });
      return best;
    });
  }
  const canvasPixels = largePixels && largeSize === 64
    ? largePixels
    : largePixels && largeSize === 128
      ? Array.from({ length: 64 * 64 }, (_, index) => {
          const x = index % 64, y = Math.floor(index / 64);
          for (let dy = 0; dy < 2; dy++) for (let dx = 0; dx < 2; dx++) {
            const value = largePixels[(y * 2 + dy) * 128 + x * 2 + dx];
            if (value >= 0) return value;
          }
          return -1;
        })
      : [];
  return {
    id: String(source.id ?? key),
    name: String(source.displayName ?? source.id ?? key),
    description: String(source.description ?? ""),
    isPublic: source.isPublic !== false,
    pvp: Boolean(source.pvp),
    ownerId: String(source.ownerId ?? ""),
    ownerUuid: String(source.ownerUuid ?? ""),
    treasury: Number(source.treasury ?? 0),
    submitTotal: Number(source.submitTotal ?? 0),
    submitSeason: Number(source.submitSeason ?? 0),
    maxMembers: Number(source.maxMembers ?? 0),
    islandId: String(source.islandId ?? ""),
    upgrades: { hopper: Number(source.hopperLevel ?? 0), frame: Number(source.frameLevel ?? 0), furniture: Number(source.furnitureLevel ?? 0), crop: Number(source.cropLevel ?? 0), warp: Number(source.warpLevel ?? 0), cooking: Number(source.cookingStations ?? 0) },
    emblemPixels,
    emblemCanvasPixels: canvasPixels,
    members,
    applications
  };
}
const EMBLEM_COLORS = Object.freeze([
  "#141b27", "#eff4f2", "#d34d5a", "#f08f49", "#f5c757", "#68cd8f",
  "#42a67e", "#58cddd", "#4980d0", "#8169c4", "#d270bc", "#9f6948"
]);
function guildEmblem(guild, className = "guild-emblem", full = false) {
  const pixels = full && Array.isArray(guild?.emblemCanvasPixels) && guild.emblemCanvasPixels.length === 64 * 64
    ? guild.emblemCanvasPixels
    : Array.isArray(guild?.emblemPixels) && guild.emblemPixels.length === 64 ? guild.emblemPixels : Array(64).fill(-1);
  const size = full && pixels.length === 64 * 64 ? 64 : 8;
  const cells = pixels.map((value) => {
    const color = Number.isInteger(value) && value >= 0 && value < EMBLEM_COLORS.length ? EMBLEM_COLORS[value] : "#08121d";
    return `<i style="background:${color}"></i>`;
  }).join("");
  return `<span class="${className}" style="--emblem-size:${size}" aria-label="${esc(guild?.name ?? "길드")} 엠블럼">${cells}</span>`;
}
async function minecraftGuildList() {
  const source = await readMinecraftJson(MINECRAFT_GUILDS_FILE, {});
  return Object.entries(source).filter(([, guild]) => guild && typeof guild === "object").map(([key, guild]) => normalizeGuild(key, guild)).sort((a, b) => b.submitSeason - a.submitSeason || b.members.length - a.members.length || a.name.localeCompare(b.name, "ko"));
}
async function minecraftGuildById(id) {
  const guild = (await minecraftGuildList()).find((candidate) => candidate.id === id);
  if (!guild) return null;
  const uuids = guild.members.map((member) => member.uuid).filter(validUuid);
  const linked = uuids.length ? await pool.query("SELECT minecraft_uuid FROM discord_links WHERE minecraft_uuid=ANY($1::uuid[])", [uuids]) : { rows: [] };
  const linkedSet = new Set(linked.rows.map((row) => row.minecraft_uuid));
  return { ...guild, members: guild.members.map((member) => ({ ...member, linked: linkedSet.has(member.uuid) })) };
}
function achievementRecords(ids, definitions) {
  const byId = new Map(definitions.map((definition) => [String(definition.id), definition]));
  return ids.map((id) => {
    const definition = byId.get(String(id));
    return { id: String(id), name: String(definition?.name ?? id), desc: String(definition?.desc ?? "서버의 도전과제를 완료했습니다."), tab: String(definition?.tab ?? "기록"), tier: String(definition?.tier ?? "완료") };
  });
}
function titleRecords(ids, definitions) {
  const byId = new Map(definitions.map((definition) => [String(definition.id), definition]));
  return ids.map((id) => {
    const definition = byId.get(String(id));
    return { id: String(id), name: minecraftColorless(definition?.name ?? id), desc: minecraftColorless(definition?.desc ?? "획득한 칭호") };
  });
}
async function communityProfile(uuid) {
  const link = await pool.query("SELECT minecraft_uuid,player_name,discord_id,discord_name,avatar_hash,linked_at FROM discord_links WHERE minecraft_uuid=$1", [uuid]);
  if (!link.rowCount) return null;
  const [game, posts, guild, island, profileMeta, achievementDefs, titleDefs] = await Promise.all([
    minecraftProfileData(uuid),
    pool.query("SELECT id,category,title,body,created_at FROM community_posts WHERE minecraft_uuid=$1 AND hidden=FALSE ORDER BY created_at DESC LIMIT 30", [uuid]),
    minecraftGuildFor(uuid),
    minecraftIslandFor(uuid),
    pool.query("SELECT introduction FROM community_profiles WHERE minecraft_uuid=$1", [uuid]),
    minecraftAchievementDefinitions(),
    minecraftTitleDefinitions()
  ]);
  const fishRecords = game.fishRecords && typeof game.fishRecords === "object" ? game.fishRecords : {};
  const dex = game.dexDiscovery && typeof game.dexDiscovery === "object" ? game.dexDiscovery : {};
  const extraNums = game.extraNums && typeof game.extraNums === "object" ? game.extraNums : {};
  const parts = game.equippedParts && typeof game.equippedParts === "object" ? game.equippedParts : {};
  return {
    ...link.rows[0],
    game,
    posts: posts.rows,
    guild,
    island,
    fishCount: Object.keys(fishRecords).length,
    regionCount: Array.isArray(game.visitedRegions) ? game.visitedRegions.length : Array.isArray(dex.지역) ? dex.지역.length : 0,
    totalFishing: Number(extraNums["총낚시"] ?? 0),
    popularity: Number(game.popularity ?? 0),
    achievements: achievementRecords(Array.isArray(game.completedAchievements) ? game.completedAchievements : [], achievementDefs),
    titles: titleRecords(Array.isArray(game.ownedTitles) ? game.ownedTitles : [], titleDefs),
    achievementCount: Array.isArray(game.completedAchievements) ? game.completedAchievements.length : 0,
    titleCount: Array.isArray(game.ownedTitles) ? game.ownedTitles.length : 0,
    introduction: profileMeta.rows[0]?.introduction ?? String(game.introduction ?? "").trim(),
    cookingLevel: Number(extraNums["요리레벨"] ?? 0),
    collectionLevel: Number(extraNums["수집레벨"] ?? 0),
    explorationLevel: Number(extraNums["탐험레벨"] ?? 0),
    parts
  };
}
function communityPage(current, posts, notice = "", selectedCategory = "") {
  const userMarker = current ? " data-community-user=\"1\"" : "";
  const cards = posts.length ? posts.map((post) => `<article class="post"><div class="post-category">${esc(post.category)}</div><a class="post-content" href="${COMMUNITY_BASE_URL}/post/${encodeURIComponent(post.id)}"><h2 class="post-title">${esc(post.title)}</h2><p class="post-excerpt">${esc(post.body)}</p><div class="post-stats">${communityPostStats(post)}</div></a><a class="post-meta" href="${COMMUNITY_BASE_URL}/user/${encodeURIComponent(post.minecraft_uuid)}">${esc(post.player_name)}<br>${new Date(post.created_at).toLocaleDateString("ko-KR")}</a></article>`).join("") : `<div class="empty">아직 첫 항해 기록이 없습니다. 게임에서 겪은 팁과 발견을 남겨 보세요.</div>`;
  const action = current ? `<a class="button" href="${COMMUNITY_BASE_URL}/write">글쓰기</a>` : `<a class="button" href="${COMMUNITY_BASE_URL}/login">Discord로 시작하기</a>`;
  const categories = ["전체", ...COMMUNITY_CATEGORIES].map((category) => {
    const active = category === "전체" ? !selectedCategory : category === selectedCategory;
    const href = category === "전체" ? COMMUNITY_BASE_URL : `${COMMUNITY_BASE_URL}?category=${encodeURIComponent(category)}`;
    return `<a class="filter${active ? " active" : ""}" href="${href}">${category}</a>`;
  }).join("");
  return communityLayout("커뮤니티", `<main${userMarker}><style>.post-content{display:block;min-width:0;color:inherit;text-decoration:none}.post-meta{display:block;text-decoration:none}.post-meta:hover{color:var(--accent)}.post-stats{display:flex;flex-wrap:wrap;gap:12px;margin-top:14px;color:var(--faint);font-size:11px}.post-stat.liked{color:var(--danger)}.post-stat:first-child{color:var(--accent)}</style><section class="intro"><div><p class="eyebrow">Barkan community</p><h1>커뮤니티</h1></div><p class="intro-copy">바르칸에서 먼저 알아낸 방법과 오늘의 발견을 나누는 공간입니다. 게임 계정과 연결된 Discord로 글을 남겨 보세요.</p></section>${notice ? `<div class="notice">${esc(notice)}</div>` : ""}<div class="toolbar"><div class="filters">${categories}</div><div style="display:flex;gap:8px;flex-wrap:wrap">${current ? `<a class="button ghost" href="${COMMUNITY_BASE_URL}/profile">내 프로필</a>` : ""}${action}</div></div><section class="feed" aria-label="커뮤니티 글">${cards}</section></main>`);
}
function communityWritePage(current, error = "") {
  return communityLayout("글쓰기", `<main data-community-user="1"><section class="panel"><p class="eyebrow">Write a log</p><h2>새 기록 남기기</h2><p class="muted">게임에서 직접 확인한 정보와 경험을 다른 항해자에게 건네주세요.</p>${error ? `<div class="notice danger">${esc(error)}</div>` : ""}<form method="post" action="${COMMUNITY_BASE_URL}/write"><input type="hidden" name="csrf" value="${esc(current.csrf_token)}"><label for="category">분류</label><select id="category" name="category">${COMMUNITY_CATEGORIES.map((category) => `<option value="${category}">${category}</option>`).join("")}</select><label for="title">제목</label><input id="title" name="title" maxlength="80" required placeholder="예: 비 오는 날 원양어선에서 잘 잡히는 물고기"><label for="body">내용</label><textarea id="body" name="body" maxlength="5000" required placeholder="다른 사람이 그대로 따라 할 수 있도록 장소, 조건, 순서를 자세히 적어 주세요."></textarea><small class="help">마크 계정과 Discord 닉네임이 함께 표시됩니다. 개인정보는 적지 마세요.</small><div style="display:flex;gap:9px;margin-top:22px"><button class="button" type="submit">게시하기</button><a class="button ghost" href="${COMMUNITY_BASE_URL}">취소</a></div></form></section></main>`);
}
function communityPostPage(current, post, error = "", comments = []) {
  if (!post) return communityLayout("글을 찾을 수 없음", `<main><section class="panel"><h2>기록을 찾을 수 없습니다.</h2><a class="back" href="${COMMUNITY_BASE_URL}">커뮤니티로 돌아가기</a></section></main>`);
  const postId = encodeURIComponent(post.id);
  const heart = current
    ? `<form method="post" action="${COMMUNITY_BASE_URL}/post/${postId}/heart" class="heart-form"><input type="hidden" name="csrf" value="${esc(current.csrf_token)}"><button class="heart-button${post.liked ? " active" : ""}" type="submit" aria-label="${post.liked ? "하트 취소" : "하트 보내기"}">${post.liked ? "♥" : "♡"} <span>${communityCount(post.like_count)}</span></button></form>`
    : `<a class="heart-button" href="${COMMUNITY_BASE_URL}/login">♡ <span>${communityCount(post.like_count)}</span></a>`;
  const commentCards = comments.length ? comments.map((comment) => {
    const commentHeart = current
      ? `<form method="post" action="${COMMUNITY_BASE_URL}/comment/${encodeURIComponent(comment.id)}/heart" class="comment-heart-form"><input type="hidden" name="csrf" value="${esc(current.csrf_token)}"><button class="comment-heart${comment.liked ? " active" : ""}" type="submit" aria-label="${comment.liked ? "댓글 하트 취소" : "댓글에 하트 보내기"}">${comment.liked ? "♥" : "♡"} <span>${communityCount(comment.like_count)}</span></button></form>`
      : `<a class="comment-heart" href="${COMMUNITY_BASE_URL}/login" aria-label="로그인하고 댓글에 하트 보내기">♡ <span>${communityCount(comment.like_count)}</span></a>`;
    const deleteAction = current?.minecraft_uuid === comment.minecraft_uuid
      ? `<form method="post" action="${COMMUNITY_BASE_URL}/comment/${encodeURIComponent(comment.id)}/delete" class="comment-delete-form"><input type="hidden" name="csrf" value="${esc(current.csrf_token)}"><button class="comment-delete" type="submit">삭제</button></form>`
      : "";
    return `<article class="community-comment"><div class="comment-rail" aria-hidden="true"></div><div class="comment-main"><header class="comment-header"><div><a class="comment-author" href="${COMMUNITY_BASE_URL}/user/${encodeURIComponent(comment.minecraft_uuid)}">${esc(comment.player_name)}</a><span class="comment-date">${new Date(comment.created_at).toLocaleString("ko-KR")}</span></div><div class="comment-actions">${commentHeart}${deleteAction}</div></header><p class="comment-body">${esc(comment.body)}</p></div></article>`;
  }).join("") : `<div class="comments-empty">아직 댓글이 없습니다. 이 항해 기록에 첫 번째 목소리를 남겨 보세요.</div>`;
  const composer = current
    ? `<form method="post" action="${COMMUNITY_BASE_URL}/post/${postId}/comment" class="comment-composer"><input type="hidden" name="csrf" value="${esc(current.csrf_token)}"><label for="comment-body">댓글 남기기</label><textarea id="comment-body" name="body" maxlength="1000" rows="4" required placeholder="이 기록에 대한 경험이나 질문을 남겨 주세요."></textarea><div class="comment-composer-footer"><small>최대 1,000자 · 게임 계정 이름으로 표시됩니다.</small><button class="button" type="submit">댓글 등록</button></div></form>`
    : `<div class="comment-login"><p>Discord로 로그인하면 이 기록에 댓글을 남길 수 있습니다.</p><a class="button ghost" href="${COMMUNITY_BASE_URL}/login">로그인하고 댓글 쓰기</a></div>`;
  return communityLayout(post.title, `<main${current ? " data-community-user=\"1\"" : ""}><style>.detail-head{position:relative}.detail-meta{display:flex;flex-wrap:wrap;gap:12px;align-items:center}.post-stats{display:flex;flex-wrap:wrap;gap:12px;margin-top:14px;color:var(--faint);font-size:11px}.detail-actions{display:flex;align-items:center;gap:12px;margin-top:24px}.heart-form{margin:0}.heart-button{display:inline-flex;align-items:center;gap:7px;min-height:40px;padding:8px 13px;border:1px solid rgba(226,173,103,.55);background:rgba(226,173,103,.08);color:var(--accent);font:800 14px Barkan;text-decoration:none;cursor:pointer}.heart-button:hover,.heart-button.active{background:rgba(226,173,103,.18);border-color:var(--accent)}.heart-button.active{color:var(--danger);border-color:rgba(255,155,159,.55)}.view-count{color:var(--faint);font-size:11px}.comments-section{margin-top:58px;padding-top:30px;border-top:1px solid var(--line)}.comments-heading{display:flex;align-items:end;justify-content:space-between;gap:16px;margin-bottom:19px}.comments-heading h2{margin:0;font-size:21px;letter-spacing:-.07em}.comments-heading span{color:var(--faint);font-size:11px}.comments-list{border-top:1px solid var(--line)}.community-comment{display:grid;grid-template-columns:13px minmax(0,1fr);gap:14px;padding:19px 0;border-bottom:1px solid var(--line)}.comment-rail{position:relative;width:5px;margin:4px 0 3px;background:rgba(150,217,196,.25)}.comment-rail:before{position:absolute;top:0;left:-2px;width:9px;height:9px;border:1px solid var(--mint);border-radius:50%;background:var(--ink);content:""}.comment-main{min-width:0}.comment-header{display:flex;align-items:start;justify-content:space-between;gap:14px}.comment-author{color:var(--text);font-size:13px;font-weight:800;text-decoration:none}.comment-author:hover{color:var(--accent)}.comment-date{margin-left:9px;color:var(--faint);font-size:10px}.comment-actions{display:flex;align-items:center;gap:9px}.comment-heart{display:inline-flex;align-items:center;gap:5px;padding:3px 7px;border:1px solid rgba(226,173,103,.35);background:transparent;color:var(--accent);font:800 12px Barkan;text-decoration:none;cursor:pointer}.comment-heart:hover,.comment-heart.active{border-color:var(--accent);background:rgba(226,173,103,.12)}.comment-heart.active{color:var(--danger);border-color:rgba(255,155,159,.55)}.comment-heart-form,.comment-delete-form{margin:0}.comment-delete{padding:3px 0;border:0;background:transparent;color:var(--faint);font:500 11px Barkan;cursor:pointer}.comment-delete:hover{color:var(--danger)}.comment-body{margin:11px 0 0;color:#d7e5dc;font-size:14px;line-height:1.75;white-space:pre-wrap}.comments-empty{padding:22px 0;color:var(--muted);font-size:13px}.comment-composer,.comment-login{margin-top:28px;padding:20px;border:1px solid var(--line);background:rgba(12,40,37,.42)}.comment-composer label{display:block;margin:0 0 9px;color:var(--text);font-size:14px}.comment-composer textarea{min-height:112px;margin:0;resize:vertical}.comment-composer-footer{display:flex;align-items:center;justify-content:space-between;gap:15px;margin-top:11px}.comment-composer-footer small{color:var(--faint);font-size:10px}.comment-login{display:flex;align-items:center;justify-content:space-between;gap:18px;color:var(--muted);font-size:13px}.comment-login p{margin:0}@media(max-width:720px){.comments-heading{display:block}.comments-heading span{display:block;margin-top:5px}.comment-header{display:block}.comment-actions{margin-top:9px}.comment-composer-footer,.comment-login{display:block}.comment-composer-footer .button,.comment-login .button{width:100%;margin-top:13px}}</style><article class="detail"><div class="detail-head"><p class="eyebrow">${esc(post.category)}</p><h1>${esc(post.title)}</h1><p class="detail-meta"><span>${esc(post.player_name)}</span><span>${new Date(post.created_at).toLocaleString("ko-KR")}</span><span class="view-count">조회 ${communityCount(post.view_count)}</span><span class="view-count">댓글 ${communityCount(post.comment_count)}</span></p></div>${error ? `<div class="notice danger">${esc(error)}</div>` : ""}<div class="detail-actions">${heart}<span class="view-count">이 글이 도움이 됐다면 하트를 남겨 주세요.</span></div><div class="detail-body">${esc(post.body)}</div><a class="back" href="${COMMUNITY_BASE_URL}">← 커뮤니티로 돌아가기</a><section class="comments-section" id="comments" aria-labelledby="comments-title"><div class="comments-heading"><h2 id="comments-title">댓글</h2><span>${communityCount(post.comment_count)}개의 항해 메모</span></div><div class="comments-list">${commentCards}</div>${composer}</section></article></main>`);
}
function communityViewer(req, current) {
  if (current) return { key: `user:${current.minecraft_uuid}`, cookie: null };
  const existing = cookies(req).community_viewer;
  const value = existing || token(24);
  return {
    key: `anon:${hash(value)}`,
    cookie: existing ? null : `community_viewer=${encodeURIComponent(value)}; Path=/community; Max-Age=31536000; HttpOnly; Secure; SameSite=Lax`
  };
}
function communityProfilePage(profile, current = null) {
  if (!profile) return communityLayout("프로필을 찾을 수 없음", `<main><section class="panel"><h2>연결된 프로필을 찾을 수 없습니다.</h2><a class="back" href="${COMMUNITY_BASE_URL}">커뮤니티로 돌아가기</a></section></main>`);
  const game = profile.game ?? {};
  const fishLevel = Number(game.fishingLevel ?? 0);
  const currentExp = Number(game.currentExp ?? 0);
  const requiredExp = Number(game.requiredExp ?? 0);
  const expPercent = requiredExp > 0 ? Math.max(0, Math.min(100, Math.round((currentExp / requiredExp) * 100))) : 0;
  const displayName = String(game.name ?? profile.player_name ?? "항해자");
  const titles = Array.isArray(game.ownedTitles) ? game.ownedTitles : [];
  const regions = Array.isArray(game.visitedRegions) ? game.visitedRegions : [];
  const avatar = validUuid(profile.minecraft_uuid) ? `https://mc-heads.net/avatar/${encodeURIComponent(profile.minecraft_uuid)}/160` : "";
  const skinBase = validUuid(profile.minecraft_uuid) ? `https://mc-heads.net/body/${encodeURIComponent(profile.minecraft_uuid)}/250` : "";
  const intro = esc(profile.introduction || "아직 소개글이 없습니다. 마크에서 /프로필을 열고 소개글을 설정해 보세요.").replace(/\n/g, "<br>");
  const skinViews = [
    ["앞", skinBase],
    ["오른쪽", `${skinBase}/right`],
    ["뒤", `${skinBase}/back`],
    ["왼쪽", `${skinBase}/left`]
  ];
  const stat = (label, value, detail = "") => `<div class="profile-stat"><span>${esc(label)}</span><strong>${esc(String(value))}</strong>${detail ? `<small>${esc(detail)}</small>` : ""}</div>`;
  const equipped = Object.entries(profile.parts ?? {}).filter(([, value]) => value).map(([slot, value]) => `<div class="equipment-row"><span>${esc(slot)}</span><b>${esc(String(value))}</b></div>`).join("") || `<p class="muted">장착한 장비 정보가 없습니다.</p>`;
  const postCards = profile.posts.length ? profile.posts.map((post) => `<a class="profile-post" href="${COMMUNITY_BASE_URL}/post/${encodeURIComponent(post.id)}"><span>${esc(post.category)}</span><div><strong>${esc(post.title)}</strong><small>${new Date(post.created_at).toLocaleDateString("ko-KR")}</small></div><b>→</b></a>`).join("") : `<div class="empty">아직 작성한 글이 없습니다.</div>`;
  const profileMarker = current ? " data-community-user=\"1\"" : "";
  return communityLayout("프로필", `<main${profileMarker}><style>
  .profile-hero{display:grid;grid-template-columns:1fr 240px;gap:28px;align-items:stretch;padding:34px 0 30px;border-bottom:1px solid var(--line)}
  .profile-identity{display:flex;gap:18px;align-items:center}.profile-avatar{width:72px;height:72px;object-fit:cover;border:1px solid rgba(150,217,196,.45);background:#071b1a;image-rendering:auto}.profile-kicker{margin:0 0 7px;color:var(--mint);font:800 10px ui-monospace,monospace;letter-spacing:.15em;text-transform:uppercase}.profile-name{margin:0;font-size:clamp(2rem,5vw,3.7rem);font-weight:800;letter-spacing:-.1em;line-height:.95}.profile-discord{margin:9px 0 0;color:var(--muted);font-size:12px}.profile-intro{max-width:620px;margin:24px 0 0;padding:15px 17px;border-left:2px solid var(--accent);background:rgba(226,173,103,.08);color:#dce9df;font-size:14px;line-height:1.7}.profile-skin{display:flex;justify-content:center;align-items:end;min-height:190px;border:1px solid var(--line);background:radial-gradient(circle at 50% 30%,rgba(150,217,196,.18),transparent 55%),linear-gradient(150deg,rgba(150,217,196,.13),rgba(7,27,26,.3));overflow:hidden}.skin-viewer{width:100%;height:100%;min-height:250px;display:flex;flex-direction:column;align-items:center;justify-content:end;cursor:grab;touch-action:none;user-select:none}.skin-viewer:active{cursor:grabbing}.skin-stage{position:relative;display:flex;width:180px;height:222px;align-items:end;justify-content:center;perspective:650px;transform-style:preserve-3d}.skin-figure{position:relative;display:flex;width:170px;height:215px;align-items:end;justify-content:center;transform-origin:50% 75%;will-change:transform;transition:transform .12s ease-out}.skin-figure img{position:absolute;bottom:0;height:215px;max-width:170px;object-fit:contain;object-position:center bottom;filter:drop-shadow(0 18px 14px rgba(0,0,0,.38));transition:opacity .15s ease}.skin-figure img[hidden]{display:none}.skin-hint{display:flex;align-items:center;gap:10px;margin:4px 0 12px;color:var(--muted);font-size:10px}.skin-hint b{color:var(--mint);font-weight:800}.profile-stats{display:grid;grid-template-columns:repeat(6,1fr);gap:1px;margin:24px 0;background:var(--line);border:1px solid var(--line)}.profile-stat{min-height:104px;padding:15px;background:rgba(12,40,37,.74)}.profile-stat span,.profile-stat small{display:block;color:var(--muted);font-size:11px}.profile-stat strong{display:block;margin-top:9px;color:var(--text);font-size:25px;letter-spacing:-.06em}.profile-stat small{margin-top:3px;color:var(--faint)}.profile-layout{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(260px,.8fr);gap:26px}.profile-section{padding-top:27px;border-top:1px solid var(--line)}.profile-section h2{margin:0 0 15px;font-size:19px;letter-spacing:-.07em}.profile-section h2 small{margin-left:7px;color:var(--faint);font:500 11px ui-monospace,monospace;letter-spacing:0}.progress{height:7px;margin:12px 0 7px;background:#071b1a;border:1px solid var(--line)}.progress i{display:block;height:100%;background:var(--mint)}.progress-line{display:flex;justify-content:space-between;color:var(--muted);font-size:11px}.profile-posts{border-top:1px solid var(--line)}.profile-post{display:grid;grid-template-columns:58px minmax(0,1fr) 20px;gap:13px;align-items:center;padding:15px 0;border-bottom:1px solid var(--line);color:var(--text);text-decoration:none}.profile-post:hover strong{color:var(--accent)}.profile-post>span{color:var(--mint);font:800 10px ui-monospace,monospace}.profile-post strong{display:block;font-size:15px;font-weight:500;letter-spacing:-.04em}.profile-post small{display:block;margin-top:3px;color:var(--faint);font-size:10px}.profile-post>b{color:var(--accent);font-size:18px;font-weight:400}.equipment{border-top:1px solid var(--line)}.equipment-row{display:flex;justify-content:space-between;gap:10px;padding:10px 0;border-bottom:1px solid var(--line);font-size:12px}.equipment-row span{color:var(--muted)}.equipment-row b{font-weight:500;text-align:right}.profile-tags{display:flex;flex-wrap:wrap;gap:6px}.profile-tag{padding:6px 9px;border:1px solid var(--line);color:var(--muted);font-size:11px}.profile-actions{display:flex;gap:9px;margin-top:20px}.profile-actions .button{min-height:38px;padding:8px 12px}@media(max-width:760px){.profile-hero{grid-template-columns:1fr}.profile-skin{min-height:150px}.skin-stage{height:210px}.skin-figure{height:200px}.skin-figure img{height:200px;max-width:160px}.profile-stats{grid-template-columns:repeat(2,1fr)}.profile-stat:last-child{grid-column:span 2}.profile-layout{grid-template-columns:1fr}}
  </style><section class="profile-hero"><div><div class="profile-identity">${avatar ? `<img class="profile-avatar" src="${avatar}" alt="Discord 프로필 이미지">` : `<div class="profile-avatar" aria-hidden="true"></div>`}<div><p class="profile-kicker">Barkan profile</p><h1 class="profile-name">${esc(displayName)}</h1><p class="profile-discord">${esc(profile.discord_name ?? "Discord 연결됨")} · ${esc(game.equippedTitle ?? "항해자")}</p></div></div><div class="profile-actions"><a class="button ghost" href="${COMMUNITY_BASE_URL}">커뮤니티로</a>${current ? `<a class="button" href="${COMMUNITY_BASE_URL}/write">글쓰기</a>` : ""}</div></div><div class="profile-skin">${skin ? `<img src="${skin}" alt="${esc(displayName)}의 마인크래프트 스킨" loading="lazy">` : `<span class="muted">스킨 정보를 준비 중입니다.</span>`}</div></section><section class="profile-stats" aria-label="서버 기록">${stat("낚시 레벨", fishLevel)}${stat("발견 물고기", `${profile.fishCount}종`)}${stat("탐험 지역", `${profile.regionCount}곳`)}${stat("총 낚시", profile.totalFishing)}${stat("최고 콤보", Number(game.maxCombo ?? 0))}</section><div class="profile-layout"><div><section class="profile-section"><h2>성장 기록 <small>GAME PROGRESS</small></h2><div class="progress"><i style="width:${expPercent}%"></i></div><div class="progress-line"><span>낚시 경험치</span><span>${currentExp.toLocaleString("ko-KR")} / ${requiredExp.toLocaleString("ko-KR")}</span></div><div class="profile-tags" style="margin-top:17px">${["요리", "수집", "탐험"].map((label) => `<span class="profile-tag">${label} Lv.${Number(label === "요리" ? profile.cookingLevel : label === "수집" ? profile.collectionLevel : profile.explorationLevel)}</span>`).join("")}</div></section><section class="profile-section"><h2>작성한 글 <small>${profile.posts.length} POSTS</small></h2><div class="profile-posts">${postCards}</div></section></div><aside><section class="profile-section"><h2>항해 정보</h2><div class="equipment"><div class="equipment-row"><span>길드</span><b>${profile.guild ? `${esc(profile.guild.name)} · ${profile.guild.memberCount}명` : "가입한 길드 없음"}</b></div><div class="equipment-row"><span>섬</span><b>${profile.island ? `${esc(profile.island.name)} · 방문 ${profile.island.visitCount}회` : "개인 섬 없음"}</b></div><div class="equipment-row"><span>칭호</span><b>${esc(game.equippedTitle ?? "항해자")}</b></div></div></section><section class="profile-section"><h2>장착 장비 <small>EQUIPMENT</small></h2><div class="equipment">${equipped}</div></section><section class="profile-section"><h2>발견한 지역</h2><div class="profile-tags">${regions.length ? regions.slice(0, 18).map((region) => `<span class="profile-tag">${esc(region)}</span>`).join("") : `<span class="muted">아직 기록이 없습니다.</span>`}</div></section></aside></div></main>`);
}
function communityProfileEditPage(current, introduction = "", error = "") {
  return communityLayout("소개글 수정", `<main data-community-user="1"><section class="panel"><p class="eyebrow">Edit profile</p><h2>소개글 수정</h2><p class="muted">최대 100자이며, 저장하면 마크 서버의 <code>/프로필</code>과 웹 프로필에 함께 표시됩니다.</p>${error ? `<div class="notice danger">${esc(error)}</div>` : ""}<form method="post" action="${COMMUNITY_BASE_URL}/profile/edit"><input type="hidden" name="csrf" value="${esc(current.csrf_token)}"><label for="introduction">소개글</label><textarea id="introduction" name="introduction" maxlength="100" rows="4" placeholder="예: 항구에서 낚시와 요리를 연구하는 항해자입니다.">${esc(introduction)}</textarea><small class="help">비워 두면 기본 안내가 표시됩니다.</small><div style="display:flex;gap:9px;margin-top:22px"><button class="button" type="submit">저장하기</button><a class="button ghost" href="${COMMUNITY_BASE_URL}/profile">취소</a></div></form></section></main>`);
}

function profileClientJs() {
  return [
    "(()=>{",
    "const root=document.querySelector('[data-skin-viewer]'),canvas=root?.querySelector('[data-skin-canvas]');if(!root||!canvas)return;root.querySelector('.skin-hint span')?.remove();const avatar=root.closest('main')?.querySelector('.profile-avatar')?.src||'';const uuid=(avatar.match(/avatar\\/([^/]+)/)||[])[1]||'';const label=root.querySelector('[data-skin-angle]');",
    "const skinUrl=uuid?'https://mc-heads.net/skin/'+uuid+'/':'';const canRender=Boolean(canvas.getContext?.('webgl2')||canvas.getContext?.('webgl'));",
    "if(window.skinview3d&&canRender){const viewer=new skinview3d.SkinViewer({canvas,width:280,height:250,skin:skinUrl});viewer.controls.enableRotate=true;viewer.controls.enableZoom=true;viewer.controls.enablePan=false;viewer.zoom=0.84;viewer.animation=new skinview3d.IdleAnimation();function updateLabel(){const rotation=viewer.playerObject?.rotation?.y??0;const degrees=Math.round((((rotation*180/Math.PI)%360)+360)%360);if(label)label.textContent=degrees+'°';}canvas.addEventListener('pointerdown',()=>root.classList.add('is-dragging'));canvas.addEventListener('pointerup',()=>root.classList.remove('is-dragging'));canvas.addEventListener('pointerleave',()=>root.classList.remove('is-dragging'));canvas.addEventListener('pointercancel',()=>root.classList.remove('is-dragging'));const tick=()=>{if(!document.documentElement.contains(root)){viewer.dispose?.();return;}updateLabel();requestAnimationFrame(tick)};requestAnimationFrame(tick);}else if(label)label.textContent='';",
    "const recordsStyle=document.createElement('style');recordsStyle.textContent='.profile-record-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.profile-record{padding:12px;border:1px solid var(--line);background:rgba(12,40,37,.5)}.profile-record strong{display:block;font-size:13px}.profile-record small{display:block;margin-top:3px;color:var(--mint);font-size:10px}.profile-record p{margin:7px 0 0;color:var(--muted);font-size:11px;line-height:1.55}.profile-record a{color:var(--text);text-decoration:none}.profile-record a:hover{color:var(--accent)}@media(max-width:760px){.profile-record-grid{grid-template-columns:1fr}}';document.head.append(recordsStyle);",
    "const makeText=(tag,value,cls='')=>{const node=document.createElement(tag);if(cls)node.className=cls;node.textContent=String(value??'');return node;};",
    "const linkGuild=(guild)=>{if(!guild?.id)return;const row=[...root.closest('main').querySelectorAll('.equipment-row')].find((candidate)=>candidate.firstElementChild?.textContent==='길드');if(!row?.lastElementChild)return;const link=document.createElement('a');link.href='/community/guild/'+encodeURIComponent(guild.id);link.textContent=String(guild.name)+' · '+String(guild.memberCount)+'명';link.style.color='inherit';link.style.textDecoration='none';row.lastElementChild.textContent='';row.lastElementChild.append(link);};",
    "const renderRecords=(data)=>{const layout=root.closest('main')?.querySelector('.profile-layout'),left=layout?.firstElementChild;if(!left||!data)return;const makeSection=(title,meta,items,kind)=>{const section=document.createElement('section');section.className='profile-section';const heading=document.createElement('h2');heading.append(makeText('span',title),makeText('small',meta));const grid=document.createElement('div');grid.className='profile-record-grid';if(!items?.length){grid.append(makeText('p','아직 기록이 없습니다.','muted'));}else items.forEach((item)=>{const card=document.createElement('article');card.className='profile-record';if(kind==='achievement'){card.append(makeText('strong',item.name),makeText('small',(item.tab||'기록')+' · '+(item.tier||'완료')),makeText('p',item.desc));}else{card.append(makeText('strong',item.name),makeText('small','획득한 칭호'),makeText('p',item.desc));}grid.append(card);});section.append(heading,grid);return section;};const posts=left.querySelector('.profile-posts')?.closest('.profile-section');left.insertBefore(makeSection('클리어한 도전과제',(data.achievements?.length||0)+' ACHIEVEMENTS',data.achievements,'achievement'),posts||null);left.insertBefore(makeSection('획득한 칭호',(data.titles?.length||0)+' TITLES',data.titles,'title'),posts||null);};",
    "fetch('/community/profile/records/'+encodeURIComponent(uuid)).then((response)=>response.ok?response.json():null).then((data)=>{linkGuild(data?.guild);renderRecords(data);}).catch(()=>{});",
    "})();"
  ].join("\n");
}

function communityProfilePageInteractive(profile, current = null, notice = "") {
  if (!profile) return communityLayout("프로필을 찾을 수 없음", `<main><section class="panel"><h2>연결된 프로필을 찾을 수 없습니다.</h2><a class="back" href="${COMMUNITY_BASE_URL}">커뮤니티로 돌아가기</a></section></main>`);
  const game = profile.game ?? {};
  const displayName = String(game.name ?? profile.player_name ?? "항해자");
  const intro = esc(profile.introduction || "아직 소개글이 없습니다. 마크에서 /프로필을 열고 소개글을 설정해 보세요.").replace(/\n/g, "<br>");
  const uuid = encodeURIComponent(profile.minecraft_uuid);
  const fishLevel = Number(game.fishingLevel ?? 0);
  const currentExp = Number(game.currentExp ?? 0);
  const requiredExp = Number(game.requiredExp ?? 0);
  const expPercent = requiredExp > 0 ? Math.max(0, Math.min(100, Math.round(currentExp * 100 / requiredExp))) : 0;
  const regions = Array.isArray(game.visitedRegions) ? game.visitedRegions : [];
  const titles = Array.isArray(game.ownedTitles) ? game.ownedTitles : [];
  const stat = (label, value, accent = "") => `<div class="profile-stat"><span>${esc(label)}</span><strong class="${accent}">${esc(String(value))}</strong></div>`;
  const equipped = Object.entries(profile.parts ?? {}).filter(([, value]) => value).map(([slot, value]) => `<div class="equipment-row"><span>${esc(slot)}</span><b>${esc(String(value))}</b></div>`).join("") || `<p class="muted">장착한 장비 정보가 없습니다.</p>`;
  const postCards = profile.posts.length ? profile.posts.map((post) => `<a class="profile-post" href="${COMMUNITY_BASE_URL}/post/${encodeURIComponent(post.id)}"><span>${esc(post.category)}</span><div><strong>${esc(post.title)}</strong><small>${new Date(post.created_at).toLocaleDateString("ko-KR")}</small></div><b>→</b></a>`).join("") : `<div class="empty">아직 작성한 글이 없습니다.</div>`;
  const currentMarker = current ? " data-community-user=\"1\"" : ""; /*
  return communityLayout("프로필", `<main${currentMarker}>${notice ? `<div class="notice ok">${esc(notice)}</div>` : ""}<style>.skin-canvas{display:block;width:100%;height:250px;touch-action:none;cursor:grab}.skin-canvas:active{cursor:grabbing}</style><style>
  .profile-hero{display:grid;grid-template-columns:minmax(0,1fr) 270px;gap:28px;align-items:stretch;padding:34px 0 30px;border-bottom:1px solid var(--line)}.profile-identity{display:flex;gap:18px;align-items:center}.profile-avatar{width:76px;height:76px;object-fit:cover;border:1px solid rgba(150,217,196,.45);background:#071b1a}.profile-kicker{margin:0 0 7px;color:var(--mint);font:800 10px ui-monospace,monospace;letter-spacing:.15em;text-transform:uppercase}.profile-name{margin:0;font-size:clamp(2rem,5vw,3.7rem);font-weight:800;letter-spacing:-.1em;line-height:.95}.profile-discord{margin:9px 0 0;color:var(--muted);font-size:12px}.profile-intro{max-width:650px;margin:25px 0 0;padding:15px 17px;border-left:2px solid var(--accent);background:rgba(226,173,103,.08);color:#dce9df;font-size:14px;line-height:1.7}.profile-skin{display:flex;justify-content:center;align-items:end;min-height:255px;border:1px solid var(--line);background:radial-gradient(circle at 50% 30%,rgba(150,217,196,.18),transparent 55%),linear-gradient(150deg,rgba(150,217,196,.13),rgba(7,27,26,.3));overflow:hidden}.skin-viewer{width:100%;min-height:255px;display:flex;flex-direction:column;align-items:center;justify-content:end;cursor:grab;touch-action:none;user-select:none}.skin-viewer:active{cursor:grabbing}.skin-stage{position:relative;width:190px;height:225px;perspective:650px}.skin-figure{position:relative;display:flex;width:180px;height:220px;align-items:end;justify-content:center;transform-origin:50% 75%;will-change:transform;transition:transform .1s ease-out}.skin-figure img{position:absolute;bottom:0;height:220px;max-width:175px;object-fit:contain;object-position:center bottom;filter:drop-shadow(0 18px 14px rgba(0,0,0,.38));transition:opacity .12s ease}.skin-figure img[hidden]{display:none}.skin-hint{display:flex;align-items:center;gap:10px;margin:3px 0 12px;color:var(--muted);font-size:10px}.skin-hint b{color:var(--mint);font-weight:800}.profile-stats{display:grid;grid-template-columns:repeat(6,1fr);gap:1px;margin:24px 0;background:var(--line);border:1px solid var(--line)}.profile-stat{min-height:96px;padding:15px;background:rgba(12,40,37,.74)}.profile-stat span{display:block;color:var(--muted);font-size:11px}.profile-stat strong{display:block;margin-top:9px;color:var(--text);font-size:23px;letter-spacing:-.06em}.profile-stat strong.pop{color:var(--accent)}.profile-layout{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(260px,.8fr);gap:26px}.profile-section{padding-top:27px;border-top:1px solid var(--line)}.profile-section h2{margin:0 0 15px;font-size:19px;letter-spacing:-.07em}.profile-section h2 small{margin-left:7px;color:var(--faint);font:500 11px ui-monospace,monospace;letter-spacing:0}.progress{height:7px;margin:12px 0 7px;background:#071b1a;border:1px solid var(--line)}.progress i{display:block;height:100%;background:var(--mint)}.progress-line{display:flex;justify-content:space-between;color:var(--muted);font-size:11px}.profile-posts{border-top:1px solid var(--line)}.profile-post{display:grid;grid-template-columns:58px minmax(0,1fr) 20px;gap:13px;align-items:center;padding:15px 0;border-bottom:1px solid var(--line);color:var(--text);text-decoration:none}.profile-post:hover strong{color:var(--accent)}.profile-post>span{color:var(--mint);font:800 10px ui-monospace,monospace}.profile-post strong{display:block;font-size:15px;font-weight:500;letter-spacing:-.04em}.profile-post small{display:block;margin-top:3px;color:var(--faint);font-size:10px}.profile-post>b{color:var(--accent);font-size:18px;font-weight:400}.equipment{border-top:1px solid var(--line)}.equipment-row{display:flex;justify-content:space-between;gap:10px;padding:10px 0;border-bottom:1px solid var(--line);font-size:12px}.equipment-row span{color:var(--muted)}.equipment-row b{font-weight:500;text-align:right}.profile-tags{display:flex;flex-wrap:wrap;gap:6px}.profile-tag{padding:6px 9px;border:1px solid var(--line);color:var(--muted);font-size:11px}.profile-actions{display:flex;gap:9px;margin-top:20px}.profile-actions .button{min-height:38px;padding:8px 12px}@media(max-width:760px){.profile-hero{grid-template-columns:1fr}.profile-skin,.skin-viewer{min-height:235px}.profile-stats{grid-template-columns:repeat(2,1fr)}.profile-stat:last-child{grid-column:span 2}.profile-layout{grid-template-columns:1fr}}
  return communityLayout("프로필", `<main${currentMarker}>${notice ? `<div class="notice ok">${esc(notice)}</div>` : ""}<style>
}

*/
  return communityLayout("프로필", `<main${currentMarker}>${notice ? `<div class="notice ok">${esc(notice)}</div>` : ""}<style>
  .profile-hero{display:grid;grid-template-columns:minmax(0,1fr) 280px;gap:28px;align-items:stretch;padding:34px 0 30px;border-bottom:1px solid var(--line)}.profile-identity{display:flex;gap:18px;align-items:center}.profile-avatar{width:76px;height:76px;object-fit:cover;border:1px solid rgba(150,217,196,.45);background:#071b1a}.profile-kicker{margin:0 0 7px;color:var(--mint);font:800 10px ui-monospace,monospace;letter-spacing:.15em;text-transform:uppercase}.profile-name{margin:0;font-size:clamp(2rem,5vw,3.7rem);font-weight:800;letter-spacing:-.1em;line-height:.95}.profile-discord{margin:9px 0 0;color:var(--muted);font-size:12px}.profile-intro{max-width:650px;margin:25px 0 0;padding:15px 17px;border-left:2px solid var(--accent);background:rgba(226,173,103,.08);color:#dce9df;font-size:14px;line-height:1.7}.profile-skin{display:flex;justify-content:center;align-items:end;min-height:255px;border:1px solid var(--line);background:radial-gradient(circle at 50% 30%,rgba(150,217,196,.18),transparent 55%),linear-gradient(150deg,rgba(150,217,196,.13),rgba(7,27,26,.3));overflow:hidden}.skin-viewer{width:100%;min-height:255px;display:flex;flex-direction:column;align-items:center;justify-content:end;cursor:grab;touch-action:none;user-select:none}.skin-viewer:active{cursor:grabbing}.skin-stage{position:relative;width:190px;height:225px;perspective:650px}.skin-figure{position:relative;display:flex;width:180px;height:220px;align-items:end;justify-content:center;transform-origin:50% 75%;will-change:transform;transition:transform .1s ease-out}.skin-figure img{position:absolute;bottom:0;height:220px;max-width:175px;object-fit:contain;object-position:center bottom;filter:drop-shadow(0 18px 14px rgba(0,0,0,.38));transition:opacity .12s ease}.skin-figure img[hidden]{display:none}.skin-hint{display:flex;align-items:center;gap:10px;margin:3px 0 12px;color:var(--muted);font-size:10px}.skin-hint b{color:var(--mint);font-weight:800}.profile-stats{display:grid;grid-template-columns:repeat(6,1fr);gap:1px;margin:24px 0;background:var(--line);border:1px solid var(--line)}.profile-stat{min-height:96px;padding:15px;background:rgba(12,40,37,.74)}.profile-stat span{display:block;color:var(--muted);font-size:11px}.profile-stat strong{display:block;margin-top:9px;color:var(--text);font-size:23px;letter-spacing:-.06em}.profile-stat strong.pop{color:var(--accent)}.profile-layout{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(260px,.8fr);gap:26px}.profile-section{padding-top:27px;border-top:1px solid var(--line)}.profile-section h2{margin:0 0 15px;font-size:19px;letter-spacing:-.07em}.profile-section h2 small{margin-left:7px;color:var(--faint);font:500 11px ui-monospace,monospace;letter-spacing:0}.progress{height:7px;margin:12px 0 7px;background:#071b1a;border:1px solid var(--line)}.progress i{display:block;height:100%;background:var(--mint)}.progress-line{display:flex;justify-content:space-between;color:var(--muted);font-size:11px}.profile-posts{border-top:1px solid var(--line)}.profile-post{display:grid;grid-template-columns:58px minmax(0,1fr) 20px;gap:13px;align-items:center;padding:15px 0;border-bottom:1px solid var(--line);color:var(--text);text-decoration:none}.profile-post:hover strong{color:var(--accent)}.profile-post>span{color:var(--mint);font:800 10px ui-monospace,monospace}.profile-post strong{display:block;font-size:15px;font-weight:500;letter-spacing:-.04em}.profile-post small{display:block;margin-top:3px;color:var(--faint);font-size:10px}.profile-post>b{color:var(--accent);font-size:18px;font-weight:400}.equipment{border-top:1px solid var(--line)}.equipment-row{display:flex;justify-content:space-between;gap:10px;padding:10px 0;border-bottom:1px solid var(--line);font-size:12px}.equipment-row span{color:var(--muted)}.equipment-row b{font-weight:500;text-align:right}.profile-tags{display:flex;flex-wrap:wrap;gap:6px}.profile-tag{padding:6px 9px;border:1px solid var(--line);color:var(--muted);font-size:11px}.profile-actions{display:flex;gap:9px;margin-top:20px}.profile-actions .button{min-height:38px;padding:8px 12px}@media(max-width:760px){.profile-hero{grid-template-columns:1fr}.profile-skin,.skin-viewer{min-height:235px}.profile-stats{grid-template-columns:repeat(2,1fr)}.profile-stat:last-child{grid-column:span 2}.profile-layout{grid-template-columns:1fr}}
  </style><section class="profile-hero"><div><div class="profile-identity"><img class="profile-avatar" src="https://mc-heads.net/avatar/${uuid}/160" alt="${esc(displayName)}의 마인크래프트 스킨 머리" loading="lazy"><div><p class="profile-kicker">Barkan profile</p><h1 class="profile-name">${esc(displayName)}</h1><p class="profile-discord">${esc(profile.discord_name ?? "Discord 연결됨")} · ${esc(game.equippedTitle ?? "항해자")}</p></div></div><p class="profile-intro">${intro}</p><div class="profile-actions"><a class="button ghost" href="${COMMUNITY_BASE_URL}">커뮤니티로</a>${current ? `<a class="button ghost" href="${COMMUNITY_BASE_URL}/profile/edit">소개글 수정</a><a class="button" href="${COMMUNITY_BASE_URL}/write">글쓰기</a>` : ""}</div></div><div class="profile-skin"><div class="skin-viewer" data-skin-viewer tabindex="0" aria-label="마인크래프트 스킨 3D 회전 뷰어"><canvas class="skin-canvas" data-skin-canvas></canvas><div class="skin-hint"><span>드래그해서 360° 회전 · 휠로 확대</span><b data-skin-angle>3D</b></div></div></div></section><section class="profile-stats" aria-label="서버 기록">${stat("낚시 레벨", fishLevel)}${stat("인기도", `♥ ${profile.popularity}`, "pop")}${stat("발견 물고기", `${profile.fishCount}종`)}${stat("탐험 지역", `${profile.regionCount}곳`)}${stat("총 낚시", profile.totalFishing)}${stat("최고 콤보", Number(game.maxCombo ?? 0))}</section><div class="profile-layout"><div><section class="profile-section"><h2>성장 기록 <small>GAME PROGRESS</small></h2><div class="progress"><i style="width:${expPercent}%"></i></div><div class="progress-line"><span>낚시 경험치</span><span>${currentExp.toLocaleString("ko-KR")} / ${requiredExp.toLocaleString("ko-KR")}</span></div><div class="profile-tags" style="margin-top:17px"><span class="profile-tag">요리 Lv.${profile.cookingLevel}</span><span class="profile-tag">수집 Lv.${profile.collectionLevel}</span><span class="profile-tag">탐험 Lv.${profile.explorationLevel}</span><span class="profile-tag">도전과제 ${profile.achievementCount}개</span><span class="profile-tag">칭호 ${profile.titleCount}개</span></div></section><section class="profile-section"><h2>작성한 글 <small>${profile.posts.length} POSTS</small></h2><div class="profile-posts">${postCards}</div></section></div><aside><section class="profile-section"><h2>항해 정보</h2><div class="equipment"><div class="equipment-row"><span>길드</span><b>${profile.guild ? `${esc(profile.guild.name)} · ${profile.guild.memberCount}명` : "가입한 길드 없음"}</b></div><div class="equipment-row"><span>섬</span><b>${profile.island ? `${esc(profile.island.name)} · 방문 ${profile.island.visitCount}회` : "개인 섬 없음"}</b></div><div class="equipment-row"><span>칭호</span><b>${esc(game.equippedTitle ?? "항해자")}</b></div></div></section><section class="profile-section"><h2>장착 장비 <small>EQUIPMENT</small></h2><div class="equipment">${equipped}</div></section><section class="profile-section"><h2>발견한 지역</h2><div class="profile-tags">${regions.length ? regions.slice(0, 18).map((region) => `<span class="profile-tag">${esc(region)}</span>`).join("") : `<span class="muted">아직 기록이 없습니다.</span>`}</div></section></aside></div><script src="/assets/skinview3d.bundle.js" defer></script><script src="${COMMUNITY_BASE_URL}/profile.js" defer></script></main>`);
}

function guildRoleLabel(role) {
  return ({ MASTER: "길드장", VICE_MASTER: "부길드장", OFFICER: "간부", MEMBER: "길드원" })[role] ?? role;
}
function guildDate(timestamp) {
  return timestamp > 0 ? new Date(timestamp).toLocaleDateString("ko-KR") : "기록 없음";
}
function communityGuildListPage(current, guilds) {
  const marker = current ? " data-community-user=\"1\"" : "";
  const cards = guilds.length ? guilds.map((guild, index) => `<a class="guild-card" href="${COMMUNITY_BASE_URL}/guild/${encodeURIComponent(guild.id)}">${guildEmblem(guild, "guild-emblem small", true)}<div class="guild-rank">${String(index + 1).padStart(2, "0")}</div><div class="guild-card-main"><div class="guild-card-top"><h2>${esc(guild.name)}</h2><span class="guild-visibility">${guild.isPublic ? "공개 길드" : "비공개"}</span></div><p>${esc(guild.description || "아직 길드 소개가 없습니다.")}</p><div class="guild-card-meta"><span>${guild.members.length}/${guild.maxMembers || "—"}명</span><span>시즌 기여 ${guild.submitSeason.toLocaleString("ko-KR")}</span><span>길드장 ${esc(guild.ownerId || "알 수 없음")}</span></div></div><b class="guild-arrow">→</b></a>`).join("") : `<div class="empty">아직 공개된 길드가 없습니다.</div>`;
  return communityLayout("길드", `<main${marker}><style>.guild-directory{padding:34px 0 24px;border-bottom:1px solid var(--line)}.guild-directory h1{margin:0}.guild-directory-copy{max-width:580px;margin:18px 0 0;color:var(--muted);font-size:14px}.guild-toolbar{display:flex;justify-content:space-between;align-items:center;gap:15px;margin:24px 0 13px;color:var(--muted);font-size:12px}.guild-list{border-top:1px solid var(--line)}.guild-card{display:grid;grid-template-columns:72px 58px minmax(0,1fr) 24px;gap:16px;align-items:center;padding:23px 0;border-bottom:1px solid var(--line);color:var(--text);text-decoration:none}.guild-card:hover h2,.guild-card:hover .guild-arrow{color:var(--accent)}.guild-rank{color:var(--accent);font:800 17px ui-monospace,monospace}.guild-card-top{display:flex;align-items:center;gap:10px}.guild-card h2{margin:0;font-size:23px;font-weight:500;letter-spacing:-.07em;transition:color .15s}.guild-visibility{padding:3px 7px;border:1px solid var(--line);color:var(--faint);font-size:10px}.guild-card p{margin:7px 0 12px;color:var(--muted);font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.guild-card-meta{display:flex;flex-wrap:wrap;gap:14px;color:var(--faint);font-size:11px}.guild-arrow{color:var(--accent);font-size:19px;font-weight:400}.guild-emblem{display:grid;grid-template-columns:repeat(var(--emblem-size,8),1fr);grid-template-rows:repeat(var(--emblem-size,8),1fr);width:130px;height:130px;padding:5px;border:1px solid rgba(226,173,103,.48);background:#08121d;image-rendering:pixelated}.guild-emblem i{display:block}.guild-emblem.small{width:64px;height:64px;padding:2px;border-color:var(--line)}.guild-back{margin-top:20px}@media(max-width:720px){.guild-card{grid-template-columns:56px 40px minmax(0,1fr) 18px;gap:10px;padding:19px 0}.guild-card h2{font-size:19px}.guild-card p{font-size:12px}.guild-card-meta{gap:8px;font-size:10px}.guild-emblem.small{width:52px;height:52px}}</style><section class="guild-directory"><p class="eyebrow">Barkan guilds</p><h1>길드 목록</h1><p class="guild-directory-copy">함께 섬을 키우고, 요리와 채집을 나누며 항해하는 동료들의 기록입니다. 길드를 선택하면 구성원과 성장 현황을 볼 수 있습니다.</p></section><div class="guild-toolbar"><span>${guilds.length}개 길드</span><a class="button ghost" href="${COMMUNITY_BASE_URL}">커뮤니티로</a></div><section class="guild-list" aria-label="길드 목록">${cards}</section></main>`);
}
function communityGuildPage(current, guild) {
  if (!guild) return communityLayout("길드를 찾을 수 없음", `<main><section class="panel"><h2>길드 정보를 찾을 수 없습니다.</h2><a class="back" href="${COMMUNITY_BASE_URL}/guilds">길드 목록으로 돌아가기</a></section></main>`);
  const marker = current ? " data-community-user=\"1\"" : "";
  const memberCards = guild.members.length ? guild.members.map((member) => {
    const avatar = validUuid(member.uuid) ? `<img src="https://mc-heads.net/avatar/${encodeURIComponent(member.uuid)}/80" alt="${esc(member.name)} 스킨" loading="lazy">` : `<span class="guild-member-avatar"></span>`;
    const name = member.linked ? `<a href="${COMMUNITY_BASE_URL}/user/${encodeURIComponent(member.uuid)}">${esc(member.name)}</a>` : `<span>${esc(member.name)}</span>`;
    return `<div class="guild-member"><div class="guild-member-avatar-wrap">${avatar}</div><div><strong>${name}</strong><small>${esc(guildRoleLabel(member.role))} · 가입 ${esc(guildDate(member.joinedAt))}</small></div><b>${member.contributed.toLocaleString("ko-KR")} 기여</b></div>`;
  }).join("") : `<div class="empty">등록된 구성원이 없습니다.</div>`;
  const upgradeRows = [["수확기", guild.upgrades.hopper], ["액자", guild.upgrades.frame], ["가구", guild.upgrades.furniture], ["작물", guild.upgrades.crop], ["워프", guild.upgrades.warp], ["요리대", guild.upgrades.cooking]].map(([label, level]) => `<div><span>${label}</span><b>Lv.${level}</b></div>`).join("");
  return communityLayout(guild.name, `<main${marker}><style>.guild-detail-head{display:flex;justify-content:space-between;align-items:end;gap:28px;padding:34px 0 30px;border-bottom:1px solid var(--line)}.guild-detail-kicker{margin:0 0 8px;color:var(--mint);font:800 10px ui-monospace,monospace;letter-spacing:.16em;text-transform:uppercase}.guild-detail-head h1{margin:0;font-size:clamp(2.7rem,6vw,5.3rem)}.guild-detail-copy{max-width:530px;margin:17px 0 0;color:var(--muted);font-size:14px}.guild-badge{display:grid;grid-template-columns:repeat(var(--emblem-size,8),1fr);grid-template-rows:repeat(var(--emblem-size,8),1fr);width:130px;height:130px;padding:5px;border:1px solid rgba(226,173,103,.48);background:#08121d;image-rendering:pixelated}.guild-badge.full{width:min(34vw,360px);height:min(34vw,360px);min-width:180px;min-height:180px}.guild-badge i{display:block}.guild-stats{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;margin:24px 0;background:var(--line);border:1px solid var(--line)}.guild-stat{padding:16px;background:rgba(12,40,37,.74)}.guild-stat span{display:block;color:var(--muted);font-size:11px}.guild-stat strong{display:block;margin-top:8px;font-size:23px;letter-spacing:-.05em}.guild-detail-grid{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(260px,.75fr);gap:27px}.guild-section{padding-top:27px;border-top:1px solid var(--line)}.guild-section h2{margin:0 0 15px;font-size:20px;letter-spacing:-.07em}.guild-members{border-top:1px solid var(--line)}.guild-member{display:grid;grid-template-columns:44px minmax(0,1fr) auto;gap:12px;align-items:center;padding:12px 0;border-bottom:1px solid var(--line)}.guild-member-avatar-wrap,.guild-member-avatar{width:40px;height:40px;background:#071b1a;border:1px solid var(--line)}.guild-member-avatar-wrap img{display:block;width:100%;height:100%;object-fit:cover}.guild-member strong{display:block;font-size:13px}.guild-member strong a{color:var(--text);text-decoration:none}.guild-member strong a:hover{color:var(--accent)}.guild-member small{display:block;margin-top:3px;color:var(--faint);font-size:10px}.guild-member>b{color:var(--muted);font-size:11px;font-weight:500;text-align:right}.guild-upgrades{border-top:1px solid var(--line)}.guild-upgrades>div{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--line);color:var(--muted);font-size:12px}.guild-upgrades b{color:var(--text);font-weight:500}.guild-note{margin-top:16px;color:var(--faint);font-size:11px}.guild-back{margin-top:24px}@media(max-width:720px){.guild-detail-head{display:block}.guild-badge.full{width:min(80vw,320px);height:min(80vw,320px);margin-top:24px}.guild-stats{grid-template-columns:repeat(2,1fr)}.guild-detail-grid{grid-template-columns:1fr}.guild-member{grid-template-columns:40px minmax(0,1fr)}.guild-member>b{grid-column:2;text-align:left}}</style><div class="guild-detail-head"><div><p class="guild-detail-kicker">Guild profile</p><h1>${esc(guild.name)}</h1><p class="guild-detail-copy">${esc(guild.description || "아직 길드 소개가 없습니다.")}</p></div>${guildEmblem(guild, "guild-badge full", true)}</div><section class="guild-stats" aria-label="길드 기록"><div class="guild-stat"><span>구성원</span><strong>${guild.members.length}${guild.maxMembers ? ` / ${guild.maxMembers}` : ""}명</strong></div><div class="guild-stat"><span>시즌 기여</span><strong>${guild.submitSeason.toLocaleString("ko-KR")}</strong></div><div class="guild-stat"><span>누적 기여</span><strong>${guild.submitTotal.toLocaleString("ko-KR")}</strong></div><div class="guild-stat"><span>생성일</span><strong>${guildDate(guild.createdAt)}</strong></div></section><div class="guild-detail-grid"><section class="guild-section"><h2>구성원 <small>${guild.members.length} MEMBERS</small></h2><div class="guild-members">${memberCards}</div></section><aside><section class="guild-section"><h2>길드 성장</h2><div class="guild-upgrades">${upgradeRows}</div><p class="guild-note">길드장 ${esc(guild.ownerId || "알 수 없음")} · ${guild.pvp ? "길드 PvP 허용" : "길드 PvP 비허용"}</p></section><a class="back guild-back" href="${COMMUNITY_BASE_URL}/guilds">← 길드 목록으로</a></aside></div></main>`);
}

function communityGuildPageWithApply(current, guild, notice = "") {
  const page = communityGuildPage(current, guild);
  if (!guild) return page;
  const uuid = current?.minecraft_uuid;
  const member = uuid && guild.members.some((candidate) => candidate.uuid === uuid);
  const pending = uuid && guild.applications?.some((application) => application.uuid === uuid);
  const applyUrl = `${COMMUNITY_BASE_URL}/guild/${encodeURIComponent(guild.id)}/apply`;
  let panel;
  if (!current) {
    panel = `<section class="panel" style="margin:28px 0 0"><h2>길드 가입 신청</h2><p class="muted">Discord로 로그인하고 마인크래프트 계정과 연결하면 이 길드에 바로 신청할 수 있습니다.</p><a class="button" href="${COMMUNITY_BASE_URL}/login">Discord로 로그인</a></section>`;
  } else if (member) {
    panel = `<section class="panel" style="margin:28px 0 0"><h2>이미 가입한 길드입니다</h2><p class="muted">현재 ${esc(guild.name)}의 구성원으로 등록되어 있습니다.</p></section>`;
  } else if (pending) {
    panel = `<section class="panel" style="margin:28px 0 0"><h2>가입 신청을 검토 중입니다</h2><p class="muted">길드장 또는 간부가 마인크래프트에서 신청을 확인하고 승인합니다.</p></section>`;
  } else if (guild.maxMembers > 0 && guild.members.length >= guild.maxMembers) {
    panel = `<section class="panel" style="margin:28px 0 0"><h2>길드 정원이 가득 찼습니다</h2><p class="muted">현재 ${guild.members.length}/${guild.maxMembers}명입니다.</p></section>`;
  } else {
    panel = `<section class="panel" style="margin:28px 0 0"><h2>길드 가입 신청</h2><p class="muted">가입하고 싶은 이유나 함께 하고 싶은 플레이를 짧게 남겨 주세요. 신청은 길드장 또는 간부의 승인 후 확정됩니다.</p><form method="post" action="${applyUrl}"><input type="hidden" name="csrf" value="${esc(current.csrf_token)}"><label for="guild-application-message">신청 메시지 <span class="muted">(선택)</span></label><textarea id="guild-application-message" name="message" maxlength="200" rows="3" placeholder="예: 낚시와 섬 건축을 함께 하고 싶어요."></textarea><button class="button" type="submit">가입 신청 보내기</button></form></section>`;
  }
  const insertion = `${notice ? `<div class="notice" style="margin-top:28px">${esc(notice)}</div>` : ""}${panel}<div class="guild-detail-grid">`;
  return page.replace('<div class="guild-detail-grid">', insertion);
}

async function discordOAuthUser(code) {
  const tokenResponse = await fetch("https://discord.com/api/v10/oauth2/token", { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body: new URLSearchParams({ client_id: DISCORD_CLIENT_ID, client_secret: DISCORD_CLIENT_SECRET, grant_type: "authorization_code", code, redirect_uri: `${COMMUNITY_BASE_URL}/oauth/callback` }) });
  const tokenBody = await tokenResponse.json();
  if (!tokenResponse.ok || !tokenBody.access_token) throw new Error("Discord 로그인 승인을 확인하지 못했습니다.");
  const userResponse = await fetch("https://discord.com/api/v10/users/@me", { headers: { Authorization: `Bearer ${tokenBody.access_token}` } });
  const user = await userResponse.json();
  if (!userResponse.ok || !/^\d{16,22}$/.test(String(user.id ?? ""))) throw new Error("Discord 사용자 정보를 가져오지 못했습니다.");
  return user;
}

function transferReference() { return `BK${randomBytes(4).toString("hex").toUpperCase()}`; }

async function route(req, res) {
  const url = new URL(req.url, "http://localhost");
  // Caddy handle_path /vip/* strips the complete /vip/ prefix, leaving an empty path for /vip/.
  const path = url.pathname || "/";
  if (path === "/community" || path === "/community/") {
    const current = await communitySession(req);
    const category = url.searchParams.get("category") ?? "";
    return send(res, 200, communityPage(current, await communityPosts(category), url.searchParams.get("notice") ?? "", category));
  }
  if (path === "/community/session" && req.method === "GET") {
    const current = await communitySession(req);
    return json(res, 200, { authenticated: Boolean(current), playerName: current?.player_name ?? null, profileUrl: current ? `${COMMUNITY_BASE_URL}/profile` : `${COMMUNITY_BASE_URL}/login` });
  }
  if (path === "/community/guilds" && req.method === "GET") {
    return send(res, 200, communityGuildListPage(await communitySession(req), await minecraftGuildList()));
  }
  if (path.startsWith("/community/guild/") && path.endsWith("/apply") && req.method === "POST") {
    const current = await communitySession(req);
    if (!current) return redirect(res, `${COMMUNITY_BASE_URL}/login`);
    const guildIdPart = path.slice("/community/guild/".length, -"/apply".length);
    let guildId = "";
    try { guildId = decodeURIComponent(guildIdPart); } catch { guildId = ""; }
    const guild = guildId ? await minecraftGuildById(guildId) : null;
    const data = await form(req);
    const message = String(data.message ?? "").replace(/[\r\n]+/g, " ").trim();
    if (!guild || !requireCsrf(data, current) || message.length > 200) {
      return send(res, 400, communityGuildPageWithApply(current, guild, "신청 정보를 확인해 주세요."));
    }
    try {
      const submitted = await submitGuildApplication(current, guild.id, message);
      if (!submitted) return send(res, 409, communityGuildPageWithApply(current, guild, "이미 가입했거나 신청이 진행 중입니다."));
      return redirect(res, `${COMMUNITY_BASE_URL}/guild/${encodeURIComponent(guild.id)}?notice=${encodeURIComponent("가입 신청을 보냈습니다. 길드장 승인 후 가입됩니다.")}`);
    } catch (error) {
      console.error("guild web application failed", error.message);
      return send(res, 502, communityGuildPageWithApply(current, guild, "게임 서버와 연결하지 못했습니다. 잠시 후 다시 시도해 주세요."));
    }
  }
  if (path.startsWith("/community/guild/") && req.method === "GET") {
    let guildId = "";
    try { guildId = decodeURIComponent(path.slice("/community/guild/".length)); } catch { guildId = ""; }
    return send(res, 200, communityGuildPageWithApply(await communitySession(req), guildId ? await minecraftGuildById(guildId) : null, url.searchParams.get("notice") ?? ""));
  }
  if (path === "/community/login" && req.method === "GET") {
    if (!communityConfigured()) {
      return send(res, 503, communityLayout("Discord 로그인 준비 중", `<main><section class="panel"><p class="eyebrow">Community access</p><h2>Discord 로그인 준비 중입니다.</h2><p class="muted">OAuth 앱 설정이 아직 완료되지 않았습니다. 잠시 후 다시 시도해 주세요.</p><a class="back" href="${COMMUNITY_BASE_URL}">커뮤니티로 돌아가기</a></section></main>`));
    }
    const state = token(24);
    const authorize = new URL("https://discord.com/oauth2/authorize");
    authorize.searchParams.set("client_id", DISCORD_CLIENT_ID);
    authorize.searchParams.set("redirect_uri", `${COMMUNITY_BASE_URL}/oauth/callback`);
    authorize.searchParams.set("response_type", "code");
    authorize.searchParams.set("scope", "identify");
    authorize.searchParams.set("state", state);
    return redirect(res, authorize.toString(), [`community_oauth_state=${encodeURIComponent(state)}; Path=/community; Max-Age=600; HttpOnly; Secure; SameSite=Lax`]);
  }
  if (path === "/community/oauth/callback" && req.method === "GET") {
    const stateCookie = cookies(req).community_oauth_state;
    const state = url.searchParams.get("state") ?? "";
    const code = url.searchParams.get("code") ?? "";
    const clearState = "community_oauth_state=; Path=/community; Max-Age=0; HttpOnly; Secure; SameSite=Lax";
    if (!communityConfigured() || !stateCookie || !state || stateCookie !== state || !code) {
      return send(res, 400, communityLayout("로그인 오류", `<main><section class="panel"><h2>로그인 요청이 만료되었습니다.</h2><p class="muted">커뮤니티에서 Discord 로그인을 다시 시작해 주세요.</p><a class="back" href="${COMMUNITY_BASE_URL}">돌아가기</a></section></main>`), "text/html; charset=utf-8", { "Set-Cookie": clearState });
    }
    try {
      const user = await discordOAuthUser(code);
      const link = await pool.query("SELECT minecraft_uuid,player_name FROM discord_links WHERE discord_id=$1", [user.id]);
      if (!link.rowCount) {
        return send(res, 403, communityLayout("계정 연결 필요", `<main><section class="panel"><p class="eyebrow">Link required</p><h2>게임 계정 연결이 먼저 필요합니다.</h2><p class="muted">마인크래프트에서 <code>/디스코드</code>를 실행해 계정을 인증한 뒤 다시 로그인해 주세요.</p><a class="button" href="${COMMUNITY_BASE_URL}">커뮤니티로 돌아가기</a></section></main>`), "text/html; charset=utf-8", { "Set-Cookie": clearState });
      }
      const sessionToken = token();
      const csrf = token(24);
      const discordName = String(user.global_name ?? user.username ?? "").slice(0, 100);
      const avatarHash = user.avatar ? `${user.id}/${user.avatar}` : null;
      await pool.query("UPDATE discord_links SET discord_name=$1,avatar_hash=$2,updated_at=NOW() WHERE discord_id=$3", [discordName || null, avatarHash, user.id]);
      await pool.query("INSERT INTO community_sessions (token_hash,discord_id,minecraft_uuid,player_name,discord_name,avatar_hash,csrf_token,expires_at) VALUES ($1,$2,$3,$4,$5,$6,$7,NOW()+INTERVAL '30 days')", [hash(sessionToken), user.id, link.rows[0].minecraft_uuid, link.rows[0].player_name, discordName, avatarHash, csrf]);
      return redirect(res, COMMUNITY_BASE_URL, [`community_session=${encodeURIComponent(sessionToken)}; Path=/; Max-Age=2592000; HttpOnly; Secure; SameSite=Lax`, "community_session=; Path=/community; Max-Age=0; HttpOnly; Secure; SameSite=Lax", clearState]);
    } catch (error) {
      return send(res, 502, communityLayout("로그인 오류", `<main><section class="panel"><h2>Discord 로그인에 실패했습니다.</h2><p class="muted">잠시 후 다시 시도해 주세요.</p><a class="back" href="${COMMUNITY_BASE_URL}">돌아가기</a></section></main>`), "text/html; charset=utf-8", { "Set-Cookie": clearState });
    }
  }
  if (path === "/community/logout" && req.method === "GET") {
    return redirect(res, COMMUNITY_BASE_URL, ["community_session=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Lax", "community_session=; Path=/community; Max-Age=0; HttpOnly; Secure; SameSite=Lax"]);
  }
  if (path === "/community/profile.js" && req.method === "GET") {
    return send(res, 200, profileClientJs(), "application/javascript; charset=utf-8");
  }
  if (path.startsWith("/community/profile/records/") && req.method === "GET") {
    const uuid = decodeURIComponent(path.slice("/community/profile/records/".length));
    if (!validUuid(uuid)) return json(res, 404, { error: "profile_not_found" });
    const profile = await communityProfile(uuid);
    if (!profile) return json(res, 404, { error: "profile_not_found" });
    return json(res, 200, { achievements: profile.achievements, titles: profile.titles, guild: profile.guild });
  }
  if (path === "/community/profile" && req.method === "GET") {
    const current = await communitySession(req);
    if (!current) return redirect(res, `${COMMUNITY_BASE_URL}/login`);
    return send(res, 200, communityProfilePageInteractive(await communityProfile(current.minecraft_uuid), current, url.searchParams.get("notice") ?? ""));
  }
  if (path.startsWith("/community/user/") && req.method === "GET") {
    const uuid = path.slice("/community/user/".length);
    if (!validUuid(uuid)) return send(res, 404, communityLayout("프로필을 찾을 수 없음", `<main><section class="panel"><h2>프로필 주소가 올바르지 않습니다.</h2><a class="back" href="${COMMUNITY_BASE_URL}">커뮤니티로 돌아가기</a></section></main>`));
    return send(res, 200, communityProfilePageInteractive(await communityProfile(uuid), await communitySession(req)));
  }
  if (path === "/community/profile/edit" && req.method === "GET") {
    const current = await communitySession(req);
    if (!current) return redirect(res, `${COMMUNITY_BASE_URL}/login`);
    const profile = await communityProfile(current.minecraft_uuid);
    return send(res, 200, communityProfileEditPage(current, profile?.introduction ?? ""));
  }
  if (path === "/community/profile/edit" && req.method === "POST") {
    const current = await communitySession(req);
    if (!current) return redirect(res, `${COMMUNITY_BASE_URL}/login`);
    const data = await form(req);
    const introduction = String(data.introduction ?? "").trim();
    if (!requireCsrf(data, current) || introduction.length > 100) {
      return send(res, 400, communityProfileEditPage(current, introduction, "소개글은 100자 이하로 입력해 주세요."));
    }
    await pool.query(`INSERT INTO community_profiles (minecraft_uuid,introduction,updated_at) VALUES ($1,$2,NOW())
      ON CONFLICT (minecraft_uuid) DO UPDATE SET introduction=EXCLUDED.introduction,updated_at=NOW()`, [current.minecraft_uuid, introduction]);
    return redirect(res, `${COMMUNITY_BASE_URL}/profile?notice=${encodeURIComponent("소개글을 저장했습니다.")}`);
  }
  if (path === "/community/write" && req.method === "GET") {
    const current = await communitySession(req);
    if (!current) return redirect(res, `${COMMUNITY_BASE_URL}/login`);
    return send(res, 200, communityWritePage(current));
  }
  if (path === "/community/write" && req.method === "POST") {
    const current = await communitySession(req);
    if (!current) return redirect(res, `${COMMUNITY_BASE_URL}/login`);
    const data = await form(req);
    const category = String(data.category ?? "").trim();
    const title = String(data.title ?? "").trim();
    const body = String(data.body ?? "").trim();
    if (data.csrf !== current.csrf_token || !COMMUNITY_CATEGORIES.includes(category) || title.length < 2 || title.length > 80 || body.length < 10 || body.length > 5000) {
      return send(res, 400, communityWritePage(current, "분류·제목·내용을 확인해 주세요. 내용은 10자 이상 5,000자 이하입니다."));
    }
    await pool.query("INSERT INTO community_posts (id,discord_id,minecraft_uuid,player_name,discord_name,category,title,body) VALUES ($1,$2,$3,$4,$5,$6,$7,$8)", [randomUUID(), current.discord_id, current.minecraft_uuid, current.player_name, current.discord_name, category, title, body]);
    return redirect(res, `${COMMUNITY_BASE_URL}?notice=${encodeURIComponent("기록을 게시했습니다.")}`);
  }
  if (path.startsWith("/community/post/") && path.endsWith("/comment") && req.method === "POST") {
    const id = path.slice("/community/post/".length, -"/comment".length);
    const current = await communitySession(req);
    if (!current) return redirect(res, `${COMMUNITY_BASE_URL}/login`);
    const post = await communityPost(id, current);
    if (!post) return send(res, 404, communityPostPage(current, null));
    const data = await form(req);
    const body = String(data.body ?? "").trim();
    const comments = await communityComments(id, current);
    if (!requireCsrf(data, current) || body.length < 1 || body.length > 1000) {
      return send(res, 400, communityPostPage(current, post, "댓글은 1자 이상 1,000자 이하로 입력해 주세요.", comments));
    }
    await pool.query("INSERT INTO community_comments (id,post_id,discord_id,minecraft_uuid,player_name,discord_name,body) VALUES ($1,$2::uuid,$3,$4,$5,$6,$7)", [randomUUID(), id, current.discord_id, current.minecraft_uuid, current.player_name, current.discord_name, body]);
    return redirect(res, `${COMMUNITY_BASE_URL}/post/${encodeURIComponent(id)}#comments`);
  }
  if (path.startsWith("/community/post/") && path.endsWith("/heart") && req.method === "POST") {
    const id = path.slice("/community/post/".length, -"/heart".length);
    const current = await communitySession(req);
    if (!current) return redirect(res, `${COMMUNITY_BASE_URL}/login`);
    const post = await communityPost(id, current);
    if (!post) return send(res, 404, communityPostPage(current, null));
    const data = await form(req);
    if (!requireCsrf(data, current)) return send(res, 403, communityPostPage(current, post, "요청이 만료되었습니다. 페이지를 새로고침한 뒤 다시 시도해 주세요.", await communityComments(id, current)));
    const removed = await pool.query("DELETE FROM community_post_likes WHERE post_id=$1::uuid AND minecraft_uuid=$2::uuid RETURNING post_id", [id, current.minecraft_uuid]);
    if (!removed.rowCount) {
      await pool.query("INSERT INTO community_post_likes (post_id,minecraft_uuid) VALUES ($1::uuid,$2::uuid) ON CONFLICT DO NOTHING", [id, current.minecraft_uuid]);
    }
    return redirect(res, `${COMMUNITY_BASE_URL}/post/${encodeURIComponent(id)}`);
  }
  if (path.startsWith("/community/comment/") && path.endsWith("/heart") && req.method === "POST") {
    const id = path.slice("/community/comment/".length, -"/heart".length);
    const current = await communitySession(req);
    if (!current) return redirect(res, `${COMMUNITY_BASE_URL}/login`);
    const comment = await communityComment(id, current);
    if (!comment) return send(res, 404, communityPostPage(current, null));
    const data = await form(req);
    if (!requireCsrf(data, current)) {
      const post = await communityPost(comment.post_id, current);
      return send(res, 403, communityPostPage(current, post, "요청이 만료되었습니다. 페이지를 새로고침한 뒤 다시 시도해 주세요.", await communityComments(comment.post_id, current)));
    }
    const removed = await pool.query("DELETE FROM community_comment_likes WHERE comment_id=$1::uuid AND minecraft_uuid=$2::uuid RETURNING comment_id", [id, current.minecraft_uuid]);
    if (!removed.rowCount) {
      await pool.query("INSERT INTO community_comment_likes (comment_id,minecraft_uuid) VALUES ($1::uuid,$2::uuid) ON CONFLICT DO NOTHING", [id, current.minecraft_uuid]);
    }
    return redirect(res, `${COMMUNITY_BASE_URL}/post/${encodeURIComponent(comment.post_id)}#comments`);
  }
  if (path.startsWith("/community/comment/") && path.endsWith("/delete") && req.method === "POST") {
    const id = path.slice("/community/comment/".length, -"/delete".length);
    const current = await communitySession(req);
    if (!current) return redirect(res, `${COMMUNITY_BASE_URL}/login`);
    const comment = await communityComment(id, current);
    if (!comment) return send(res, 404, communityPostPage(current, null));
    const data = await form(req);
    if (!requireCsrf(data, current) || comment.minecraft_uuid !== current.minecraft_uuid) {
      const post = await communityPost(comment.post_id, current);
      return send(res, 403, communityPostPage(current, post, "댓글을 삭제할 수 없습니다.", await communityComments(comment.post_id, current)));
    }
    await pool.query("UPDATE community_comments SET hidden=TRUE,updated_at=NOW() WHERE id=$1::uuid AND minecraft_uuid=$2::uuid", [id, current.minecraft_uuid]);
    return redirect(res, `${COMMUNITY_BASE_URL}/post/${encodeURIComponent(comment.post_id)}#comments`);
  }
  if (path.startsWith("/community/post/") && req.method === "GET") {
    const id = path.slice("/community/post/".length);
    const current = await communitySession(req);
    const existing = await communityPost(id, current);
    if (!existing) return send(res, 200, communityPostPage(current, null));
    const viewer = communityViewer(req, current);
    await pool.query("INSERT INTO community_post_views (post_id,viewer_key) VALUES ($1::uuid,$2) ON CONFLICT DO NOTHING", [id, viewer.key]);
    const post = await communityPost(id, current);
    return send(res, 200, communityPostPage(current, post, "", await communityComments(id, current)), "text/html; charset=utf-8", viewer.cookie ? { "Set-Cookie": viewer.cookie } : {});
  }
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
  if (path === "/internal/profile/introduction" && req.method === "POST") {
    if (!internal(req)) return json(res, 401, { error: "unauthorized" });
    const data = await bodyJson(req);
    const uuid = String(data.uuid ?? "").trim();
    const playerName = String(data.playerName ?? "").trim();
    const introduction = String(data.introduction ?? "").trim();
    if (!validUuid(uuid) || !minecraftName(playerName) || introduction.length > 100) return json(res, 400, { error: "invalid_profile" });
    await pool.query(`INSERT INTO community_profiles (minecraft_uuid,introduction,updated_at) VALUES ($1,$2,NOW())
      ON CONFLICT (minecraft_uuid) DO UPDATE SET introduction=EXCLUDED.introduction,updated_at=NOW()`, [uuid, introduction]);
    return json(res, 200, { synced: true, minecraftUuid: uuid, introduction });
  }
  if (/^\/internal\/profile\/introduction\/[0-9a-f-]+$/i.test(path) && req.method === "GET") {
    if (!internal(req)) return json(res, 401, { error: "unauthorized" });
    const uuid = path.slice("/internal/profile/introduction/".length);
    if (!validUuid(uuid)) return json(res, 400, { error: "invalid_uuid" });
    const found = await pool.query("SELECT introduction,updated_at FROM community_profiles WHERE minecraft_uuid=$1", [uuid]);
    if (!found.rowCount) return json(res, 200, { configured: false, minecraftUuid: uuid });
    return json(res, 200, { configured: true, minecraftUuid: uuid, introduction: found.rows[0].introduction, updatedAt: found.rows[0].updated_at });
  }
  if (path === "/internal/discord/link" && req.method === "POST") {
    if (!internal(req)) return json(res, 401, { error: "unauthorized" });
    const data = await bodyJson(req);
    const code = String(data.code ?? "").toUpperCase().replace(/[^A-Z0-9-]/g, "");
    const discordId = String(data.discordId ?? "").trim();
    const discordName = String(data.discordName ?? "").trim().slice(0, 100);
    if (!/^BK-[A-Z0-9]{8}$/.test(code) || !/^\d{16,22}$/.test(discordId)) return json(res, 400, { error: "invalid_request" });
    const client = await pool.connect();
    try {
      await client.query("BEGIN");
      const found = await client.query(
        "SELECT minecraft_uuid,player_name,used_at FROM link_codes WHERE code_hash=$1 AND expires_at>NOW() FOR UPDATE",
        [hash(code)]
      );
      if (!found.rowCount) { await client.query("ROLLBACK"); return json(res, 404, { error: "code_invalid" }); }
      const link = found.rows[0];
      const byMinecraft = await client.query("SELECT discord_id FROM discord_links WHERE minecraft_uuid=$1 FOR UPDATE", [link.minecraft_uuid]);
      const byDiscord = await client.query("SELECT minecraft_uuid FROM discord_links WHERE discord_id=$1 FOR UPDATE", [discordId]);
      // 역할 지급 실패 후 같은 사용자가 재시도할 수 있도록, 이미 연결된 동일 쌍만 멱등 처리한다.
      // 다른 계정이 사용한 코드는 절대 재사용하지 않는다.
      if (link.used_at) {
        const sameMinecraft = byMinecraft.rowCount && byMinecraft.rows[0].discord_id === discordId;
        const sameDiscord = byDiscord.rowCount && byDiscord.rows[0].minecraft_uuid === link.minecraft_uuid;
        if (sameMinecraft && sameDiscord) {
          await client.query("COMMIT");
          return json(res, 200, { linked: true, minecraftUuid: link.minecraft_uuid, playerName: link.player_name, discordId, retry: true });
        }
        await client.query("ROLLBACK");
        return json(res, 404, { error: "code_invalid" });
      }
      if (byMinecraft.rowCount && byMinecraft.rows[0].discord_id !== discordId) {
        await client.query("ROLLBACK"); return json(res, 409, { error: "minecraft_already_linked" });
      }
      if (byDiscord.rowCount && byDiscord.rows[0].minecraft_uuid !== link.minecraft_uuid) {
        await client.query("ROLLBACK"); return json(res, 409, { error: "discord_already_linked" });
      }
      await client.query("UPDATE link_codes SET used_at=NOW() WHERE code_hash=$1", [hash(code)]);
      await client.query(`INSERT INTO discord_links (minecraft_uuid,player_name,discord_id,discord_name)
        VALUES ($1,$2,$3,$4)
        ON CONFLICT (minecraft_uuid) DO UPDATE SET player_name=EXCLUDED.player_name, discord_id=EXCLUDED.discord_id,
          discord_name=EXCLUDED.discord_name, updated_at=NOW()`, [link.minecraft_uuid, link.player_name, discordId, discordName || null]);
      // 연동 직후 소속 길드 역할을 바로 받게 한다. 미연동 상태로 이미 가입해 있던 사람이 여기서 구제된다.
      const joined = await client.query("SELECT guild_id FROM guild_member_mirror WHERE minecraft_uuid=$1", [link.minecraft_uuid]);
      for (const row of joined.rows) await enqueueGuildJob(client, "guild_members", row.guild_id);
      await client.query("COMMIT");
      return json(res, 200, { linked: true, minecraftUuid: link.minecraft_uuid, playerName: link.player_name, discordId });
    } catch (error) {
      await client.query("ROLLBACK");
      throw error;
    } finally { client.release(); }
  }
  if (path === "/internal/discord/verified" && req.method === "POST") {
    if (!internal(req)) return json(res, 401, { error: "unauthorized" });
    const data = await bodyJson(req);
    const minecraftUuid = String(data.minecraftUuid ?? "").trim();
    const discordId = String(data.discordId ?? "").trim();
    if (!validUuid(minecraftUuid) || !/^\d{16,22}$/.test(discordId)) return json(res, 400, { error: "invalid_request" });
    const updated = await pool.query(
      "UPDATE discord_links SET verified_at=COALESCE(verified_at,NOW()),updated_at=NOW() WHERE minecraft_uuid=$1 AND discord_id=$2 RETURNING minecraft_uuid",
      [minecraftUuid, discordId]
    );
    if (!updated.rowCount) return json(res, 404, { error: "link_not_found" });
    return json(res, 200, { verified: true, minecraftUuid, discordId });
  }
  // === 길드 디스코드 연동 ===
  // 게임이 길드 명부 전체를 밀어넣으면 직전 스냅샷과 비교해 작업만 큐에 남긴다.
  if (path === "/internal/guild/sync" && req.method === "POST") {
    if (!internal(req)) return json(res, 401, { error: "unauthorized" });
    const data = await bodyJson(req);
    if (!Array.isArray(data.guilds)) return json(res, 400, { error: "invalid_request" });
    const snapshot = new Map();
    for (const raw of data.guilds) {
      const guildId = String(raw?.id ?? "").trim();
      if (!guildId || guildId.length > 64) return json(res, 400, { error: "invalid_guild_id" });
      const members = [];
      for (const m of Array.isArray(raw.members) ? raw.members : []) {
        const uuid = String(m?.uuid ?? "").trim();
        const rank = String(m?.rank ?? "MEMBER").trim().toUpperCase();
        if (!validUuid(uuid) || !GUILD_RANKS.has(rank)) continue;
        members.push({ uuid, rank });
      }
      const ownerUuid = String(raw?.ownerUuid ?? "").trim();
      snapshot.set(guildId, { ownerUuid: validUuid(ownerUuid) ? ownerUuid : null, members });
    }
    const client = await pool.connect();
    try {
      await client.query("BEGIN");
      // 대량 삭제 방어. 게임 쪽에서 guilds.json 을 못 읽었거나 반쯤 로드된 상태로 스냅샷이 오면
      // 그대로 반영할 경우 멀쩡한 길드 채널을 통째로 지운다(2026-08 staging JSON 덮어쓰기 사고와 같은 계열).
      // 정상적인 대량 해체는 force:true 로 명시해야 통과한다.
      const provisionedBefore = await client.query("SELECT guild_id FROM guild_discord");
      const dropping = provisionedBefore.rows.filter((row) => !snapshot.has(row.guild_id)).length;
      // 1~2개가 사라지는 건 평범한 해체다. "한 번에 여럿이, 그것도 절반 넘게" 사라질 때만 막는다.
      // (마지막 남은 길드가 해체돼 스냅샷이 비는 것도 정상이라 빈 스냅샷 자체를 막으면 안 된다.)
      const suspicious = dropping > 2 && dropping * 2 > provisionedBefore.rowCount;
      if (suspicious && data.force !== true) {
        await client.query("ROLLBACK");
        console.warn(`[Guild] refused snapshot: ${dropping}/${provisionedBefore.rowCount} guilds would be deleted`);
        return json(res, 409, { error: "suspicious_snapshot", dropping, provisioned: provisionedBefore.rowCount });
      }
      const before = await client.query("SELECT guild_id,minecraft_uuid,guild_rank FROM guild_member_mirror");
      const beforeSig = new Map();
      for (const row of before.rows) {
        if (!beforeSig.has(row.guild_id)) beforeSig.set(row.guild_id, new Set());
        beforeSig.get(row.guild_id).add(`${row.minecraft_uuid}:${row.guild_rank}`);
      }
      const ids = [...snapshot.keys()];
      await client.query("DELETE FROM guild_mirror WHERE NOT (guild_id = ANY($1::text[]))", [ids]);
      for (const [guildId, guild] of snapshot) {
        await client.query(
          `INSERT INTO guild_mirror (guild_id,owner_uuid,updated_at) VALUES ($1,$2,NOW())
           ON CONFLICT (guild_id) DO UPDATE SET owner_uuid=EXCLUDED.owner_uuid, updated_at=NOW()`,
          [guildId, guild.ownerUuid]
        );
        await client.query("DELETE FROM guild_member_mirror WHERE guild_id=$1", [guildId]);
        for (const member of guild.members) {
          await client.query(
            "INSERT INTO guild_member_mirror (guild_id,minecraft_uuid,guild_rank) VALUES ($1,$2,$3)",
            [guildId, member.uuid, member.rank]
          );
        }
      }
      const provisionedIds = new Set(provisionedBefore.rows.map((row) => row.guild_id));
      let queued = 0;
      for (const [guildId, guild] of snapshot) {
        if (!provisionedIds.has(guildId)) { await enqueueGuildJob(client, "guild_create", guildId); queued += 1; }
        const after = new Set(guild.members.map((m) => `${m.uuid}:${m.rank}`));
        const previous = beforeSig.get(guildId) ?? new Set();
        const changed = after.size !== previous.size || [...after].some((sig) => !previous.has(sig));
        if (changed) { await enqueueGuildJob(client, "guild_members", guildId); queued += 1; }
      }
      for (const guildId of provisionedIds) {
        if (!snapshot.has(guildId)) { await enqueueGuildJob(client, "guild_delete", guildId); queued += 1; }
      }
      await client.query("COMMIT");
      return json(res, 200, { synced: true, guilds: snapshot.size, queued });
    } catch (error) {
      await client.query("ROLLBACK");
      throw error;
    } finally { client.release(); }
  }
  // 봇이 처리할 작업을 선점한다. 실패한 작업은 run_after 로 밀려 있다가 다시 잡힌다.
  if (path === "/internal/guild/jobs" && req.method === "GET") {
    if (!internal(req)) return json(res, 401, { error: "unauthorized" });
    const claimed = await pool.query(
      `UPDATE guild_discord_jobs SET claimed_at=NOW(), attempts=attempts+1
        WHERE id IN (SELECT id FROM guild_discord_jobs WHERE done_at IS NULL AND run_after <= NOW()
                      ORDER BY id LIMIT 3 FOR UPDATE SKIP LOCKED)
        RETURNING id,kind,guild_id,payload,attempts`
    );
    const jobs = [];
    // UPDATE ... RETURNING 의 행 순서는 보장되지 않는다. id 순으로 세우지 않으면 같은 배치 안에서
    // guild_delete 가 guild_create/guild_members 보다 먼저 처리돼 지운 채널이 되살아난다.
    claimed.rows.sort((a, b) => Number(a.id) - Number(b.id));
    for (const job of claimed.rows) {
      // 이미 해체된 길드의 잔여 작업. 그대로 두면 provisionGuild 가 채널을 다시 만든다.
      if (job.kind !== "guild_delete") {
        const alive = await pool.query("SELECT 1 FROM guild_mirror WHERE guild_id=$1", [job.guild_id]);
        if (!alive.rowCount) {
          await pool.query("UPDATE guild_discord_jobs SET done_at=NOW(), last_error='guild_gone' WHERE id=$1", [job.id]);
          continue;
        }
      }
      jobs.push({
        id: Number(job.id), kind: job.kind, guildId: job.guild_id,
        attempts: job.attempts, payload: job.payload,
        discord: await guildDiscordRow(job.guild_id),
        members: job.kind === "guild_delete" ? [] : await guildMemberTargets(job.guild_id),
      });
    }
    return json(res, 200, { jobs });
  }
  if (path === "/internal/guild/jobs/result" && req.method === "POST") {
    if (!internal(req)) return json(res, 401, { error: "unauthorized" });
    const data = await bodyJson(req);
    // id 0 은 큐에서 나온 작업이 아니라 봇의 정기 점검 결과다. 매핑만 갱신하고 큐는 건드리지 않는다.
    const id = Number(data.id);
    if (!Number.isInteger(id) || id < 0) return json(res, 400, { error: "invalid_request" });
    if (data.ok) {
      const discord = data.discord ?? null;
      if (discord && typeof discord === "object") {
        await pool.query(
          `INSERT INTO guild_discord (guild_id,role_id,category_id,text_channel_id,voice_channel_id,updated_at)
           VALUES ($1,$2,$3,$4,$5,NOW())
           ON CONFLICT (guild_id) DO UPDATE SET role_id=EXCLUDED.role_id, category_id=EXCLUDED.category_id,
             text_channel_id=EXCLUDED.text_channel_id, voice_channel_id=EXCLUDED.voice_channel_id, updated_at=NOW()`,
          [String(data.guildId ?? ""), discord.roleId ?? null, discord.categoryId ?? null,
           discord.textChannelId ?? null, discord.voiceChannelId ?? null]
        );
      }
      if (data.removed) await pool.query("DELETE FROM guild_discord WHERE guild_id=$1", [String(data.guildId ?? "")]);
      if (id > 0) await pool.query("UPDATE guild_discord_jobs SET done_at=NOW(), last_error=NULL WHERE id=$1", [id]);
      return json(res, 200, { acknowledged: true });
    }
    if (id === 0) return json(res, 200, { acknowledged: true });
    // 실패는 지수 백오프로 되돌린다. 10회를 넘기면 포기하고 기록만 남긴다 — 다음 전체 동기화가 다시 큐에 넣는다.
    const failure = String(data.error ?? "unknown").slice(0, 500);
    await pool.query(
      `UPDATE guild_discord_jobs
          SET last_error=$2,
              run_after=NOW() + (LEAST(attempts,6) * INTERVAL '30 seconds'),
              claimed_at=NULL,
              done_at=CASE WHEN attempts >= 10 THEN NOW() ELSE NULL END
        WHERE id=$1 AND done_at IS NULL`,
      [id, failure]
    );
    return json(res, 200, { acknowledged: true, retried: true });
  }
  // 봇 재접속·주기 점검용 전체 기대 상태.
  if (path === "/internal/guild/state" && req.method === "GET") {
    if (!internal(req)) return json(res, 401, { error: "unauthorized" });
    const rows = await pool.query("SELECT guild_id FROM guild_mirror ORDER BY guild_id");
    const guilds = [];
    for (const row of rows.rows) {
      guilds.push({
        guildId: row.guild_id,
        discord: await guildDiscordRow(row.guild_id),
        members: await guildMemberTargets(row.guild_id),
      });
    }
    return json(res, 200, { guilds });
  }
  if (path === "/internal/discord/reward/status" && req.method === "POST") {
    if (!internal(req)) return json(res, 401, { error: "unauthorized" });
    const data = await bodyJson(req);
    const minecraftUuid = String(data.minecraftUuid ?? "").trim();
    if (!validUuid(minecraftUuid)) return json(res, 400, { error: "invalid_request" });
    const found = await pool.query(
      "SELECT verified_at,reward_claimed_at FROM discord_links WHERE minecraft_uuid=$1",
      [minecraftUuid]
    );
    if (!found.rowCount || !found.rows[0].verified_at) return json(res, 200, { eligible: false });
    const claimed = Boolean(found.rows[0].reward_claimed_at);
    return json(res, 200, { eligible: true, claimed, rewardId: "discord-join-v1", amount: 1000 });
  }
  if (path === "/internal/discord/reward/confirm" && req.method === "POST") {
    if (!internal(req)) return json(res, 401, { error: "unauthorized" });
    const data = await bodyJson(req);
    const minecraftUuid = String(data.minecraftUuid ?? "").trim();
    const rewardId = String(data.rewardId ?? "").trim();
    if (!validUuid(minecraftUuid) || rewardId !== "discord-join-v1") return json(res, 400, { error: "invalid_request" });
    const claimed = await pool.query(
      "UPDATE discord_links SET reward_claimed_at=NOW(),updated_at=NOW() WHERE minecraft_uuid=$1 AND verified_at IS NOT NULL AND reward_claimed_at IS NULL RETURNING minecraft_uuid",
      [minecraftUuid]
    );
    if (claimed.rowCount) return json(res, 200, { claimed: true, rewardId });
    const existing = await pool.query("SELECT reward_claimed_at FROM discord_links WHERE minecraft_uuid=$1 AND verified_at IS NOT NULL", [minecraftUuid]);
    if (existing.rowCount && existing.rows[0].reward_claimed_at) return json(res, 200, { claimed: true, rewardId, alreadyClaimed: true });
    return json(res, 409, { error: "reward_not_eligible" });
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
