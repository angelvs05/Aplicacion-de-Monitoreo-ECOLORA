# Archivo de configuración para almacenar constantes y parámetros globales.

# --- Base de Datos ---
DB_NAME = "ecolora_data.db"

# --- Interfaz Gráfica ---
UPDATE_INTERVAL_MS = 1000  # Intervalo de actualización de la GUI en milisegundos
GRAPH_MAX_POINTS = 100     # Número máximo de puntos a mostrar en los gráficos en tiempo real

# --- Mapeo de Nodos ---
# Asigna nombres amigables a los IDs de tus nodos Meshtastic.
# El ID debe estar en formato hexadecimal con un '!' al principio.
# Ejemplo: '!a1b2c3d4': "Sensor del Jardín"
NODE_ALIASES = {
    '!433c1f6c': "Nodo 1f6c",
    '!3bffe0': "Nodo ffe0",
    # Añade aquí los alias de tus otros nodos
}

