// Módulo frontend: vista 3D en cliente + integración con backend /generate
import * as THREE from 'https://unpkg.com/three@0.152.2/build/three.module.js';
import { STLLoader } from 'https://unpkg.com/three@0.152.2/examples/jsm/loaders/STLLoader.js';
import { OrbitControls } from 'https://unpkg.com/three@0.152.2/examples/jsm/controls/OrbitControls.js';

// selectores y utilidades
const qs = s => document.querySelector(s);
const qsa = s => Array.from(document.querySelectorAll(s));
const functionsList = qs('#functionsList');
const template = qs('#fnTemplate');
const status = qs('#status');

// añadir / reset funciones
function addFunctionRow(expr='x', density=20, shape='o', size=3.0) {
  const node = document.createElement('div');
  node.className = 'card p-3 mt-2';
  node.innerHTML = template.innerHTML;
  const inputExpr = node.querySelector('.fn-expr');
  const inputDen = node.querySelector('.fn-density');
  const inputShape = node.querySelector('.fn-shape');
  const inputSize = node.querySelector('.fn-size');
  inputExpr.value = expr;
  inputDen.value = density;
  inputShape.value = shape;
  inputSize.value = size;
  node.querySelector('.remove-fn').onclick = () => node.remove();
  for (const el of node.querySelectorAll('input, select')) el.addEventListener('input', scheduleUpdate);
  functionsList.appendChild(node);
}
function resetDefaults(){
  functionsList.innerHTML='';
  addFunctionRow('x',20,'o',3.0);
  addFunctionRow('x**2',7,'s',3.0);
  addFunctionRow('x**3',6,'^',3.5);
}

// construir config para backend
function buildConfig(){
  const funcs=[], shapes=[], sizes=[], densities=[], segments=[];
  const only_markers = qs('#only_markers') ? qs('#only_markers').checked : true;
  for (const card of functionsList.children){
    const expr = card.querySelector('.fn-expr').value.trim() || 'x';
    const den = parseInt(card.querySelector('.fn-density').value) || 0;
    const shape = card.querySelector('.fn-shape').value;
    const size = parseFloat(card.querySelector('.fn-size').value) || 3.0;
    funcs.push(expr); shapes.push(shape); sizes.push(size);
    densities.push([den]); segments.push([[-5.5,5.5]]);
  }
  return {
    functions: funcs,
    labels: funcs.map(f=>f),
    curve_styles: funcs.map(()=>'-'),
    curve_linewidths: funcs.map(()=>1.0),
    marker_shapes: shapes,
    marker_sizes: sizes,
    marker_segments: segments,
    marker_densities: densities,
    fig_size_mm: [ parseFloat(qs('#fig_w').value || 173), parseFloat(qs('#fig_h').value || 113) ],
    dpi: parseInt(qs('#dpi').value) || 96,
    auto_limits: true,
    step_mm: 7.45,
    tick_step: 0.5,
    plate_thickness_mm: parseFloat(qs('#plate_thickness_mm').value) || 0.8,
    marker_height_mm: parseFloat(qs('#marker_height_mm').value) || 0.8,
    output_filename: qs('#output_filename') ? qs('#output_filename').value : 'grafica_export.stl',
    only_markers: only_markers,
    mm_per_inch: 23.4555555,
    save_pdf: false
  };
}

// parser de expresiones con mathjs (global "math")
function compileExpression(expr){
  try{
    const node = math.compile(expr);
    return x => {
      const v = node.evaluate({ x });
      if (typeof v === 'object' && v && 're' in v) return v.re;
      return Number(v);
    };
  }catch(e){
    console.warn('Parse error', expr, e);
    return x => NaN;
  }
}

// mapping simple de datos a mm (igual que backend)
function calcular_limites(fig_size_mm, paso_mm=7.45, tick_step=0.5){
  const [ancho_mm, alto_mm] = fig_size_mm;
  const divisiones_x = Math.max(1, Math.floor(ancho_mm / paso_mm));
  const divisiones_y = Math.max(1, Math.floor(alto_mm / paso_mm));
  let rango_x = Math.floor(divisiones_x / 2) * tick_step;
  let rango_y = Math.floor(divisiones_y / 2) * tick_step;
  if (rango_x === 0) rango_x = Math.max(1.0, tick_step * 2);
  if (rango_y === 0) rango_y = Math.max(1.0, tick_step * 2);
  return [[-rango_x, rango_x], [-rango_y, rango_y]];
}
function mapDataToPlate(x,y,config){
  const [plateW, plateH] = config.fig_size_mm;
  const xlim = config.xlim; const ylim = config.ylim;
  const span_x = xlim[1]-xlim[0] || 1; const span_y = ylim[1]-ylim[0] || 1;
  const x_mm = ((x - xlim[0]) / span_x - 0.5) * plateW;
  const y_mm = ((y - ylim[0]) / span_y - 0.5) * plateH;
  return [x_mm, y_mm];
}

