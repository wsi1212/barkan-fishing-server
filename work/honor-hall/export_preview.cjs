// Generate geometry directly from the user-approved preview, preserving draw order.
const fs = require('fs');
const path = require('path');
const source = fs.readFileSync('/Users/user/.codex/visualizations/2026/09/16/01a0a9e9-c3bc-7303-9e89-757cf6c96adc/honor-hall-redesign.html', 'utf8');
const start = source.indexOf('      function box(');
const end = source.indexOf('      // Static instancing');
if (start < 0 || end < start) throw Error('Preview geometry boundaries changed');
let code = source.slice(start, end);
code = code.replace('blocks.get(key).push([x+w/2,y+h/2,z+d/2,w,h,d]);', 'blocks.get(key).push([x+w/2,y+h/2,z+d/2,w,h,d]); records.push({x,y,z,w,h,d,material,group});');
const records=[];
new Function('blocks','records',code)(new Map(),records);
fs.writeFileSync(path.join(__dirname,'approved_geometry.json'), JSON.stringify(records));
console.log(JSON.stringify({boxes:records.length, architecture:records.filter(r=>r.group!=='forest'&&r.group!=='glass').length}));
