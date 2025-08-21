import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrow

# Conversión mm → pulgadas
def mm2in(mm):
    return mm / 25.4  # conversión real para el lienzo físico

def mm2pt(mm):
    return mm * 2.83465

def marco_a5_con_ejes(cfg):
    # Crear figura del tamaño físico del A5
    fig_w_in = mm2in(cfg['a5_size_mm'][0])
    fig_h_in = mm2in(cfg['a5_size_mm'][1])
    fig, ax = plt.subplots(figsize=(fig_w_in, fig_h_in), dpi=cfg['dpi'])

    # Configurar ejes en mm reales
    ax.set_xlim(0, cfg['a5_size_mm'][0])
    ax.set_ylim(0, cfg['a5_size_mm'][1])
    ax.set_aspect('equal')

    # Quitar ticks y etiquetas
    ax.axis('off')

    # Marco A5
    marco_lw_pt = mm2pt(cfg['frame_linewidth_mm'])
    rect = Rectangle((0, 0),
                     cfg['a5_size_mm'][0], cfg['a5_size_mm'][1],
                     fill=False, linewidth=marco_lw_pt, edgecolor='black')
    ax.add_patch(rect)

    # Eje X con flecha
    ax.add_patch(FancyArrow(0, cfg['a5_size_mm'][1] / 2,
                            cfg['a5_size_mm'][0] + cfg['axis_extension_mm'], 0,
                            width=0.5,
                            head_width=3,
                            head_length=5,
                            linewidth=mm2pt(cfg['axis_linewidth_mm']),
                            color='black',
                            length_includes_head=True))

    # Eje Y con flecha
    ax.add_patch(FancyArrow(cfg['a5_size_mm'][0] / 2, 0,
                            0, cfg['a5_size_mm'][1] + cfg['axis_extension_mm'],
                            width=0.5,
                            head_width=3,
                            head_length=5,
                            linewidth=mm2pt(cfg['axis_linewidth_mm']),
                            color='black',
                            length_includes_head=True))

    # Forzar a ocupar todo el lienzo sin recorte
    ax.set_position([0, 0, 1, 1])

    # Guardar sin recortar nada
    plt.savefig(cfg['output_filename'], format='svg', bbox_inches=None)
    plt.show()


# Configuración
config_a5 = {
    'a5_size_mm': (210, 148.5),  # A5 horizontal
    'dpi': 96,
    'frame_linewidth_mm': 0.6,
    'axis_linewidth_mm': 0.6,
    'axis_extension_mm': 10,  # cuanto sobresale la flecha
    'output_filename': 'marco_a5_flechas.svg'
}

marco_a5_con_ejes(config_a5)
