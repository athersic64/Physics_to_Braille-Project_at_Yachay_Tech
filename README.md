# Generador Táctil — flujo: SVG → DXF → Onshape → 3D → impresión

Proyecto para generar gráficas táctiles (marcadas + Braille) y llevarlas hasta la impresión 3D.
Este README describe el *workflow* que sigues y añade la etapa final de fabricación (Cura / Chitubox).

---

## Resumen del workflow (rápido)

1. **Generar la gráfica** (curvas, marcadores, grid, braille) en **Jupyter Notebook / Google Colab** y exportar **SVG** con tamaño físico en mm (A5 u otro).
2. **Colocar / ajustar SVG en Inkscape** sobre la plantilla base (marco A5), organizar capas (Curves, Markers, Braille, Grid).
3. **Exportar desde Inkscape a DXF** (unidades: mm) — formato para CAD.
4. **Importar DXF a Onshape** (o tu CAD preferido) y usarlo como croquis para modelado.
5. **Modelar en 3D**: extruir placa, crear cilindros para los puntos Braille y unir (Boolean union).
6. **Exportar STL** desde Onshape.
7. **Preparar impresión:**
   - **FDM**: abrir STL en **Ultimaker Cura**, ajustar parámetros (temperatura, capa, relleno), exportar **G-code**, enviar a impresora FDM.
   - **Resina (SLA/DLP/LCD)**: abrir STL en **CHITUBOX** (u otro slicer), slicear y exportar al formato del equipo (CHITUBOX soporta múltiples formatos de salida — p. ej. `.cbddlp`, `.ctb`, `.cws`, entre otros). :contentReference[oaicite:1]{index=1}

---

## Detalle paso a paso

### 1) Generar SVG en Jupyter/Colab
- Usar unidades físicas (mm) en el lienzo.  
- Forzar que Matplotlib use el área completa: `ax.set_position([0,0,1,1])`.  
- Guardar con `plt.savefig("mi.svg", format="svg", bbox_inches=None, pad_inches=0)`.  
- Verificar en Inkscape que `Documento → Unidades` esté en `mm` y el `page size` coincida con A5 si ese es tu objetivo.

**Consejo:** si notas diferencias de escala entre Matplotlib e Inkscape, revisa la conversión mm→in que usas (25.4 mm/in es la real; tú mencionaste un factor empírico 23.4555555 que a veces corrige la medida en tu flujo).

---

### 2) Inkscape — colocar / alinear / preparar
- Abrir `mi.svg` en Inkscape; abrir la plantilla A5 (o ajustar `Documento → Tamaño de página` a A5).  
- Verifica capas (Layers) y que cada grupo esté correctamente etiquetado (p. ej. `Curves`, `Markers`, `Braille`, `Grid`, `Frame`).  
- Si hay texto, convertir a trazado (`Trayecto → Convertir a trayecto`) antes de exportar para que no dependa de fuentes.  
- Ajusta posiciones en mm con la caja de Transformación.

---

### 3) Exportar DXF desde Inkscape (A5, mm)
- `Archivo → Guardar como... → AutoCAD DXF R14` (o el exportador DXF que tu versión de Inkscape provea).  
- En el diálogo de exportación: seleccionar **mm** y escala **1.0**.  
- Opciones útiles: `Convertir texto a trayecto`, `LWPOLYLINE` si está disponible.

**Alternativa programática:** usar `ezdxf` en Python para generar DXF con capas y líneas (útil para automatizar).

---

### 4) Importar DXF a Onshape
- `+ → Import` y subir el `.dxf`.  
- Comprueba **unidades = mm** durante la importación.  
- Insertar como `Sketch` en el plano deseado y limpiar geometría si hace falta.

---

### 5) Modelado 3D en Onshape (ejemplo)
- `Extrude` la placa base (p. ej. 2.5–3.0 mm de altura).  
- Para los puntos Braille, crear cilindros con:
  - diámetro aproximado: **1.2–1.8 mm**,
  - altura (saliente): **0.6–1.0 mm**,
  - separación entre centros: **2.2–2.6 mm** (ajustar según norma de braille).
