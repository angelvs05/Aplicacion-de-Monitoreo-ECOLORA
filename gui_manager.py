# =============================================================================
# ### ARCHIVO: gui_manager.py ###
# =============================================================================
import customtkinter as ctk
import queue
import time
import threading
from datetime import datetime, timedelta
from tkinter import messagebox
from PIL import Image
import os
import json

try:
    from plyer import notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False
    print("Advertencia: La librería 'plyer' no está instalada. Las notificaciones de escritorio no funcionarán.")

from serial_manager import SerialManager
from database_manager import DatabaseManager
from data_processor import DataProcessor
import config
import utils

from tabs.dashboard_tab import DashboardTab
from tabs.node_detail_tab import NodeDetailTab
from tabs.map_tab import MapTab
from tabs.messaging_tab import MessagingTab
from tabs.history_tab import HistoryTab
from tabs.analysis_tab import AnalysisTab
from tabs.serial_monitor_tab import SerialMonitorTab
from tabs.settings_window import SettingsWindow
# La importación de ToolTip ha sido eliminada

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.db_manager = DatabaseManager(config.DB_NAME)
        self.load_user_preferences()

        if os.path.exists("ecolora_logo.ico"):
            self.iconbitmap("ecolora_logo.ico")

        self.title("ECOLORA - Panel de Monitoreo y Control")
        self.geometry("1400x900")
        self.minsize(1200, 750)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.is_connected = False
        self.selected_node_id = None
        self.local_node_id = None
        self.settings_window = None
        self.original_status_text = "Desconectado"
        self.tabs = {}
        self.full_packet_queue = queue.Queue()
        self.log_queue = queue.Queue()
        self.error_queue = queue.Queue()
        self.alert_queue = queue.Queue()

        self.data_processor = DataProcessor(self.db_manager, self.log_queue)
        self.serial_manager = SerialManager(self.full_packet_queue, self.update_status_bar, self.log_queue, self.error_queue)

        self.create_widgets()
        self.load_initial_data() 
        
        self.after(100, self.process_queues)
        self.after(300000, self.check_node_heartbeats)

    def load_user_preferences(self):
        appearance_mode = self.db_manager.get_setting("appearance_mode", "dark")
        color_theme = self.db_manager.get_setting("color_theme", "green")
        ctk.set_appearance_mode(appearance_mode)
        ctk.set_default_color_theme(color_theme)

    def check_node_heartbeats(self):
        self.log_queue.put(("HEARTBEAT", "Verificando estado de los nodos..."))
        nodes = self.db_manager.get_nodes()
        now = datetime.now()

        for node in nodes:
            node_id, alias, last_seen_str, _, _, _, _, _, _, _ = node
            if node_id == self.local_node_id: continue

            if last_seen_str:
                last_seen_dt = datetime.fromisoformat(last_seen_str)
                if (now - last_seen_dt) > timedelta(minutes=30):
                    last_alert = self.db_manager.get_last_alert_for_node(node_id)
                    if not last_alert or "Desconectado" not in last_alert[0]:
                        message = "El nodo no ha reportado datos en más de 30 minutos."
                        self.db_manager.insert_alert(node_id, message, "CRITICAL")
                        self.alert_queue.put((f"Alerta de Conexión: {alias or node_id[-4:]}", message))

        self.after(300000, self.check_node_heartbeats)

    def create_widgets(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.create_left_menu()
        self.create_main_content()
        self.create_status_bar()
        self.create_loading_overlay()

    def create_left_menu(self):
        self.left_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.left_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.left_frame.grid_rowconfigure(4, weight=1)
        
        logo_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=20, pady=20)
        if os.path.exists("ecolora_logo.png"):
            self.logo_image = ctk.CTkImage(Image.open("ecolora_logo.png"), size=(70, 70)) 
            ctk.CTkLabel(logo_frame, image=self.logo_image, text="").pack(side="left", padx=(0, 10))
        ctk.CTkLabel(logo_frame, text="ECOLORA", font=ctk.CTkFont(size=20, weight="bold")).pack(side="left")
        
        connection_frame = ctk.CTkFrame(self.left_frame)
        connection_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        
        ctk.CTkLabel(connection_frame, text="Puerto COM:").pack(pady=(10,0))
        
        port_frame = ctk.CTkFrame(connection_frame, fg_color="transparent")
        port_frame.pack(padx=10, pady=5, fill="x")
        port_frame.grid_columnconfigure(0, weight=1)

        available_ports = self.serial_manager.get_available_ports()
        auto_detected_port = self.serial_manager.find_meshtastic_port()
        self.port_combobox = ctk.CTkComboBox(port_frame, values=available_ports)
        if auto_detected_port: self.port_combobox.set(auto_detected_port)
        elif available_ports: self.port_combobox.set(available_ports[0])
        else: self.port_combobox.set("No hay puertos")
        self.port_combobox.grid(row=0, column=0, sticky="ew")

        self.rescan_button = ctk.CTkButton(port_frame, text="⟳", width=30, command=self.rescan_com_ports)
        self.rescan_button.grid(row=0, column=1, padx=(5,0))
        
        self.connect_button = ctk.CTkButton(connection_frame, text="Conectar", command=self.toggle_connection)
        self.connect_button.pack(padx=10, pady=10, fill="x")

    def rescan_com_ports(self):
        self.log_queue.put(("INFO", "Rescaneando puertos COM..."))
        available_ports = self.serial_manager.get_available_ports()
        self.port_combobox.configure(values=available_ports)
        auto_detected_port = self.serial_manager.find_meshtastic_port()
        if auto_detected_port:
            self.port_combobox.set(auto_detected_port)
            self.log_queue.put(("INFO", f"Puerto Meshtastic detectado en {auto_detected_port}."))
        elif available_ports:
            self.port_combobox.set(available_ports[0])
        else:
            self.port_combobox.set("No hay puertos")

    def create_main_content(self):
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        if os.path.exists("settings_icon.png"):
            self.settings_image = ctk.CTkImage(Image.open("settings_icon.png"), size=(24, 24))
            self.settings_button = ctk.CTkButton(header_frame, image=self.settings_image, text="", width=30, command=self.open_settings)
            self.settings_button.pack(side="right")
        
        self.tab_view = ctk.CTkTabview(self.main_frame, anchor="w", command=self.on_tab_change)
        self.tab_view.grid(row=1, column=0, sticky="nsew")

        self.tab_view.add("Dashboard")
        self.tab_view.add("Detalle de Nodo")
        self.tab_view.add("Mapa de Nodos")
        self.tab_view.add("Mensajes")
        self.tab_view.add("Historial")
        self.tab_view.add("Análisis y Alertas")
        self.tab_view.add("Monitor Serial")

        self.tabs['dashboard'] = DashboardTab(self.tab_view.tab("Dashboard"), self)
        self.tabs['dashboard'].pack(fill="both", expand=True)
        self.tabs['detail'] = NodeDetailTab(self.tab_view.tab("Detalle de Nodo"), self) 
        self.tabs['detail'].pack(fill="both", expand=True)
        self.tabs['map'] = MapTab(self.tab_view.tab("Mapa de Nodos"), self)
        self.tabs['map'].pack(fill="both", expand=True)
        self.tabs['msg'] = MessagingTab(self.tab_view.tab("Mensajes"), self)
        self.tabs['msg'].pack(fill="both", expand=True)
        self.tabs['history'] = HistoryTab(self.tab_view.tab("Historial"), self)
        self.tabs['history'].pack(fill="both", expand=True)
        self.tabs['analysis'] = AnalysisTab(self.tab_view.tab("Análisis y Alertas"), self)
        self.tabs['analysis'].pack(fill="both", expand=True)
        self.tabs['serial'] = SerialMonitorTab(self.tab_view.tab("Monitor Serial"), self)
        self.tabs['serial'].pack(fill="both", expand=True)
        
    def create_status_bar(self):
        self.status_label = ctk.CTkLabel(self, text="Desconectado", anchor="w", height=20)
        self.status_label.grid(row=1, column=1, padx=10, pady=(0, 10), sticky="ew")

    def create_loading_overlay(self):
        self.overlay_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.loading_label = ctk.CTkLabel(self.overlay_frame, text="Sincronizando con la red...", font=ctk.CTkFont(size=18))
        self.loading_label.pack(pady=(150, 20), padx=50)
        self.progress_bar = ctk.CTkProgressBar(self.overlay_frame, width=300)
        self.progress_bar.pack(pady=10)

    def load_initial_data(self):
        self.update_node_selectors()
        self.tabs['msg'].load_message_history()
        nodes = self.db_manager.get_nodes()
        for node_data in nodes:
            node_id, _, _, _, _, _, _, lat, lon, _ = node_data
            if lat is not None and lon is not None:
                self.tabs['map'].update_map_marker(node_id, lat, lon)

    def process_queues(self):
        self.process_full_packet_queue()
        self.tabs['serial'].process_log_queue()
        self.process_error_queue()
        self.process_alert_queue()
        self.after(config.UPDATE_INTERVAL_MS, self.process_queues)

    def process_full_packet_queue(self):
        try:
            while not self.full_packet_queue.empty():
                packet = self.full_packet_queue.get_nowait()
                
                try:
                    packet_str = json.dumps(packet, indent=2)
                    self.log_queue.put(("DEBUG", f"Paquete JSON recibido:\n{packet_str}"))
                except Exception:
                    self.log_queue.put(("DEBUG", f"Paquete no-JSON recibido: {packet}"))

                node_id = packet.get('fromId')
                if not node_id: continue
                if not self.db_manager.get_node(node_id):
                    alias = config.NODE_ALIASES.get(node_id, f"Nodo {node_id[-4:]}")
                    self.db_manager.register_node(node_id, alias)
                    self.update_node_selectors()
                bat = packet['decoded'].get('telemetry', {}).get('deviceMetrics', {}).get('batteryLevel')
                snr = packet.get('snr')
                rssi = packet.get('rssi')
                hops = packet.get('hopLimit')
                self.db_manager.update_node_stats(node_id, bat, snr, rssi, hops)
                
                if self.local_node_id and snr is not None:
                    self.db_manager.update_link(node_id, self.local_node_id, snr)

                portnum = packet['decoded'].get('portnum')
                if portnum == 'TEXT_MESSAGE_APP': self.tabs['msg'].handle_text_message(packet)
                elif portnum == 'TELEMETRY_APP': self.handle_telemetry(packet)
                elif portnum == 'POSITION_APP': self.handle_position(packet)
                elif portnum == 'OPAQUE_APP': self.tabs['detail'].handle_binary_sensor(packet)
        except queue.Empty:
            pass

    def process_error_queue(self):
        try:
            while not self.error_queue.empty():
                title, message = self.error_queue.get_nowait()
                messagebox.showerror(title, message)
        except queue.Empty:
            pass
            
    def process_alert_queue(self):
        try:
            while not self.alert_queue.empty():
                title, message = self.alert_queue.get_nowait()
                if PLYER_AVAILABLE:
                    notification.notify(title=title, message=message, app_name="ECOLORA", timeout=10)
                else:
                    self.log_queue.put(("WARNING", "Notificación de escritorio omitida (plyer no disponible)."))
                self.tabs['analysis'].load_alerts()
        except queue.Empty:
            pass
            
    def handle_telemetry(self, packet):
        node_id = packet['fromId']
        self.log_queue.put(("INFO", f"Procesando telemetría del nodo {node_id[-4:]}"))
        telemetry = packet['decoded'].get('telemetry', {})
        processed_data = {'node_id': node_id}
        node_info = self.db_manager.get_node(node_id)
        if node_info: processed_data['alias'] = node_info[1]
        
        if 'environmentMetrics' in telemetry:
            em = telemetry['environmentMetrics']
            if 'temperature' in em: processed_data['temperature'] = round(em['temperature'], 2)
            if 'relativeHumidity' in em: processed_data['humidity'] = round(em['relativeHumidity'], 2)
            if 'barometricPressure' in em: processed_data['pressure'] = round(em['barometricPressure'], 2)
            if 'gasResistance' in em: processed_data['iaq'] = round(em['gasResistance'], 2)
        
        if 'deviceMetrics' in telemetry:
            dm = telemetry['deviceMetrics']
            if 'batteryLevel' in dm: processed_data['battery'] = min(100, dm['batteryLevel'])

        self.data_processor.evaluate_rules(processed_data, self.serial_manager)

        analysis_message = self.data_processor.get_bot_analysis_message(processed_data)
        self.tabs['analysis'].update_log(analysis_message)

        if len(processed_data) > 1:
            smoothed_data = self.data_processor.smooth_data(processed_data)
            if smoothed_data:
                self.db_manager.insert_reading(smoothed_data)
                self.log_queue.put(("DEBUG", f"Nueva lectura guardada en BD para {node_id[-4:]}"))
                self.tabs['dashboard'].update_data(node_id, smoothed_data)
                if self.selected_node_id == node_id:
                    self.tabs['detail'].update_ui(smoothed_data)
    
    def handle_position(self, packet):
        node_id = packet['fromId']
        pos = packet['decoded'].get('position', {})
        if 'latitudeI' in pos and 'longitudeI' in pos:
            lat = pos['latitudeI'] / 1e7
            lon = pos['longitudeI'] / 1e7
            if lat != 0 and lon != 0:
                self.db_manager.update_node_position(node_id, lat, lon)
                self.tabs['map'].update_map_marker(node_id, lat, lon)

    def check_local_node_position(self, retries=5):
        if not self.is_connected or retries <= 0:
            return
        if self.serial_manager.interface and self.local_node_id:
            my_info = self.serial_manager.interface.myInfo
            if my_info and hasattr(my_info, 'position') and my_info.position and 'latitudeI' in my_info.position:
                lat = my_info.position['latitudeI'] / 1e7
                lon = my_info.position['longitudeI'] / 1e7
                if lat != 0 and lon != 0:
                    self.db_manager.update_node_position(self.local_node_id, lat, lon)
                    self.tabs['map'].update_map_marker(self.local_node_id, lat, lon)
                    self.log_queue.put(("INFO", f"Posición del nodo local actualizada: {lat:.4f}, {lon:.4f}"))
                    return
        self.log_queue.put(("DEBUG", f"No se encontró la posición del nodo local, reintentando... ({retries-1} restantes)"))
        self.after(30000, lambda: self.check_local_node_position(retries - 1))
    
    def toggle_connection(self):
        if self.is_connected:
            self.serial_manager.disconnect()
        else:
            port = self.port_combobox.get()
            if port and port != "No hay puertos":
                self.connect_button.configure(state="disabled")
                self.port_combobox.configure(state="disabled")
                self.rescan_button.configure(state="disabled")
                self.status_label.configure(text=f"Conectando a {port}...", text_color="orange")
                self.show_loading_overlay(True)
                threading.Thread(target=self.serial_manager.connect, args=(port,), daemon=True).start()
            else:
                self.update_status_bar("Seleccione un puerto", "orange", False)

    def update_status_bar(self, message, color, is_connected, local_node_num=None):
        display_message = message
        self.is_connected = is_connected
        if is_connected and local_node_num:
            self.local_node_id = f"!{local_node_num:x}"
            if not self.db_manager.get_node(self.local_node_id):
                alias = config.NODE_ALIASES.get(self.local_node_id, f"Nodo Local {self.local_node_id[-4:]}")
                self.db_manager.register_node(self.local_node_id, alias)
            node_info = self.db_manager.get_node(self.local_node_id)
            alias = node_info[1] if node_info and node_info[1] else f"Nodo {self.local_node_id[-4:]}"
            display_message = f"Conectado a {alias}"
            self.original_status_text = display_message
            self.tabs['msg'].update_channel_list()
            self.show_loading_overlay(False)
            self.connect_button.configure(text="Desconectar")
            self.update_node_selectors()
            self.after(5000, self.check_local_node_position)
        else:
            self.local_node_id = None
            self.connect_button.configure(text="Conectar")
            self.show_loading_overlay(False)
        self.status_label.configure(text=display_message, text_color=color)
        self.connect_button.configure(state="normal")
        self.port_combobox.configure(state="normal" if not is_connected else "disabled")
        self.rescan_button.configure(state="normal" if not is_connected else "disabled")
        
    def get_full_node_id_from_display(self, display_name):
        try:
            node_id_short = display_name.split('(')[-1][:-1]
            nodes_from_db = self.db_manager.get_nodes()
            return next((nid for nid, *rest in nodes_from_db if nid.endswith(node_id_short)), None)
        except (IndexError, StopIteration):
            return None

    def update_node_selectors(self):
        nodes = self.db_manager.get_nodes()
        node_list_display = [f"{n[1] or 'Sin Alias'} ({n[0][-4:]})" for n in nodes]
        self.tabs['detail'].update_node_selector(node_list_display)
        self.tabs['history'].update_node_selector(node_list_display)
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.update_rules_list_view()
            self.settings_window.update_node_list_view()
            self.settings_window.update_actuator_node_list([f"{n[1] or 'Sin Alias'} ({n[0][-4:]})" for n in nodes if n[0] != self.local_node_id])

    def select_node(self, node_id):
        self.selected_node_id = node_id
        self.tabs['detail'].select_node(node_id)
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.destroy()
        self.tab_view.set("Detalle de Nodo")

    def select_node_and_switch_tab(self, node_id):
        if self.selected_node_id != node_id:
            self.selected_node_id = node_id
            self.tabs['detail'].select_node(node_id)
        self.tab_view.set("Detalle de Nodo")

    def open_settings(self):
        if self.settings_window is None or not self.settings_window.winfo_exists():
            channel_names = ["Primary"] + [ch.settings.name for ch in self.serial_manager.get_channels() if hasattr(ch, 'settings') and ch.settings.name]
            node_list = self.db_manager.get_nodes()
            node_display_list = [f"{n[1] or 'Sin Alias'} ({n[0][-4:]})" for n in node_list if n[0] != self.local_node_id]
            self.settings_window = SettingsWindow(self, self, channel_names=channel_names, node_list=node_display_list)
            self.settings_window.grab_set()
        else:
            self.settings_window.focus()

    def show_loading_overlay(self, show=True):
        if show:
            self.overlay_frame.place(relx=0.5, rely=0.5, anchor="center")
        else:
            self.overlay_frame.place_forget()
            
    def on_tab_change(self):
        current_tab_name = self.tab_view.get()
        if "Análisis y Alertas" in current_tab_name:
            self.db_manager.mark_alerts_as_read()
            
    def request_all_positions(self):
        if not self.is_connected:
            self.log_queue.put(("ERROR", "Debes estar conectado para solicitar posiciones."))
            return
        self.serial_manager.request_all_positions()
        self.log_queue.put(("INFO", "Solicitando posiciones a todos los nodos..."))

    def on_actuator_button_press(self):
        threading.Thread(target=self._send_actuator_sequence, daemon=True).start()
    
    def _send_actuator_sequence(self):
        self.after(0, self._set_actuator_buttons_state, "disabled", "Enviando...")
        self.after(0, self.status_label.configure, {"text": "Enviando comando al actuador..."})

        try:
            node_display = self.db_manager.get_setting("actuator_node_display")
            node_id = self.get_full_node_id_from_display(node_display) if node_display else None
            start_cmd = self.db_manager.get_setting("actuator_start_cmd")
            stop_cmd = self.db_manager.get_setting("actuator_stop_cmd")
            duration_str = self.db_manager.get_setting("actuator_duration", "0")
            
            if not node_id or not start_cmd:
                self.error_queue.put(("No Configurado", "La acción del actuador no está configurada."))
                return

            if not self.serial_manager.is_node_known(node_id):
                self.error_queue.put(("Error de Envío", f"No se pudo enviar el comando.\nEl nodo objetivo ({node_id[-4:]}) no está en la red."))
                self.log_queue.put(("ERROR", f"Intento de activar acción en nodo desconocido: {node_id}"))
                return

            duration = int(duration_str) if duration_str.isdigit() else 0
            
            self.log_queue.put(("CONTROL", f"Enviando '{start_cmd}' al nodo {node_id}"))
            success = self.serial_manager.send_text_message(start_cmd, destination_id=node_id, want_ack=True)
            
            if not success:
                self.error_queue.put(("Fallo de Envío", f"El nodo actuador ({node_id[-4:]}) no respondió.\nPuede estar fuera de rango o apagado."))
                return

            self.log_queue.put(("INFO", f"Comando '{start_cmd}' confirmado por el nodo {node_id[-4:]}."))
            if duration > 0 and stop_cmd:
                self.log_queue.put(("CONTROL", f"Esperando {duration} segundos..."))
                time.sleep(duration)
                self.log_queue.put(("CONTROL", f"Enviando comando de fin '{stop_cmd}' al nodo {node_id}"))
                self.serial_manager.send_text_message(stop_cmd, destination_id=node_id, want_ack=False)
        finally:
            self.after(0, self._restore_actuator_buttons)

    def _set_actuator_buttons_state(self, state, text):
        self.tabs['detail'].actuator_button.configure(state=state, text=text)
        for widget_data in self.tabs['dashboard'].widgets.values():
            if widget_data["info"]["type"] == "actuador":
                widget_data["elements"]["button"].configure(state=state, text=text)
    def on_closing(self):
        if messagebox.askokcancel("Salir", "¿Estás seguro de que quieres salir?"):
            print("Cerrando la aplicación...")
            if self.serial_manager:
                self.serial_manager.stop() # ¡Línea clave!
            self.root.destroy()

    # Y asignarlo a la ventana
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _restore_actuator_buttons(self):
        self.tabs['detail'].update_actuator_button_state()
        for widget_data in self.tabs['dashboard'].widgets.values():
            if widget_data["info"]["type"] == "actuador":
                widget_data["elements"]["button"].configure(state="normal", text="Actuador Remoto")
        self.status_label.configure(text=self.original_status_text)

    def on_closing(self):
        if self.is_connected:
            self.serial_manager.disconnect()
        self.db_manager.close()
        self.destroy()