// Three.js viewer
const container = qs('#viewer');
let renderer, scene, camera, controls, currentGroup;
function initViewer(){
  renderer = new THREE.WebGLRenderer({ antialias:true });
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setSize(container.clientWidth, container.clientHeight, false);
  container.innerHTML=''; container.appendChild(renderer.domElement);
  scene = new THREE.Scene(); scene.background = new THREE.Color(0xf0f4fa);
  const aspect = container.clientWidth / Math.max(1, container.clientHeight);
  camera = new THREE.PerspectiveCamera(45, aspect, 0.1, 5000); camera.position.set(300,300,300);
  const hemi = new THREE.HemisphereLight(0xffffff, 0x444444, 0.85); hemi.position.set(0,200,0); scene.add(hemi);
  const dir = new THREE.DirectionalLight(0xffffff, 0.6); dir.position.set(100,100,100); scene.add(dir);
  const grid = new THREE.GridHelper(500, 20, 0xdddddd, 0xeeeeee); grid.material.opacity = 0.6; grid.material.transparent = true; scene.add(grid);
  controls = new OrbitControls(camera, renderer.domElement); controls.enableDamping=true; controls.dampingFactor=0.1;
  window.addEventListener('resize', ()=> { renderer.setSize(container.clientWidth, container.clientHeight, false); camera.aspect = container.clientWidth / Math.max(1, container.clientHeight); camera.updateProjectionMatrix(); });
  currentGroup = new THREE.Group(); scene.add(currentGroup);
  animate();
}
function animate(){ requestAnimationFrame(animate); controls.update(); renderer.render(scene, camera); }
function clearGroup(){ while(currentGroup.children.length){ const c=currentGroup.children.pop(); if(c.geometry) c.geometry.dispose(); if(c.material) { if(Array.isArray(c.material)) c.material.forEach(m=>m.dispose&&m.dispose()); else c.material.dispose&&c.material.dispose(); } } }

// crear marcadores simples
function makeCylinderMesh(radius,height){ const geom=new THREE.CylinderGeometry(radius, radius, height, 20); const mat=new THREE.MeshPhongMaterial({ color:0x1f77b4, shininess:30 }); return new THREE.Mesh(geom, mat); }
function makeBoxMesh(w,h,d){ const geom=new THREE.BoxGeometry(w, d, h); const mat=new THREE.MeshPhongMaterial({ color:0x1f77b4, shininess:30 }); return new THREE.Mesh(geom, mat); }
function makeTriangleExtrude(size, height){ const shape=new THREE.Shape(); const a=size; const h=Math.sqrt(3)/2*a; shape.moveTo(-a/2, -h/3); shape.lineTo(a/2, -h/3); shape.lineTo(0, 2*h/3); shape.closePath(); const geom=new THREE.ExtrudeGeometry(shape,{ depth: height, bevelEnabled:false}); const mat=new THREE.MeshPhongMaterial({ color:0x1f77b4, shininess:30 }); return new THREE.Mesh(geom, mat); }

// construir preview cliente (rápido)
function buildClientPreview(){
  const cfg = buildConfig();
  if (cfg.auto_limits){ const [xlim, ylim] = calcular_limites(cfg.fig_size_mm, cfg.step_mm, cfg.tick_step); cfg.xlim = xlim; cfg.ylim = ylim; }
  else { cfg.xlim = cfg.xlim || [-5.5,5.5]; cfg.ylim = cfg.ylim || [-5.5,5.5]; }
  const fns = cfg.functions.map(s => compileExpression(s));
  clearGroup();
  // placa visual
  const plateMat = new THREE.MeshPhongMaterial({ color:0xf5f5f5, specular:0x111111 });
  const plateGeom = new THREE.BoxGeometry(cfg.fig_size_mm[0], cfg.fig_size_mm[1], cfg.plate_thickness_mm);
  const plate = new THREE.Mesh(plateGeom, plateMat); plate.position.set(0,0,cfg.plate_thickness_mm/2); currentGroup.add(plate);
  // marcadores
  fns.forEach((fn,i)=> {
    const densArr = cfg.marker_densities ? cfg.marker_densities[i] : [10];
    const N = Array.isArray(densArr) ? (densArr[0] || 0) : (densArr || 0);
    if (N<=0) return;
    const xs=[]; for(let k=0;k<N;k++) xs.push(cfg.xlim[0] + (k / Math.max(1,N-1)) * (cfg.xlim[1] - cfg.xlim[0]));
    const shape = cfg.marker_shapes[i] || 'o'; const size = cfg.marker_sizes[i] || 3.0; const markerHeight = cfg.marker_height_mm || 0.8;
    xs.forEach(x => { const y = fn(x); if(!isFinite(y)) return; const [xm, ym] = mapDataToPlate(x,y,cfg); let m; if(shape==='o'){ m=makeCylinderMesh(size/2, markerHeight); } else if(shape==='s'){ m=makeBoxMesh(size, markerHeight, size); } else if(shape==='^'){ m=makeTriangleExtrude(size, markerHeight); } else m=makeCylinderMesh(size/2, markerHeight); m.position.set(xm, ym, cfg.plate_thickness_mm + markerHeight/2); currentGroup.add(m); });
  });
  // ajustar cámara
  const box = new THREE.Box3().setFromObject(currentGroup);
  const size = box.getSize(new THREE.Vector3()).length(); const center = box.getCenter(new THREE.Vector3());
  const halfSizeToFitOnScreen = size * 0.5; const dist = halfSizeToFitOnScreen / Math.tan((camera.fov * Math.PI) / 360);
  const dir = new THREE.Vector3().subVectors(camera.position, center).normalize();
  camera.position.copy(dir.multiplyScalar(dist).add(center)); camera.near = size/100; camera.far = size*100; camera.updateProjectionMatrix();
  controls.target.copy(center); controls.update();
}

