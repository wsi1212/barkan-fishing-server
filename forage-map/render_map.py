"""forage_map_data.json -> forage_map.html (Artifact 배포용 완성 HTML, 자유선 영역 그리기 UI 포함)."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(HERE, "forage_map_data.json")))
payload = json.dumps(data, ensure_ascii=False)

html = """<meta charset="utf-8">
<title>바르칸 열도 — 채집 노드 지도</title>
<style>
:root{
  --bg:#12161d; --panel:#1a2029; --panel2:#212836; --border:#2b3342;
  --text:#e7ebf1; --muted:#8b96aa; --muted2:#647087;
  --rare-ring:#f2d48a; --accent:#5b8fd1; --draw:#e5544d;
}
:root[data-theme="light"]{
  --bg:#eef1f0; --panel:#ffffff; --panel2:#f4f6f5;
  --border:#d7ddd9; --text:#1d2622; --muted:#5b665f; --muted2:#7c887f;
  --rare-ring:#a8721f; --accent:#3f6fa8; --draw:#c23a33;
}
@media (prefers-color-scheme: light){
  :root:not([data-theme="dark"]){
    --bg:#eef1f0; --panel:#ffffff; --panel2:#f4f6f5;
    --border:#d7ddd9; --text:#1d2622; --muted:#5b665f; --muted2:#7c887f;
    --rare-ring:#a8721f; --accent:#3f6fa8; --draw:#c23a33;
  }
}
*{box-sizing:border-box;}
html,body{margin:0;padding:0;background:var(--bg);color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Malgun Gothic",Segoe UI,sans-serif;
  height:100%;overflow:hidden;}
.wrap{display:flex;flex-direction:column;height:100vh;}
.topbar{display:flex;align-items:center;gap:14px;padding:12px 20px;
  border-bottom:1px solid var(--border);flex-shrink:0;background:var(--panel);}
.topbar h1{font-size:16px;font-weight:700;margin:0;letter-spacing:.2px;}
.topbar .sub{font-size:12px;color:var(--muted);}
.topbar .count{margin-left:auto;font-size:12px;color:var(--muted2);font-variant-numeric:tabular-nums;}
.modeswitch{display:flex;gap:2px;background:var(--panel2);border:1px solid var(--border);
  border-radius:7px;padding:2px;margin-left:6px;}
.modeswitch button{border:none;background:transparent;color:var(--muted);font-size:12px;
  padding:5px 10px;border-radius:5px;cursor:pointer;font-weight:600;}
.modeswitch button.active{background:var(--accent);color:#fff;}
.body{display:flex;flex:1;min-height:0;}
.stage{flex:1;position:relative;overflow:hidden;background:var(--bg);}
.stage canvas{position:absolute;top:0;left:0;cursor:grab;}
.stage.dragging canvas{cursor:grabbing;}
.stage.drawmode canvas{cursor:crosshair;}
.hint{position:absolute;left:16px;bottom:14px;font-size:11.5px;color:var(--muted2);
  background:rgba(0,0,0,.28);padding:5px 10px;border-radius:5px;pointer-events:none;backdrop-filter:blur(2px);}
.zoomctl{position:absolute;right:16px;bottom:14px;display:flex;flex-direction:column;
  gap:1px;background:var(--panel);border:1px solid var(--border);border-radius:7px;overflow:hidden;}
.zoomctl button{width:30px;height:28px;border:none;background:transparent;color:var(--text);font-size:15px;cursor:pointer;}
.zoomctl button:hover{background:var(--panel2);}
.tooltip{position:absolute;pointer-events:none;background:var(--panel);border:1px solid var(--border);
  border-radius:7px;padding:8px 10px;font-size:12.5px;line-height:1.5;box-shadow:0 6px 18px rgba(0,0,0,.28);
  display:none;white-space:nowrap;z-index:5;}
.tooltip .name{font-weight:700;}
.tooltip .meta{color:var(--muted);font-size:11.5px;margin-top:2px;}
.side{width:330px;flex-shrink:0;background:var(--panel);border-left:1px solid var(--border);
  padding:14px;overflow-y:auto;display:flex;flex-direction:column;gap:12px;}
.side h2{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);
  margin:0;font-weight:600;display:flex;align-items:center;}
.statline{font-size:12.5px;color:var(--muted);display:flex;justify-content:space-between;}
.statline b{color:var(--text);font-variant-numeric:tabular-nums;}
.toggleall{font-size:11px;color:var(--accent);cursor:pointer;background:none;border:none;
  padding:0;text-decoration:underline;text-underline-offset:2px;margin-left:auto;font-weight:500;}
.region-group{margin-bottom:8px;}
.region-head{display:flex;align-items:center;gap:7px;font-size:12.5px;font-weight:700;
  padding:5px 0 4px;cursor:pointer;color:var(--text);}
.region-head input{accent-color:var(--accent);width:13px;height:13px;flex-shrink:0;}
.region-head .rc{margin-left:auto;color:var(--muted2);font-size:11px;font-weight:400;font-variant-numeric:tabular-nums;}
.species-row{display:flex;align-items:center;gap:7px;font-size:12px;padding:3px 0 3px 20px;
  cursor:pointer;color:var(--muted);}
.species-row:hover{color:var(--text);}
.species-row input{accent-color:var(--accent);width:12px;height:12px;flex-shrink:0;}
.swatch{width:9px;height:9px;border-radius:50%;flex-shrink:0;border:1px solid rgba(0,0,0,.3);}
.species-row .sname{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.species-row .rare-mark{color:var(--rare-ring);font-size:9px;}
.species-row .cnt{color:var(--muted2);font-size:10.5px;font-variant-numeric:tabular-nums;}
.rulebadge{font-size:10px;}
.drawbtn{background:var(--draw);color:#fff;border:none;border-radius:6px;padding:6px 12px;
  font-size:12.5px;font-weight:600;cursor:pointer;}
.drawbtn:hover{filter:brightness(1.08);}
.circle-card{border:1px solid var(--border);border-radius:8px;padding:10px;background:var(--panel2);
  display:flex;flex-direction:column;gap:8px;}
.circle-card .chead{display:flex;align-items:center;gap:6px;font-size:12px;font-weight:700;}
.circle-card .chead .coord{color:var(--muted2);font-weight:400;font-variant-numeric:tabular-nums;font-size:11px;}
.circle-card .rm{margin-left:auto;background:none;border:none;color:var(--muted2);cursor:pointer;font-size:14px;}
.circle-card .rm:hover{color:var(--draw);}
.picker{max-height:440px;overflow-y:auto;border:1px solid var(--border);border-radius:8px;padding:10px 12px;
  background:var(--bg);}
.pick-row{display:flex;align-items:center;gap:9px;font-size:13.5px;padding:6px 2px;color:var(--muted);cursor:pointer;}
.pick-row:hover{color:var(--text);}
.pick-row input[type=checkbox]{accent-color:var(--accent);width:15px;height:15px;flex-shrink:0;}
.pick-row .pname{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.pick-row .w-input{width:56px;font-size:13.5px;background:var(--panel2);border:1px solid var(--border);
  color:var(--text);border-radius:5px;padding:4px 6px;text-align:center;}
.pick-region{font-size:11.5px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;
  margin:12px 0 3px;padding-left:2px;}
.pick-region:first-child{margin-top:0;}
.countrow{display:flex;align-items:center;gap:8px;font-size:12.5px;color:var(--muted);}
.countrow input{width:56px;font-size:11.5px;background:var(--bg);border:1px solid var(--border);
  color:var(--text);border-radius:4px;padding:3px 5px;}
.sendbar{border-top:1px solid var(--border);padding-top:10px;display:flex;flex-direction:column;gap:8px;}
.sendbtn{background:var(--accent);color:#fff;border:none;border-radius:7px;padding:9px;
  font-size:13px;font-weight:700;cursor:pointer;}
.sendbtn:disabled{opacity:.4;cursor:not-allowed;}
.empty-note{font-size:11.5px;color:var(--muted2);line-height:1.5;}
.preview-item{display:flex;align-items:center;gap:7px;font-size:12px;padding:6px 7px;border-radius:6px;
  cursor:pointer;color:var(--text);border:1px solid transparent;}
.preview-item:hover{background:var(--panel2);border-color:var(--border);}
.preview-item .pi-coord{margin-left:auto;color:var(--muted2);font-size:10.5px;font-variant-numeric:tabular-nums;}
.preview-item .pi-flag{font-size:10px;}
.preview-item .rm{background:none;border:none;color:var(--muted2);cursor:pointer;font-size:13px;padding:0 2px;}
.preview-item .rm:hover{color:var(--draw);}
.modal-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.55);display:flex;align-items:center;
  justify-content:center;z-index:20;}
