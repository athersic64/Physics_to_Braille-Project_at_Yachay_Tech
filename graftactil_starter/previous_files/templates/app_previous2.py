# app.py
# Improved FastAPI + Trimesh project for GrafTactil

import os
import numpy as np
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
import matplotlib.pyplot as plt
import trimesh
from shapely.geometry import Polygon

# -------------------------
# UTILITIES
# -------------------------
def mm2pt(mm):
    return mm * 2.83465

def mm2in(mm, mm_per_inch=23.4555555):
    return mm / mm_per_inch

def muestreo_adaptativo(segmentos, densidades):
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
    return (-rango_x, rango_x), (-rango_y, rango_y)

def build_3d_from_config(config):
    plate_w_mm, plate_h_mm = config['fig_size_mm']
    plate_thickness = config.get('plate_thickness_mm', 0.8)
    marker_height = config.get('marker_height_mm', 0.8)

    meshes = []

    # Base plate
    plate = trimesh.creation.box(extents=[plate_w_mm, plate_h_mm, plate_thickness])
    plate.apply_translation([0.0, 0.0, plate_thickness / 2.0])
    meshes.append(plate)

    span_x = config['xlim'][1] - config['xlim'][0]
    span_y = config['ylim'][1] - config['ylim'][0]
    if span_x == 0: span_x = 1.0
    if span_y == 0: span_y = 1.0

    for i, f in enumerate(config['functions']):
        x_marks = muestreo_adaptativo(config['marker_segments'][i], config['marker_densities'][i])
        if x_marks.size == 0:
            continue
        y_marks = f(x_marks)
        shape = config['marker_shapes'][i].lower()
        size_mm = float(config['marker_sizes'][i])

        for xm, ym in zip(x_marks, y_marks):
            x_mm = (((xm - config['xlim'][0]) / span_x) - 0.5) * plate_w_mm
            y_mm = (((ym - config['ylim'][0]) / span_y) - 0.5) * plate_h_mm

            if shape in ['o', 'circle', 'c']:
                radius = size_mm / 2.0
                cyl = trimesh.creation.cylinder(radius=radius, height=marker_height, sections=24)
                cyl.apply_translation([x_mm, y_mm, plate_thickness + marker_height / 2.0])
                meshes.append(cyl)
            elif shape in ['s', 'square', 'box', 'rect']:
                box = trimesh.creation.box(extents=[size_mm, size_mm, marker_height])
                box.apply_translation([x_mm, y_mm, plate_thickness + marker_height / 2.0])
                meshes.append(box)
            elif shape in ['^', 'triangle', 'tri']:
                a = size_mm
                h = (np.sqrt(3) / 2.0) * a
                coords = [(-a/2.0, -h/3.0), (a/2.0, -h/3.0), (0.0, 2*h/3.0)]
                poly = Polygon(coords)
                try:
                    tri_mesh = trimesh.creation.extrude_polygon(poly, height=marker_height)
                    tri_mesh.apply_translation([x_mm, y_mm, plate_thickness])
                    meshes.append(tri_mesh)
                except Exception:
                    cyl = trimesh.creation.cylinder(radius=a/3.0, height=marker_height, sections=16)
                    cyl.apply_translation([x_mm, y_mm, plate_thickness + marker_height / 2.0])
                    meshes.append(cyl)
            else:
                cyl = trimesh.creation.cylinder(radius=size_mm/2.0, height=marker_height, sections=16)
                cyl.apply_translation([x_mm, y_mm, plate_thickness + marker_height / 2.0])
                meshes.append(cyl)

    if len(meshes) == 0:
        return None

    combined = trimesh.util.concatenate(meshes)
    combined.remove_duplicate_faces()
    combined.merge_vertices()
    return combined

# -------------------------
# FASTAPI APP
# -------------------------
app = FastAPI()
OUT_DIR = os.path.join(os.path.dirname(__file__), 'outputs')
os.makedirs(OUT_DIR, exist_ok=True)

@app.get("/")
def root():
    return {"message": "GrafTactil starter API. POST JSON to /generate"}

