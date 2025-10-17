# =============================================================================
# ### ARCHIVO: tabs/map_tab.py (CORREGIDO) ###
# =============================================================================
import customtkinter as ctk
from tkintermapview import TkinterMapView
from utils import PilImage, PilImageTk

class MapTab(ctk.CTkFrame):
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db_manager = db_manager
        self.markers = {}
        self.map_initialized = False # <-- NUEVO: Bandera para controlar el centrado inicial

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.map_widget = TkinterMapView(self, corner_radius=10)
        self.map_widget.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Inicia en una vista general del mundo, esperando datos
        self.map_widget.set_zoom(1) 
        self.map_widget.set_position(20, 0) # Una posición neutral

    def update_node_on_map(self, node_id, alias, lat, lon):
        if lat is None or lon is None:
            return

        # <-- NUEVO: Centra el mapa en la primera coordenada recibida
        if not self.map_initialized:
            self.map_widget.set_position(lat, lon)
            self.map_widget.set_zoom(15)
            self.map_initialized = True

        marker_text = f"{alias}\n({node_id[-4:]})"
        
        if node_id in self.markers:
            # Actualiza la posición del marcador existente
            self.markers[node_id].set_position(lat, lon)
            self.markers[node_id].set_text(marker_text)
        else:
            # Crea un nuevo marcador si no existe
            new_marker = self.map_widget.set_marker(
                lat, lon, text=marker_text,
                text_color="#FFFFFF", marker_color_circle="#242424",
                marker_color_outside="#565B5E"
            )
            self.markers[node_id] = new_marker

    def clear_map(self):
        """Elimina todos los marcadores del mapa."""
        for marker in self.markers.values():
            marker.delete()
        self.markers = {}
        self.map_initialized = False # Resetea la bandera si se limpia el mapa
        print("Mapa limpiado, todos los marcadores eliminados.")