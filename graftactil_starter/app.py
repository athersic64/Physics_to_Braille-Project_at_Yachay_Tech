import os
import logging
import numpy as np
import sympy as sp
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import trimesh
from shapely.geometry import Polygon
from typing import Dict, Any

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("graftactil")

# Directories
BASE_DIR = os.path.dirname(__file__)
OUT_DIR = os.path.join(BASE_DIR, "outputs")
STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# FastAPI app + CORS + static
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ajustar en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# -------------------------
# UTILITIES
# -------------------------
def mm2pt(mm: float) -> float:
    return mm * 2.83465

def mm2in(mm: float, mm_per_inch: float = 23.4555555) -> float:
    return mm / mm_per_inch

def muestreo_adaptativo(segmentos, densidades):
    """
    segmentos: list of [a,b] ranges
    densidades: list of counts per segment
    """
    puntos = []
    for (a, b), n in zip(segmentos, densidades):
        n = int(n)
        if n <= 0:
            continue
        if n == 1:
            puntos.append(np.array([(a + b) / 2.0]))
        else:
            puntos.append(np.linspace(a, b, n))
    if len(puntos) == 0:
        return np.array([])
    return np.concatenate(puntos)

def calcular_limites(fig_size_mm, paso_mm, tick_step):
    ancho_mm, alto_mm = fig_size_mm
    divisiones_x = max(1, int(ancho_mm // paso_mm))
    divisiones_y = max(1, int(alto_mm // paso_mm))
    rango_x = (divisiones_x // 2) * tick_step
    rango_y = (divisiones_y // 2) * tick_step
    if rango_x == 0:
        rango_x = max(1.0, tick_step * 2)
    if rango_y == 0:
        rango_y = max(1.0, tick_step * 2)
    return (-rango_x, rango_x), (-rango_y, rango_y)

def make_callable_from_expr(expr_str: str):
    """
    Convierte una expresión en 'x' a una función evaluable con numpy usando sympy.
    Acepta funciones estándar: sin, cos, exp, log, etc.
    """
    x = sp.symbols('x')
    try:
        expr = sp.sympify(expr_str, evaluate=True)
        fn = sp.lambdify(x, expr, modules=["numpy"])
        # prueba rápida
        _ = fn(0.1)
        return fn
    except Exception as e:
        raise ValueError(f"Failed to parse expression '{expr_str}': {e}")

def build_3d_from_config(config: Dict[str, Any]):
    plate_w_mm, plate_h_mm = config['fig_size_mm']
    plate_thickness = float(config.get('plate_thickness_mm', 0.8))
    marker_height = float(config.get('marker_height_mm', 0.8))

    meshes = []

    # base plate centrada en origen, cara superior en z=plate_thickness
    plate = trimesh.creation.box(extents=[plate_w_mm, plate_h_mm, plate_thickness])
    plate.apply_translation([0.0, 0.0, plate_thickness / 2.0])
    meshes.append(plate)

    span_x = float(config['xlim'][1]) - float(config['xlim'][0])
    span_y = float(config['ylim'][1]) - float(config['ylim'][0])
    if span_x == 0:
        span_x = 1.0
    if span_y == 0:
        span_y = 1.0

    for i, f in enumerate(config['functions']):
        x_marks = muestreo_adaptativo(config['marker_segments'][i], config['marker_densities'][i])
        if x_marks.size == 0:
            continue
        y_marks = np.asarray(f(x_marks))
        shape = str(config['marker_shapes'][i]).lower()
        size_mm = float(config['marker_sizes'][i])

        for xm, ym in zip(x_marks, y_marks):
            x_mm = (((float(xm) - float(config['xlim'][0])) / span_x) - 0.5) * plate_w_mm
            y_mm = (((float(ym) - float(config['ylim'][0])) / span_y) - 0.5) * plate_h_mm

            if shape in ['o', 'circle', 'c']:
                radius = size_mm / 2.0
                cyl = trimesh.creation.cylinder(radius=radius, height=marker_height, sections=32)
                cyl.apply_translation([x_mm, y_mm, plate_thickness + marker_height / 2.0])
                meshes.append(cyl)
            elif shape in ['s', 'square', 'box', 'rect']:
                box = trimesh.creation.box(extents=[size_mm, size_mm, marker_height])
                box.apply_translation([x_mm, y_mm, plate_thickness + marker_height / 2.0])
                meshes.append(box)
            elif shape in ['^', 'triangle', 'tri']:
                a = size_mm
                h = (np.sqrt(3) / 2.0) * a
                coords = [(-a / 2.0, -h / 3.0), (a / 2.0, -h / 3.0), (0.0, 2 * h / 3.0)]
                poly = Polygon(coords)
                try:
                    tri_mesh = trimesh.creation.extrude_polygon(poly, height=marker_height)
                    tri_mesh.apply_translation([x_mm, y_mm, plate_thickness])
                    meshes.append(tri_mesh)
                except Exception:
                    cyl = trimesh.creation.cylinder(radius=a / 3.0, height=marker_height, sections=16)
                    cyl.apply_translation([x_mm, y_mm, plate_thickness + marker_height / 2.0])
                    meshes.append(cyl)
            else:
                cyl = trimesh.creation.cylinder(radius=size_mm / 2.0, height=marker_height, sections=16)
                cyl.apply_translation([x_mm, y_mm, plate_thickness + marker_height / 2.0])
                meshes.append(cyl)

    if len(meshes) == 0:
        return None

    combined = trimesh.util.concatenate(meshes)
    try:
        combined.remove_duplicate_faces()
    except Exception:
        pass
    try:
        combined.merge_vertices()
    except Exception:
        pass
    return combined

def export_mesh_bg(mesh: trimesh.Trimesh, outpath: str):
    try:
        mesh.export(outpath)
        logger.info("Exported mesh to %s", outpath)
    except Exception as e:
        logger.exception("Export failed: %s", e)


# -------------------------
# ROUTES
# -------------------------
@app.get("/", include_in_schema=False)
def index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return RedirectResponse(url="/static/index.html")

@app.get("/favicon.ico")
def favicon():
    path = os.path.join(BASE_DIR, "favicon.ico")
    if not os.path.exists(path):
        return JSONResponse({"error": "Not found"}, status_code=404)
    return FileResponse(path, media_type="image/x-icon")

@app.post("/generate")
async def generate(request: Request, background_tasks: BackgroundTasks):
    content = await request.json()
    if not isinstance(content, dict):
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    # Auto limits
    if content.get('auto_limits', False):
        xlim, ylim = calcular_limites(tuple(content['fig_size_mm']), content['step_mm'], content['tick_step'])
        content['xlim'] = list(xlim)
        content['ylim'] = list(ylim)

    # Build functions safely with sympy
    funcs = []
    try:
        for expr in content.get('functions', []):
            funcs.append(make_callable_from_expr(str(expr)))
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    if len(funcs) == 0:
        return JSONResponse({"error": "No functions provided"}, status_code=400)
    content['functions'] = funcs

    # Validate marker arrays lengths
    nfunc = len(funcs)
    required_keys = ['marker_segments', 'marker_densities', 'marker_shapes', 'marker_sizes']
    for key in required_keys:
        if key not in content:
            return JSONResponse({"error": f"Missing required key: {key}"}, status_code=400)
        if len(content[key]) != nfunc:
            return JSONResponse({"error": f"Length of '{key}' must match number of functions ({nfunc})"}, status_code=400)

    # Default limits if missing
    if 'xlim' not in content or 'ylim' not in content:
        xlim, ylim = calcular_limites(tuple(content['fig_size_mm']), content['step_mm'], content['tick_step'])
        content.setdefault('xlim', list(xlim))
        content.setdefault('ylim', list(ylim))

    # Generate mesh
    try:
        mesh = build_3d_from_config(content)
    except Exception as e:
        logger.exception("Mesh generation failed")
        return JSONResponse({"error": f"Mesh generation failed: {e}"}, status_code=500)

    if mesh is None:
        return JSONResponse({"error": "No mesh generated"}, status_code=500)

    outname = os.path.basename(content.get('output_filename', 'out_model.stl'))
    outpath = os.path.join(OUT_DIR, outname)
    background_tasks.add_task(export_mesh_bg, mesh, outpath)

    # Generate preview SVG synchronously
    preview_svg = os.path.join(OUT_DIR, outname.rsplit('.', 1)[0] + '_preview.svg')
    try:
        mm_per_inch = content.get('mm_per_inch', 23.4555555)
        fig_w = mm2in(content['fig_size_mm'][0], mm_per_inch)
        fig_h = mm2in(content['fig_size_mm'][1], mm_per_inch)
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=content.get('dpi', 96))
        only_markers = content.get('only_markers', False)
        x_cont = np.linspace(content['xlim'][0], content['xlim'][1], 800)
        for i, f in enumerate(content['functions']):
            if not only_markers:
                style = content.get('curve_styles', ['-'] * nfunc)[i]
                lw = mm2pt(float(content.get('curve_linewidths', [1.0] * nfunc)[i]))
                ax.plot(x_cont, f(x_cont), style, linewidth=lw)
            x_marks = muestreo_adaptativo(content['marker_segments'][i], content['marker_densities'][i])
            if x_marks.size == 0:
                continue
            y_marks = np.asarray(f(x_marks))
            marker = content.get('marker_shapes', ['o'] * nfunc)[i]
            ms = mm2pt(float(content.get('marker_sizes', [3.0] * nfunc)[i]))
            ax.plot(x_marks, y_marks, linestyle='None', marker=marker, markersize=ms,
                    markerfacecolor='white', markeredgewidth=0.8)
        xticks = np.arange(content['xlim'][0], content['xlim'][1] + content['tick_step'], content['tick_step'])
        yticks = np.arange(content['ylim'][0], content['ylim'][1] + content['tick_step'], content['tick_step'])
        ax.set_xticks(xticks); ax.set_yticks(yticks)
        ax.set_xlim(content['xlim']); ax.set_ylim(content['ylim'])
        ax.set_aspect('equal', 'box')
        ax.axis('off')
        fig.savefig(preview_svg, bbox_inches='tight')
        plt.close(fig)
        preview_url = f"{str(request.base_url).rstrip('/')}/outputs/{os.path.basename(preview_svg)}"
    except Exception as e:
        logger.exception("Preview generation failed")
        preview_url = None

    stl_url = f"{str(request.base_url).rstrip('/')}/outputs/{os.path.basename(outpath)}"
    return JSONResponse({"stl": stl_url, "preview_svg": preview_url, "status": "export_started"})

@app.get("/outputs/{filename}")
def get_file(filename: str):
    path = os.path.join(OUT_DIR, filename)
    if not os.path.exists(path):
        return JSONResponse({"error": "Not found"}, status_code=404)
    if filename.lower().endswith('.svg'):
        return FileResponse(path, media_type='image/svg+xml', filename=filename)
    if filename.lower().endswith('.stl'):
        return FileResponse(path, media_type='model/stl', filename=filename)
    return FileResponse(path, media_type='application/octet-stream', filename=filename)