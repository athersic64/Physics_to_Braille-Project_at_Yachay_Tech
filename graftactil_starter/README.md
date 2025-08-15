GrafTactil Starter
==================

Contenido
- app.py : FastAPI backend que genera STL y preview SVG a partir de un JSON config.
- templates/index.html : interfaz mínima para pegar el JSON y generar archivos.
- outputs/ : carpeta donde se guardan los STL/SVG generados.

Instalación (recomendada con conda)
-----------------------------------
1) Crear ambiente (recomendado conda-forge para CadQuery/OCCT):
   conda create -n graf3d python=3.11 -y
   conda activate graf3d

2) Instalar dependencias (con conda/pip):
   conda install -c conda-forge fastapi uvicorn trimesh shapely matplotlib numpy -y
   # CadQuery se instala mejor desde conda-forge:
   conda install -c conda-forge cadquery -y

3) Ejecutar el servidor:
   uvicorn app:app --reload --port 5000

4) Abrir el navegador en:
   http://127.0.0.1:5000/

Uso
---
- Abre la página, pega tu JSON config (ejemplo incluido) y pulsa Generate STL.
- Los archivos generados aparecerán en la carpeta outputs/.

Notas
-----
- CadQuery es recomendado para generar STEP/STL paramétricos. Si no necesitas CadQuery,
  el servidor seguirá generando un STL usando trimesh (si config produce marcadores).
- Este starter está pensado para desarrollo local. No desplegar con eval inseguro en producción.
- Para más funcionalidades (frontend react, edición en vivo, transform controls) sigue la guía en la documentación del proyecto.
