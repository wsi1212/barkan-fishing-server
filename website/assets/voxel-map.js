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
  const gridWidth = terrainData.gridWidth;
  const gridDepth = terrainData.gridDepth;
  const cellSize = terrainData.cellSize;
  const baseY = 60;
  const globalView = [-5200, -5200, 10400, 10400];
  const legend = terrainData.legend || [];
  const cells = [];
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
      if (!maskBytes[index] || (materialBytes[index] === 0 && height <= baseY)) continue;
      cells.push({ i, j, x: terrainData.xOrigin + i * cellSize, z: terrainData.zOrigin + j * cellSize, height, material: materialBytes[index] });
    }
  }

  const camera = { cx: 0, cz: 0, viewWidth: globalView[2], yaw: -0.34, pitch: 0.9 };
  let selectedId = '';
  let width = 1;
  let height = 1;
  let dragging = null;
  let moved = false;
  let lastViewKey = '';

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
    if (name.includes('water') || name.includes('ice')) color = '#3c88a1';
    else if (name.includes('sand') || name.includes('sandstone')) color = '#c5aa6b';
    else if (name.includes('snow')) color = '#d5e5de';
    else if (name.includes('leaves') || name.includes('moss') || name.includes('grass') || name.includes('azalea')) color = '#4d8c65';
    else if (name.includes('wood') || name.includes('log') || name.includes('planks')) color = '#80654c';
    else if (name.includes('terracotta') || name.includes('concrete')) color = '#9b6650';
    else if (name.includes('stone') || name.includes('deepslate') || name.includes('andesite') || name.includes('tuff')) color = '#6e7d79';
    else if (name.includes('path') || name.includes('dirt') || name.includes('mud')) color = '#806b4a';
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

    const ordered = cells.slice().sort((a, b) => {
      const c = Math.cos(camera.yaw); const s = Math.sin(camera.yaw);
      return ((a.x - camera.cx) * s + (a.z - camera.cz) * c) - ((b.x - camera.cx) * s + (b.z - camera.cz) * c);
    });
    ordered.forEach(cell => {
      const x = cell.x; const z = cell.z; const h = cell.height;
      const top = [project(x, z, h), project(x + cellSize, z, h), project(x + cellSize, z + cellSize, h), project(x, z + cellSize, h)];
      const color = materialColor(cell.material, h);
      const east = heightAt(cell.i + 1, cell.j);
      const south = heightAt(cell.i, cell.j + 1);
      if (east < h - 1) quad([top[1], top[2], project(x + cellSize, z + cellSize, east), project(x + cellSize, z, east)], shade(color, -42));
      if (south < h - 1) quad([top[3], top[2], project(x + cellSize, z + cellSize, south), project(x, z + cellSize, south)], shade(color, -26));
      quad(top, color, 'rgba(4,20,21,.14)');
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
  window.addEventListener('barkan-map-state', event => { selectedId = event.detail?.id || ''; draw(); });
  window.addEventListener('barkan-map-filter', draw);

  viewport.addEventListener('contextmenu', event => event.preventDefault());
  viewport.addEventListener('pointerdown', event => {
    if (event.button !== 0 || event.target.closest('button, a')) return;
    dragging = { x: event.clientX, y: event.clientY, cx: camera.cx, cz: camera.cz, yaw: camera.yaw, pitch: camera.pitch, orbit: event.shiftKey || event.altKey };
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
