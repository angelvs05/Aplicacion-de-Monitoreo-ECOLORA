# =============================================================================
# ### ARCHIVO: utils.py ###
# =============================================================================
import matplotlib.patches as mpatches
import numpy as np
import matplotlib.dates as mdates

def convert_temp(value, unit_pref):
    """Convierte temperatura a la unidad preferida por el usuario."""
    if value is None:
        return None
    if unit_pref == 'C':
        return round(value, 2)
    return round((value * 9/5) + 32, 2)

def convert_pressure(value, unit_pref):
    """Convierte presión a la unidad preferida por el usuario."""
    if value is None:
        return None
    if unit_pref == 'hPa':
        return round(value, 2)
    return round(value * 0.02953, 2)

def create_gauge(ax, label, value, min_val, max_val, unit, color):
    """Dibuja un único medidor (gauge) en un eje de Matplotlib (ax)."""
    ax.clear()
    ax.set_facecolor("#242424")
    ax.set_aspect('equal')
    ax.add_artist(mpatches.Wedge((0, 0), 1, 0, 180, width=0.3, facecolor='#3c3c3c', zorder=1))
    ax.add_artist(mpatches.Wedge((0, 0), 1, 0, 180, width=0.05, facecolor='gray', zorder=2))
    angle, value_display, draw_wedge = 180, "--", False
    try:
        numeric_value = float(value)
        if np.isfinite(numeric_value):
            clipped = max(min_val, min(max_val, numeric_value))
            norm_value = (clipped - min_val) / (max_val - min_val)
            angle = 180 * (1 - norm_value)
            value_display = f"{numeric_value:.1f}"
            draw_wedge = True
    except (ValueError, TypeError):
        pass
    if draw_wedge:
        ax.add_artist(mpatches.Wedge((0, 0), 1, angle, 180, width=0.3, facecolor=color, zorder=3))
    ax.text(0, 0.1, value_display, ha='center', va='center', fontsize=22, color='white', weight='bold', zorder=4)
    ax.text(0, -0.25, unit if draw_wedge else "", ha='center', va='center', fontsize=10, color='lightgray', zorder=4)
    ax.text(0, -0.65, label, ha='center', va='center', fontsize=12, color='gray', zorder=4)
    ax.set_xlim(-1.5, 1.5); ax.set_ylim(-1, 1.2); ax.axis('off')

def create_multi_gauge(ax, title, temp_val, temp_unit, hum_val, pres_val, pres_unit):
    """Dibuja un widget combinado de 3 sensores en un solo eje."""
    ax.clear()
    ax.set_facecolor("#242424")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    # Colores
    temp_color = "#e57373"  # Rojo Suave
    hum_color = "#64b5f6"   # Azul Suave
    pres_color = "#81c784"  # Verde Suave

    # Título del Nodo
    ax.text(0.5, 0.90, title, ha='center', va='center', fontsize=14, color='white', weight='bold')

    # Temperatura
    ax.text(0.05, 0.6, "Temp", ha='left', va='center', fontsize=12, color='gray')
    ax.text(0.95, 0.6, f"{temp_val or '--':>5} °{temp_unit}", ha='right', va='center', fontsize=16, color=temp_color, family='monospace')

    # Humedad
    ax.text(0.05, 0.4, "Humedad", ha='left', va='center', fontsize=12, color='gray')
    ax.text(0.95, 0.4, f"{hum_val or '--':>5} %", ha='right', va='center', fontsize=16, color=hum_color, family='monospace')

    # Presión
    ax.text(0.05, 0.2, "Presión", ha='left', va='center', fontsize=12, color='gray')
    ax.text(0.95, 0.2, f"{pres_val or '--':>5} {pres_unit}", ha='right', va='center', fontsize=16, color=pres_color, family='monospace')

def draw_graph_widget(ax_temp, ax_hum, data):
    """Dibuja una gráfica de sensores en los ejes proporcionados."""
    ax_temp.clear()
    ax_hum.clear()
    ax_temp.grid(True, linestyle='--', alpha=0.5, color='gray')
    if data and data['timestamps']:
        line_temp, = ax_temp.plot(data['timestamps'], data['temperature'], '-', label="Temperatura", color="#e57373")
        line_hum, = ax_hum.plot(data['timestamps'], data['humidity'], '-', label="Humedad", color="#64b5f6")
        legend = ax_temp.legend(handles=[line_temp, line_hum], loc='upper left', facecolor='#3c3c3c', edgecolor='white', fontsize='small')
        for text in legend.get_texts(): text.set_color("white")
    ax_temp.set_ylim(0, 50)
    ax_hum.set_ylim(0, 100)
    ax_temp.figure.autofmt_xdate()
    ax_temp.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))