- `Boolean Union` para formar un único sólido (o mantener cuerpos separados si quieres modularidad).
- Revisar y reparar mallas si Onshape o el conversor STL indica errores.

---

### 6) Exportar STL desde Onshape
- Exportar como STL (binario preferido) y en unidades **mm**.
- Comprobar la malla en un visor (MeshLab, PrusaSlicer o Cura) para asegurarse de que no hay agujeros ni errores.

---

### 7A) Impresión FDM (Cura → G-code)
**Flujo:**
1. Abrir STL en Cura.
2. Ajustar orientaciones (aplanar la base y evitar ángulos que necesiten demasiados soportes).
3. Parche de configuración recomendada (valores iniciales, ajustar a tu impresora/filamento):
   - Nozzle: **0.4 mm**
   - Layer height: **0.12–0.20 mm** (0.12 para detalles finos en Braille)
   - Wall/Perímetro: **2–3** perímetros
   - Infill: **10–20%** (si la placa es sólida, puedes usar 0% y una base sólida)
   - Print temp (PLA): **200–210 °C**, Bed: **50–60 °C**
   - Print speed: **40–60 mm/s**
   - Retraction: según tu hotend
   - Adhesión de cama: brim si la pieza es delgada
4. Slice → `Save G-code` → transferir a impresora (SD/USB/Wi-Fi).

**Consejos para Braille en FDM**
- Usa altura de capa fina (0.12 mm) para que los puntos Braille queden nítidos.  
- Si los puntos quedan “redondeados” o deformes, sube el diámetro del punto en el modelo (ej. 1.5→1.8 mm) o aumenta la velocidad de enfriamiento.

---

### 7B) Impresión resina (CHITUBOX → formato impresora)
**Flujo:**
1. Abrir STL en CHITUBOX.
2. Ajustar orientación y soportes (las superficies planas con puntos salientes suelen funcionar mejor con la base plana y soportes mínimos en los extremos).
3. Slice con la resolución apropiada (p. ej. 50–35 µm según tu impresora).
4. Guardar/exportar en el formato que corresponda a tu impresora: CHITUBOX soporta múltiples formatos de salida (por ejemplo `.cbddlp`, `.ctb`, `.cws`, etc., según modelo y plugins). :contentReference[oaicite:2]{index=2}
5. Transferir archivo al equipo (USB, tarjeta) y proceder a impresión.

**Nota:** algunos formatos (ej. `.cws`) pueden requerir un *plugin* o una versión concreta de Chitubox para estar disponibles; revisa la versión de Chitubox y el listado de formatos en tu instalación.

---

## Recomendaciones generales / buenas prácticas
- **Unidades:** trabajar todo en mm evita errores de escala.  
- **Nombres de archivo:** incluir `size_format_material` en el nombre (ej.: `grafica_A5_PLA_0.12mm.stl`).  
- **Pruebas:** imprime una prueba pequeña con un fragmento del Braille antes de imprimir la placa entera.  
- **Alturas seguras:** para lectores táctiles humanos, suele recomendarse altura de punto entre **0.6–1.0 mm**; ajusta según experiencia y prueba táctil.  
- **Mantén backups** de `params.json` y del notebook para reproducir resultados.

---

## 📁 Estructura del repositorio

- 📄 **README.md** — Documentación principal  
- 📜 **LICENSE** — Licencia (ej. MIT)  
- 📓 **notebooks/**
  - 📘 `generar_svg.ipynb` — Notebook para crear SVG desde Jupyter/Colab  
- 🧰 **scripts/**
  - ⚙️ `generate_svg_from_params.py` — Generador automático de SVG  
  - 🧩 `add_braille_layer.py` — Inserta capa Braille en el SVG  
  - 🔧 `export_frame_axes_svg_dxf.py` — Exporta a SVG y DXF (A5)  
- 🔧 **params.json** — Parámetros editables (figuras, tamaño, braille...)  
- 🖼️ **templates/**
  - 🗂️ `A5_template.svg` — plantilla base A5 para Inkscape  
- 📂 **outputs/** (resultados)
  - 🖼️ `*.svg`  
  - 📐 `*.dxf`  
  - 🧱 `*.stl`  
  - 🖨️ `*.gcode`