// debounce actualizaciones en vivo
let updateTimer = null;
function scheduleUpdate(){
  if (!qs('#live_preview') || !qs('#live_preview').checked) return;
  if (updateTimer) clearTimeout(updateTimer);
  updateTimer = setTimeout(() => { try { buildClientPreview(); status.textContent = 'Vista 3D actualizada'; } catch(e){ status.textContent = 'Error preview: '+e.message; console.error(e); } }, 300);
}

// cargar STL del backend (con retry)
async function loadSTL(url){
  return new Promise((resolve,reject)=> {
    const loader = new STLLoader();
    loader.load(url, geometry => {
      geometry.computeBoundingBox(); const bbox = geometry.boundingBox;
      geometry.translate(- (bbox.min.x + bbox.max.x)/2, - (bbox.min.y + bbox.max.y)/2, -bbox.min.z);
      const material = new THREE.MeshPhongMaterial({ color:0x1f77b4, shininess:40 });
      const mesh = new THREE.Mesh(geometry, material);
      clearGroup(); currentGroup.add(mesh);
      const box = new THREE.Box3().setFromObject(mesh); const boxSize = box.getSize(new THREE.Vector3()).length(); const boxCenter = box.getCenter(new THREE.Vector3());
      const halfSizeToFit = boxSize * 0.5; const dist = halfSizeToFit / Math.tan((camera.fov * Math.PI) / 360);
      const dir = new THREE.Vector3().subVectors(camera.position, boxCenter).normalize();
      camera.position.copy(dir.multiplyScalar(dist).add(boxCenter)); camera.near = boxSize/100; camera.far = boxSize*100; camera.updateProjectionMatrix();
      controls.target.copy(boxCenter); controls.update();
      resolve();
    }, undefined, err => reject(err));
  });
}
async function loadSTLWithRetry(url, attempts=10, delay=800){ for(let i=0;i<attempts;i++){ try{ await loadSTL(url); return; } catch(e){ await new Promise(r=>setTimeout(r, delay)); } } throw new Error('No se pudo cargar STL'); }

// botones y eventos
qs('#previewBtn')?.addEventListener('click', ()=>{ try{ buildClientPreview(); status.textContent='Vista 3D actualizada'; }catch(e){ status.textContent='Error preview: '+e.message; } });
qs('#generateBtn')?.addEventListener('click', async ()=>{ status.textContent='Solicitando export al servidor...'; const cfg = buildConfig(); try{ const res = await fetch('/generate',{ method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(cfg) }); const j = await res.json(); if(!res.ok){ status.textContent = 'Error: '+(j.error||JSON.stringify(j)); return; } status.textContent='Export iniciado en backend.'; if(j.preview_svg) qs('#preview').innerHTML = `<div class="card p-3"><h6>Previsualización</h6><img src="${j.preview_svg}"/></div>`; if(j.stl){ qs('#downloadStlBtn').href=j.stl; qs('#downloadStlBtn').style.display=''; qs('#viewerStatus').innerHTML='<span class="loader"></span> Cargando STL...'; try{ await loadSTLWithRetry(j.stl,12,1000); qs('#viewerStatus').textContent=''; }catch(e){ qs('#viewerStatus').textContent='No se pudo cargar STL automáticamente. Descarga manualmente.'; } } }catch(e){ status.textContent='Error conexión: '+e.message; } });
qs('#addFn')?.addEventListener('click', ()=>addFunctionRow());
qs('#resetBtn')?.addEventListener('click', ()=>{ resetDefaults(); scheduleUpdate(); status.textContent=''; qs('#preview').innerHTML=''; });
for(const el of qsa('input, select')) el.addEventListener('input', scheduleUpdate);
qs('#live_preview')?.addEventListener('change', ()=>{ if (qs('#live_preview').checked) scheduleUpdate(); });
qs('#resetView')?.addEventListener('click', ()=>{ camera.position.set(300,300,300); controls.target.set(0,0,0); controls.update(); });

// init
initViewer(); resetDefaults(); scheduleUpdate();