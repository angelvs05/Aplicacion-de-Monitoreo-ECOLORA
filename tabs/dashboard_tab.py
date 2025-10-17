# =============================================================================
# ### ARCHIVO: tabs/dashboard_tab.py ###
# =============================================================================
import customtkinter as ctk
from tkinter import messagebox
import json
import uuid
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime
import config
import utils
from tabs.custom_dialogs import AddWidgetDialog, SelectNodeMetricDialog

class DashboardTab(ctk.CTkFrame):
    def __init__(self, master, app_instance):
        super().__init__(master)
        self.app = app_instance
        self.db = app_instance.db_manager
        self.widgets = {}
        self.node_graph_data = {}
        self.is_edit_mode = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.controls_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        edit_switch_var = ctk.StringVar(value="off")
        self.edit_switch = ctk.CTkSwitch(self.controls_frame, text="Modo Edición", variable=edit_switch_var, onvalue="on", offvalue="off", command=self.toggle_edit_mode)
        self.edit_switch.pack(side="left")

        self.dashboard_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.dashboard_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        for i in range(3):
            self.dashboard_frame.grid_columnconfigure(i, weight=1, uniform="grid")
            self.dashboard_frame.grid_rowconfigure(i, weight=1, uniform="grid")

        self.load_grid()

    def toggle_edit_mode(self):
        self.is_edit_mode = not self.is_edit_mode
        self.load_grid()

    def add_widget_dialog(self, row, col):
        dialog_type = AddWidgetDialog(self)
        widget_type = dialog_type.wait_for_result()
        if not widget_type: return

        widget_info = {"type": widget_type, "id": str(uuid.uuid4())}

        if widget_type == "actuador":
            self.widgets[f"cell_{row}-{col}"] = {"info": widget_info}
            self.save_grid()
            self.load_grid()
            return
            
        nodes = self.db.get_nodes()
        if not nodes:
            messagebox.showerror("Error", "No hay nodos en la red para asignar.", parent=self)
            return
        
        node_list_display = [f"{n[1] or 'Sin Alias'} ({n[0][-4:]})" for n in nodes]
        
        metric_list = None
        if widget_type == "gauge":
            metric_list = ['temperature', 'humidity', 'pressure', 'iaq', 'battery']
        
        dialog_config = SelectNodeMetricDialog(self, node_list_display, metric_list)
        config_result = dialog_config.wait_for_result()
        if not config_result: return
        
        node_id = self.app.get_full_node_id_from_display(config_result["node_display"])
        if not node_id:
            messagebox.showerror("Error", "Nodo no válido o no encontrado.", parent=self)
            return

        widget_info["node_id"] = node_id
        if config_result.get("metric"):
            widget_info["metric"] = config_result["metric"]

        self.widgets[f"cell_{row}-{col}"] = {"info": widget_info}
        self.save_grid()
        self.load_grid()

    def delete_widget(self, cell_key):
        if cell_key in self.widgets:
            del self.widgets[cell_key]
            self.save_grid()
            self.load_grid()
    
    def save_grid(self):
        layout_to_save = {key: {"info": value["info"]} for key, value in self.widgets.items()}
        self.db.set_setting("dashboard_grid", json.dumps(layout_to_save))

    def load_grid(self):
        for child in self.dashboard_frame.winfo_children():
            child.destroy()
        
        layout_str = self.db.get_setting("dashboard_grid", "{}")
        try:
            self.widgets = json.loads(layout_str)
        except json.JSONDecodeError:
            self.widgets = {}

        for r in range(3):
            for c in range(3):
                cell_key = f"cell_{r}-{c}"
                cell_frame = ctk.CTkFrame(self.dashboard_frame, fg_color="gray24", border_width=1, border_color="gray30")
                cell_frame.grid(row=r, column=c, padx=5, pady=5, sticky="nsew")

                if cell_key in self.widgets:
                    self.create_widget_in_cell(cell_frame, cell_key)
                elif self.is_edit_mode:
                    add_btn = ctk.CTkButton(cell_frame, text="+", font=ctk.CTkFont(size=50), fg_color="transparent", hover_color="gray30",
                                            command=lambda ro=r, co=c: self.add_widget_dialog(ro, co))
                    add_btn.pack(expand=True, fill="both")
    
    def create_widget_in_cell(self, cell_frame, cell_key):
        widget_info = self.widgets[cell_key]["info"]
        self.widgets[cell_key]["elements"] = {}
        
        inner_frame = ctk.CTkFrame(cell_frame, fg_color="transparent")
        inner_frame.pack(expand=True, fill="both")
        
        if not self.is_edit_mode:
            inner_frame.bind("<Button-1>", lambda event, r=cell_key: self.on_cell_click(r))

        if self.is_edit_mode:
            del_btn = ctk.CTkButton(cell_frame, text="X", width=20, height=20, corner_radius=10, fg_color="red", hover_color="#8B0000",
                                    command=lambda key=cell_key: self.delete_widget(key))
            del_btn.place(relx=1.0, rely=0, x=-5, y=5, anchor="ne")
            self.widgets[cell_key]["delete_button"] = del_btn

        if widget_info["type"] == "actuador":
            btn = ctk.CTkButton(inner_frame, text="Actuador Remoto", command=self.app.on_actuator_button_press)
            btn.pack(padx=20, pady=20, expand=True, fill="both")
            self.widgets[cell_key]["elements"]["button"] = btn
            
        elif widget_info["type"] == "gauge" or widget_info["type"] == "multi-gauge":
            fig = Figure(figsize=(2, 1.5), dpi=100, facecolor="#242424")
            ax = fig.add_subplot(111)
            canvas = FigureCanvasTkAgg(fig, master=inner_frame)
            canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
            self.widgets[cell_key]["elements"] = {"fig": fig, "ax": ax, "canvas": canvas}
            self.update_widget(cell_key)

        elif widget_info["type"] == "grafica":
            fig = Figure(figsize=(4, 2.5), dpi=100, facecolor="#242424")
            ax_temp = fig.add_subplot(111)
            ax_hum = ax_temp.twinx()
            canvas = FigureCanvasTkAgg(fig, master=inner_frame)
            canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
            self.widgets[cell_key]["elements"] = {"fig": fig, "ax_temp": ax_temp, "ax_hum": ax_hum, "canvas": canvas}
            
            node_id = widget_info["node_id"]
            if node_id not in self.node_graph_data:
                self.node_graph_data[node_id] = {'timestamps': [], 'temperature': [], 'humidity': []}
                recent_data = self.db.get_recent_readings(node_id, config.GRAPH_MAX_POINTS)
                for row in recent_data:
                    timestamp, temp, hum = row
                    self.node_graph_data[node_id]['timestamps'].append(datetime.fromisoformat(timestamp))
                    self.node_graph_data[node_id]['temperature'].append(temp)
                    self.node_graph_data[node_id]['humidity'].append(hum)
            
            self.update_widget(cell_key)

    def on_cell_click(self, cell_key):
        if cell_key in self.widgets and "node_id" in self.widgets[cell_key]['info']:
            node_id = self.widgets[cell_key]['info']['node_id']
            self.app.select_node_and_switch_tab(node_id)

    def update_data(self, node_id, data):
        if node_id not in self.node_graph_data:
            self.node_graph_data[node_id] = {'timestamps': [], 'temperature': [], 'humidity': []}
        d = self.node_graph_data[node_id]
        if data.get('temperature') is not None and data.get('humidity') is not None:
            d['timestamps'].append(datetime.now())
            d['temperature'].append(data.get('temperature'))
            d['humidity'].append(data.get('humidity'))
            for key in d:
                if len(d[key]) > config.GRAPH_MAX_POINTS: d[key].pop(0)

        for cell_key, widget_data in self.widgets.items():
            if widget_data.get("info", {}).get("node_id") == node_id:
                self.update_widget(cell_key, data)
                
    def update_all_widgets(self):
        for cell_key in self.widgets.keys():
            self.update_widget(cell_key)

    def update_widget(self, cell_key, data=None):
        if cell_key not in self.widgets: return
        
        widget_info = self.widgets[cell_key]["info"]
        elements = self.widgets[cell_key].get("elements", {})
        if not elements: return

        node_id = widget_info.get("node_id")
        if not node_id: return

        last_reading = self.db.get_last_reading(node_id) if data is None else data
        last_reading = last_reading or {}

        node_info = self.db.get_node(node_id)
        alias = node_info[1] if node_info else node_id[-4:]
        
        temp_unit = self.db.get_setting("unit_temp", "C")
        pressure_unit = self.db.get_setting("unit_pressure", "hPa")

        if widget_info["type"] == "multi-gauge":
            utils.create_multi_gauge(elements["ax"],
                title=alias,
                temp_val=utils.convert_temp(last_reading.get('temperature'), temp_unit),
                temp_unit=temp_unit,
                hum_val=last_reading.get('humidity'),
                pres_val=utils.convert_pressure(last_reading.get('pressure'), pressure_unit),
                pres_unit=pressure_unit)
            elements["canvas"].draw()

        elif widget_info["type"] == "gauge":
            metric = widget_info["metric"]
            value = None
            if metric == 'battery':
                value = min(100, node_info[3]) if node_info and node_info[3] is not None else None
            else:
                value = last_reading.get(metric)

            params = {'label': f"{metric.capitalize()} - {alias}", 'value': value}
            if metric == 'temperature': 
                params.update({'min_val': 0, 'max_val': 50 if temp_unit == 'C' else 122, 'unit': f'°{temp_unit}', 'color': '#e57373', 'value': utils.convert_temp(value, temp_unit)})
            elif metric == 'humidity': 
                params.update({'min_val': 0, 'max_val': 100, 'unit': '%', 'color': '#64b5f6'})
            elif metric == 'pressure': 
                params.update({'min_val': 900 if pressure_unit == 'hPa' else 26.5, 'max_val': 1100 if pressure_unit == 'hPa' else 32.5, 'unit': pressure_unit, 'color': '#81c784', 'value': utils.convert_pressure(value, pressure_unit)})
            elif metric == 'battery': 
                params.update({'min_val': 0, 'max_val': 100, 'unit': '%', 'color': '#a5d6a7'})
            else: # IAQ
                params.update({'min_val': 0, 'max_val': 500, 'unit': '', 'color': '#fff176'})
            
            utils.create_gauge(elements["ax"], **params)
            elements["canvas"].draw()

        elif widget_info["type"] == "grafica":
            graph_data = self.node_graph_data.get(node_id)
            utils.draw_graph_widget(elements["ax_temp"], elements["ax_hum"], graph_data)
            elements["canvas"].draw()