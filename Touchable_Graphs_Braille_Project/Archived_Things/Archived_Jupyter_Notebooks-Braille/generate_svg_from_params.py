#!/usr/bin/env python3
"""
generate_svg_from_params.py

Lee un archivo JSON de parámetros (params.json) y genera un SVG con capas:
 - Plate (fondo)
 - Grid
 - Axes
 - Curves
 - Markers
 - Ticks
 - Braille (cada etiqueta en subgrupo)

Requisitos:
    pip install svgwrite numpy

Uso:
    python generate_svg_from_params.py params.json
"""

import sys
import json
import math
import numpy as np
import svgwrite
from pathlib import Path

# -----------------------
# UTILIDADES / BRAILLE
# -----------------------

# Mapa Braille básico (letters a-z)
BRAILLE_ALPHA = {
    'a': (1,), 'b': (1,2), 'c': (1,4), 'd': (1,4,5), 'e': (1,5),
    'f': (1,2,4), 'g': (1,2,4,5), 'h': (1,2,5), 'i': (2,4), 'j': (2,4,5),
    'k': (1,3), 'l': (1,2,3), 'm': (1,3,4), 'n': (1,3,4,5), 'o': (1,3,5),
    'p': (1,2,3,4), 'q': (1,2,3,4,5), 'r': (1,2,3,5), 's': (2,3,4), 't': (2,3,4,5),
    'u': (1,3,6), 'v': (1,2,3,6), 'w': (2,4,5,6), 'x': (1,3,4,6), 'y': (1,3,4,5,6), 'z': (1,3,5,6),
}
CAPITAL_SIGN = (6,)
NUMBER_SIGN = (3,4,5,6)
SPACE = ()
DIGIT_TO_ALPHA = { '1':'a','2':'b','3':'c','4':'d','5':'e','6':'f','7':'g','8':'h','9':'i','0':'j' }

def char_to_cells(ch):
    """Mapa básico: retorna lista de celdas (tuplas de puntos) para ch."""
    if ch == ' ':
        return [SPACE]
    if ch in [',', '.', ';', '-', '_', '/', '(', ')', ':']:
        return [SPACE]
    if ch.lower() in BRAILLE_ALPHA:
        if ch.isupper():
            return [CAPITAL_SIGN, BRAILLE_ALPHA[ch.lower()]]
        else:
            return [BRAILLE_ALPHA[ch.lower()]]
    return [SPACE]

def text_to_cells(text):
    """Convierte texto a secuencia de celdas Braille, maneja números."""
    cells = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch.isdigit():
            cells.append(NUMBER_SIGN)
            while i < len(text) and text[i].isdigit():
                cells.extend(char_to_cells(DIGIT_TO_ALPHA[text[i]]))
                i += 1
            continue
        cells.extend(char_to_cells(ch))
        i += 1
    return cells

# -----------------------
# GEOM → SVG helpers
# -----------------------

def data_to_svg_coords(x, y, xlim, ylim, width_mm, height_mm):
    """
    Mapea (x,y) en datos a coordenadas SVG en mm.
    Sistema de datos mapeado linealmente al rectángulo físico [0,width_mm]x[0,height_mm].
    """
    x0, x1 = xlim
    y0, y1 = ylim
    fx = (x - x0) / (x1 - x0)
    fy = (y - y0) / (y1 - y0)
    sx = fx * width_mm
    sy = (1 - fy) * height_mm
    return sx, sy

def svg_stroke_dash(style_name):
    if style_name == "solid": return None
    if style_name == "dash": return "6,3"
    if style_name == "dot": return "1,3"
    return None

# -----------------------
# RENDER BRAILLE TO SVG
# -----------------------

def render_braille_to_group(dwg, text, origin_mm, dot_diameter_mm=1.5, dot_spacing_mm=2.5,
                            char_spacing_mm=3.0, line_spacing_mm=4.0, fill_color="#000000"):
    """
    Devuelve un grupo (svgwrite container) con los círculos que representan el Braille.
    origin_mm está en coordenadas centradas (-w/2..w/2, -h/2..h/2) y la función convertirá
    a coordenadas SVG en mm cuando lo insertemos.
    """
    g = dwg.g()
    ox, oy = origin_mm
    # NOTE: caller must translate el grupo a coordenadas svg adecuadas (alternativa: calcular en caller)
    # Aquí dibujamos en coordenadas relativas: (0,0) corresponde al origin_mm en el sistema centrado.
    lines = text.split('\n')
    cursor_y = 0.0
    for line in lines:
        cells = text_to_cells(line)
        cursor_x = 0.0
        for cell in cells:
            if cell == SPACE:
                cursor_x += char_spacing_mm
                continue
            for d in cell:
                # map dot index -> offset
                col = 0 if d in (1,2,3) else 1
                row_map = {1:0,2:1,3:2,4:0,5:1,6:2}
                row = row_map[d]
                x_offset = (col - 0.5) * dot_spacing_mm
                y_offset = (1 - row) * dot_spacing_mm  # row0 top, row2 bottom
                cx = cursor_x + x_offset
                cy = cursor_y + y_offset
                # circle center at (cx, cy) in mm relative to origin
                g.add(dwg.circle(center=(f"{cx}mm", f"{cy}mm"),
                                 r=f"{dot_diameter_mm/2.0:.3f}mm",
                                 fill=fill_color, stroke="none"))
            cursor_x += char_spacing_mm
        cursor_y += line_spacing_mm
    # The group is drawn centered at (0,0) — caller should transform/translate to absolute svg coords.
    return g