.modal{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:16px;
  width:420px;display:flex;flex-direction:column;gap:10px;box-shadow:0 20px 60px rgba(0,0,0,.4);}
.modal h3{margin:0;font-size:14px;display:flex;align-items:center;gap:8px;}
.modal .miso-wrap{position:relative;border-radius:8px;overflow:hidden;background:#0c1016;
  border:1px solid var(--border);}
.modal canvas#iso{display:block;cursor:grab;}
.modal .iso-hint{font-size:11px;color:var(--muted2);line-height:1.4;}
.modal .modal-actions{display:flex;gap:8px;justify-content:flex-end;margin-top:2px;}
.modal .modal-actions button{border:none;border-radius:6px;padding:7px 14px;font-size:12.5px;
  font-weight:600;cursor:pointer;}
.modal .btn-cancel{background:var(--panel2);color:var(--text);border:1px solid var(--border) !important;}
.modal .btn-ok{background:var(--accent);color:#fff;}
.modal .coordline{font-size:11.5px;color:var(--muted);font-variant-numeric:tabular-nums;}
</style>
<div class="wrap">
  <div class="topbar">
    <h1>바르칸 열도 — 채집 노드 지도</h1>
    <span class="sub">설치된 노드 + 신규 배치 영역 지정</span>
    <div class="modeswitch">
      <button id="mode-view" class="active">보기</button>
      <button id="mode-draw">영역 그리기</button>
      <button id="mode-preview">미리보기</button>
    </div>
    <span class="count" id="count"></span>
  </div>
  <div class="body">
    <div class="stage" id="stage">
      <canvas id="map"></canvas>
      <div class="tooltip" id="tooltip"></div>
      <div class="hint" id="hint">드래그로 이동 · 휠/버튼으로 확대 · ✦ = 희귀</div>
      <div class="zoomctl">
        <button id="zin">+</button>
        <button id="zout">−</button>
      </div>
    </div>
    <div class="side" id="side"></div>
  </div>
  <div id="modal-root"></div>
</div>
<script>
const DATA = __DATA__;
const meta = DATA.meta, nodes = DATA.nodes, catalog = DATA.species_catalog, regionOrder = DATA.region_order;
const habitatRules = DATA.habitat_rules || {};
const terrainLookup = DATA.terrain_lookup;
const RULE_ICON = { adjacent_log: '🪵', near_flower: '🌼', adjacent_wheat_no_overlap: '🌾' };

function ruleIcon(typeId){
  const r = habitatRules[typeId];
  return r ? (RULE_ICON[r.rule] || '⚙') : '';
}
function ruleNote(typeId){
  const r = habitatRules[typeId];
  return r ? r.note : '';
}

// ---- 클라이언트 사이드 후보 생성 (서버 왕복 없이 즉시 계산) ----
// 정밀도는 지도에 내장된 대략 지형 그리드 수준 — 실제 설치 직전엔 항상 서버에서
// 정확한 블록으로 재확인함(이 좌표는 '미리보기'용 근사치일 뿐).
function lookupCell(x, z){
  const tl = terrainLookup;
  const lx = Math.floor((x - tl.x_origin) / tl.cell_size);
  const lz = Math.floor((z - tl.z_origin) / tl.cell_size);
  if(lx < 0 || lz < 0 || lx >= tl.grid_width || lz >= tl.grid_depth) return null;
  const li = tl.material[lz][lx];
  if(li === -1) return null;
  return { material: tl.legend[li], height: tl.height[lz][lx] };
}
function isBadGround(cell){
  if(!cell) return true;
  const m = cell.material;
  return m.includes('water') || m.includes('lava') || m === 'minecraft:air';
}
function lookupCanopyCell(x, z){
  const tl = terrainLookup;
  if(!tl.canopy) return false;
  const lx = Math.floor((x - tl.x_origin) / tl.cell_size);
  const lz = Math.floor((z - tl.z_origin) / tl.cell_size);
  if(lx < 0 || lz < 0 || lx >= tl.grid_width || lz >= tl.grid_depth) return false;
  return tl.canopy[lz][lx] === 1;
}
// 성긴 그리드(16블록/칸) 경계에 걸쳐 작은 나무를 놓치지 않도록 3x3 이웃칸도 같이 확인.
// under_leaves(열매류)는 나뭇잎 자체가 목적이므로 이 캐노피 체크가 맞는 신호임.
function nearCanopy(x, z){
  const tl = terrainLookup;
  const step = tl.cell_size || 16;
  for(let dz=-1; dz<=1; dz++){
    for(let dx=-1; dx<=1; dx++){
      if(lookupCanopyCell(x + dx*step, z + dz*step)) return true;
    }
  }
  return false;
}

// ---- 원목(log) 정밀 인접 판정 (2026-07-28 신설) ----
// adjacent_log(버섯)는 예전엔 위 nearCanopy(나뭇잎 유무)를 그대로 재사용했는데, 나뭇잎
// 캐노피는 실제 몸통(log)보다 훨씬 넓게 퍼져있어(가지 끝 잎이 몸통에서 여러 블록 떨어짐
// + 성긴 16블록 칸 3x3=48블록 반경까지 "근처" 판정) "반경1 원목 인접"의 대용 지표로
// 부정확했음 — 실사용 33개 중 31개가 이 체크는 통과했지만 실제 최인접 원목까지
// 8~21블록이나 떨어져 있었던 사고 이후, build_map_data.py가 만드는 log_cells(원목
// 블록이 있는 base cell_size=4블록 그리드 좌표, 다운샘플 없는 sparse 리스트)를 직접 써서
// "원목 그 자체"에 정밀하게 근접 판정한다.
const logCellSet = (function(){
  const tl = terrainLookup;
  const set = new Set();
  if(tl && tl.log_cells){
    for(const [lx, lz] of tl.log_cells) set.add(lx + ',' + lz);
  }
  return set;
})();
function nearLog(x, z){
  const tl = terrainLookup;
  if(!tl.log_cells || !tl.log_cell_size) return nearCanopy(x, z); // 구버전 데이터 폴백
  const size = tl.log_cell_size;
  const lx = Math.floor((x - tl.x_origin) / size);
  const lz = Math.floor((z - tl.z_origin) / size);
  // ±2칸(=±8블록) 이웃까지 확인 — 규칙 자체는 반경1이지만 후보점 지터/그리드 양자화
  // 오차를 흡수할 최소한의 여유만 둔다(예전 48블록 반경과는 차원이 다르게 타이트함).
  for(let dz=-2; dz<=2; dz++){
    for(let dx=-2; dx<=2; dx++){
      if(logCellSet.has((lx+dx) + ',' + (lz+dz))) return true;
    }
  }
  return false;
}
function pointInPoly(x, z, poly){
  let inside = false;
  for(let i=0, j=poly.length-1; i<poly.length; j=i++){
    const [xi, zi] = poly[i], [xj, zj] = poly[j];
    if(((zi > z) !== (zj > z)) && (x < (xj-xi)*(z-zi)/(zj-zi+1e-12)+xi)) inside = !inside;
  }
  return inside;
}
function shoelace(poly){
  let a = 0;
  for(let i=0;i<poly.length;i++){ const [x1,z1]=poly[i], [x2,z2]=poly[(i+1)%poly.length]; a += x1*z2 - x2*z1; }
  return Math.abs(a) / 2;
}
function generateCandidates(poly, oversample, jitterFrac){
  jitterFrac = jitterFrac === undefined ? 0.45 : jitterFrac;
  const xs = poly.map(p=>p[0]), zs = poly.map(p=>p[1]);
  const minx = Math.min(...xs), maxx = Math.max(...xs), minz = Math.min(...zs), maxz = Math.max(...zs);
  const area = shoelace(poly);
  const spacing = Math.sqrt(area / Math.max(1, oversample));
  const cands = [];
  let row = 0;
  for(let z=minz; z<=maxz; z+=spacing){
    const x0 = minx + (row % 2 ? spacing/2 : 0);
    for(let x=x0; x<=maxx; x+=spacing){
      const jx = x + (Math.random()*2-1) * spacing * jitterFrac;
      const jz = z + (Math.random()*2-1) * spacing * jitterFrac;
      cands.push([jx, jz]);
    }
    row++;
  }
  return cands.filter(([x,z])=>pointInPoly(x,z,poly)).map(([x,z])=>[Math.round(x), Math.round(z)]);
}
let nextPreviewId = 1;
// under_leaves(열매)는 나뭇잎 근접(nearCanopy), adjacent_log(버섯)는 원목 근접(nearLog) —
// 서로 다른 신호라 하나의 CANOPY_RULES로 뭉뚱그리지 않고 규칙별로 분리한다.
const LEAF_RULES = new Set(['under_leaves']);
const LOG_RULES = new Set(['adjacent_log']);
function generatePreviewFromAreas(){
  const added = [];
  const shortfalls = [];
  areas.forEach(ar=>{
    ar.species.forEach(sp=>{
      const need = sp.count;
      const rule = (habitatRules[sp.typeId] || {}).rule;
      const wantsLeaf = LEAF_RULES.has(rule);
      const wantsLog = LOG_RULES.has(rule);
      const wantsTreeProximity = wantsLeaf || wantsLog;
      const hanging = rule === 'under_leaves';
      let pool = [];
      let attempts = 0;
      // 나무 근처가 필요한 품목은 걸러지는 후보가 훨씬 많아서 오버샘플/재시도를 늘림.
      const oversample = wantsTreeProximity ? need * 12 : need * 3;
      const maxAttempts = wantsTreeProximity ? 12 : 6;
      while(pool.length < need && attempts < maxAttempts){
        const raw = generateCandidates(ar.points, Math.max(oversample, 12));
        pool = pool.concat(raw.filter(([x,z]) => {
          if(isBadGround(lookupCell(x, z))) return false;
          if(wantsLeaf && !nearCanopy(x, z)) return false;
          if(wantsLog && !nearLog(x, z)) return false;
          return true;
        }));
        attempts++;
      }
      const seen = new Set();
      const uniq = pool.filter(([x,z])=>{
        const k = x+','+z;
        if(seen.has(k)) return false;
        seen.add(k); return true;
      });
      for(let i=uniq.length-1;i>0;i--){ const j=Math.floor(Math.random()*(i+1)); [uniq[i],uniq[j]]=[uniq[j],uniq[i]]; }
      const picked = uniq.slice(0, need);
      if(picked.length < need) shortfalls.push({name: (catalog.find(s=>s.typeId===sp.typeId)||{}).name || sp.typeId, need, got: picked.length});
      const info = catalog.find(s=>s.typeId===sp.typeId);
      picked.forEach(([x,z])=>{
        const cell = lookupCell(x, z);
        const groundY = cell ? cell.height : 70;
        // 매달림형(열매류)은 나뭇잎 밑에 붙는 것 — 대략 그 칸의 최상단(대체로 잎 캐노피)
        // 높이 근처를 미리보기 y로 삼는다. 정확한 나뭇잎 블록은 3D요청/설치확정 때 서버에서 재확인.
        const y = hanging ? Math.max(groundY - 1, groundY - 3) : groundY + 1;
        added.push({
          id: nextPreviewId++, world: 'world',
          x: x + 0.5, y, z: z + 0.5,
          typeId: sp.typeId, name: info.name, color: info.color, rarity: info.rarity,
          ruleOk: true, hasVoxel: false, hanging,
        });
      });
    });
  });
  previewNodes = previewNodes.concat(added);
  lastShortfalls = shortfalls;
  return added.length;
}

const active = new Set(catalog.map(s => s.typeId));
document.getElementById('count').textContent = nodes.length + '개 노드 · ' + catalog.length + '개 품목';

let uiMode = 'view'; // 'view' | 'draw' | 'preview'
let areas = [];        // {id, points:[[x,z],...], count, species:[{typeId,weight}]}
let nextAreaId = 1;
let drawing = null;    // {points:[[x,z],...]} live freehand path while dragging

// preview_nodes: 배치 요청을 처리한 뒤 다시 이 아티팩트를 republish할 때 채워짐.
// 각 항목: {id, x, y, z, typeId, name, color, rarity, ruleOk, note, voxel:{...}}
let previewNodes = (DATA.preview_nodes || []).map(n => ({...n}));
let previewDraggingId = null;
let previewMouseDownPos = null;
let lastShortfalls = [];

function polygonBounds(points){
  const xs = points.map(p=>p[0]), zs = points.map(p=>p[1]);
  return { minX: Math.min(...xs), maxX: Math.max(...xs), minZ: Math.min(...zs), maxZ: Math.max(...zs) };
}

const side = document.getElementById('side');
const stage = document.getElementById('stage');
const hint = document.getElementById('hint');

function renderSide(){
  const prevScroll = side.scrollTop;
  side.innerHTML = '';
  if(uiMode === 'view'){ renderViewPanel(); }
  else if(uiMode === 'draw'){ renderDrawPanel(); }
  else { renderPreviewPanel(); }
  side.scrollTop = prevScroll;
}

function renderViewPanel(){
  const wrap = document.createElement('div');
  wrap.innerHTML = `<h2>품목 <button class="toggleall" id="toggleall">전체 토글</button></h2>`;
  side.appendChild(wrap);
  const filtersEl = document.createElement('div');
  filtersEl.id = 'filters';
  side.appendChild(filtersEl);
  regionOrder.forEach(region=>{
    const species = catalog.filter(s => s.region === region);
    const group = document.createElement('div');
    group.className = 'region-group';
    const total = species.reduce((a,s)=>a+s.count, 0);
    const head = document.createElement('div');
    head.className = 'region-head';
    head.innerHTML = `<input type="checkbox" checked><span>${region}</span><span class="rc">${total}</span>`;
    group.appendChild(head);
    const headBox = head.querySelector('input');
    headBox.addEventListener('change', ()=>{
      species.forEach(s=>{ if(headBox.checked) active.add(s.typeId); else active.delete(s.typeId); });
      group.querySelectorAll('.species-row input').forEach(b=>b.checked = headBox.checked);
      draw();
    });
    species.forEach(s=>{
      const row = document.createElement('label');
      row.className = 'species-row';
      row.innerHTML = `<input type="checkbox" ${active.has(s.typeId)?'checked':''} data-tid="${s.typeId}">
        <span class="swatch" style="background:${s.color}"></span>
        <span class="sname">${s.name}</span>
        ${s.rarity === '희귀' ? '<span class="rare-mark">✦</span>' : ''}
        ${ruleIcon(s.typeId) ? `<span class="rulebadge" title="${ruleNote(s.typeId)}">${ruleIcon(s.typeId)}</span>` : ''}
        <span class="cnt">${s.count}</span>`;
      group.appendChild(row);
      row.querySelector('input').addEventListener('change', e=>{
        if(e.target.checked) active.add(s.typeId); else active.delete(s.typeId);
        const all = [...group.querySelectorAll('.species-row input')].every(b=>b.checked);
        headBox.checked = all;
        draw();
      });
    });
    filtersEl.appendChild(group);
  });
  document.getElementById('toggleall').addEventListener('click', ()=>{
    const boxes = filtersEl.querySelectorAll('input[type=checkbox]');
    const allOn = [...boxes].every(b=>b.checked);
    boxes.forEach(b=>{ b.checked = !allOn; });
    active.clear();
    if(!allOn) catalog.forEach(s=>active.add(s.typeId));
    draw();
  });

  const statsWrap = document.createElement('div');
  const commonCount = nodes.filter(n=>n.rarity==='흔함').length;
  const rareCount = nodes.filter(n=>n.rarity==='희귀').length;
  statsWrap.innerHTML = `<h2>통계</h2><div style="display:flex;flex-direction:column;gap:4px;margin-top:6px;">
    <div class="statline"><span>총 노드</span><b>${nodes.length}</b></div>
    <div class="statline"><span>흔함</span><b>${commonCount}</b></div>
    <div class="statline"><span>희귀</span><b>${rareCount}</b></div>
  </div>`;
  side.appendChild(statsWrap);
}

function renderDrawPanel(){
  const head = document.createElement('div');
  head.innerHTML = `<h2>배치 영역 (${areas.length})</h2>`;
  side.appendChild(head);
  if(areas.length === 0){
    const note = document.createElement('div');
    note.className = 'empty-note';
    note.textContent = '지도 위에서 클릭한 채로 드래그해서 원하는 모양의 선을 그리세요. 손을 떼면 시작점과 이어져 영역이 닫힙니다.';
    side.appendChild(note);
  }
  areas.forEach(a=>{
    side.appendChild(buildAreaCard(a));
  });
  const sendWrap = document.createElement('div');
  sendWrap.className = 'sendbar';
  const missing = areas.filter(a => a.species.length === 0);
  const ready = areas.length > 0 && missing.length === 0;
  let reason = '';
  if(areas.length === 0) reason = '⚠ 먼저 지도 위에서 영역을 그려주세요.';
  else if(missing.length > 0) reason = `⚠ 영역 #${missing.map(a=>a.id).join(', #')}에 품목을 아직 선택 안 했습니다.`;
  sendWrap.innerHTML = `
    <div class="empty-note">${areas.length}개 영역 · 총 <span id="grand-total-num">${areas.reduce((a,x)=>a+areaTotal(x),0)}</span>개 노드 예정</div>
    ${reason ? `<div class="empty-note" style="color:var(--draw);">${reason}</div>` : ''}
    <div class="empty-note">이 페이지 안에서 바로 후보 위치를 계산합니다 (서버에 요청 안 보냄).</div>
    <button class="sendbtn" id="sendbtn" ${ready ? '' : 'disabled'} title="${ready ? '' : reason}">${ready ? '미리보기 생성' : '먼저 위 조건을 채워주세요'}</button>`;
  side.appendChild(sendWrap);
  const btn = document.getElementById('sendbtn');
  if(btn && ready) btn.addEventListener('click', ()=>{
    const n = generatePreviewFromAreas();
    areas = [];
    setMode('preview');
  });
}

function buildAreaCard(c){
  const card = document.createElement('div');
  card.className = 'circle-card';
  const b = polygonBounds(c.points);
  const cx = Math.round((b.minX+b.maxX)/2), cz = Math.round((b.minZ+b.maxZ)/2);
  const chead = document.createElement('div');
  chead.className = 'chead';
  chead.innerHTML = `<span>영역 #${c.id}</span><span class="coord">중심 (${cx}, ${cz}) · ${c.points.length}점</span>
    <button class="rm" title="삭제">✕</button>`;
  chead.querySelector('.rm').addEventListener('click', ()=>{
    areas = areas.filter(x=>x.id!==c.id);
    renderSide(); draw();
  });
  card.appendChild(chead);

  const picker = document.createElement('div');
  picker.className = 'picker';
  regionOrder.forEach(region=>{
    const species = catalog.filter(s=>s.region===region);
    const rh = document.createElement('div');
    rh.className = 'pick-region';
    rh.textContent = region;
    picker.appendChild(rh);
    species.forEach(s=>{
      const existing = c.species.find(x=>x.typeId===s.typeId);
      const row = document.createElement('label');
      row.className = 'pick-row';
      row.innerHTML = `<input type="checkbox" ${existing?'checked':''}>
        <span class="swatch" style="background:${s.color}"></span>
        <span class="pname">${s.name}${s.rarity==='희귀'?' ✦':''} ${ruleIcon(s.typeId)}</span>
        <input type="number" class="w-input" min="1" title="이 품목을 몇 개 놓을지" value="${existing?existing.count:8}" ${existing?'':'style="visibility:hidden"'}>`;
      const cb = row.querySelector('input[type=checkbox]');
      const cIn = row.querySelector('.w-input');
      cb.addEventListener('change', ()=>{
        if(cb.checked){ c.species.push({typeId:s.typeId, count: Math.max(1, Number(cIn.value)||8)}); cIn.style.visibility='visible'; }
        else { c.species = c.species.filter(x=>x.typeId!==s.typeId); cIn.style.visibility='hidden'; }
        renderSide();
      });
      cIn.addEventListener('input', ()=>{
        const e = c.species.find(x=>x.typeId===s.typeId);
        if(e) e.count = Math.max(1, Number(cIn.value)||1);
        // 전체 사이드바를 다시 그리면 스크롤 위치/입력 포커스가 날아가므로
        // 합계 표시만 직접 갱신한다 (renderSide() 호출 금지).
        updateTotals();
      });
      picker.appendChild(row);
    });
  });
  card.appendChild(picker);

  const totalRow = document.createElement('div');
  totalRow.className = 'countrow';
  totalRow.innerHTML = `<span>이 영역 합계</span><b id="total-${c.id}" style="font-variant-numeric:tabular-nums;">${areaTotal(c)}개</b>`;
  card.appendChild(totalRow);

  if(c.species.length === 0){
    const warn = document.createElement('div');
    warn.className = 'empty-note';
    warn.textContent = '⚠ 이 영역에 배치할 품목을 최소 1개 선택하세요. 체크한 뒤 옆 숫자칸에 개수를 입력하세요.';
    card.appendChild(warn);
  }
  return card;
}

function areaTotal(c){ return c.species.reduce((a,s)=>a+s.count, 0); }

function updateTotals(){
  areas.forEach(c=>{
    const el = document.getElementById('total-'+c.id);
    if(el) el.textContent = areaTotal(c) + '개';
  });
  const grand = document.getElementById('grand-total-num');
  if(grand) grand.textContent = areas.reduce((a,x)=>a+areaTotal(x),0);
}

function sendToClaude(msg, btnId){
  const btn = btnId ? document.getElementById(btnId) : null;
  if(window.sendPrompt){
    window.sendPrompt(msg);
    if(btn){
      const orig = btn.textContent;
      btn.textContent = '✓ 전송됨 — 채팅을 확인하세요';
      setTimeout(()=>{ if(document.getElementById(btnId)) document.getElementById(btnId).textContent = orig; }, 2500);
    }
  } else {
    openFallbackSendModal(msg);
  }
}

function requestVoxelData(){
  const need = previewNodes.filter(n => !n.hasVoxel);
  if(need.length === 0) return;
  // typeId/name/color/rarity/hanging도 같이 보냄 — 재게시할 때 이 필드들을 그대로
  // 복원해야 하는데, 좌표만 받으면 어떤 품목인지 서버 쪽엔 기록이 없어서 복원 불가능.
  const payload = need.map(n => ({
    id: n.id, world: n.world, x: Math.round(n.x), y: Math.round(n.y), z: Math.round(n.z),
    typeId: n.typeId, name: n.name, color: n.color, rarity: n.rarity, hanging: !!n.hanging,
  }));
  const msg = '아래 미리보기 후보들 주변의 실제 지형(3D 확인용)을 스캔해서, 이 지도를 미리보기 데이터가 채워진 채로 다시 게시해줘:\\n' + JSON.stringify(payload, null, 1);
  sendToClaude(msg, 'voxelreqbtn');
}

function openFallbackSendModal(msg){
  const root = document.getElementById('modal-root');
  root.innerHTML = '';
  const backdrop = document.createElement('div');
  backdrop.className = 'modal-backdrop';
  const modal = document.createElement('div');
  modal.className = 'modal';
  modal.style.width = '480px';
  modal.innerHTML = `<h3>요청 준비 완료</h3>
    <div class="empty-note">아래 내용이 이미 전체 선택돼 있어요. 복사한 뒤 채팅창에 붙여넣어서 보내주세요.</div>
    <textarea id="fallback-ta" readonly style="width:100%;height:180px;background:var(--bg);color:var(--text);
      border:1px solid var(--border);border-radius:6px;padding:8px;font-size:11.5px;font-family:monospace;
      resize:vertical;"></textarea>
    <div class="modal-actions">
      <button class="btn-cancel">닫기</button>
      <button class="btn-ok" id="fallback-copy">전체 복사</button>
    </div>`;
  root.appendChild(backdrop);
  backdrop.appendChild(modal);
  const ta = modal.querySelector('#fallback-ta');
  ta.value = msg;
  ta.focus(); ta.select();
  modal.querySelector('.btn-cancel').addEventListener('click', ()=>root.innerHTML='');
  modal.querySelector('#fallback-copy').addEventListener('click', ()=>{
    ta.select();
    let ok = false;
    try { ok = document.execCommand('copy'); } catch(e) {}
    if(navigator.clipboard && navigator.clipboard.writeText){
      navigator.clipboard.writeText(msg).catch(()=>{});
    }
    modal.querySelector('#fallback-copy').textContent = ok ? '복사됨!' : '선택됨 (Ctrl/Cmd+C)';
  });
  backdrop.addEventListener('click', e=>{ if(e.target===backdrop) root.innerHTML=''; });
}

function renderPreviewPanel(){
  const head = document.createElement('div');
  head.innerHTML = `<h2>배치 미리보기 (${previewNodes.length})</h2>`;
  side.appendChild(head);
  if(lastShortfalls.length){
    const warn = document.createElement('div');
    warn.className = 'empty-note';
    warn.style.color = 'var(--draw)';
    warn.textContent = '⚠ 나무(원목/나뭇잎) 근처가 부족해서 목표를 못 채운 품목: ' +
      lastShortfalls.map(s=>`${s.name} ${s.got}/${s.need}개`).join(', ');
    side.appendChild(warn);
  }
  if(previewNodes.length === 0){
    const note = document.createElement('div');
    note.className = 'empty-note';
    note.textContent = '아직 미리볼 배치가 없습니다. "영역 그리기"에서 영역+품목을 정하고 "미리보기 생성"을 누르면 여기 바로 채워집니다.';
    side.appendChild(note);
    return;
  }
  const list = document.createElement('div');
  list.style.cssText = 'display:flex;flex-direction:column;gap:2px;max-height:340px;overflow-y:auto;';
  previewNodes.forEach(n=>{
    const row = document.createElement('div');
    row.className = 'preview-item';
    row.innerHTML = `<span class="swatch" style="background:${n.color}"></span>
      <span class="sname" style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${n.name}${n.rarity==='희귀'?' ✦':''}</span>
      ${n.hanging ? '<span class="pi-flag" title="나뭇잎 밑 매달림">🍃</span>' : ''}
      ${n.ruleOk===false ? '<span class="pi-flag" title="'+(n.note||'조건 미충족')+'">⚠</span>' : ''}
      <span class="pi-coord">(${Math.round(n.x)}, ${Math.round(n.z)})</span>
      <button class="rm" title="이 노드 제외">✕</button>`;
    row.addEventListener('click', (e)=>{
      if(e.target.closest('.rm')) return;
      openIsoModal(n.id);
    });
    row.querySelector('.rm').addEventListener('click', (e)=>{
      e.stopPropagation();
      previewNodes = previewNodes.filter(x=>x.id!==n.id);
      renderSide(); draw();
    });
    list.appendChild(row);
  });
  side.appendChild(list);

  const needVoxel = previewNodes.filter(n => !n.hasVoxel).length;
  const sendWrap = document.createElement('div');
  sendWrap.className = 'sendbar';
  sendWrap.innerHTML = `
    <div class="empty-note">마커를 지도에서 드래그해서 대략 옮길 수 있습니다. 클릭하면 3D로 주변을 봅니다
      (${needVoxel > 0 ? needVoxel + '개는 아직 3D 데이터 없음 — 아래 버튼으로 요청' : '전부 3D 데이터 있음'}).</div>
    ${needVoxel > 0 ? `<button class="sendbtn" id="voxelreqbtn" style="background:var(--panel2);color:var(--text);border:1px solid var(--border-strong);">3D 지형 요청 보내기 (${needVoxel}개)</button>` : ''}
    <button class="sendbtn" id="confirmbtn">설치 확정 (${previewNodes.length}개)</button>`;
  side.appendChild(sendWrap);
  if(needVoxel > 0) document.getElementById('voxelreqbtn').addEventListener('click', requestVoxelData);
  document.getElementById('confirmbtn').addEventListener('click', confirmInstall);
}

function confirmInstall(){
  const payload = previewNodes.map(n=>({
    id: n.id, world: n.world || 'world',
    x: Math.round(n.x*10)/10, y: Math.round(n.y*10)/10, z: Math.round(n.z*10)/10,
    typeId: n.typeId, hanging: !!n.hanging,
  }));
  const msg = '아래 미리보기 좌표(일부는 내가 드래그로 조정했을 수 있음)로 실제 채집 노드 설치를 실행해줘 — hanging:true인 항목은 나뭇잎 블록 밑 매달림(설치 Y=나뭇잎 블록 Y 그대로), 나머지는 지표면(설치 Y=지표면+1)이니 설치 직전에 실제 블록으로 정확히 재확인해줘:\\n' + JSON.stringify(payload, null, 1);
  sendToClaude(msg, 'confirmbtn');
}

const MODES = ['view', 'draw', 'preview'];
function setMode(m){
  uiMode = m;
  MODES.forEach(k=>document.getElementById('mode-'+k).classList.toggle('active', k===m));
  stage.classList.toggle('drawmode', m==='draw');
  if(m==='view') hint.textContent = '드래그로 이동 · 휠/버튼으로 확대 · ✦ = 희귀';
  else if(m==='draw') hint.textContent = '클릭한 채로 드래그해서 원하는 모양의 선을 그리세요 · 놓으면 자동으로 닫혀 영역 확정';
  else hint.textContent = '마커 드래그로 대략 이동 · 마커 클릭으로 3D 미세조정';
  renderSide(); draw();
}
document.getElementById('mode-view').addEventListener('click', ()=>setMode('view'));
document.getElementById('mode-draw').addEventListener('click', ()=>setMode('draw'));
document.getElementById('mode-preview').addEventListener('click', ()=>setMode('preview'));

// ---- canvas render (background PNG + node dots + drawn areas), pan/zoom ----
const canvas = document.getElementById('map');
const ctx = canvas.getContext('2d');
const tooltip = document.getElementById('tooltip');

const bg = new Image();
bg.src = 'data:image/png;base64,' + DATA.png_b64;

let view = { scale: 1, ox: 0, oz: 0 };
let panning = false, lastX = 0, lastY = 0;

function resizeCanvas(){
  canvas.width = stage.clientWidth;
  canvas.height = stage.clientHeight;
  draw();
}

function worldToScreen(x, z){
  const cellW = canvas.width / meta.region_width;
  const cellH = canvas.height / meta.region_depth;
  const cell = Math.min(cellW, cellH) * view.scale;
  return [(x - meta.x_origin) * cell + view.ox, (z - meta.z_origin) * cell + view.oz, cell];
}
function screenToWorld(px, py){
  const cellW = canvas.width / meta.region_width;
  const cellH = canvas.height / meta.region_depth;
  const cell = Math.min(cellW, cellH) * view.scale;
  return [(px - view.ox) / cell + meta.x_origin, (py - view.oz) / cell + meta.z_origin, cell];
}

function draw(){
  if(!bg.complete || !bg.naturalWidth) return;
  ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--bg').trim() || '#12161d';
  ctx.fillRect(0,0,canvas.width,canvas.height);
  const [ox0, oz0, cell] = worldToScreen(meta.x_origin, meta.z_origin);
  ctx.imageSmoothingEnabled = view.scale > 6;
  ctx.drawImage(bg, ox0, oz0, meta.region_width * cell, meta.region_depth * cell);

  nodes.forEach(n=>{
    if(!active.has(n.typeId)) return;
    const [x, y] = worldToScreen(n.x, n.z);
    if(x < -10 || y < -10 || x > canvas.width+10 || y > canvas.height+10) return;
    const rare = n.rarity === '희귀';
    const r = rare ? 4.6 : 3.2;
    if(rare){
      ctx.beginPath(); ctx.arc(x, y, r + 3.2, 0, Math.PI*2);
      ctx.fillStyle = 'rgba(242,212,138,.4)'; ctx.fill();
    }
    ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI*2);
    ctx.fillStyle = n.color; ctx.fill();
    ctx.lineWidth = rare ? 1.4 : 1;
    ctx.strokeStyle = rare ? 'rgba(255,255,255,.85)' : 'rgba(0,0,0,.4)';
    ctx.stroke();
  });

  const drawColor = getComputedStyle(document.documentElement).getPropertyValue('--draw').trim() || '#e5544d';
  areas.forEach(c=>{
    const pts = c.points.map(p => worldToScreen(p[0], p[1]));
    if(pts.length < 2) return;
    ctx.beginPath();
    ctx.moveTo(pts[0][0], pts[0][1]);
    for(let i=1;i<pts.length;i++) ctx.lineTo(pts[i][0], pts[i][1]);
    ctx.closePath();
    ctx.fillStyle = drawColor + '22'; ctx.fill();
    ctx.lineWidth = 2.5; ctx.strokeStyle = drawColor; ctx.stroke();
    const b = polygonBounds(c.points);
    const [lx, ly] = worldToScreen((b.minX+b.maxX)/2, (b.minZ+b.maxZ)/2);
    ctx.fillStyle = drawColor; ctx.font = 'bold 12px sans-serif'; ctx.textAlign = 'center';
    ctx.fillText('#' + c.id, lx, ly + 4);
  });
  if(drawing && drawing.points.length > 1){
    const pts = drawing.points.map(p => worldToScreen(p[0], p[1]));
    ctx.beginPath();
    ctx.moveTo(pts[0][0], pts[0][1]);
    for(let i=1;i<pts.length;i++) ctx.lineTo(pts[i][0], pts[i][1]);
    ctx.fillStyle = drawColor + '18';
    ctx.save(); ctx.closePath(); ctx.fill(); ctx.restore();
    ctx.setLineDash([5,4]); ctx.lineWidth = 2.5; ctx.strokeStyle = drawColor; ctx.stroke();
    ctx.setLineDash([]);
  }

  if(uiMode === 'preview'){
    previewNodes.forEach(n=>{
      const [x, y] = worldToScreen(n.x, n.z);
      if(x < -12 || y < -12 || x > canvas.width+12 || y > canvas.height+12) return;
      ctx.beginPath(); ctx.arc(x, y, 6, 0, Math.PI*2);
      ctx.fillStyle = n.color; ctx.fill();
      ctx.lineWidth = 2; ctx.strokeStyle = n.ruleOk === false ? '#e5544d' : '#ffffff'; ctx.stroke();
      ctx.beginPath(); ctx.arc(x, y, 9, 0, Math.PI*2);
      ctx.strokeStyle = 'rgba(255,255,255,.35)'; ctx.lineWidth = 1; ctx.stroke();
    });
  }
}

