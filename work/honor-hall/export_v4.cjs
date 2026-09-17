// Offline DESIGN export only. No network, server commands or world modifications.
const fs=require('fs'),path=require('path'),assert=require('assert');
const sourcePath='/Users/user/.codex/visualizations/2026/09/16/01a0a9e9-c3bc-7303-9e89-757cf6c96adc/honor-hall-v4.html';
const source=fs.readFileSync(sourcePath,'utf8');
const start=source.indexOf('// GEOMETRY-BEGIN'),end=source.indexOf('// GEOMETRY-END');
assert(start>=0&&end>start);
const records=[],markers=[];
new Function('blocks','records','markers',source.slice(start,end))(new Map(),records,markers);
const voxels=new Map();
const materials={quartz:'minecraft:smooth_quartz',pillar:'minecraft:quartz_pillar[axis=y]',tile:'minecraft:polished_diorite',stone:'minecraft:polished_andesite',jade:'minecraft:dark_prismarine',gold:'minecraft:gold_block',grass:'minecraft:grass_block',leaf:'minecraft:oak_leaves[persistent=true]',leaf2:'minecraft:azalea_leaves[persistent=true]',bark:'minecraft:oak_log[axis=y]',water:'minecraft:water[level=0]',ground:'minecraft:grass_block',glass:'minecraft:glass',light:'minecraft:sea_lantern'};
for(const b of records){
  for(const k of ['x','y','z','w','h','d'])assert(Number.isInteger(b[k]),`Fractional ${k}: ${JSON.stringify(b)}`);
  assert(materials[b.material],b.material);
  for(let y=b.y;y<b.y+b.h;y++)for(let z=b.z;z<b.z+b.d;z++)for(let x=b.x;x<b.x+b.w;x++)voxels.set(`${x},${y},${z}`,{x,y,z,material:b.material,group:b.group});
}
const palette=Object.keys(materials),groups=[...new Set(records.map(r=>r.group))];
const list=[...voxels.values()].sort((a,b)=>a.y-b.y||a.z-b.z||a.x-b.x);
// Runs: x, localY, z, length along +X, palette index, group index.
const runs=[];
for(const v of list){const pi=palette.indexOf(v.material),gi=groups.indexOf(v.group),last=runs.at(-1);if(last&&last[1]===v.y&&last[2]===v.z&&last[0]+last[3]===v.x&&last[4]===pi&&last[5]===gi)last[3]++;else runs.push([v.x,v.y,v.z,1,pi,gi]);}
const at=(x,y,z)=>voxels.get(`${x},${y},${z}`);
const plinths=markers.filter(m=>m.type==='plinth'),staff=plinths.filter(m=>m.kind==='staff');assert.equal(staff.length,4);assert.equal(plinths.length,22);
for(const m of plinths)for(let x=m.x;x<m.x+3;x++)for(let z=m.z;z<m.z+3;z++){
  for(let y=2;y<4;y++)assert(['quartz','pillar','gold'].includes(at(x,y,z)?.material),'Plinth solid');
  assert(!at(x,4,z),'Plinth headroom');
}
// Every dome column is covered by solid roof or intentional central glazing.
let domeColumns=0,maxStep=0;
const roofRange=(x,z)=>{const ys=[];for(let y=24;y<=42;y++)if(['roof','glass'].includes(at(x,y,z)?.group))ys.push(y);return ys;};
for(let x=-33;x<33;x++)for(let z=-33;z<33;z++)if(Math.hypot(x+.5,z+.5)<33){
  const ys=roofRange(x,z);assert(ys.length,`Uncovered dome ${x},${z}`);domeColumns++;
  for(const [dx,dz]of [[1,0],[0,1]])if(Math.hypot(x+dx+.5,z+dz+.5)<33){const other=roofRange(x+dx,z+dz);assert(ys.some(y=>other.includes(y)),`Unsealed dome joint ${x},${z}`);maxStep=Math.max(maxStep,Math.abs(Math.max(...ys)-Math.max(...other)));}
}
// No colored roof material in the walkable temple floor.
assert(!list.some(v=>v.y===1&&['jade','gold'].includes(v.material)),'Floor palette');
const arch=list.filter(v=>!['forest','planting','terrain'].includes(v.group));
const bounds=arr=>({min:['x','y','z'].map(k=>Math.min(...arr.map(v=>v[k]))),max:['x','y','z'].map(k=>Math.max(...arr.map(v=>v[k])))});
// Avoid argument-count limit for the complete forest dataset.
const bbox=arr=>arr.reduce((b,v)=>{for(const [i,k]of ['x','y','z'].entries()){b.min[i]=Math.min(b.min[i],v[k]);b.max[i]=Math.max(b.max[i],v[k]);}return b;},{min:[Infinity,Infinity,Infinity],max:[-Infinity,-Infinity,-Infinity]});
const report={status:'OFFLINE_DESIGN_ONLY',blocks:list.length,architectureBlocks:arch.length,runs:runs.length,trees:markers.filter(m=>m.type==='tree').length,plinths:plinths.length,staffPlinths:staff.length,domeCoveredColumns:domeColumns,domeMaxAdjacentHeightDifference:maxStep,checks:['integer geometry','22 clear 3x3x2 plinths; 4 staff','continuous dome and glazing with adjacent shared solid levels','no teal or gold floor'],architectureBounds:bbox(arch),allBounds:bbox(list)};
const blueprint={version:4,status:'DESIGN_NOT_DEPLOYED',world:'honor_hall',offset:[0,65,0],source:sourcePath,palette:palette.map(k=>({name:k,block:materials[k]})),groups,runFormat:['x','localY','z','lengthX','paletteIndex','groupIndex'],runs,markers,report};
fs.writeFileSync(path.join(__dirname,'honor-hall-v4-blueprint.json'),JSON.stringify(blueprint));
fs.writeFileSync(path.join(__dirname,'honor-hall-v4-validation.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