# -----------------------
# MAIN: lee params y genera svg
# -----------------------

def make_default_marker_xs(xlim):
    """Muestreo adaptativo por defecto (similar al que usabas). Devuelve lista por función."""
    xs1 = np.linspace(xlim[0], xlim[1], 35)
    xs2 = np.concatenate([
        np.linspace(xlim[0], -3.0, 1),
        np.linspace(-3.0, -2.0, 10),
        np.linspace(-2.0, -1.0, 7),
        np.linspace(-1.0, 1.0, 7),
        np.linspace(1.0, 2.0, 7),
        np.linspace(2.0, 3.0, 10),
        np.linspace(3.0, xlim[1], 1)
    ])
    xs3 = np.concatenate([
        np.linspace(xlim[0], -2.0, 1),
        np.linspace(-2.0, -1.5, 10),
        np.linspace(-1.5, -1.0, 6),
        np.linspace(-1.0, 1.0, 6),
        np.linspace(1.0, 1.5, 6),
        np.linspace(1.5, 2.0, 10),
        np.linspace(2.0, xlim[1], 1)
    ])
    return [xs1, xs2, xs3]

def load_params(path):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"params file not found: {path}")
    with p.open("r", encoding="utf8") as fh:
        return json.load(fh)

def build_svg_from_params(params):
    # read common params
    fig_w_mm, fig_h_mm = params.get("fig_size_mm", [173.0, 113.0])
    xlim = tuple(params.get("xlim", [-7.0, 7.0]))
    ylim = tuple(params.get("ylim", [-7.0, 7.0]))
    tick_step = params.get("tick_step", 0.5)
    output_svg = params.get("output_svg", "output.svg")

    # create svgwrite drawing with physical mm size
    dwg = svgwrite.Drawing(filename=output_svg, size=(f"{fig_w_mm}mm", f"{fig_h_mm}mm"), profile='tiny')

    # layers (groups) with inkscape-compatible attributes
    # we will add groups and then fill them
    inkscape_extra = {"inkscape:groupmode": "layer"}  # note: svgwrite won't add namespace by default but inkscape reads the attributes

    # 1) plate (background)
    plate = dwg.g(id="plate", **{"inkscape:groupmode":"layer", "inkscape:label":"Plate"})
    plate.add(dwg.rect(insert=(0,0), size=(f"{fig_w_mm}mm", f"{fig_h_mm}mm"), fill="#ffffff"))
    dwg.add(plate)

    # 2) grid
    layer_grid = dwg.g(id="grid", **{"inkscape:groupmode":"layer", "inkscape:label":"Grid"})
    grid_stroke_mm = params.get("grid_stroke_mm", 0.25)
    xticks = np.arange(xlim[0], xlim[1] + 1e-9, tick_step)
    yticks = np.arange(ylim[0], ylim[1] + 1e-9, tick_step)
    for xv in xticks:
        sx1, sy1 = data_to_svg_coords(xv, ylim[0], xlim, ylim, fig_w_mm, fig_h_mm)
        sx2, sy2 = data_to_svg_coords(xv, ylim[1], xlim, ylim, fig_w_mm, fig_h_mm)
        layer_grid.add(dwg.line(start=(f"{sx1}mm", f"{sy1}mm"), end=(f"{sx2}mm", f"{sy2}mm"),
                                stroke="#e6e6e6", stroke_width=f"{grid_stroke_mm}mm"))
    for yv in yticks:
        sx1, sy1 = data_to_svg_coords(xlim[0], yv, xlim, ylim, fig_w_mm, fig_h_mm)
        sx2, sy2 = data_to_svg_coords(xlim[1], yv, xlim, ylim, fig_w_mm, fig_h_mm)
        layer_grid.add(dwg.line(start=(f"{sx1}mm", f"{sy1}mm"), end=(f"{sx2}mm", f"{sy2}mm"),
                                stroke="#f5f5f5", stroke_width=f"{grid_stroke_mm}mm"))
    dwg.add(layer_grid)

    # 3) axes
    layer_axes = dwg.g(id="axes", **{"inkscape:groupmode":"layer", "inkscape:label":"Axes"})
    axis_stroke_mm = params.get("axis_stroke_mm", 0.6)
    sx1, sy1 = data_to_svg_coords(xlim[0], 0.0, xlim, ylim, fig_w_mm, fig_h_mm)
    sx2, sy2 = data_to_svg_coords(xlim[1], 0.0, xlim, ylim, fig_w_mm, fig_h_mm)
    layer_axes.add(dwg.line(start=(f"{sx1}mm", f"{sy1}mm"), end=(f"{sx2}mm", f"{sy2}mm"),
                            stroke="#000000", stroke_width=f"{axis_stroke_mm}mm"))
    sx1, sy1 = data_to_svg_coords(0.0, ylim[0], xlim, ylim, fig_w_mm, fig_h_mm)
    sx2, sy2 = data_to_svg_coords(0.0, ylim[1], xlim, ylim, fig_w_mm, fig_h_mm)
    layer_axes.add(dwg.line(start=(f"{sx1}mm", f"{sy1}mm"), end=(f"{sx2}mm", f"{sy2}mm"),
                            stroke="#000000", stroke_width=f"{axis_stroke_mm}mm"))
    dwg.add(layer_axes)

    # 4) curves
    layer_curves = dwg.g(id="curves", **{"inkscape:groupmode":"layer", "inkscape:label":"Curves"})
    funcs_expr = params.get("functions", ["x"])
    curve_styles = params.get("curve_styles", ["solid"]*len(funcs_expr))
    n_samples = params.get("n_curve_samples", 800)

    # build callable functions from strings (evaluated safely with numpy)
    funcs = []
    for expr in funcs_expr:
        expr_str = str(expr)
        def make_func(expression):
            def f(x):
                return eval(expression, {"np": np, "x": x, "__builtins__": {}})
            return f
        funcs.append(make_func(expr_str))

    x_cont = np.linspace(xlim[0], xlim[1], n_samples)
    curve_stroke_mm = params.get("curve_stroke_mm", 0.9)
    for i, f in enumerate(funcs):
        ys = f(x_cont)
        pts_svg = [ data_to_svg_coords(xv, yv, xlim, ylim, fig_w_mm, fig_h_mm) for xv, yv in zip(x_cont, ys) ]
        pts_str = [ (f"{px:.6f}mm", f"{py:.6f}mm") for px,py in pts_svg ]
        dash = svg_stroke_dash(curve_styles[i] if i < len(curve_styles) else "solid")
        stroke_kwargs = {"stroke":"#222222", "fill":"none", "stroke_width":f"{curve_stroke_mm}mm"}
        if dash:
            stroke_kwargs["stroke_dasharray"] = dash
        layer_curves.add(dwg.polyline(points=[(x,y) for x,y in pts_str], **stroke_kwargs))
    dwg.add(layer_curves)

    # 5) markers
    layer_markers = dwg.g(id="markers", **{"inkscape:groupmode":"layer", "inkscape:label":"Markers"})
    marker_shapes = params.get("marker_shapes", ["o"])
    marker_sizes = params.get("marker_sizes_mm", [3.0])
    # marker_xs: either "adaptive_default" or explicit list
    marker_xs_param = params.get("marker_xs", "adaptive_default")
    if marker_xs_param == "adaptive_default":
        marker_xs = make_default_marker_xs(xlim)
    else:
        # expect a list of lists in params
        marker_xs = marker_xs_param

    marker_edge_stroke_mm = params.get("marker_edge_stroke_mm", 0.2)
    for i, f in enumerate(funcs):
        xs = np.array(marker_xs[i]) if i < len(marker_xs) else np.array([])
        ys = f(xs) if xs.size else np.array([])
        shape = marker_shapes[i] if i < len(marker_shapes) else "o"
        size_mm = marker_sizes[i] if i < len(marker_sizes) else 3.0
        for xm, ym in zip(xs, ys):
            sx, sy = data_to_svg_coords(float(xm), float(ym), xlim, ylim, fig_w_mm, fig_h_mm)
            if shape == 'o':
                layer_markers.add(dwg.circle(center=(f"{sx}mm", f"{sy}mm"),
                                             r=f"{(size_mm/2.0):.3f}mm",
                                             fill="#ffffff", stroke="#000000",
                                             stroke_width=f"{marker_edge_stroke_mm}mm"))
            elif shape == 's':
                half = size_mm/2.0
                x0 = sx - half
                y0 = sy - half
                layer_markers.add(dwg.rect(insert=(f"{x0}mm", f"{y0}mm"),
                                           size=(f"{size_mm}mm", f"{size_mm}mm"),
                                           fill="#ffffff", stroke="#000000",
                                           stroke_width=f"{marker_edge_stroke_mm}mm"))
            elif shape == '^':
                a = size_mm
                h = (math.sqrt(3)/2.0) * a
                v1 = (sx, sy - 2*h/3.0)
                v2 = (sx - a/2.0, sy + h/3.0)
                v3 = (sx + a/2.0, sy + h/3.0)
                layer_markers.add(dwg.polygon(points=[(f"{v1[0]}mm", f"{v1[1]}mm"),
                                                      (f"{v2[0]}mm", f"{v2[1]}mm"),
                                                      (f"{v3[0]}mm", f"{v3[1]}mm")],
                                              fill="#ffffff", stroke="#000000", stroke_width=f"{marker_edge_stroke_mm}mm"))
            else:
                layer_markers.add(dwg.circle(center=(f"{sx}mm", f"{sy}mm"),
                                             r=f"{(size_mm/2.0):.3f}mm",
                                             fill="#ffffff", stroke="#000000",
                                             stroke_width=f"{marker_edge_stroke_mm}mm"))
    dwg.add(layer_markers)

    # 6) ticks (small axis marks)
    layer_ticks = dwg.g(id="ticks", **{"inkscape:groupmode":"layer", "inkscape:label":"Ticks"})
    tick_len_mm = 0.8
    for yv in yticks:
        sx1, sy1 = data_to_svg_coords(0.12, yv, xlim, ylim, fig_w_mm, fig_h_mm)
        sx2, sy2 = data_to_svg_coords(-0.12, yv, xlim, ylim, fig_w_mm, fig_h_mm)
        layer_ticks.add(dwg.line(start=(f"{sx1}mm", f"{sy1}mm"), end=(f"{sx2}mm", f"{sy2}mm"),
                                 stroke="#000000", stroke_width=f"{axis_stroke_mm}mm"))
    for xv in xticks:
        sx1, sy1 = data_to_svg_coords(xv, 0.12, xlim, ylim, fig_w_mm, fig_h_mm)
        sx2, sy2 = data_to_svg_coords(xv, -0.12, xlim, ylim, fig_w_mm, fig_h_mm)
        layer_ticks.add(dwg.line(start=(f"{sx1}mm", f"{sy1}mm"), end=(f"{sx2}mm", f"{sy2}mm"),
                                 stroke="#000000", stroke_width=f"{axis_stroke_mm}mm"))
    dwg.add(layer_ticks)

    # 7) braille labels: each label as sub-group (translated to absolute svg coords)
    layer_braille = dwg.g(id="braille", **{"inkscape:groupmode":"layer", "inkscape:label":"Braille"})
    for lbl in params.get("braille_labels", []):
        text = lbl.get("text", "")
        pos = lbl.get("position_mm", [0.0, 0.0])  # coordenadas centradas (-w/2..w/2)
        d_diam = float(lbl.get("dot_diameter_mm", 1.5))
        d_sp = float(lbl.get("dot_spacing_mm", 2.5))
        c_sp = float(lbl.get("char_spacing_mm", 3.0))
        l_sp = float(lbl.get("line_spacing_mm", 4.0))
        # create sub-group for label
        sub_id = f"braille_{text.replace(' ', '_')}"
        sub = dwg.g(id=sub_id, **{"inkscape:groupmode":"layer", "inkscape:label":f"Braille: {text}"})
        # render braille group (relative coords)
        braille_group = render_braille_to_group(dwg, text,
                                                origin_mm=(0.0, 0.0),
                                                dot_diameter_mm=d_diam,
                                                dot_spacing_mm=d_sp,
                                                char_spacing_mm=c_sp,
                                                line_spacing_mm=l_sp)
        # translate group from centered coordinates to absolute svg coordinates
        # compute transform: origin centered (-w/2..w/2) -> svg coord
        ox_mm = pos[0] + fig_w_mm / 2.0   # center->svg x
        oy_mm = fig_h_mm / 2.0 - pos[1]   # center->svg y (invert)
        # append braille_group children into sub with translation
        # simplest: wrap braille_group into <g transform="translate(ox,oy)">
        trans = f"translate({ox_mm},{oy_mm})"
        sub.add(dwg.g(braille_group.elements, transform=trans))
        layer_braille.add(sub)
    dwg.add(layer_braille)

    # Save file
    dwg.save()
    print(f"SVG saved to: {output_svg}")

# -----------------------
# ENTRY POINT
# -----------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_svg_from_params.py params.json")
        sys.exit(1)
    params_path = sys.argv[1]
    params = load_params(params_path)
    build_svg_from_params(params)
