# =============================================================================
# ### ARCHIVO: tabs/map_tab.py ###
# =============================================================================
import customtkinter as ctk
from tkintermapview import TkinterMapView
from datetime import datetime, timezone, timedelta
import os
import json
from PIL import Image, ImageTk

class MapTab(ctk.CTkFrame):
    def __init__(self, master, app_instance):
        super().__init__(master) # Se eliminó fg_color="transparent" para compatibilidad
        
        self.app = app_instance
        self.db = app_instance.db_manager
        self.map_markers = {}
        self.is_satellite_view = False
        self.icon_cache = {}
        self.network_paths = []

        # Cargar el ícono por defecto al iniciar
        self.load_icon("default.png")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.map_widget = TkinterMapView(self, corner_radius=10)
        self.map_widget.grid(row=0, column=0, sticky="nsew")
        
        # URLs para los tipos de mapa
        self.map_url = "https://mt0.google.com/vt/lyrs=m&hl=es&x={x}&y={y}&z={z}&s=Ga"
        self.satellite_url = "https://mt0.google.com/vt/lyrs=s&hl=es&x={x}&y={y}&z={z}&s=Ga"
        
        self.map_widget.set_tile_server(self.map_url, max_zoom=22)
        self.map_widget.set_position(27.0732, -109.7445) # Navojoa, Sonora
        self.map_widget.set_zoom(12)

        # --- Controles del Mapa ---
        controls_frame = ctk.CTkFrame(self.map_widget, fg_color="transparent")
        controls_frame.place(relx=0.02, rely=0.02, anchor="nw")
        ctk.CTkButton(controls_frame, text="Centrar en mi Nodo", width=150, command=self.center_map_on_local_node).pack(side="left", padx=(0, 10))
        ctk.CTkButton(controls_frame, text="Solicitar Posiciones", width=160, command=self.app.request_all_positions).pack(side="left", padx=(0, 10))
        
        self.map_view_button = ctk.CTkButton(controls_frame, text="Vista Satélite", width=120, command=self.toggle_map_view)
        self.map_view_button.pack(side="left", padx=(0, 10))
        
        self.show_links_var = ctk.StringVar(value="off")
        self.show_links_switch = ctk.CTkSwitch(controls_frame, text="Mostrar Enlaces", variable=self.show_links_var, onvalue="on", offvalue="off", command=self.draw_network_links)
        self.show_links_switch.pack(side="left", padx=10)

        # --- Panel de Información del Marcador ---
        self.map_info_frame = ctk.CTkFrame(self.map_widget, corner_radius=10)
        self.map_info_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(self.map_info_frame, text="X", width=20, command=self.map_info_frame.place_forget).grid(row=0, column=2, sticky="ne", padx=5, pady=5)
        self.map_info_alias = ctk.CTkLabel(self.map_info_frame, text="Alias:", font=ctk.CTkFont(weight="bold"))
        self.map_info_alias.grid(row=0, column=0, columnspan=2, padx=10, pady=(5,0), sticky="w")
        
        ctk.CTkLabel(self.map_info_frame, text="Coords:").grid(row=1, column=0, sticky="w", padx=10, pady=2)
        self.map_info_coords = ctk.CTkLabel(self.map_info_frame, text="--")
        self.map_info_coords.grid(row=1, column=1, sticky="w", padx=10, pady=2)
        
        ctk.CTkLabel(self.map_info_frame, text="Batería:").grid(row=2, column=0, sticky="w", padx=10, pady=2)
        self.map_info_battery = ctk.CTkLabel(self.map_info_frame, text="--")
        self.map_info_battery.grid(row=2, column=1, sticky="w", padx=10, pady=2)
        
        ctk.CTkLabel(self.map_info_frame, text="SNR/RSSI:").grid(row=3, column=0, sticky="w", padx=10, pady=2)
        self.map_info_signal = ctk.CTkLabel(self.map_info_frame, text="--")
        self.map_info_signal.grid(row=3, column=1, sticky="w", padx=10, pady=2)

        ctk.CTkLabel(self.map_info_frame, text="Temp/Hum:").grid(row=4, column=0, sticky="w", padx=10, pady=2)
        self.map_info_sensors = ctk.CTkLabel(self.map_info_frame, text="-- / --")
        self.map_info_sensors.grid(row=4, column=1, sticky="w", padx=10, pady=2)
        
        ctk.CTkLabel(self.map_info_frame, text="Última vez:").grid(row=5, column=0, sticky="w", padx=10, pady=2)
        self.map_info_lastseen = ctk.CTkLabel(self.map_info_frame, text="--")
        self.map_info_lastseen.grid(row=5, column=1, columnspan=2, sticky="w", padx=10, pady=(2,10))

    def load_icon(self, icon_name, size=(30, 30)):
        cache_key = f"{icon_name}_{size[0]}x{size[1]}"
        if cache_key in self.icon_cache:
            return self.icon_cache[cache_key]
        
        icon_path = os.path.join("assets", icon_name)
        if os.path.exists(icon_path):
            try:
                # Usar ImageTk para compatibilidad con TkinterMapView
                img = Image.open(icon_path).resize(size, Image.Resampling.LANCZOS)
                photo_image = ImageTk.PhotoImage(img)
                self.icon_cache[cache_key] = photo_image
                return photo_image
            except Exception as e:
                self.app.log_queue.put(("ERROR", f"Al cargar el ícono '{icon_name}': {e}"))
        
        if icon_name == "default.png":
            self.icon_cache[cache_key] = None
        return self.icon_cache.get(f"default.png_{size[0]}x{size[1]}")

    def toggle_map_view(self):
        if self.is_satellite_view:
            self.map_widget.set_tile_server(self.map_url)
            self.map_view_button.configure(text="Vista Satélite")
            self.is_satellite_view = False
        else:
            self.map_widget.set_tile_server(self.satellite_url)
            self.map_view_button.configure(text="Vista Mapa")
            self.is_satellite_view = True

    def draw_network_links(self):
        for path in self.network_paths:
            path.delete()
        self.network_paths = []

        if self.show_links_var.get() == "off":
            return
            
        if not self.app.local_node_id: return
        links = self.db.get_all_links()
        local_node_data = self.db.get_node(self.app.local_node_id)
        if not local_node_data or local_node_data[7] is None:
            return

        gateway_pos = (local_node_data[7], local_node_data[8])

        for source_id, target_id, snr in links:
            if target_id == self.app.local_node_id:
                node_data = self.db.get_node(source_id)
                if node_data and node_data[7] is not None:
                    node_pos = (node_data[7], node_data[8])
                    
                    color = "#d62728" # Rojo (Mala)
                    if snr is not None:
                        if snr > 5: color = "#2ca02c" # Verde (Buena)
                        elif snr > 0: color = "#FFA500" # Naranja (Regular)
                    
                    path = self.map_widget.set_path([gateway_pos, node_pos], color=color, width=2)
                    self.network_paths.append(path)

    def update_map_marker(self, node_id, lat, lon):
        node_info = self.db.get_node(node_id)
        if not node_info: return
        
        alias, ui_prefs_str = node_info[1], node_info[9]
        
        icon_image = self.load_icon("default.png")
        if ui_prefs_str:
            try:
                prefs = json.loads(ui_prefs_str)
                if prefs.get('icon'):
                    loaded_icon = self.load_icon(prefs['icon'])
                    if loaded_icon:
                        icon_image = loaded_icon
            except (json.JSONDecodeError, TypeError):
                pass
        
        if node_id in self.map_markers:
            marker = self.map_markers[node_id]
            if marker.position != (lat, lon):
                marker.set_position(lat, lon)
            marker.set_text(alias or node_id)
            if marker.icon != icon_image:
                marker.set_icon(icon_image)
        else:
            marker = self.map_widget.set_marker(lat, lon, text=alias or node_id, command=self.on_marker_click, icon=icon_image)
            marker.data = node_id
            self.map_markers[node_id] = marker
    
    def on_marker_click(self, marker):
        node_id = marker.data
        node_data = self.db.get_node(node_id)
        if not node_data: return
        
        _, alias, last_seen, bat, snr, rssi, _, lat, lon, _ = node_data
        
        last_reading = self.db.get_last_reading(node_id)
        temp_str = f"{last_reading['temperature']:.1f}°C" if last_reading and last_reading.get('temperature') is not None else "--"
        hum_str = f"{last_reading['humidity']:.1f}%" if last_reading and last_reading.get('humidity') is not None else "--"

        self.map_info_alias.configure(text=alias or node_id)
        self.map_info_coords.configure(text=f"{lat:.5f}, {lon:.5f}")
        self.map_info_battery.configure(text=f"{min(100, int(bat))}%" if bat is not None else "--")
        
        snr_text = f"{snr:.2f}" if snr is not None else "--"
        rssi_text = str(rssi) if rssi is not None else "--"
        self.map_info_signal.configure(text=f"{snr_text} / {rssi_text}")
        
        self.map_info_sensors.configure(text=f"{temp_str} / {hum_str}")
        self.map_info_lastseen.configure(text=str(last_seen).split('.')[0] if last_seen else "N/A")
        
        self.map_info_frame.place(relx=0.02, rely=0.98, anchor="sw")

    def handle_position(self, packet):
        node_id = packet['fromId']
        pos = packet['decoded'].get('position', {})
        if 'latitudeI' in pos and 'longitudeI' in pos:
            lat = pos['latitudeI'] / 1e7
            lon = pos['longitudeI'] / 1e7
            if lat != 0 and lon != 0:
                self.db.update_node_position(node_id, lat, lon)
                self.update_map_marker(node_id, lat, lon)

    def center_map_on_local_node(self):
        if self.app.local_node_id:
            local_node_data = self.db.get_node(self.app.local_node_id)
            if local_node_data and local_node_data[7] is not None and local_node_data[8] is not None:
                lat, lon = local_node_data[7], local_node_data[8]
                self.map_widget.set_position(lat, lon)
                self.map_widget.set_zoom(15)