bg.onload = ()=>{
  const fitCell = Math.min(canvas.width / meta.region_width, canvas.height / meta.region_depth);
  view.scale = 1;
  view.ox = (canvas.width - meta.region_width * fitCell) / 2;
  view.oz = (canvas.height - meta.region_depth * fitCell) / 2;
  draw();
};
window.addEventListener('resize', resizeCanvas);
resizeCanvas();

const MIN_POINT_GAP_SCREEN = 4; // px — drop points closer than this to keep paths light

function findPreviewNodeAt(mx, my){
  let hit = null, hitDist = 100;
  previewNodes.forEach(n=>{
    const [x, y] = worldToScreen(n.x, n.z);
    const d = (x-mx)*(x-mx) + (y-my)*(y-my);
    if(d < hitDist){ hitDist = d; hit = n; }
  });
  return hit;
}

stage.addEventListener('mousedown', e=>{
  const rect = canvas.getBoundingClientRect();
  const mx = e.clientX - rect.left, my = e.clientY - rect.top;
  if(uiMode === 'draw'){
    const [wx, wz] = screenToWorld(mx, my);
    drawing = { points: [[wx, wz]], lastScreen: [mx, my] };
    return;
  }
  if(uiMode === 'preview'){
    const hit = findPreviewNodeAt(mx, my);
    previewMouseDownPos = [mx, my];
    previewDraggingId = hit ? hit.id : null;
    return;
  }
  panning = true; lastX = e.clientX; lastY = e.clientY; stage.classList.add('dragging');
});
window.addEventListener('mouseup', e=>{
  if(uiMode === 'draw' && drawing){
    if(drawing.points.length >= 3){
      const a = { id: nextAreaId++, points: drawing.points, species: [] };
      areas.push(a);
      renderSide();
    }
    drawing = null; draw();
    return;
  }
  if(uiMode === 'preview'){
    if(previewDraggingId != null && previewMouseDownPos){
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left, my = e.clientY - rect.top;
      const moved = Math.hypot(mx-previewMouseDownPos[0], my-previewMouseDownPos[1]);
      if(moved < 4) openIsoModal(previewDraggingId); // 거의 안 움직였으면 클릭으로 간주 → 3D 팝업
    }
    previewDraggingId = null; previewMouseDownPos = null;
    return;
  }
  panning = false; stage.classList.remove('dragging');
});
window.addEventListener('mousemove', e=>{
  const rect = canvas.getBoundingClientRect();
  const mx = e.clientX - rect.left, my = e.clientY - rect.top;
  if(uiMode === 'draw' && drawing){
    const [lx, ly] = drawing.lastScreen;
    if(Math.hypot(mx-lx, my-ly) >= MIN_POINT_GAP_SCREEN){
      const [wx, wz] = screenToWorld(mx, my);
      drawing.points.push([wx, wz]);
      drawing.lastScreen = [mx, my];
      draw();
    }
    return;
  }
  if(uiMode === 'preview' && previewDraggingId != null){
    const n = previewNodes.find(x=>x.id===previewDraggingId);
    if(n){
      const [wx, wz] = screenToWorld(mx, my);
      n.x = wx; n.z = wz;
      draw();
    }
    return;
  }
  if(panning){
    view.ox += e.clientX - lastX; view.oz += e.clientY - lastY;
    lastX = e.clientX; lastY = e.clientY;
    draw(); tooltip.style.display = 'none';
    return;
  }
  if(uiMode !== 'view'){ tooltip.style.display = 'none'; return; }
  let hit = null, hitDist = 64;
  nodes.forEach(n=>{
    if(!active.has(n.typeId)) return;
    const [x, y] = worldToScreen(n.x, n.z);
    const d = (x-mx)*(x-mx) + (y-my)*(y-my);
    if(d < hitDist){ hitDist = d; hit = n; }
  });
  if(hit){
    tooltip.style.display = 'block';
    tooltip.style.left = (mx + 14) + 'px'; tooltip.style.top = (my + 10) + 'px';
    tooltip.innerHTML = `<div class="name" style="color:${hit.color}">${hit.name}${hit.rarity==='희귀' ? ' ✦' : ''}</div>
      <div class="meta">${hit.rarity} · ${hit.region}</div>
      <div class="meta">(${Math.round(hit.x)}, ${Math.round(hit.z)})</div>`;
  } else { tooltip.style.display = 'none'; }
});
stage.addEventListener('wheel', e=>{
  e.preventDefault();
  const rect = canvas.getBoundingClientRect();
  const mx = e.clientX - rect.left, my = e.clientY - rect.top;
  const before = view.scale;
  const factor = e.deltaY < 0 ? 1.15 : 1/1.15;
  view.scale = Math.min(60, Math.max(1, view.scale * factor));
  const k = view.scale / before;
  view.ox = mx - (mx - view.ox) * k; view.oz = my - (my - view.oz) * k;
  draw();
}, { passive: false });
document.getElementById('zin').addEventListener('click', ()=>{ view.scale = Math.min(60, view.scale * 1.3); draw(); });
document.getElementById('zout').addEventListener('click', ()=>{ view.scale = Math.max(1, view.scale / 1.3); draw(); });

