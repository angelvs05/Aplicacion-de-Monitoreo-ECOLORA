# =============================================================================
# ### ARCHIVO: tabs/node_detail_tab.py ###
# =============================================================================
import customtkinter as ctk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter import messagebox
from datetime import datetime
import json
import config
import utils

class NodeDetailTab(ctk.CTkFrame):
    def __init__(self, master, app_instance):
        super().__init__(master, fg_color="transparent")
        self.app = app_instance
        self.db = app_instance.db_manager
        
        self.latest_sensor_data = {}
        self.latest_binary_data = {}
        self.node_graph_data = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # --- Controles Superiores ---
        controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        controls_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        ctk.CTkLabel(controls_frame, text="Monitoreando Nodo:").pack(side="left", padx=(0, 10))
        self.node_selector = ctk.CTkComboBox(controls_frame, values=["Esperando nodos..."], command=self.on_node_select)
        self.node_selector.pack(side="left", padx=(0, 20))
        
        self.graph_type_selector = ctk.CTkSegmentedButton(controls_frame, values=["Gauges", "Sensores"], command=self.on_graph_type_select)
        self.graph_type_selector.set("Gauges")
        self.graph_type_selector.pack(side="left", padx=(0, 20))
        
        self.request_button = ctk.CTkButton(controls_frame, text="Solicitar Muestra", command=self.request_telemetry)
        self.request_button.pack(side="left")

        # --- Tarjetas de Información ---
        cards_frame = ctk.CTkFrame(self)
        cards_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10), padx=10)
        self.create_info_cards(cards_frame)

        # --- Contenedor de Gráficas ---
        self.content_container = ctk.CTkFrame(self, fg_color="transparent")
        self.content_container.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        self.content_container.grid_columnconfigure(0, weight=1)
        self.content_container.grid_rowconfigure(0, weight=1)
        
        # --- LLAMADAS A LAS FUNCIONES RESTAURADAS ---
        self.create_matplotlib_graph(self.content_container)
        self.create_gauge_charts(self.content_container)

        # --- Frame Inferior ---
        bottom_frame = ctk.CTkFrame(self)
        bottom_frame.grid(row=3, column=0, padx=20, pady=5, sticky="ew")
        
        self.binary_indicator_frame = ctk.CTkFrame(bottom_frame)
        self.binary_indicator_frame.pack(side="left", padx=(0, 20))
        self.binary_indicator_light = ctk.CTkCanvas(self.binary_indicator_frame, width=20, height=20, bg="#2b2b2b", highlightthickness=0)
        self.binary_indicator_light.grid(row=0, column=0, padx=(0, 5))
        self.binary_indicator_label = ctk.CTkLabel(self.binary_indicator_frame, text="Sensor Binario: Sin Datos", anchor="w")
        self.binary_indicator_label.grid(row=0, column=1, sticky="ew")

        self.actuator_button = ctk.CTkButton(bottom_frame, text="Activar Acción", state="disabled", command=self.app.on_actuator_button_press)
        self.actuator_button.pack(side="left")
        
        self.on_graph_type_select("Gauges")
        self.update_binary_indicator()
        self.update_ui({})

    # --- FUNCIÓN RESTAURADA ---
    def create_gauge_charts(self, parent):
        self.gauge_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.gauge_frame.grid(row=0, column=0, sticky="nsew")
        self.gauge_fig = Figure(figsize=(10, 8), facecolor="#2b2b2b")
        self.gauge_axs = self.gauge_fig.subplots(2, 2)
        self.gauge_canvas = FigureCanvasTkAgg(self.gauge_fig, master=self.gauge_frame)
        self.gauge_canvas.get_tk_widget().pack(side="top", fill="both", expand=True)

    # --- FUNCIÓN RESTAURADA ---
    def create_matplotlib_graph(self, parent):
        self.live_graph_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.live_graph_frame.grid(row=0, column=0, sticky="nsew")
        self.live_graph_frame.grid_rowconfigure(0, weight=1)
        self.live_graph_frame.grid_columnconfigure(0, weight=1)
        
        self.live_fig = Figure(figsize=(5, 4), dpi=100, facecolor="#2b2b2b")
        self.live_ax_temp = self.live_fig.add_subplot(111)
        self.live_fig.subplots_adjust(right=0.85, top=0.95, bottom=0.15, left=0.1)
        self.live_ax_hum = self.live_ax_temp.twinx()
        self.live_canvas = FigureCanvasTkAgg(self.live_fig, master=self.live_graph_frame)
        self.live_canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        graph_controls_frame = ctk.CTkFrame(self.live_graph_frame, fg_color="transparent")
        graph_controls_frame.grid(row=1, column=0, pady=(5,0), sticky="ew")
        graph_controls_frame.grid_columnconfigure((0,1,2,3,4), weight=1)

        ctk.CTkButton(graph_controls_frame, text="<", width=40, command=self.pan_left).grid(row=0, column=0)
        ctk.CTkButton(graph_controls_frame, text=">", width=40, command=self.pan_right).grid(row=0, column=1)
        ctk.CTkButton(graph_controls_frame, text="-", width=40, command=self.zoom_out).grid(row=0, column=3)
        ctk.CTkButton(graph_controls_frame, text="+", width=40, command=self.zoom_in).grid(row=0, column=4)

    def request_telemetry(self):
        if not self.app.selected_node_id:
            messagebox.showwarning("Sin Nodo", "No hay ningún nodo seleccionado.", parent=self)
            return
        command = "!request_telemetry"
        self.app.log_queue.put(("CONTROL", f"Solicitando telemetría al nodo {self.app.selected_node_id}"))
        self.app.serial_manager.send_text_message(command, destination_id=self.app.selected_node_id)
        messagebox.showinfo("Comando Enviado", f"Solicitud de telemetría enviada al nodo {self.app.selected_node_id[-4:]}.", parent=self)

    def create_info_cards(self, parent):
        parent.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
        font = ctk.CTkFont(size=18)
        
        temp_frame = ctk.CTkFrame(parent, fg_color="transparent")
        temp_frame.grid(row=0, column=0, padx=5, pady=10)
        self.temp_label = ctk.CTkLabel(temp_frame, text="Temp:\n--", font=font)
        self.temp_label.pack()

        hum_frame = ctk.CTkFrame(parent, fg_color="transparent")
        hum_frame.grid(row=0, column=1, padx=5, pady=10)
        self.hum_label = ctk.CTkLabel(hum_frame, text="Humedad:\n-- %", font=font)
        self.hum_label.pack()

        pres_frame = ctk.CTkFrame(parent, fg_color="transparent")
        pres_frame.grid(row=0, column=2, padx=5, pady=10)
        self.pres_label = ctk.CTkLabel(pres_frame, text="Presión:\n--", font=font)
        self.pres_label.pack()

        iaq_frame = ctk.CTkFrame(parent, fg_color="transparent")
        iaq_frame.grid(row=0, column=3, padx=5, pady=10)
        self.iaq_label = ctk.CTkLabel(iaq_frame, text="IAQ:\n--", font=font)
        self.iaq_label.pack()

        battery_frame = ctk.CTkFrame(parent, fg_color="transparent")
        battery_frame.grid(row=0, column=4, padx=5, pady=10)
        self.battery_label = ctk.CTkLabel(battery_frame, text="Batería:\n-- %", font=font)
        self.battery_label.pack()

    def update_gauge_charts(self, data):
        data = data or {}
        temp_unit = self.db.get_setting("unit_temp", "C")
        pressure_unit = self.db.get_setting("unit_pressure", "hPa")
        
        temp_val = utils.convert_temp(data.get('temperature'), temp_unit)
        pressure_val = utils.convert_pressure(data.get('pressure'), pressure_unit)

        utils.create_gauge(self.gauge_axs[0, 0], 'Temperatura', temp_val, 0, 50 if temp_unit == 'C' else 122, f'°{temp_unit}', '#e57373')
        utils.create_gauge(self.gauge_axs[0, 1], 'Humedad', data.get('humidity'), 0, 100, '%', '#64b5f6')
        utils.create_gauge(self.gauge_axs[1, 0], 'Presión', pressure_val, 900 if pressure_unit == 'hPa' else 26.5, 1100 if pressure_unit == 'hPa' else 32.5, pressure_unit, '#81c784')
        utils.create_gauge(self.gauge_axs[1, 1], 'IAQ', data.get('iaq'), 0, 500, '', '#fff176')
        
        try: self.gauge_fig.tight_layout(pad=0.5) 
        except Exception: pass
        self.gauge_canvas.draw()
        
    def update_graph_plot(self):
        node_id = self.app.selected_node_id
        graph_data = self.node_graph_data.get(node_id)
        utils.draw_graph_widget(self.live_ax_temp, self.live_ax_hum, graph_data)
        self.live_canvas.draw()

    def pan_left(self):
        cur_xlim = self.live_ax_temp.get_xlim()
        range_val = cur_xlim[1] - cur_xlim[0]
        self.live_ax_temp.set_xlim(cur_xlim[0] - range_val*0.1, cur_xlim[1] - range_val*0.1)
        self.live_canvas.draw()

    def pan_right(self):
        cur_xlim = self.live_ax_temp.get_xlim()
        range_val = cur_xlim[1] - cur_xlim[0]
        self.live_ax_temp.set_xlim(cur_xlim[0] + range_val*0.1, cur_xlim[1] + range_val*0.1)
        self.live_canvas.draw()

    def zoom_in(self):
        cur_xlim = self.live_ax_temp.get_xlim()
        center = (cur_xlim[1] + cur_xlim[0]) / 2
        range_val = (cur_xlim[1] - cur_xlim[0]) * 0.8 / 2
        self.live_ax_temp.set_xlim(center - range_val, center + range_val)
        self.live_canvas.draw()

    def zoom_out(self):
        cur_xlim = self.live_ax_temp.get_xlim()
        center = (cur_xlim[1] + cur_xlim[0]) / 2
        range_val = (cur_xlim[1] - cur_xlim[0]) * 1.25 / 2
        self.live_ax_temp.set_xlim(center - range_val, center + range_val)
        self.live_canvas.draw()

    def update_graph_data(self, data):
        node_id = data.get('node_id')
        if not node_id: return
        if node_id not in self.node_graph_data:
            self.node_graph_data[node_id] = {'timestamps': [], 'temperature': [], 'humidity': []}
        d = self.node_graph_data[node_id]
        if data.get('temperature') is not None and data.get('humidity') is not None:
            d['timestamps'].append(datetime.now())
            d['temperature'].append(data.get('temperature'))
            d['humidity'].append(data.get('humidity'))
            for key in d:
                if len(d[key]) > config.GRAPH_MAX_POINTS:
                    d[key].pop(0)
        if node_id == self.app.selected_node_id:
            self.update_graph_plot()
            
    def update_node_selector(self, node_list):
        current_selection = self.node_selector.get()
        self.node_selector.configure(values=node_list)
        if current_selection in node_list:
            self.node_selector.set(current_selection)
        elif node_list and not self.app.selected_node_id:
             self.on_node_select(node_list[0])

    def on_node_select(self, selected_display_name):
        try:
            full_node_id = self.app.get_full_node_id_from_display(selected_display_name)
            if full_node_id: self.app.select_node(full_node_id)
        except (IndexError, AttributeError):
            print(f"No se pudo encontrar el ID para '{selected_display_name}'")

    def on_graph_type_select(self, selection):
        if selection == "Sensores":
            self.live_graph_frame.lift()
        elif selection == "Gauges":
            self.gauge_frame.lift()
            self.update_gauge_charts(self.latest_sensor_data.get(self.app.selected_node_id))
            
    def select_node(self, node_id):
        node_info = self.db.get_node(node_id)
        if not node_info: return
        alias = node_info[1] or 'Sin Alias'
        display_name = f"{alias} ({node_id[-4:]})"
        self.node_selector.set(display_name)

        self.node_graph_data[node_id] = {'timestamps': [], 'temperature': [], 'humidity': []}
        recent_data = self.db.get_recent_readings(node_id, config.GRAPH_MAX_POINTS)
        for row in recent_data:
            timestamp, temp, hum = row
            self.node_graph_data[node_id]['timestamps'].append(datetime.fromisoformat(timestamp))
            self.node_graph_data[node_id]['temperature'].append(temp)
            self.node_graph_data[node_id]['humidity'].append(hum)

        last_data = self.db.get_last_reading(node_id)
        self.update_ui(last_data or {})
        
        self.update_binary_indicator()
        self.update_graph_plot()
        self.update_actuator_button_state()

    def update_ui(self, data):
        node_id = self.app.selected_node_id
        if not node_id: return

        self.latest_sensor_data[node_id] = data
        temp_unit = self.db.get_setting("unit_temp", "C")
        pressure_unit = self.db.get_setting("unit_pressure", "hPa")

        temp_val = utils.convert_temp(data.get('temperature'), temp_unit)
        pressure_val = utils.convert_pressure(data.get('pressure'), pressure_unit)

        self.temp_label.configure(text=f"Temp:\n{temp_val or '--'} °{temp_unit}")
        self.hum_label.configure(text=f"Humedad:\n{data.get('humidity', '--')} %")
        self.pres_label.configure(text=f"Presión:\n{pressure_val or '--'} {pressure_unit}")
        self.iaq_label.configure(text=f"IAQ:\n{data.get('iaq', 'No Disp.')}")
        
        node_db_data = self.db.get_node(node_id)
        if node_db_data and node_db_data[3] is not None:
            battery_level = min(100, int(node_db_data[3]))
            self.battery_label.configure(text=f"Batería:\n{battery_level} %")
        else:
            self.battery_label.configure(text="Batería:\n-- %")

        if self.graph_type_selector.get() == "Gauges":
            self.update_gauge_charts(data)
        self.update_graph_data(data)

    def update_binary_indicator(self):
        state = self.latest_binary_data.get(self.app.selected_node_id)
        self.binary_indicator_light.delete("all")
        color, tooltip_text = "gray", "Sin Datos"
        if state == 1: color, tooltip_text = "#2ca02c", "ON"
        elif state == 0: color, tooltip_text = "#d62728", "OFF"
        self.binary_indicator_light.create_oval(2, 2, 18, 18, fill=color, outline="white", width=1)
        sensor_name = self.db.get_setting("binary_sensor_name", "Sensor Binario")
        self.binary_indicator_label.configure(text=f"{sensor_name}: {tooltip_text}")

    def handle_binary_sensor(self, packet):
        node_id = packet['fromId']
        try:
            payload_str = packet['decoded']['payload'].decode('utf-8')
            data = json.loads(payload_str)
            if 'sensor' in data and 'state' in data:
                state = data['state']
                self.db.insert_binary_reading(node_id, data['sensor'], state)
                self.latest_binary_data[node_id] = state
                if node_id == self.app.selected_node_id:
                    self.update_binary_indicator()
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.app.log_queue.put(("ERROR", f"Paquete binario malformado recibido de {node_id}"))
        
    def update_actuator_button_state(self):
        actuator_node_display = self.db.get_setting("actuator_node_display")
        actuator_node_id = self.app.get_full_node_id_from_display(actuator_node_display) if actuator_node_display else None
        
        if actuator_node_id and self.app.selected_node_id == actuator_node_id:
            self.actuator_button.configure(state="normal", text="Activar Acción")
        else:
            self.actuator_button.configure(state="disabled", text="Activar Acción")