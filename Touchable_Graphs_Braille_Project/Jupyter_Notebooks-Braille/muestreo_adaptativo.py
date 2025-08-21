import numpy as np
import matplotlib.pyplot as plt

# Conversión mm → pt y mm → in
def mm2pt(mm):
    return mm * 2.83465

def mm2in(mm):
    return mm / 25.4

# Función generadora de muestreo adaptativo
def muestreo_adaptativo(func, x_min, x_max, segmentos, densidades):
    """
    Genera puntos de muestreo adaptativo.

    func        : función evaluable
    x_min, x_max: dominio de la función
    segmentos   : lista de pares [a, b] delimitando subintervalos
    densidades  : cantidad de puntos por cada subintervalo

    Retorna: array de puntos muestreados en x
    """
    puntos = []
    for (a, b), n_puntos in zip(segmentos, densidades):
        puntos.append(np.linspace(a, b, n_puntos))
    return np.concatenate(puntos)

# Dominio continuo
x_cont = np.linspace(-7, 7, 500)

# Dimensiones marcadores en pt
d_circ = mm2pt(3.0)
a_cuad = mm2pt(3.0)
b_tri  = mm2pt(3.8)

# Tamaño gráfico en pulgadas
fig_w_in = mm2in(168)
fig_h_in = mm2in(168)
fig, ax = plt.subplots(figsize=(fig_w_in, fig_h_in))

# Grosor de líneas en pt
lw1 = mm2pt(0.25)
lw2 = mm2pt(0.6)
lw3 = mm2pt(1.0)
lw4 = mm2pt(1.3)
lw5 = mm2pt(1.6)

# Curvas continuas
ax.plot(x_cont, x_cont, '-',  linewidth=lw3, label='$x$')
ax.plot(x_cont, x_cont**2, '--', linewidth=lw4, label='$x^2$')
ax.plot(x_cont, x_cont**3, '-.', linewidth=lw5, label='$x^3$')

# Definir segmentos y densidades personalizadas
seg_x = [[-7, 7]]
pts_x = [35]

seg_x2 = [[-7, -3], [-3, -2], [-2, -1], [-1, 1], [1, 2], [2, 3], [3, 7]]
pts_x2 = [1, 10, 7, 7, 7, 10, 1]

seg_x3 = [[-7, -2], [-2, -1.5], [-1.5, -1], [-1, 1], [1, 1.5], [1.5, 2], [2, 7]]
pts_x3 = [1, 10, 6, 6, 6, 10, 1]

# Generar muestreos adaptativos
x_marcadores_1 = muestreo_adaptativo(lambda x: x, -7, 7, seg_x, pts_x)
x_marcadores_2 = muestreo_adaptativo(lambda x: x**2, -7, 7, seg_x2, pts_x2)
x_marcadores_3 = muestreo_adaptativo(lambda x: x**3, -7, 7, seg_x3, pts_x3)

# Dibujar marcadores
ax.plot(x_marcadores_1, x_marcadores_1, linestyle='None', marker='o', markersize=d_circ, markeredgewidth=0.2, markerfacecolor='white')
ax.plot(x_marcadores_2, x_marcadores_2**2, linestyle='None', marker='s', markersize=a_cuad, markeredgewidth=0.2, markerfacecolor='white')
ax.plot(x_marcadores_3, x_marcadores_3**3, linestyle='None', marker='^', markersize=b_tri, markeredgewidth=0.2, markerfacecolor='white')

# Definir divisiones y límites de ejes
xticks = np.arange(-7, 7.5, 0.5)
yticks = np.arange(-7, 7.5, 0.5)
ax.set_xticks(xticks)
ax.set_yticks(yticks)
ax.set_xlim(-7, 7)
ax.set_ylim(-7, 7)

# Ejes en 0
ax.axhline(0, color='black', linewidth=lw2)
ax.axvline(0, color='black', linewidth=lw2)

# Cuadrícula
ax.grid(True, which='both', axis='both', color='gray', linestyle='-', linewidth=lw1)

# Ocultar etiquetas de ejes
ax.tick_params(axis='x', which='both', labeltop=False, labelbottom=False, length=0)
ax.tick_params(axis='y', which='both', labelleft=False, labelright=False, length=0)

# Marcas en los ejes
for y in np.arange(-7, 7.5, 0.5):
    ax.plot([0.15, -0.15], [y, y], color='black', linewidth=lw2)
for x in np.arange(-7, 7.5, 0.5):
    ax.plot([x, x], [0.15, -0.15], color='black', linewidth=lw2)

# Márgenes y aspecto
plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)
ax.set_aspect(1)

# Guardar SVG
plt.savefig('x_x2_x3_tactil_adaptativo_funcion.svg', format='svg', bbox_inches='tight')

# Mostrar
plt.show()
