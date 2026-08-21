(() => {
  const canvas = document.querySelector('#voxel-map');
  const svg = document.querySelector('#map-svg');
  const viewport = document.querySelector('#map-viewport');
  const plane = document.querySelector('.map-plane');
  const mapData = window.BARKAN_MAP_DATA;
  const terrainData = window.BARKAN_TERRAIN_DATA;
  if (!canvas || !svg || !viewport || !plane || !mapData || !terrainData) return;

  const ctx = canvas.getContext('2d');
  const decode = value => {
    const raw = atob(value);
    const bytes = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i += 1) bytes[i] = raw.charCodeAt(i);
    return bytes;
  };
  const materialBytes = decode(terrainData.materials);
  const maskBytes = decode(terrainData.mask);
  const heightBytes = decode(terrainData.heights);
  const detailBytes = terrainData.details ? decode(terrainData.details) : new Uint8Array();
  const gridWidth = terrainData.gridWidth;
  const gridDepth = terrainData.gridDepth;
  const cellSize = terrainData.cellSize;
  const baseY = 60;
  const globalView = [-5200, -5200, 10400, 10400];
  const legend = terrainData.legend || [];
  const detailRegions = terrainData.detailRegions || [];
  const inDetailRegion = (x, z) => detailRegions.some(region => x >= region.x1 && x <= region.x2 && z >= region.z1 && z <= region.z2);
  const baseCells = [];
  const coarseCells = [];
  const detailHeightMap = new Map();
  const heightAt = (i, j) => {
    if (i < 0 || j < 0 || i >= gridWidth || j >= gridDepth) return baseY;
    const index = j * gridWidth + i;
    return (heightBytes[index * 2] | (heightBytes[index * 2 + 1] << 8)) - 128;
  };
  const materialAt = (i, j) => {
    if (i < 0 || j < 0 || i >= gridWidth || j >= gridDepth) return 0;
    return materialBytes[j * gridWidth + i];
  };
  for (let j = 0; j < gridDepth; j += 1) {
    for (let i = 0; i < gridWidth; i += 1) {
      const index = j * gridWidth + i;
      const height = heightAt(i, j);
      const x = terrainData.xOrigin + i * cellSize;
      const z = terrainData.zOrigin + j * cellSize;
      if (!maskBytes[index] || (materialBytes[index] === 0 && height <= baseY)) continue;
      baseCells.push({ i, j, x, z, height, material: materialBytes[index], size: cellSize });
    }
  }
  const detailStep = Number(terrainData.detailStep) || 4;
  for (let i = 0; i < Number(terrainData.detailCount || 0); i += 1) {
    const offset = i * 7;
    const x = (detailBytes[offset] | (detailBytes[offset + 1] << 8)) - 4096;
    const z = (detailBytes[offset + 2] | (detailBytes[offset + 3] << 8)) - 4096;
    const height = (detailBytes[offset + 4] | (detailBytes[offset + 5] << 8)) - 128;
    const material = detailBytes[offset + 6];
    detailHeightMap.set(`${x},${z}`, height);
    coarseCells.push({ x, z, height, material, size: detailStep, detail: true });
  }

  const camera = { cx: 0, cz: 0, viewWidth: globalView[2], yaw: -0.34, pitch: 0.9 };
  let selectedId = '';
  let width = 1;
  let height = 1;
  let dragging = null;
  let moved = false;
  let lastViewKey = '';
  const farCellSize = cellSize * 2;
  const farCellMap = new Map();
  baseCells.forEach(cell => {
    const key = `${Math.floor(cell.x / farCellSize)},${Math.floor(cell.z / farCellSize)}`;
    const previous = farCellMap.get(key);
    if (!previous || cell.height > previous.height) farCellMap.set(key, { x: Math.floor(cell.x / farCellSize) * farCellSize, z: Math.floor(cell.z / farCellSize) * farCellSize, height: cell.height, material: cell.material, size: farCellSize, detail: true });
  });
  const farCells = [...farCellMap.values()];
  let finePayload = null;
  let fineBytes = new Uint8Array();
  let fineMaterialMap = [];
  let fineLodCache = new Map();
  let fineRegions = [];
  const fineCache = new Map();
  const fineLoading = new Set();
  const townSlugs = { '사막마을': 'desert-town', '스폰도시': 'spawn-city', '상단마을': 'upper-town', '왕도': 'royal-city', '항구': 'harbor' };
  const inFineRegion = (x, z) => fineRegions.some(region => x >= region.x1 && x <= region.x2 && z >= region.z1 && z <= region.z2);
  const clearFineTown = () => {
    finePayload = null;
    fineBytes = new Uint8Array();
    fineMaterialMap = [];
    fineLodCache = new Map();
    fineRegions = [];
  };
  const activateFineTown = payload => {
    clearFineTown();
    const localLegend = payload.legend || [];
    const localIndex = new Map(legend.map((name, index) => [name, index]));
    localLegend.forEach(name => { if (!localIndex.has(name)) { localIndex.set(name, legend.length); legend.push(name); } });
    finePayload = payload;
    fineBytes = decode(payload.details);
    fineMaterialMap = localLegend.map(name => localIndex.get(name) ?? 0);
    fineRegions.push(payload.region);
  };
  const fineLod = step => {
    if (fineLodCache.has(step)) return fineLodCache.get(step);
    const buckets = new Map();
    if (finePayload) {
      if (finePayload.format === 'runs8') {
        const originX = Number(finePayload.xOrigin) || 0;
        const originZ = Number(finePayload.zOrigin) || 0;
        const originY = Number(finePayload.yOrigin) || 0;
        // Runs are emitted bottom-to-top for each column. Keep the highest
        // contiguous stack only for drawing, while the payload still retains
        // every scanned run (including air gaps between stacks).
        const addColumn = (rawX, rawZ, bottom, height, material) => {
          const x = Math.floor(rawX / step) * step;
          const z = Math.floor(rawZ / step) * step;
          const key = `${x},${z}`;
          const previous = buckets.get(key);
          if (!previous || height >= previous.height) {
            buckets.set(key, { x, z, height, bottom, material, size: step, lodStep: step, detail: true, fine: true });
          }
        };
        if (finePayload.columns && finePayload.columnCount) {
          const columnBytes = decode(finePayload.columns);
          for (let i = 0; i < finePayload.columnCount; i += 1) {
            const offset = i * 8;
            const rawX = originX + ((columnBytes[offset] << 8) | columnBytes[offset + 1]);
            const rawZ = originZ + ((columnBytes[offset + 2] << 8) | columnBytes[offset + 3]);
            const bottom = originY + columnBytes[offset + 4];
            const height = bottom + Math.max(1, columnBytes[offset + 5]) - 1;
            const material = fineMaterialMap[(columnBytes[offset + 6] << 8) | columnBytes[offset + 7]] ?? 0;
            addColumn(rawX, rawZ, bottom, height, material);
          }
        } else {
          const columns = new Map();
          for (let i = 0; i < finePayload.count; i += 1) {
            const offset = i * 8;
            const rawX = originX + ((fineBytes[offset] << 8) | fineBytes[offset + 1]);
            const rawZ = originZ + ((fineBytes[offset + 2] << 8) | fineBytes[offset + 3]);
            const start = originY + fineBytes[offset + 4];
            const length = fineBytes[offset + 5];
            const end = start + Math.max(1, length) - 1;
            const materialIndex = (fineBytes[offset + 6] << 8) | fineBytes[offset + 7];
            const material = fineMaterialMap[materialIndex] ?? 0;
            const key = `${rawX},${rawZ}`;
            const previous = columns.get(key);
            if (!previous || start > previous.lastEnd + 1) {
              columns.set(key, { x: rawX, z: rawZ, height: end, bottom: start, material, lastEnd: end });
            } else {
              previous.bottom = start;
              previous.lastEnd = end;
              previous.height = end;
              previous.material = material;
            }
          }
          columns.forEach(column => addColumn(column.x, column.z, column.bottom, column.height, column.material));
        }
      } else if (finePayload.format === 'vox4') {
        const originX = Number(finePayload.xOrigin) || 0;
        const originZ = Number(finePayload.zOrigin) || 0;
        const originY = Number(finePayload.yOrigin) || 0;
        for (let i = 0; i < finePayload.count; i += 1) {
          const offset = i * 4;
          const rawX = originX + fineBytes[offset];
          const rawZ = originZ + fineBytes[offset + 1];
          const y = originY + fineBytes[offset + 2];
          const material = fineMaterialMap[fineBytes[offset + 3]] ?? 0;
          const x = Math.floor(rawX / step) * step;
          const z = Math.floor(rawZ / step) * step;
          const key = `${x},${z}`;
          const previous = buckets.get(key);
          if (!previous) buckets.set(key, { x, z, height: y, bottom: y, material, size: step, lodStep: step, detail: true, fine: true });
          else {
            previous.bottom = Math.min(previous.bottom, y);
            if (y >= previous.height) { previous.height = y; previous.material = material; }
          }
        }
      } else {
        for (let i = 0; i < finePayload.count; i += 1) {
          const offset = i * 7;
          const rawX = (fineBytes[offset] | (fineBytes[offset + 1] << 8)) - 4096;
          const rawZ = (fineBytes[offset + 2] | (fineBytes[offset + 3] << 8)) - 4096;
          const x = Math.floor(rawX / step) * step;
          const z = Math.floor(rawZ / step) * step;
          const height = (fineBytes[offset + 4] | (fineBytes[offset + 5] << 8)) - 128;
          const key = `${x},${z}`;
          const previous = buckets.get(key);
          if (!previous || height > previous.height) buckets.set(key, { x, z, height, material: fineMaterialMap[fineBytes[offset + 6]] ?? 0, size: step, lodStep: step, detail: true, fine: true });
        }
      }
    }
    const cells = [...buckets.values()];
    const result = {
      cells,
      heightMap: new Map(cells.map(cell => [`${cell.x},${cell.z}`, cell.height])),
      columnMap: new Map(cells.map(cell => [`${cell.x},${cell.z}`, cell]))
    };
    fineLodCache.set(step, result);
    return result;
  };
  const loadFineTown = id => {
    const slug = townSlugs[id];
    if (!slug) { clearFineTown(); return; }
    if (fineCache.has(id)) {
      activateFineTown(fineCache.get(id));
      draw();
      return;
    }
    if (fineLoading.has(id)) return;
    clearFineTown();
    fineLoading.add(id);
    fetch(`/assets/town-detail-${slug}.json?v=3`, { cache: 'force-cache' })
      .then(response => response.ok ? response.json() : null)
      .then(payload => {
        fineLoading.delete(id);
        if (!payload) return;
        fineCache.set(id, payload);
        if (selectedId === id) { activateFineTown(payload); draw(); }
      })
      .catch(() => fineLoading.delete(id));
  };

  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
  const areaSegments = area => {
    const cuts = [0, ...(area.polygonBreaks || []), area.polygon.length];
    return cuts.slice(0, -1).map((start, index) => area.polygon.slice(start, cuts[index + 1]));
  };
  const center = area => {
    const [minX, maxX, minZ, maxZ] = area.bounds;
    return [(minX + maxX) / 2, (minZ + maxZ) / 2];
  };
  const pointInPolygon = (x, z, polygon) => {
    let inside = false;
    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
      const [xi, zi] = polygon[i];
      const [xj, zj] = polygon[j];
      if (((zi > z) !== (zj > z)) && x < (xj - xi) * (z - zi) / ((zj - zi) || 1e-9) + xi) inside = !inside;
    }
    return inside;
  };
  const contains = (area, x, z) => areaSegments(area).some(segment => pointInPolygon(x, z, segment));
  const nearestHeight = (x, z) => {
    const i = Math.floor((x - terrainData.xOrigin) / cellSize);
    const j = Math.floor((z - terrainData.zOrigin) / cellSize);
    return heightAt(i, j);
  };
  const project = (x, z, y = baseY) => {
    const dx = x - camera.cx;
    const dz = z - camera.cz;
    const c = Math.cos(camera.yaw);
    const s = Math.sin(camera.yaw);
    const side = dx * c - dz * s;
    const depth = dx * s + dz * c;
    const scale = width / camera.viewWidth;
    return [width / 2 + side * scale, height / 2 + (depth * Math.sin(camera.pitch) - (y - baseY) * Math.cos(camera.pitch)) * scale];
  };
  const unproject = (sx, sy) => {
    const scale = width / camera.viewWidth;
    const side = (sx - width / 2) / scale;
    const depth = (sy - height / 2) / (scale * Math.sin(camera.pitch));
    const c = Math.cos(camera.yaw);
    const s = Math.sin(camera.yaw);
    return { x: camera.cx + side * c + depth * s, z: camera.cz - side * s + depth * c };
  };
  const viewBox = () => {
    const box = svg.viewBox.baseVal;
    return { x: box.x, y: box.y, width: box.width, height: box.height };
  };
  const setViewBox = () => {
    const aspect = width / Math.max(height, 1);
    const viewHeight = camera.viewWidth / Math.max(aspect, .35);
    const next = [camera.cx - camera.viewWidth / 2, camera.cz - viewHeight / 2, camera.viewWidth, viewHeight];
    const key = next.map(value => value.toFixed(2)).join(',');
    if (key === lastViewKey) return;
    lastViewKey = key;
    svg.setAttribute('viewBox', next.join(' '));
  };
  const syncFromSvg = () => {
    const box = viewBox();
    if (!box.width || !box.height) return;
    camera.cx = box.x + box.width / 2;
    camera.cz = box.y + box.height / 2;
    camera.viewWidth = clamp(box.width, 260, globalView[2]);
    lastViewKey = [box.x, box.y, box.width, box.height].map(value => Number(value).toFixed(2)).join(',');
    draw();
  };
  const materialColor = (material, y) => {
    const name = (legend[material] || '').replace('minecraft:', '');
    let color = '#477967';
    if (name.includes('water') || name.includes('ice') || name.includes('prismarine') || name.includes('coral') || name.includes('kelp') || name.includes('seagrass')) color = '#3c88a1';
    else if (name.includes('snow')) color = '#d5e5de';
    else if (name.includes('red_') || name.includes('crimson') || name.includes('nether') || name.includes('netherrack')) color = '#a95649';
    else if (name.includes('purple') || name.includes('purpur') || name.includes('amethyst') || name.includes('chorus')) color = '#9a72a9';
    else if (name.includes('sand') || name.includes('sandstone')) color = '#c5aa6b';
    else if (name.includes('leaves') || name.includes('moss') || name.includes('grass') || name.includes('azalea') || name.includes('vine') || name.includes('bamboo') || name.includes('fern') || name.includes('sapling')) color = '#4d8c65';
    else if (name.includes('wood') || name.includes('log') || name.includes('planks') || name.includes('shelf') || name.includes('bookshelf')) color = '#80654c';
    else if (name.includes('path') || name.includes('dirt') || name.includes('mud') || name.includes('farmland') || name.includes('root')) color = '#806b4a';
    else if (name.includes('gold') || name.includes('copper') || name.includes('raw_') || name.includes('iron') || name.includes('ore') || name.includes('diamond') || name.includes('emerald')) color = name.includes('gold') ? '#d5ae45' : name.includes('copper') ? '#bd7653' : '#8d9aa0';
    else if (name.includes('terracotta') || name.includes('concrete') || name.includes('wool') || name.includes('carpet')) color = name.includes('white') ? '#d5d8ca' : name.includes('black') ? '#2b3033' : name.includes('red') ? '#c95a52' : name.includes('orange') ? '#c87845' : name.includes('yellow') ? '#d6b54c' : name.includes('lime') ? '#75ad52' : name.includes('green') ? '#4f8b64' : name.includes('cyan') ? '#4296a1' : name.includes('light_blue') ? '#6da9c5' : name.includes('blue') ? '#4e79a4' : name.includes('purple') ? '#8b64a3' : name.includes('magenta') ? '#b15a9d' : name.includes('pink') ? '#d78c9d' : name.includes('gray') ? '#69777b' : name.includes('brown') ? '#8b6049' : '#9b6650';
    else if (name.includes('stone') || name.includes('deepslate') || name.includes('andesite') || name.includes('diorite') || name.includes('granite') || name.includes('tuff') || name.includes('cobble') || name.includes('brick') || name.includes('basalt') || name.includes('obsidian')) color = '#6e7d79';
    else {
      let hash = 0; for (let i = 0; i < name.length; i += 1) hash = ((hash << 5) - hash + name.charCodeAt(i)) | 0;
      color = ['#6f8e83', '#9a806c', '#6e8795', '#98745e'][Math.abs(hash) % 4];
    }
    const lift = clamp((y - baseY) / 180, -.16, .22);
    return color.replace(/^#(..)(..)(..)$/, (_, r, g, b) => `rgb(${clamp(parseInt(r, 16) * (1 + lift), 0, 255)},${clamp(parseInt(g, 16) * (1 + lift), 0, 255)},${clamp(parseInt(b, 16) * (1 + lift), 0, 255)})`);
  };
  const shade = (color, amount) => {
    const match = color.match(/rgb\(([^,]+),([^,]+),([^\)]+)\)/);
    if (!match) return color;
    return `rgb(${clamp(Number(match[1]) + amount, 0, 255)},${clamp(Number(match[2]) + amount, 0, 255)},${clamp(Number(match[3]) + amount, 0, 255)})`;
  };
  const quad = (points, fill, stroke = null) => {
    ctx.beginPath();
    points.forEach(([x, y], index) => index ? ctx.lineTo(x, y) : ctx.moveTo(x, y));
    ctx.closePath();
    ctx.fillStyle = fill;
    ctx.fill();
    if (stroke) { ctx.strokeStyle = stroke; ctx.stroke(); }
  };
  const floatingSideBottom = (_height, neighbour) => neighbour;
  const drawBorder = area => {
    const selected = area.id === selectedId;
    ctx.save();
    ctx.beginPath();
    areaSegments(area).forEach(segment => segment.forEach(([x, z], index) => {
      const point = project(x, z, nearestHeight(x, z) + 3);
      if (index === 0) ctx.moveTo(point[0], point[1]); else ctx.lineTo(point[0], point[1]);
      if (index === segment.length - 1) ctx.closePath();
    }));
    ctx.strokeStyle = selected ? '#fff0ad' : area.category === 'town' ? '#e8b767' : area.category === 'poi' ? '#ee8e70' : 'rgba(123,224,208,.78)';
    ctx.lineWidth = selected ? 3.6 : area.category === 'town' ? 2.2 : 1.35;
    ctx.setLineDash(area.category === 'poi' ? [8, 6] : []);
    ctx.shadowColor = selected ? 'rgba(232,183,103,.85)' : 'transparent';
    ctx.shadowBlur = selected ? 12 : 0;
    ctx.stroke();
    ctx.restore();
  };
  const drawLabel = area => {
    if (area.category === 'ocean' || area.id === '바르칸' || area.id === '원양' || ['카지노', '오아시스', '항구'].includes(area.id)) return;
    const [x, z] = center(area);
    const [sx, sy] = project(x, z, nearestHeight(x, z) + 14);
    const fontSize = area.category === 'town' ? 14 : 11;
    ctx.save();
    ctx.font = `${area.category === 'town' ? 800 : 600} ${fontSize}px Barkan, sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.lineWidth = 4;
    ctx.strokeStyle = 'rgba(2,15,17,.92)';
    ctx.strokeText(area.name, sx, sy);
    ctx.fillStyle = area.category === 'town' ? '#ffe3a1' : '#c8e5d9';
    ctx.fillText(area.name, sx, sy);
    ctx.restore();
  };
  const hitArea = (sx, sy) => {
    const point = unproject(sx, sy);
    return (mapData.areas || []).slice().reverse().find(area => Array.isArray(area.polygon) && area.polygon.length >= 3 && area.category !== 'ocean' && contains(area, point.x, point.z));
  };

  function draw() {
    const rect = plane.getBoundingClientRect();
    width = Math.max(1, plane.clientWidth || rect.width);
    height = Math.max(1, plane.clientHeight || rect.height);
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(height * ratio);
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    const background = ctx.createLinearGradient(0, 0, 0, height);
    background.addColorStop(0, '#103b42');
    background.addColorStop(1, '#04161a');
    ctx.fillStyle = background;
    ctx.fillRect(0, 0, width, height);

    const useFarLod = camera.viewWidth > 5600;
    // A focused town starts zoomed out. Keep that first paint light, then reveal
    // the real per-block scan as the player zooms in further.
    const fineStep = camera.viewWidth > 900 ? 8 : camera.viewWidth > 300 ? 4 : camera.viewWidth > 140 ? 2 : 1;
    const activeFine = fineLod(fineStep);
    const renderCells = useFarLod
      ? farCells
      : baseCells.filter(cell => !inDetailRegion(cell.x + cell.size / 2, cell.z + cell.size / 2))
        .concat(coarseCells.filter(cell => !inFineRegion(cell.x + cell.size / 2, cell.z + cell.size / 2)))
        .concat(activeFine.cells);
    const ordered = renderCells.filter(cell => {
      const [sx, sy] = project(cell.x + (cell.size || cellSize) / 2, cell.z + (cell.size || cellSize) / 2, cell.height);
      return sx > -140 && sx < width + 140 && sy > -260 && sy < height + 260;
    }).sort((a, b) => {
      const c = Math.cos(camera.yaw); const s = Math.sin(camera.yaw);
      return ((a.x - camera.cx) * s + (a.z - camera.cz) * c) - ((b.x - camera.cx) * s + (b.z - camera.cz) * c);
    });
    ordered.forEach(cell => {
      const x = cell.x; const z = cell.z; const h = cell.height; const size = cell.size || cellSize;
      const top = [project(x, z, h), project(x + size, z, h), project(x + size, z + size, h), project(x, z + size, h)];
      const color = materialColor(cell.material, h);
      const neighbourMap = cell.fine ? activeFine.columnMap : null;
      const eastCell = neighbourMap?.get(`${x + size},${z}`);
      const southCell = neighbourMap?.get(`${x},${z + size}`);
      const legacyEast = cell.detail && !cell.fine ? detailHeightMap.get(`${x + size},${z}`) : undefined;
      const legacySouth = cell.detail && !cell.fine ? detailHeightMap.get(`${x},${z + size}`) : undefined;
      const east = cell.detail ? (eastCell?.height ?? legacyEast ?? baseY) : heightAt(cell.i + 1, cell.j);
      const south = cell.detail ? (southCell?.height ?? legacySouth ?? baseY) : heightAt(cell.i, cell.j + 1);
      const ownBottom = cell.bottom ?? baseY;
      const eastBottom = cell.fine ? Math.max(ownBottom, eastCell?.height ?? ownBottom) : floatingSideBottom(h, east, cell.material);
      const southBottom = cell.fine ? Math.max(ownBottom, southCell?.height ?? ownBottom) : floatingSideBottom(h, south, cell.material);
      if (eastBottom < h - 1) quad([top[1], top[2], project(x + size, z + size, eastBottom), project(x + size, z, eastBottom)], shade(color, -42));
      if (southBottom < h - 1) quad([top[3], top[2], project(x + size, z + size, southBottom), project(x, z + size, southBottom)], shade(color, -26));
      quad(top, color, cell.size >= 8 ? 'rgba(4,20,21,.14)' : null);
    });

    const hiddenAreas = new Set([...document.querySelectorAll('.area[hidden]')].map(item => item.dataset.id));
    const areas = (mapData.areas || []).filter(area => !hiddenAreas.has(area.id) && Array.isArray(area.polygon) && area.polygon.length >= 3 && area.category !== 'ocean');
    areas.forEach(drawBorder);
    areas.filter(area => area.category === 'town' || area.category === 'poi').forEach(drawLabel);
  }

  const resizeObserver = new ResizeObserver(draw);
  resizeObserver.observe(plane);
  const viewObserver = new MutationObserver(syncFromSvg);
  viewObserver.observe(svg, { attributes: true, attributeFilter: ['viewBox'] });
  window.addEventListener('resize', draw, { passive: true });
  window.addEventListener('barkan-map-state', event => { selectedId = event.detail?.id || ''; loadFineTown(selectedId); draw(); });
  window.addEventListener('barkan-map-filter', draw);

  viewport.addEventListener('contextmenu', event => event.preventDefault());
  viewport.addEventListener('pointerdown', event => {
    if (![0, 2].includes(event.button) || event.target.closest('button, a')) return;
    dragging = { x: event.clientX, y: event.clientY, cx: camera.cx, cz: camera.cz, yaw: camera.yaw, pitch: camera.pitch, orbit: event.button === 2 || event.shiftKey || event.altKey };
    moved = false;
    viewport.classList.add('is-dragging');
    viewport.setPointerCapture(event.pointerId);
  });
  viewport.addEventListener('pointermove', event => {
    if (!dragging) {
      const rect = canvas.getBoundingClientRect();
      const area = hitArea(event.clientX - rect.left, event.clientY - rect.top);
      if (area) window.dispatchEvent(new CustomEvent('barkan-map-preview', { detail: { id: area.id } }));
      return;
    }
    const dx = event.clientX - dragging.x;
    const dy = event.clientY - dragging.y;
    if (Math.abs(dx) + Math.abs(dy) > 5) moved = true;
    if (dragging.orbit) {
      camera.yaw = dragging.yaw + dx * .008;
      camera.pitch = clamp(dragging.pitch - dy * .006, .48, 1.28);
    } else {
      const scale = width / camera.viewWidth;
      const side = -dx / scale;
      const depth = -dy / (scale * Math.sin(camera.pitch));
      const c = Math.cos(camera.yaw); const s = Math.sin(camera.yaw);
      camera.cx = dragging.cx + side * c + depth * s;
      camera.cz = dragging.cz - side * s + depth * c;
    }
    setViewBox();
    draw();
    event.preventDefault();
  });
  const endDrag = event => {
    if (!dragging) return;
    dragging = null;
    viewport.classList.remove('is-dragging');
    if (event && viewport.hasPointerCapture(event.pointerId)) viewport.releasePointerCapture(event.pointerId);
  };
  viewport.addEventListener('pointerup', event => {
    if (dragging && !moved) {
      const rect = canvas.getBoundingClientRect();
      const area = hitArea(event.clientX - rect.left, event.clientY - rect.top);
      if (area) window.dispatchEvent(new CustomEvent('barkan-map-select', { detail: { id: area.id } }));
    }
    endDrag(event);
  });
  viewport.addEventListener('pointercancel', endDrag);
  viewport.addEventListener('wheel', event => {
    event.preventDefault();
    const rect = canvas.getBoundingClientRect();
    const before = unproject(event.clientX - rect.left, event.clientY - rect.top);
    camera.viewWidth = clamp(camera.viewWidth * (event.deltaY > 0 ? 1.18 : .84), 260, globalView[2]);
    const after = unproject(event.clientX - rect.left, event.clientY - rect.top);
    camera.cx += before.x - after.x;
    camera.cz += before.z - after.z;
    setViewBox();
    draw();
  }, { passive: false });

  document.querySelectorAll('[data-rotate]').forEach(button => button.addEventListener('click', () => {
    camera.yaw += button.dataset.rotate === 'left' ? -.55 : .55;
    draw();
  }));
  document.querySelectorAll('[data-pitch]').forEach(button => button.addEventListener('click', () => {
    camera.pitch = clamp(camera.pitch + (button.dataset.pitch === 'up' ? .1 : -.1), .42, 1.36);
    draw();
  }));
  document.querySelectorAll('[data-zoom]').forEach(button => button.addEventListener('click', () => {
    if (button.dataset.zoom === 'reset') {
      camera.cx = 0; camera.cz = 0; camera.viewWidth = globalView[2]; camera.yaw = -.34; camera.pitch = .9;
    } else camera.viewWidth = clamp(camera.viewWidth * (button.dataset.zoom === 'in' ? .72 : 1.38), 260, globalView[2]);
    setViewBox();
    draw();
  }));
  document.querySelector('#reset-map')?.addEventListener('click', () => {
    camera.cx = 0; camera.cz = 0; camera.viewWidth = globalView[2]; camera.yaw = -.34; camera.pitch = .9;
    setViewBox();
    draw();
  });
  syncFromSvg();
})();