// ---- 노드 클릭 → 근처 지형 아이소메트릭 3D 팝업 (드래그로 미세 위치조정) ----
const ISO = { halfW: 13, halfH: 7, blockH: 13 };
const PASSABLE = new Set(['air','short_grass','tall_grass','fern','large_fern','snow','vine',
  'poppy','dandelion','allium','blue_orchid','azure_bluet','oxeye_daisy','cornflower',
  'lily_of_the_valley','wheat','carrots','potatoes','beetroots']);

function isoProject(x, y, z){
  return [ (x - z) * ISO.halfW, (x + z) * ISO.halfH - y * ISO.blockH ];
}
function findSurfaceY(voxel, lx, lz){
  for(let y = voxel.sy - 1; y >= 0; y--){
    const mat = (voxel.legend[voxel.idx[y][lz][lx]] || 'minecraft:air').replace('minecraft:', '');
    if(mat !== 'air' && !PASSABLE.has(mat)) return y + 1;
  }
  return 0;
}
function shade(rgb, f){
  return `rgb(${Math.max(0,Math.min(255,Math.round(rgb[0]*f)))},${Math.max(0,Math.min(255,Math.round(rgb[1]*f)))},${Math.max(0,Math.min(255,Math.round(rgb[2]*f)))})`;
}

