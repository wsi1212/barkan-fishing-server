(() => {
  const canvas = document.querySelector('#voxel-map');
  const svg = document.querySelector('#map-svg');
  const viewport = document.querySelector('#map-viewport');
  const plane = document.querySelector('.map-plane');
  const data = window.BARKAN_MAP_DATA;
  if (!canvas || !svg || !viewport || !plane || !data) return;

  const ctx = canvas.getContext('2d', { alpha: false });
  // 리소스팩의 barkan:worldmap painting 원본. 웹에서 새로 그린 가짜 섬이 아니라
  // 실제 서버 월드 탑뷰를 그대로 바닥 텍스처로 쓴다.
  const worldTexture = new Image();
  worldTexture.decoding = 'async';
  worldTexture.src = '/assets/worldmap.png?v=1';
  const textureWorldBounds = { x: -1500, z: -1320, width: 3000, height: 3000 };
  const globalView = [-5200, -5200, 10400, 10400];
  const areas = (data.areas || []).filter(area => Array.isArray(area.polygon) && area.polygon.length >= 3);
  const areaById = new Map(areas.map(area => [area.id, area]));
  const outerOcean = areaById.get('원양');
  if (outerOcean) {
    outerOcean.bounds = [-5000, 5000, -5000, 5000];
    outerOcean.polygon = [[-5000, -5000], [5000, -5000], [5000, 5000], [-5000, 5000]];
    outerOcean.parent = null;
    delete outerOcean.polygonBreaks;
  }
  const land = areaById.get('바르칸');
  const oceans = areas.filter(area => area.category === 'ocean' && area.id !== '원양');
  const terrainAreas = areas.filter(area => area.category === 'region' && area.id !== '바르칸');
  const settlements = areas.filter(area => area.category === 'town' || area.category === 'poi');
  const dpr = () => Math.min(window.devicePixelRatio || 1, 2);
  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
  const hash = (x, z) => {
    let n = Math.imul((x | 0) ^ 0x45d9f3b, 0x27d4eb2d) ^ Math.imul((z | 0) ^ 0x165667b1, 0x85ebca6b);
    n = (n ^ (n >>> 15)) * 0x2c1b3c6d;
    n ^= n >>> 12;
    return (n >>> 0) / 4294967295;
  };
  const segments = area => {
    const cuts = [0, ...(area.polygonBreaks || []), area.polygon.length];
    return cuts.slice(0, -1).map((start, i) => area.polygon.slice(start, cuts[i + 1]));
  };
  const pointInPolygon = (x, z, polygon) => {
    let inside = false;
    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
      const [xi, zi] = polygon[i];
      const [xj, zj] = polygon[j];
      const intersects = ((zi > z) !== (zj > z)) && x < (xj - xi) * (z - zi) / ((zj - zi) || 1e-9) + xi;
      if (intersects) inside = !inside;
    }
    return inside;
  };
  const contains = (area, x, z) => segments(area).some(polygon => pointInPolygon(x, z, polygon));
  const polygonArea = polygon => Math.abs(polygon.reduce((sum, point, i) => {
    const next = polygon[(i + 1) % polygon.length];
    return sum + point[0] * next[1] - next[0] * point[1];
  }, 0) / 2);
  const terrainOrder = terrainAreas.slice().sort((a, b) => polygonArea(a.polygon) - polygonArea(b.polygon));
  const palettes = {
    사막: ['#a88a52', '#b99a5c', '#d0b976', '#816940'],
    붉은사막: ['#9a5a44', '#b56e4e', '#d08a5b', '#714234'],
    늪지대: ['#365b4c', '#456b50', '#5c7950', '#29443d'],
    강: ['#3e8b82', '#4fa096', '#76b9a6', '#2c655f'],
    강_상류: ['#507e6b', '#659779', '#88ae86', '#355d53'],
    정상: ['#aab9aa', '#ccd6c5', '#e8eee0', '#7c9189'],
    깊은_숲: ['#28584c', '#346b54', '#4d815d', '#1d413d'],
    대수림: ['#214e45', '#2c604b', '#437454', '#193b38'],
    설산: ['#a5c5c5', '#c9dfd7', '#eef4e5', '#789b9d'],
    default: ['#3b6f5d', '#4b8066', '#67906d', '#2b514a']
  };
  const waterPalette = [
    ['#145667', '#1b6d76', '#248991', '#0b3a49'],
    ['#104a5b', '#176275', '#207c88', '#092f40'],
    ['#175f6b', '#217a80', '#32999a', '#0d4351'],
    ['#0e4154', '#15566a', '#1c6f7f', '#082f40']
  ];
  const colorForTerrain = area => area ? (palettes[area.id] || palettes.default) : palettes.default;
  const viewBox = () => {
    const value = svg.viewBox.baseVal;
    return { x: value.x, y: value.y, width: value.width, height: value.height };
  };

  function worldToScreen(x, z, view, width, height) {
    return [(x - view.x) / view.width * width, (z - view.y) / view.height * height];
  }

  function drawVoxel(ctx2, x, y, size, colors, depth, tint = 0) {
    const side = Math.max(3, size * (0.22 + depth * 0.08));
    const shade = colors[(tint + 1) % colors.length];
    const dark = colors[(tint + 3) % colors.length];
    ctx2.fillStyle = dark;
    ctx2.fillRect(x + size - side, y + side, side, size - side);
    ctx2.fillStyle = shade;
    ctx2.fillRect(x + side, y + size - side, size - side, side);
    ctx2.fillStyle = colors[tint % colors.length];
    ctx2.fillRect(x, y, size - side, size - side);
    ctx2.fillStyle = 'rgba(238,255,238,.16)';
    ctx2.fillRect(x, y, size - side, Math.max(1, side * .52));
    ctx2.strokeStyle = 'rgba(2,20,23,.28)';
    ctx2.lineWidth = Math.max(.45, size * .035);
    ctx2.strokeRect(x + .25, y + .25, size - side - .5, size - side - .5);
  }

  function trace(ctx2, area, view, width, height) {
    segments(area).forEach(polygon => {
      polygon.forEach(([x, z], i) => {
        const [sx, sy] = worldToScreen(x, z, view, width, height);
        if (i === 0) ctx2.moveTo(sx, sy); else ctx2.lineTo(sx, sy);
      });
      ctx2.closePath();
    });
  }

  function draw() {
    const rect = plane.getBoundingClientRect();
    const pixelRatio = dpr();
    // getBoundingClientRect()에는 부모의 3D 원근 변환이 포함되므로,
    // 캔버스 좌표는 변환 전의 실제 map-plane 크기를 기준으로 잡는다.
    const width = Math.max(1, plane.clientWidth || rect.width);
    const height = Math.max(1, plane.clientHeight || rect.height);
    canvas.width = Math.round(width * pixelRatio);
    canvas.height = Math.round(height * pixelRatio);
    ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
    const view = viewBox();
    const cellWorld = clamp(view.width / 142, 42, 88);
    const cellWidth = view.width ? width * cellWorld / view.width : 8;
    const cellHeight = view.height ? height * cellWorld / view.height : 8;
    const textureReady = worldTexture.complete && worldTexture.naturalWidth > 0;
    ctx.fillStyle = textureReady ? '#4a7caa' : '#082b35';
    ctx.fillRect(0, 0, width, height);

    const startX = Math.floor(view.x / cellWorld) * cellWorld;
    const startZ = Math.floor(view.y / cellWorld) * cellWorld;
    if (!textureReady) {
      // 원본 텍스처가 늦게 도착할 때만 복셀 수심 폴백을 그린다.
      for (let x = startX; x <= view.x + view.width; x += cellWorld) {
        for (let z = startZ; z <= view.y + view.height; z += cellWorld) {
          const [sx, sy] = worldToScreen(x, z, view, width, height);
          const water = waterPalette[Math.floor(hash(x / cellWorld, z / cellWorld) * waterPalette.length) % waterPalette.length];
          const variant = Math.floor(hash(x / cellWorld + 17, z / cellWorld - 3) * water.length);
          drawVoxel(ctx, sx, sy, Math.max(cellWidth, cellHeight) + .7, water, 1 + variant % 3, variant % water.length);
        }
      }
    } else {
      const [imageX, imageY] = worldToScreen(textureWorldBounds.x, textureWorldBounds.z, view, width, height);
      const [imageRight, imageBottom] = worldToScreen(textureWorldBounds.x + textureWorldBounds.width, textureWorldBounds.z + textureWorldBounds.height, view, width, height);
      ctx.imageSmoothingEnabled = true;
      ctx.drawImage(worldTexture, imageX, imageY, imageRight - imageX, imageBottom - imageY);
    }

    // 서버의 대양 띠는 실제 폴리곤으로 표시하고, 원양은 바탕 수심으로 남긴다.
    oceans.forEach(area => {
      ctx.save();
      ctx.beginPath();
      trace(ctx, area, view, width, height);
      ctx.fillStyle = area.id === '대양' ? 'rgba(40,126,145,.13)' : 'rgba(31,99,123,.08)';
      ctx.fill();
      ctx.strokeStyle = 'rgba(132,211,232,.28)';
      ctx.lineWidth = Math.max(1, width / view.width * 9);
      ctx.setLineDash([cellWidth * .9, cellWidth * .7]);
      ctx.stroke();
      ctx.restore();
    });

    // 바르칸 본섬 안의 각 권역을 측정된 경계에 맞춰 블록으로 채운다.
    if (land && !textureReady) {
      // 셀 경계 바깥의 아주 작은 섬 끝도 빈 화면으로 끊기지 않도록
      // 실측 본섬 폴리곤을 먼저 칠하고, 그 위에 블록을 쌓는다.
      ctx.save();
      ctx.beginPath();
      trace(ctx, land, view, width, height);
      ctx.fillStyle = '#3c725b';
      ctx.fill();
      ctx.restore();
      for (let x = startX; x <= view.x + view.width; x += cellWorld) {
        for (let z = startZ; z <= view.y + view.height; z += cellWorld) {
          const cx = x + cellWorld * .5;
          const cz = z + cellWorld * .5;
          if (!contains(land, cx, cz)) continue;
          const terrain = terrainOrder.find(area => contains(area, cx, cz));
          const colors = colorForTerrain(terrain);
          const variant = Math.floor(hash(x / cellWorld + 71, z / cellWorld + 31) * colors.length) % colors.length;
          const [sx, sy] = worldToScreen(x, z, view, width, height);
          const jitter = (hash(x / cellWorld, z / cellWorld) - .5) * Math.min(cellWidth, cellHeight) * .14;
          drawVoxel(ctx, sx + jitter, sy + jitter, Math.max(cellWidth, cellHeight) + .7, colors, 2 + variant, variant);
        }
      }
      ctx.save();
      ctx.beginPath();
      trace(ctx, land, view, width, height);
      ctx.strokeStyle = '#d5bd76';
      ctx.lineWidth = Math.max(1.3, width / view.width * 16);
      ctx.shadowColor = 'rgba(0,0,0,.4)';
      ctx.shadowBlur = 9;
      ctx.stroke();
      ctx.restore();
    }
    if (land && textureReady) {
      ctx.save();
      ctx.beginPath();
      trace(ctx, land, view, width, height);
      ctx.strokeStyle = 'rgba(235,225,167,.88)';
      ctx.lineWidth = Math.max(1.5, width / view.width * 12);
      ctx.shadowColor = 'rgba(14,28,30,.55)';
      ctx.shadowBlur = 8;
      ctx.stroke();
      ctx.restore();
    }

    // 마을·항구·기능 지점은 지형 타일 위에 실제 지도 기호처럼 별도 색으로 얹는다.
    settlements.forEach(area => {
      ctx.save();
      ctx.beginPath();
      trace(ctx, area, view, width, height);
      ctx.fillStyle = area.category === 'town' ? 'rgba(220,166,75,.82)' : 'rgba(220,110,85,.78)';
      ctx.strokeStyle = area.category === 'town' ? '#f4d38a' : '#f1a08b';
      ctx.lineWidth = Math.max(1.2, width / view.width * 10);
      ctx.shadowColor = 'rgba(2,16,18,.55)';
      ctx.shadowBlur = 7;
      ctx.fill();
      ctx.stroke();
      const [minX, maxX, minZ, maxZ] = area.bounds;
      const [sx, sy] = worldToScreen((minX + maxX) / 2, (minZ + maxZ) / 2, view, width, height);
      const iconSize = clamp(Math.min(width, height) * .012, 4, 11);
      ctx.fillStyle = area.category === 'town' ? '#fff0bd' : '#ffe0d3';
      ctx.fillRect(sx - iconSize * .5, sy - iconSize * .5, iconSize, iconSize);
      ctx.restore();
    });

    // 지형 경계는 블록 위에 얇은 등고선처럼 남긴다.
    terrainAreas.forEach(area => {
      ctx.save();
      ctx.beginPath();
      trace(ctx, area, view, width, height);
      ctx.strokeStyle = 'rgba(226,244,211,.23)';
      ctx.lineWidth = Math.max(.7, width / view.width * 5);
      ctx.setLineDash([cellWidth * .35, cellWidth * .8]);
      ctx.stroke();
      ctx.restore();
    });

    // 종이 지도 같은 좌표 십자와 외곽 가장자리를 살짝 남긴다.
    ctx.strokeStyle = 'rgba(204,236,215,.16)';
    ctx.lineWidth = 1;
    const gridStep = view.width > 1800 ? 500 : view.width > 800 ? 250 : 100;
    for (let x = Math.ceil(view.x / gridStep) * gridStep; x < view.x + view.width; x += gridStep) {
      const [sx] = worldToScreen(x, 0, view, width, height);
      ctx.beginPath(); ctx.moveTo(sx, 0); ctx.lineTo(sx, height); ctx.stroke();
    }
    for (let z = Math.ceil(view.y / gridStep) * gridStep; z < view.y + view.height; z += gridStep) {
      const [, sy] = worldToScreen(0, z, view, width, height);
      ctx.beginPath(); ctx.moveTo(0, sy); ctx.lineTo(width, sy); ctx.stroke();
    }
  }

  const resizeObserver = new ResizeObserver(draw);
  resizeObserver.observe(plane);
  const viewObserver = new MutationObserver(draw);
  viewObserver.observe(svg, { attributes: true, attributeFilter: ['viewBox'] });
  window.addEventListener('resize', draw, { passive: true });
  worldTexture.addEventListener('load', draw, { once: true });
  draw();

  // 지도를 잡아당기면 복셀 지형의 원근만 살짝 바뀌어 3D 모델처럼 확인할 수 있다.
  let drag = null;
  let suppressClick = false;
  viewport.addEventListener('pointerdown', event => {
    // 영역 위에서 시작해도 클릭은 그대로 선택되고, 움직였을 때만 회전한다.
    if (event.button !== 0 || event.target.closest('button, a')) return;
    drag = { x: event.clientX, y: event.clientY, rx: parseFloat(getComputedStyle(plane).getPropertyValue('--rx')) || 42, rz: parseFloat(getComputedStyle(plane).getPropertyValue('--rz')) || -7, moved: false };
    viewport.classList.add('is-dragging');
    viewport.setPointerCapture(event.pointerId);
  });
  viewport.addEventListener('pointermove', event => {
    if (!drag) return;
    event.preventDefault();
    const dx = event.clientX - drag.x;
    const dy = event.clientY - drag.y;
    if (Math.abs(dx) + Math.abs(dy) > 6) drag.moved = true;
    plane.style.setProperty('--rx', `${clamp(drag.rx - dy * .12, 24, 72)}deg`);
    // 수평 드래그는 한 번에 최대 한 바퀴까지 회전하는 지도 앱 방식.
    plane.style.setProperty('--rz', `${clamp(drag.rz + dx * .34, -360, 360)}deg`);
  });
  const endDrag = event => {
    if (!drag) return;
    if (drag.moved) {
      suppressClick = true;
      window.setTimeout(() => { suppressClick = false; }, 80);
    }
    drag = null;
    viewport.classList.remove('is-dragging');
    if (event && viewport.hasPointerCapture(event.pointerId)) viewport.releasePointerCapture(event.pointerId);
  };
  viewport.addEventListener('pointerup', endDrag);
  viewport.addEventListener('pointercancel', endDrag);
  viewport.addEventListener('click', event => {
    if (!suppressClick) return;
    event.preventDefault();
    event.stopPropagation();
  }, true);
  document.querySelector('#reset-map')?.addEventListener('click', () => {
    plane.style.setProperty('--rx', '42deg');
    plane.style.setProperty('--rz', '-7deg');
  });
  document.querySelectorAll('[data-rotate]').forEach(button => button.addEventListener('click', () => {
    const current = parseFloat(getComputedStyle(plane).getPropertyValue('--rz')) || -7;
    const amount = button.dataset.rotate === 'left' ? -45 : 45;
    plane.style.setProperty('--rz', `${clamp(current + amount, -360, 360)}deg`);
  }));
})();