@app.get("/favicon.ico")
def favicon():
    path = os.path.join(os.path.dirname(__file__), "favicon.ico")
    if not os.path.exists(path):
        return JSONResponse({"error": "Not found"}, status_code=404)
    return FileResponse(path, media_type="image/x-icon")

@app.post("/generate")
async def generate(request: Request):
    content = await request.json()
    if content is None:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    # Auto limits
    if content.get('auto_limits', False):
        xlim, ylim = calcular_limites(tuple(content['fig_size_mm']), content['step_mm'], content['tick_step'])
        content['xlim'] = list(xlim)
        content['ylim'] = list(ylim)

    # Build functions from strings (safe eval)
    funcs = []
    for expr in content['functions']:
        expr_str = str(expr)
        def make_func(expression):
            def f(x):
                return eval(expression, {"np": np, "x": x, "__builtins__": {}})
            return f
        funcs.append(make_func(expr_str))
    content['functions'] = funcs

    # Generate mesh
    mesh = build_3d_from_config(content)
    if mesh is None:
        return JSONResponse({"error": "No mesh generated"}, status_code=500)

    outname = content.get('output_filename', 'out_model.stl')
    outpath = os.path.join(OUT_DIR, outname)
    try:
        mesh.export(outpath)
    except Exception as e:
        return JSONResponse({"error": f"Export failed: {e}"}, status_code=500)

    # Generate preview SVG (2D)
    preview_svg = os.path.join(OUT_DIR, outname.rsplit('.',1)[0] + '_preview.svg')
    try:
        mm_per_inch = content.get('mm_per_inch', 23.4555555)
        fig_w = mm2in(content['fig_size_mm'][0], mm_per_inch)
        fig_h = mm2in(content['fig_size_mm'][1], mm_per_inch)
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=content.get('dpi',96))
        if content.get('auto_limits', False):
            xlim, ylim = calcular_limites(content['fig_size_mm'], content['step_mm'], content['tick_step'])
            content['xlim'] = xlim
            content['ylim'] = ylim
        only_markers = content.get('only_markers', False)
        x_cont = np.linspace(content['xlim'][0], content['xlim'][1], 800)
        for i, f in enumerate(content['functions']):
            if not only_markers:
                ax.plot(x_cont, f(x_cont), content['curve_styles'][i], linewidth=mm2pt(content['curve_linewidths'][i]))
            x_marks = muestreo_adaptativo(content['marker_segments'][i], content['marker_densities'][i])
            if x_marks.size == 0: continue
            y_marks = f(x_marks)
            ax.plot(x_marks, y_marks, linestyle='None', marker=content['marker_shapes'][i],
                    markersize=mm2pt(content['marker_sizes'][i]), markerfacecolor='white', markeredgewidth=0.8)
        xticks = np.arange(content['xlim'][0], content['xlim'][1] + content['tick_step'], content['tick_step'])
        yticks = np.arange(content['ylim'][0], content['ylim'][1] + content['tick_step'], content['tick_step'])
        ax.set_xticks(xticks); ax.set_yticks(yticks)
        ax.set_xlim(content['xlim']); ax.set_ylim(content['ylim'])
        ax.set_aspect('equal','box')
        ax.axis('off')
        fig.savefig(preview_svg, bbox_inches='tight')
        plt.close(fig)
    except Exception:
        preview_svg = None

    # Return URLs for outputs
    base_url = str(request.base_url).rstrip('/')
    return JSONResponse({
        "stl": f"{base_url}/outputs/{os.path.basename(outpath)}",
        "preview_svg": f"{base_url}/outputs/{os.path.basename(preview_svg)}" if preview_svg else None
    })

@app.get("/outputs/{filename}")
def get_file(filename: str):
    path = os.path.join(OUT_DIR, filename)
    if not os.path.exists(path):
        return JSONResponse({"error": "Not found"}, status_code=404)
    # Serve SVG and STL with correct MIME types
    if filename.lower().endswith('.svg'):
        return FileResponse(path, media_type='image/svg+xml', filename=filename)
    if filename.lower().endswith('.stl'):
        return FileResponse(path, media_type='model/stl', filename=filename)
    return FileResponse(path, media_type='application/octet-stream', filename=filename)