let isoState = null; // {node, voxel, lx, ly, lz, ctx, canvas, dragging}

function openIsoModal(nodeId){
  const node = previewNodes.find(n=>n.id===nodeId);
  if(!node) return;
  const root = document.getElementById('modal-root');
  root.innerHTML = '';
  const backdrop = document.createElement('div');
  backdrop.className = 'modal-backdrop';
  const modal = document.createElement('div');
  modal.className = 'modal';
  backdrop.appendChild(modal);

  if(!node.voxel){
    modal.innerHTML = `<h3><span class="swatch" style="background:${node.color}"></span> ${node.name}</h3>
      <div class="empty-note">아직 이 노드 주변의 정밀 지형 스냅샷이 없습니다. 사이드바의
      "3D 지형 요청 보내기" 버튼으로 받아오면, 여기서 원목·꽃·밀 등 실제 블록을 보면서
      드래그로 위치를 미세조정할 수 있습니다.</div>
      <div class="coordline">현재 좌표 (${Math.round(node.x)}, ${Math.round(node.y)}, ${Math.round(node.z)}) — 근사치(대략 지형 기준)</div>
      <div class="modal-actions"><button class="btn-cancel">닫기</button></div>`;
    modal.querySelector('.btn-cancel').addEventListener('click', ()=>root.innerHTML='');
    root.appendChild(backdrop);
    backdrop.addEventListener('click', e=>{ if(e.target===backdrop) root.innerHTML=''; });
    return;
  }

  const voxel = node.voxel;
  const lx0 = Math.round(node.x - voxel.x0), lz0 = Math.round(node.z - voxel.z0);
  const ly0 = Math.max(0, Math.min(voxel.sy-1, Math.round(node.y - voxel.y0)));

  modal.innerHTML = `<h3><span class="swatch" style="background:${node.color}"></span> ${node.name}${node.rarity==='희귀'?' ✦':''}</h3>
    <div class="miso-wrap"><canvas id="iso" width="380" height="290"></canvas></div>
    <div class="coordline" id="iso-coord"></div>
    <div class="iso-hint">마커를 드래그하면 그 칸의 지표면 높이에 맞춰 옮겨집니다. 회색 배경 = 주변 지형(원목·잔디·꽃·밀 등 실제 블록).</div>
    <div class="modal-actions"><button class="btn-cancel">취소</button><button class="btn-ok">이 위치로 확정</button></div>`;
  root.appendChild(backdrop);

  isoState = {
    node, voxel, lx: Math.max(0,Math.min(voxel.sx-1,lx0)), ly: ly0, lz: Math.max(0,Math.min(voxel.sz-1,lz0)),
    canvas: modal.querySelector('#iso'), dragging: false,
  };
  isoState.ctx = isoState.canvas.getContext('2d');
  renderIso();

  isoState.canvas.addEventListener('mousedown', ()=>{ isoState.dragging = true; isoState.canvas.style.cursor='grabbing'; });
  window.addEventListener('mouseup', isoMouseUp);
  isoState.canvas.addEventListener('mousemove', isoMouseMove);

  modal.querySelector('.btn-cancel').addEventListener('click', closeIsoModal);
  modal.querySelector('.btn-ok').addEventListener('click', ()=>{
    const s = isoState;
    s.node.x = s.voxel.x0 + s.lx + 0.5;
    s.node.y = s.voxel.y0 + s.ly;
    s.node.z = s.voxel.z0 + s.lz + 0.5;
    closeIsoModal();
    renderSide(); draw();
  });
  backdrop.addEventListener('click', e=>{ if(e.target===backdrop) closeIsoModal(); });
}
function isoMouseUp(){ if(isoState){ isoState.dragging = false; if(isoState.canvas) isoState.canvas.style.cursor='grab'; } }
function isoMouseMove(e){
  const s = isoState;
  if(!s || !s.dragging) return;
  const rect = s.canvas.getBoundingClientRect();
  const mx = e.clientX - rect.left - s.canvas.width/2;
  const my = e.clientY - rect.top - s.canvas.height/2 + (s.ly * ISO.blockH);
  // 역투영(대략): y는 현재 칸의 지표면으로 스냅
  const fx = (mx / ISO.halfW + my / ISO.halfH) / 2;
  const fz = (my / ISO.halfH - mx / ISO.halfW) / 2;
  const lx = Math.max(0, Math.min(s.voxel.sx-1, Math.round(fx + s.voxel.sx/2)));
  const lz = Math.max(0, Math.min(s.voxel.sz-1, Math.round(fz + s.voxel.sz/2)));
  s.lx = lx; s.lz = lz; s.ly = findSurfaceY(s.voxel, lx, lz);
  renderIso();
}
function closeIsoModal(){
  window.removeEventListener('mouseup', isoMouseUp);
  document.getElementById('modal-root').innerHTML = '';
  isoState = null;
}
function renderIso(){
  const s = isoState;
  const ctx = s.ctx, voxel = s.voxel, canvas = s.canvas;
  ctx.fillStyle = '#0c1016'; ctx.fillRect(0,0,canvas.width,canvas.height);
  ctx.save();
  ctx.translate(canvas.width/2, canvas.height/2 + (voxel.sy) * ISO.blockH / 2);

  const order = [];
  for(let y=0;y<voxel.sy;y++) for(let z=0;z<voxel.sz;z++) for(let x=0;x<voxel.sx;x++){
    const li = voxel.idx[y][z][x];
    if(li === 0) continue; // air
    order.push([x,y,z,li]);
  }
  order.sort((a,b)=> (a[0]+a[2]+a[1]*0.01) - (b[0]+b[2]+b[1]*0.01));

  order.forEach(([x,y,z,li])=>{
    const rgb = voxel.colors[li] || [140,140,140];
    const [sx, sy] = isoProject(x - voxel.sx/2, y, z - voxel.sz/2);
    const hw = ISO.halfW, hh = ISO.halfH, bh = ISO.blockH;
    // top face
    ctx.beginPath();
    ctx.moveTo(sx, sy - bh);
    ctx.lineTo(sx + hw, sy - bh + hh);
    ctx.lineTo(sx, sy - bh + hh*2);
    ctx.lineTo(sx - hw, sy - bh + hh);
    ctx.closePath();
    ctx.fillStyle = shade(rgb, 1.15); ctx.fill();
    // left face
    ctx.beginPath();
    ctx.moveTo(sx - hw, sy - bh + hh);
    ctx.lineTo(sx, sy - bh + hh*2);
    ctx.lineTo(sx, sy + hh*2);
    ctx.lineTo(sx - hw, sy + hh);
    ctx.closePath();
    ctx.fillStyle = shade(rgb, 0.72); ctx.fill();
    // right face
    ctx.beginPath();
    ctx.moveTo(sx + hw, sy - bh + hh);
    ctx.lineTo(sx, sy - bh + hh*2);
    ctx.lineTo(sx, sy + hh*2);
    ctx.lineTo(sx + hw, sy + hh);
    ctx.closePath();
    ctx.fillStyle = shade(rgb, 0.9); ctx.fill();
  });

  // marker
  const [mxp, myp] = isoProject(s.lx - voxel.sx/2, s.ly, s.lz - voxel.sz/2);
  ctx.beginPath(); ctx.ellipse(mxp, myp + 4, 7, 3.5, 0, 0, Math.PI*2);
  ctx.fillStyle = 'rgba(0,0,0,.35)'; ctx.fill();
  ctx.beginPath(); ctx.arc(mxp, myp - 8, 6, 0, Math.PI*2);
  ctx.fillStyle = s.node.color; ctx.fill();
  ctx.lineWidth = 2; ctx.strokeStyle = '#fff'; ctx.stroke();
  ctx.restore();

  const coordEl = document.getElementById('iso-coord');
  if(coordEl) coordEl.textContent = `좌표 (${Math.round(voxel.x0+s.lx)}, ${Math.round(voxel.y0+s.ly)}, ${Math.round(voxel.z0+s.lz)})`;
}

renderSide();
</script>
"""

html = html.replace("__DATA__", payload)
OUT = os.path.join(HERE, "forage_map.html")
with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)
print("wrote", OUT, len(html), "bytes")
