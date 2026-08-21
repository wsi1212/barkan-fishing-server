/* Barkan voxel map v2
 *
 * The previous renderer projected one height per column onto a 2D canvas. This
 * renderer consumes the actual runs8 scan and draws real instanced WebGL boxes:
 * every contiguous vertical material run keeps its own height, position and
 * color. There are no canvas shadows or fake side faces.
 */
(() => {
  const canvas = document.querySelector('#voxel-map');
  const viewport = document.querySelector('#map-viewport');
  const plane = document.querySelector('.map-plane');
  const terrain = window.BARKAN_TERRAIN_DATA;
  const mapData = window.BARKAN_MAP_DATA;
  if (!canvas || !viewport || !plane || !terrain || !mapData || !window.THREE || !window.THREE.OrbitControls) return;

  const THREE = window.THREE;
  const status = document.querySelector('#map-status');
  const decode = value => {
    const raw = atob(value || '');
    const bytes = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i += 1) bytes[i] = raw.charCodeAt(i);
    return bytes;
  };
  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
  const legend = terrain.legend || [];
  const baseY = 60;
  const townSlugs = { '사막마을': 'desert-town', '스폰도시': 'spawn-city', '상단마을': 'upper-town', '왕도': 'royal-city', '항구': 'harbor' };
  const townAreas = new Map((mapData.areas || []).map(area => [area.id, area]));
  const detailRegions = terrain.detailRegions || [];
  const detailRegionFor = id => {
    const area = townAreas.get(id);
    return area ? { x1: area.bounds[0], x2: area.bounds[1], z1: area.bounds[2], z2: area.bounds[3] } : null;
  };
  const inRegion = (x, z, region) => region && x >= region.x1 && x <= region.x2 && z >= region.z1 && z <= region.z2;

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setClearColor(0x061517, 1);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(42, 1, 1, 40000);
  camera.near = 0.1;
  camera.updateProjectionMatrix();
  const controls = new THREE.OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.screenSpacePanning = true;
  controls.minDistance = 110;
  controls.maxDistance = 22000;
  controls.maxPolarAngle = Math.PI * 0.49;
  controls.minPolarAngle = 0.12;

  const world = new THREE.Group();
  const voxelGroup = new THREE.Group();
  const borderGroup = new THREE.Group();
  world.add(voxelGroup, borderGroup);
  scene.add(world);
  // No synthetic ocean plane: water must come from the scanned Minecraft
  // blocks too, otherwise maximum zoom shows a fake flat blue sheet.
  scene.add(new THREE.HemisphereLight(0xb8e7db, 0x11272b, 1.18));
  const fillLight = new THREE.DirectionalLight(0xffedc3, 0.42);
  fillLight.position.set(420, 900, 260);
  scene.add(fillLight);

  const materialCache = new Map();
  const rgb = hex => new THREE.Color(hex);
  const blockColor = nameRaw => {
    const name = String(nameRaw || '').replace('minecraft:', '');
    if (!name) return '#477967';
    if (/terracotta|concrete|wool|carpet/.test(name)) {
      if (name.includes('white')) return '#d5d8ca';
      if (name.includes('light_gray')) return '#a9b3af';
      if (name.includes('gray')) return '#69777b';
      if (name.includes('black')) return '#2b3033';
      if (name.includes('red')) return '#c95a52';
      if (name.includes('orange')) return '#c87845';
      if (name.includes('yellow')) return '#d6b54c';
      if (name.includes('lime')) return '#75ad52';
      if (name.includes('green')) return '#4f8b64';
      if (name.includes('cyan')) return '#4296a1';
      if (name.includes('light_blue')) return '#6da9c5';
      if (name.includes('blue')) return '#4e79a4';
      if (name.includes('purple')) return '#8b64a3';
      if (name.includes('magenta')) return '#b15a9d';
      if (name.includes('pink')) return '#d78c9d';
      if (name.includes('brown')) return '#8b6049';
      return '#9b6650';
    }
    if (/water|ice|prismarine|coral|kelp|seagrass/.test(name)) return '#3c88a1';
    if (name.includes('snow')) return '#d5e5de';
    if (/red_|crimson|nether|netherrack/.test(name)) return '#a95649';
    if (/purple|purpur|amethyst|chorus/.test(name)) return '#9a72a9';
    if (/sand|sandstone/.test(name)) return '#c5aa6b';
    if (/leaves|moss|grass|azalea|vine|bamboo|fern|sapling/.test(name)) {
      if (name.includes('birch')) return '#74a96f';
      if (name.includes('jungle')) return '#3f8b5f';
      if (name.includes('spruce')) return '#47785c';
      if (name.includes('dark_oak')) return '#3f7658';
      return '#4d9868';
    }
    if (name.includes('birch')) return '#b9a874';
    if (name.includes('spruce')) return '#705641';
    if (name.includes('dark_oak')) return '#5d4333';
    if (name.includes('jungle')) return '#9c704f';
    if (name.includes('acacia')) return '#a96f4d';
    if (name.includes('mangrove')) return '#95504a';
    if (/wood|log|planks|shelf|bookshelf|fence|gate|trapdoor/.test(name)) return '#96704d';
    if (/path|dirt|mud|farmland|root/.test(name)) return '#806b4a';
    if (name.includes('gold') || name.includes('hay_block')) return '#d5ae45';
    if (name.includes('copper')) return '#bd7653';
    if (/raw_|iron|ore|diamond|emerald/.test(name)) return '#8d9aa0';
    if (/glass|quartz/.test(name)) return '#c5d3ce';
    if (/gravel|clay/.test(name)) return '#8f8a7c';
    if (name.includes('cactus')) return '#4d8c65';
    if (name.includes('pumpkin')) return '#c8893f';
    if (name.includes('stone_brick')) return '#7c827d';
    if (name.includes('brick')) return '#a36858';
    if (name.includes('diorite')) return '#b3b8af';
    if (name.includes('granite')) return '#a47c68';
    if (name.includes('andesite')) return '#7f8c8b';
    if (name.includes('deepslate')) return '#536267';
    if (name.includes('tuff')) return '#878b7e';
    if (name.includes('cobble')) return '#747b77';
    if (name.includes('basalt')) return '#5f686a';
    if (name.includes('obsidian')) return '#34324c';
    if (/stone/.test(name)) return '#858b87';
    let hash = 0;
    for (let i = 0; i < name.length; i += 1) hash = ((hash << 5) - hash + name.charCodeAt(i)) | 0;
    return ['#6f8e83', '#9a806c', '#6e8795', '#98745e'][Math.abs(hash) % 4];
  };
  const materialFor = name => {
    const key = String(name || '');
    // BoxGeometry is already faceted; keep the Lambert material warning-free on r128.
    if (!materialCache.has(key)) materialCache.set(key, new THREE.MeshLambertMaterial({ color: rgb(blockColor(key)) }));
    return materialCache.get(key);
  };

  const clearGroup = group => { while (group.children.length) group.remove(group.children[group.children.length - 1]); };
  const addRecord = (groups, materialName, x, y, z, sx, sy, sz) => {
    const key = materialName || 'minecraft:stone';
    let list = groups.get(key);
    if (!list) { list = []; groups.set(key, list); }
    list.push({ x, y, z, sx, sy, sz });
  };
  const buildMeshes = (groups, target) => {
    const geometry = new THREE.BoxGeometry(1, 1, 1);
    const matrix = new THREE.Matrix4();
    groups.forEach((records, materialName) => {
      // Splitting prevents a single giant instance buffer on large towns.
      for (let start = 0; start < records.length; start += 50000) {
        const chunk = records.slice(start, start + 50000);
        const mesh = new THREE.InstancedMesh(geometry, materialFor(materialName), chunk.length);
        mesh.instanceMatrix.setUsage(THREE.StaticDrawUsage);
        chunk.forEach((record, index) => {
          matrix.makeScale(record.sx, record.sy, record.sz);
          matrix.setPosition(record.x, record.y, record.z);
          mesh.setMatrixAt(index, matrix);
        });
        mesh.instanceMatrix.needsUpdate = true;
        target.add(mesh);
      }
    });
  };

  const buildOverview = (excludeId = '') => {
    const groups = new Map();
    const materials = decode(terrain.materials);
    const mask = decode(terrain.mask);
    const heights = decode(terrain.heights);
    const cellSize = Number(terrain.cellSize) || 8;
    const width = Number(terrain.gridWidth) || 0;
    const depth = Number(terrain.gridDepth) || 0;
    const excludedArea = townAreas.get(excludeId);
    const excludedBounds = excludedArea ? excludedArea.bounds : null;
    const excludedMargin = 48;
    for (let j = 0; j < depth; j += 1) {
      for (let i = 0; i < width; i += 1) {
        const index = j * width + i;
        if (!mask[index]) continue;
        const height = (heights[index * 2] | (heights[index * 2 + 1] << 8)) - 128;
        if (height <= baseY) continue;
        const x = Number(terrain.xOrigin) + i * cellSize;
        const z = Number(terrain.zOrigin) + j * cellSize;
        if (detailRegions.some(region => inRegion(x + cellSize / 2, z + cellSize / 2, region))) continue;
        if (excludedBounds) {
          const cx = x + cellSize / 2; const cz = z + cellSize / 2;
          if (cx >= excludedBounds[0] - excludedMargin && cx <= excludedBounds[1] + excludedMargin && cz >= excludedBounds[2] - excludedMargin && cz <= excludedBounds[3] + excludedMargin) continue;
        }
        const sy = Math.max(1, height - baseY);
        addRecord(groups, legend[materials[index]] || 'minecraft:grass_block', x + cellSize / 2, baseY + sy / 2, z + cellSize / 2, cellSize, sy, cellSize);
      }
    }
    buildMeshes(groups, voxelGroup);
  };

  const buildDetail = payload => {
    const groups = new Map();
    const bytes = decode(payload.details);
    const localLegend = payload.legend || [];
    const originX = Number(payload.xOrigin) || 0;
    const originZ = Number(payload.zOrigin) || 0;
    const originY = Number(payload.yOrigin) || 0;
    const floor = Number(payload.surfaceFloor ?? 60);
    // One instance represents one scanned block run at its real X/Z cell.
    // We merge only identical runs; air gaps and material changes remain visible.
    const lod = 1;
    const merged = new Map();
    for (let i = 0; i < Number(payload.count || 0); i += 1) {
      const offset = i * 8;
      const rawX = originX + ((bytes[offset] << 8) | bytes[offset + 1]);
      const rawZ = originZ + ((bytes[offset + 2] << 8) | bytes[offset + 3]);
      const rawY = originY + bytes[offset + 4];
      const length = Math.max(1, bytes[offset + 5]);
      const end = rawY + length;
      if (end <= floor) continue;
      const y = Math.max(rawY, floor);
      const h = end - y;
      const materialName = localLegend[(bytes[offset + 6] << 8) | bytes[offset + 7]] || 'minecraft:stone';
      const x = Math.floor(rawX / lod) * lod;
      const z = Math.floor(rawZ / lod) * lod;
      // Merge only identical vertical runs in the same LOD cell. Different
      // heights/materials remain separate boxes, so air gaps stay air.
      const key = `${materialName}|${x}|${z}|${y}|${h}`;
      if (!merged.has(key)) merged.set(key, { materialName, x, z, y, h });
    }
    merged.forEach(record => addRecord(groups, record.materialName, record.x + lod / 2, record.y + record.h / 2, record.z + lod / 2, lod, record.h, lod));
    buildMeshes(groups, voxelGroup);
    return merged.size;
  };

  const buildCloseDetail = payload => {
    const groups = new Map();
    const bytes = decode(payload.details);
    const localLegend = payload.legend || [];
    const originX = Number(payload.xOrigin) || 0;
    const originZ = Number(payload.zOrigin) || 0;
    const originY = Number(payload.yOrigin) || 0;
    const floor = Number(payload.surfaceFloor ?? 60);
    const distance = camera.position.distanceTo(controls.target);
    // Keep the close view bounded, but never truncate the scan halfway through
    // a town. The old 420k cap cut off the later X/Z columns (often the lower
    // half of a build) and made structures look exploded.
    const radius = clamp(distance * 2.2, 48, 80);
    const centerX = controls.target.x;
    const centerZ = controls.target.z;
    let blockCount = 0;
    const maxBlocks = 1500000;
    // Keep a real block occupancy map first, then draw only the exposed shell.
    // Rendering every buried block made buildings look like exploded pixels and
    // wasted most of the GPU budget on faces nobody could see.
    const blocks = new Map();
    const keyFor = (x, y, z) => `${x}|${y}|${z}`;
    const columnKeyFor = (x, z) => `${x}|${z}`;
    const runRecords = [];
    const groundedColumns = new Set();
    for (let i = 0; i < Number(payload.count || 0); i += 1) {
      const offset = i * 8;
      const rawX = originX + ((bytes[offset] << 8) | bytes[offset + 1]);
      const rawZ = originZ + ((bytes[offset + 2] << 8) | bytes[offset + 3]);
      if (Math.abs(rawX - centerX) > radius || Math.abs(rawZ - centerZ) > radius) continue;
      const rawY = originY + bytes[offset + 4];
      const length = Math.max(1, bytes[offset + 5]);
      const end = rawY + length;
      const materialName = localLegend[(bytes[offset + 6] << 8) | bytes[offset + 7]] || 'minecraft:stone';
      runRecords.push({ rawX, rawZ, rawY, end, materialName });
      if (rawY <= floor && end > floor) groundedColumns.add(columnKeyFor(rawX, rawZ));
    }
    runRecords.forEach(run => {
      // A column that reaches the surface is terrain: hide its underground
      // mass. A column with no surface block is floating architecture, so keep
      // its lower pieces (balloon baskets, bridges, suspended docks, etc.).
      const floating = !groundedColumns.has(columnKeyFor(run.rawX, run.rawZ));
      if (run.end <= floor && !floating) return;
      const yStart = floating ? run.rawY : Math.max(run.rawY, floor);
      for (let y = yStart; y < run.end; y += 1) {
        if (blockCount >= maxBlocks) return;
        blocks.set(keyFor(run.rawX, y, run.rawZ), { materialName: run.materialName, x: run.rawX, y, z: run.rawZ });
        blockCount += 1;
      }
    });
    const exposed = ['1,0,0', '-1,0,0', '0,1,0', '0,-1,0', '0,0,1', '0,0,-1'];
    blocks.forEach(block => {
      const visible = exposed.some(offset => {
        const [dx, dy, dz] = offset.split(',').map(Number);
        return !blocks.has(keyFor(block.x + dx, block.y + dy, block.z + dz));
      });
      if (visible) addRecord(groups, block.materialName, block.x + 0.5, block.y + 0.5, block.z + 0.5, 1, 1, 1);
    });
    buildMeshes(groups, voxelGroup);
    return blockCount;
  };

  const addLabel = (text, x, z, color) => {
    const canvas2 = document.createElement('canvas');
    canvas2.width = 512; canvas2.height = 128;
    const c = canvas2.getContext('2d');
    c.clearRect(0, 0, 512, 128);
    c.font = '800 48px Barkan, sans-serif';
    c.textAlign = 'center'; c.textBaseline = 'middle';
    c.lineWidth = 12; c.strokeStyle = '#061517'; c.strokeText(text, 256, 64);
    c.fillStyle = color; c.fillText(text, 256, 64);
    const texture = new THREE.CanvasTexture(canvas2);
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture, transparent: true, depthTest: true, depthWrite: false }));
    sprite.position.set(x, 250, z);
    sprite.scale.set(140, 35, 1);
    borderGroup.add(sprite);
  };
  const buildBorders = selectedId => {
    clearGroup(borderGroup);
    (mapData.areas || []).filter(area => area.category !== 'ocean' && Array.isArray(area.polygon) && area.polygon.length >= 3).forEach(area => {
      const segments = [0, ...(area.polygonBreaks || []), area.polygon.length];
      for (let i = 0; i < segments.length - 1; i += 1) {
        const points = area.polygon.slice(segments[i], segments[i + 1]).map(([x, z]) => new THREE.Vector3(x, area.id === selectedId ? 205 : 185, z));
        if (points.length < 3) continue;
        const geometry = new THREE.BufferGeometry().setFromPoints([...points, points[0]]);
        const color = area.id === selectedId ? 0xffe09a : area.category === 'town' ? 0xe8b767 : area.category === 'poi' ? 0xee8e70 : 0x7be0d0;
        borderGroup.add(new THREE.Line(geometry, new THREE.LineBasicMaterial({ color, transparent: true, opacity: area.id === selectedId ? 0.95 : 0.48 }))); 
      }
      if (area.category === 'town' || area.category === 'poi') {
        const [minX, maxX, minZ, maxZ] = area.bounds;
        addLabel(area.name, (minX + maxX) / 2, (minZ + maxZ) / 2, area.category === 'town' ? '#ffe6a4' : '#d8f4ea');
      }
    });
  };

  const fitOverview = () => {
    controls.target.set(0, 80, 0);
    camera.position.set(6400, 6100, 6400);
    controls.minDistance = 180; controls.maxDistance = 22000;
    controls.update();
  };
  const zoomBy = factor => {
    const offset = camera.position.clone().sub(controls.target).multiplyScalar(factor);
    camera.position.copy(controls.target).add(offset);
    controls.update();
  };
  const orbitBy = (azimuth, polar = 0) => {
    const offset = camera.position.clone().sub(controls.target);
    const spherical = new THREE.Spherical().setFromVector3(offset);
    spherical.theta += azimuth;
    spherical.phi = clamp(spherical.phi + polar, controls.minPolarAngle + 0.02, controls.maxPolarAngle - 0.02);
    offset.setFromSpherical(spherical);
    camera.position.copy(controls.target).add(offset);
    controls.update();
  };
  const focusArea = area => {
    if (!area) return;
    const [minX, maxX, minZ, maxZ] = area.bounds;
    const cx = (minX + maxX) / 2; const cz = (minZ + maxZ) / 2;
    const size = Math.max(maxX - minX, maxZ - minZ, 180);
    controls.target.set(cx, 80, cz);
    camera.position.set(cx + size * 0.95, 80 + size * 1.12, cz + size * 0.95);
    // Close enough to see individual 1×1×1 block cubes.
    controls.minDistance = 8;
    controls.maxDistance = Math.max(1200, size * 8);
    controls.update();
  };
  const resize = () => {
    const rect = viewport.getBoundingClientRect();
    const w = Math.max(1, rect.width); const h = Math.max(1, rect.height);
    renderer.setSize(w, h, false);
    camera.aspect = w / h; camera.updateProjectionMatrix();
  };
  const render = () => { controls.update(); renderer.render(scene, camera); requestAnimationFrame(render); };
  let activePayload = null;
  let activeTownId = '';
  let activeMode = 'run';
  let closeCenter = new THREE.Vector3();
  let rebuildTimer = 0;
  let rebuilding = false;
  const rebuildForCamera = force => {
    if (!activePayload || rebuilding) return;
    const distance = camera.position.distanceTo(controls.target);
    const wantsClose = distance < 120;
    const movedClose = wantsClose && controls.target.distanceTo(closeCenter) > 24;
    if (!force && ((wantsClose === (activeMode === 'block')) && !movedClose)) return;
    rebuilding = true;
    clearGroup(voxelGroup);
    if (!wantsClose) buildOverview(activeTownId);
    if (wantsClose) {
      const count = buildCloseDetail(activePayload);
      if (count > 0) {
        activeMode = 'block';
        closeCenter.copy(controls.target);
        status.textContent = `1:1 BLOCKS · ${activeTownId.toUpperCase()} · ${count.toLocaleString()} blocks`;
      } else {
        const runCount = buildDetail(activePayload);
        activeMode = 'run';
        status.textContent = `3D VOXEL · ${activeTownId.toUpperCase()} · ${runCount.toLocaleString()} meshes`;
      }
    } else {
      const runCount = buildDetail(activePayload);
      activeMode = 'run';
      status.textContent = `3D VOXEL · ${activeTownId.toUpperCase()} · ${runCount.toLocaleString()} meshes`;
    }
    rebuilding = false;
  };
  const scheduleRebuild = () => {
    if (!activePayload || rebuildTimer) return;
    rebuildTimer = window.setTimeout(() => { rebuildTimer = 0; rebuildForCamera(false); }, 140);
  };
  const loadTown = async id => {
    const area = townAreas.get(id);
    const slug = townSlugs[id];
    clearGroup(voxelGroup);
    buildBorders(id);
    if (!slug) { buildOverview(); fitOverview(); return; }
    const token = `${id}:${Date.now()}`;
    loadTown.token = token;
    status.textContent = '3D 블록 스캔을 불러오는 중…';
    try {
      const response = await fetch(`/assets/town-detail-${slug}.json?v=4`, { cache: 'no-store' });
      const payload = await response.json();
      if (loadTown.token !== token) return;
      activePayload = payload;
      activeTownId = id;
      activeMode = 'run';
      buildOverview(id);
      const count = buildDetail(payload);
      closeCenter.copy(controls.target);
      status.textContent = `3D VOXEL · ${id.toUpperCase()} · ${count.toLocaleString()} meshes`;
    } catch (error) {
      status.textContent = '3D 스캔을 불러오지 못했습니다';
      console.error(error);
    }
    focusArea(area);
  };

  document.querySelectorAll('.map-zoom button').forEach(button => button.addEventListener('click', () => {
    if (button.dataset.zoom === 'in') zoomBy(0.78);
    if (button.dataset.zoom === 'out') zoomBy(1.28);
    if (button.dataset.rotate === 'left') orbitBy(Math.PI / 10);
    if (button.dataset.rotate === 'right') orbitBy(-Math.PI / 10);
    if (button.dataset.pitch === 'up') orbitBy(0, -Math.PI / 14);
    if (button.dataset.pitch === 'down') orbitBy(0, Math.PI / 14);
    if (button.dataset.zoom === 'reset') fitOverview();
    controls.update();
  }));
  document.querySelector('#map-svg')?.style.setProperty('display', 'none');
  buildOverview(); buildBorders('스폰도시'); fitOverview(); resize();
  window.addEventListener('resize', resize, { passive: true });
  controls.addEventListener('change', scheduleRebuild);
  window.addEventListener('barkan-map-state', event => {
    const id = event.detail?.id || '';
    const area = townAreas.get(id);
    buildBorders(id);
    loadTown(id);
    if (area && !townSlugs[id]) focusArea(area);
  });
  render();
  loadTown('스폰도시');
})();
