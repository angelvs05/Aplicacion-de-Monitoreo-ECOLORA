# =============================================================================
# ### ARCHIVO: tabs/settings_window.py ###
# =============================================================================
import customtkinter as ctk
from tkinter import simpledialog, messagebox
import json
import os
from PIL import Image

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master, app_instance, channel_names, node_list):
        super().__init__(master)
        self.app = app_instance
        self.db = app_instance.db_manager
        self.serial = app_instance.serial_manager
        self.channel_names = channel_names
        self.node_list = node_list

        self.title("Configuración y Gestión")
        self.geometry("950x700")
        self.transient(master)
        
        self.tab_view = ctk.CTkTabview(self, anchor="w")
        self.tab_view.pack(expand=True, fill="both", padx=10, pady=10)

        self.tab_view.add("Gestión de Nodos")
        self.tab_view.add("Configuración de Nodo")
        self.tab_view.add("Reglas del Bot")
        self.tab_view.add("Apariencia")
        self.tab_view.add("Unidades")

        self.condition_rows = []

        # --- LLAMADAS A LAS FUNCIONES PARA CREAR CADA PESTAÑA ---
        self.create_nodes_tab(self.tab_view.tab("Gestión de Nodos"))
        self.create_config_tab(self.tab_view.tab("Configuración de Nodo"))
        self.create_rules_tab(self.tab_view.tab("Reglas del Bot"))
        self.create_appearance_tab(self.tab_view.tab("Apariencia"))
        self.create_units_tab(self.tab_view.tab("Unidades"))
        
        icon_path = os.path.join("assets", "palette.png")
        if os.path.exists(icon_path):
            self.palette_icon = ctk.CTkImage(Image.open(icon_path).resize((20,20), Image.Resampling.LANCZOS))
        else:
            self.palette_icon = None

        self.update_node_list_view()
        self.update_rules_list_view()

    ## -------------------------------------------------------------------
    ## Pestaña Gestión de Nodos
    ## -------------------------------------------------------------------
    def create_nodes_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)
        header_frame = ctk.CTkFrame(tab, fg_color="gray20")
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10,0))
        headers = ["Alias", "Última Vez", "Batería", "SNR", "RSSI", "Saltos", "Acciones"]
        weights = [3, 3, 1, 1, 1, 1, 3]
        for i, (header, weight) in enumerate(zip(headers, weights)):
            header_frame.grid_columnconfigure(i, weight=weight)
            ctk.CTkLabel(header_frame, text=header, font=ctk.CTkFont(weight="bold")).grid(row=0, column=i, padx=5, pady=5)
        self.node_list_scroll_frame = ctk.CTkScrollableFrame(tab)
        self.node_list_scroll_frame.grid(row=1, column=0, padx=10, pady=(0,10), sticky="nsew")
        self.node_list_scroll_frame.grid_columnconfigure(0, weight=1)
        self.node_frames = {}

    def update_node_list_view(self):
        nodes = self.db.get_nodes()
        for node_id_key in list(self.node_frames.keys()):
            self.node_frames[node_id_key]["frame"].destroy()
            del self.node_frames[node_id_key]
        for node_data in nodes:
            node_id, alias, last_seen, bat, snr, rssi, hops, _, _, ui_prefs = node_data
            row_frame = ctk.CTkFrame(self.node_list_scroll_frame, fg_color=("gray85", "gray19"))
            row_frame.pack(fill="x", pady=2, ipady=3)
            weights = [3, 3, 1, 1, 1, 1, 3]
            for c, w in enumerate(weights): row_frame.grid_columnconfigure(c, weight=w)
            action_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
            action_frame.grid(row=0, column=6, padx=5)
            widgets = {
                "alias": ctk.CTkLabel(row_frame, text=alias or node_id, anchor="w"),
                "last_seen": ctk.CTkLabel(row_frame, text=str(last_seen).split('.')[0] if last_seen else 'N/A', anchor="w"),
                "battery": ctk.CTkLabel(row_frame, text=f"{min(100, int(bat))}%" if bat is not None else "--"),
                "snr": ctk.CTkLabel(row_frame, text=f"{snr:.2f}" if snr is not None else "--"),
                "rssi": ctk.CTkLabel(row_frame, text=str(rssi) if rssi is not None else "--"),
                "hops": ctk.CTkLabel(row_frame, text=str(hops) if hops is not None else "--"),
                "button_view": ctk.CTkButton(action_frame, text="Ver", width=60, command=lambda n=node_id: self.app.select_node_and_switch_tab(n)),
                "button_edit": ctk.CTkButton(action_frame, text="Editar", width=60, command=lambda n=node_id, a=alias: self.edit_node_alias(n, a)),
                "button_ui": ctk.CTkButton(action_frame, image=self.palette_icon, text="", width=30, command=lambda n=node_id, p=ui_prefs: self.customize_node_ui(n, p))
            }
            self.node_frames[node_id] = {"frame": row_frame, "widgets": widgets}
            widgets["alias"].grid(row=0, column=0, padx=5, sticky="w")
            widgets["last_seen"].grid(row=0, column=1, padx=5, sticky="w")
            widgets["battery"].grid(row=0, column=2, padx=5)
            widgets["snr"].grid(row=0, column=3, padx=5)
            widgets["rssi"].grid(row=0, column=4, padx=5)
            widgets["hops"].grid(row=0, column=5, padx=5)
            widgets["button_view"].pack(side="left", padx=2)
            widgets["button_edit"].pack(side="left", padx=2)
            widgets["button_ui"].pack(side="left", padx=2)

    def edit_node_alias(self, node_id, current_alias):
        new_alias = simpledialog.askstring("Editar Alias", f"Nuevo alias para el nodo {node_id[-4:]}:", initialvalue=current_alias, parent=self)
        if new_alias and new_alias != current_alias:
            self.db.update_node_alias(node_id, new_alias)
            self.update_node_list_view()
            self.app.update_node_selectors()
            node_data = self.db.get_node(node_id)
            if node_data and node_data[7] is not None:
                self.app.tabs['map'].update_map_marker(node_id, node_data[7], node_data[8])

    def customize_node_ui(self, node_id, current_prefs_str):
        try:
            current_prefs = json.loads(current_prefs_str) if current_prefs_str else {}
        except (json.JSONDecodeError, TypeError):
            current_prefs = {}
        new_icon = simpledialog.askstring("Personalizar Ícono", "Nombre del archivo de ícono (ej: sensor.png):\nDebe estar en la carpeta 'assets'.", initialvalue=current_prefs.get('icon', 'default.png'), parent=self)
        if new_icon is not None:
            new_prefs = {'icon': new_icon}
            self.db.update_node_ui_prefs(node_id, new_prefs)
            node_data = self.db.get_node(node_id)
            if node_data and node_data[7] is not None:
                self.app.tabs['map'].update_map_marker(node_id, node_data[7], node_data[8])

    ## -------------------------------------------------------------------
    ## Pestaña Configuración de Nodo
    ## -------------------------------------------------------------------
    def create_config_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        self.config_frame = ctk.CTkFrame(tab, fg_color="transparent")
        self.config_frame.pack(padx=20, pady=20, fill="x")
        self.config_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self.config_frame, text="Configuración del Nodo Conectado", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=3, pady=(0, 20))
        ctk.CTkLabel(self.config_frame, text="Intervalo de Sensores (s):").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.telemetry_interval_entry = ctk.CTkEntry(self.config_frame, placeholder_text="Ej: 60 (0 para defecto)")
        self.telemetry_interval_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        ctk.CTkButton(self.config_frame, text="Aplicar", command=lambda: self.apply_node_config('telemetry.environment-update-interval')).grid(row=1, column=2, padx=10)
        ctk.CTkLabel(self.config_frame, text="Intervalo de Posición (s):").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.position_interval_entry = ctk.CTkEntry(self.config_frame, placeholder_text="Ej: 300 (0 para defecto)")
        self.position_interval_entry.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        ctk.CTkButton(self.config_frame, text="Aplicar", command=lambda: self.apply_node_config('position.position-broadcast-secs')).grid(row=2, column=2, padx=10)
        ctk.CTkLabel(self.config_frame, text="─" * 80, text_color="gray").grid(row=3, column=0, columnspan=3, pady=10)
        ctk.CTkLabel(self.config_frame, text="Nombre Sensor Binario:").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.binary_sensor_name_entry = ctk.CTkEntry(self.config_frame)
        self.binary_sensor_name_entry.grid(row=4, column=1, padx=10, pady=5, sticky="ew")
        self.binary_sensor_name_entry.insert(0, self.db.get_setting("binary_sensor_name", "Sensor Binario"))
        ctk.CTkLabel(self.config_frame, text="Pin GPIO del Sensor:").grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.binary_sensor_pin_entry = ctk.CTkEntry(self.config_frame, placeholder_text="Ej: 32")
        self.binary_sensor_pin_entry.grid(row=5, column=1, padx=10, pady=5, sticky="ew")
        self.binary_sensor_pin_entry.insert(0, self.db.get_setting("binary_sensor_pin", ""))
        ctk.CTkButton(self.config_frame, text="Guardar Sensor", command=self.save_binary_sensor_config).grid(row=4, rowspan=2, column=2, padx=10)
        ctk.CTkLabel(self.config_frame, text="─" * 80, text_color="gray").grid(row=6, column=0, columnspan=3, pady=15)
        ctk.CTkLabel(self.config_frame, text="Control Remoto (Acción Programada)", font=ctk.CTkFont(size=16, weight="bold")).grid(row=7, column=0, columnspan=3, pady=(0, 10))
        
        ctk.CTkLabel(self.config_frame, text="Nodo Actuador:").grid(row=8, column=0, padx=10, pady=5, sticky="w")
        self.actuator_node_combo = ctk.CTkComboBox(self.config_frame, values=self.node_list)
        self.actuator_node_combo.grid(row=8, column=1, padx=10, pady=5, sticky="ew")
        saved_node_display = self.db.get_setting("actuator_node_display", "")
        if self.node_list:
            if saved_node_display in self.node_list:
                self.actuator_node_combo.set(saved_node_display)
            else:
                self.actuator_node_combo.set(self.node_list[0])
        else:
            self.actuator_node_combo.set("No hay nodos remotos")

        ctk.CTkLabel(self.config_frame, text="Comando de Inicio:").grid(row=9, column=0, padx=10, pady=5, sticky="w")
        self.actuator_start_cmd_entry = ctk.CTkEntry(self.config_frame, placeholder_text="Ej: !relay_on")
        self.actuator_start_cmd_entry.grid(row=9, column=1, padx=10, pady=5, sticky="ew")
        self.actuator_start_cmd_entry.insert(0, self.db.get_setting("actuator_start_cmd", ""))
        
        ctk.CTkLabel(self.config_frame, text="Comando de Fin (Opcional):").grid(row=10, column=0, padx=10, pady=5, sticky="w")
        self.actuator_stop_cmd_entry = ctk.CTkEntry(self.config_frame, placeholder_text="Ej: !relay_off")
        self.actuator_stop_cmd_entry.grid(row=10, column=1, padx=10, pady=5, sticky="ew")
        self.actuator_stop_cmd_entry.insert(0, self.db.get_setting("actuator_stop_cmd", ""))
        
        ctk.CTkLabel(self.config_frame, text="Duración (s, 0 para pulso):").grid(row=11, column=0, padx=10, pady=5, sticky="w")
        self.actuator_duration_entry = ctk.CTkEntry(self.config_frame, placeholder_text="Ej: 10")
        self.actuator_duration_entry.grid(row=11, column=1, padx=10, pady=5, sticky="ew")
        self.actuator_duration_entry.insert(0, self.db.get_setting("actuator_duration", "0"))
        
        ctk.CTkButton(self.config_frame, text="Guardar Acción", command=self.save_actuator_config).grid(row=9, rowspan=3, column=2, padx=10)

    def apply_node_config(self, setting_name):
        if not self.app.is_connected:
            messagebox.showwarning("Desconectado", "Debes estar conectado a un nodo para aplicar la configuración.", parent=self)
            return
        entry_widget = None
        if 'environment' in setting_name: entry_widget = self.telemetry_interval_entry
        elif 'position' in setting_name: entry_widget = self.position_interval_entry
        if entry_widget:
            value_str = entry_widget.get()
            if value_str.isdigit():
                self.serial.set_node_config(setting_name, int(value_str))
                messagebox.showinfo("Éxito", f"Comando para configurar '{setting_name}' enviado al nodo.", parent=self)
                entry_widget.delete(0, 'end')
            else:
                messagebox.showerror("Error", f"El valor para '{setting_name}' debe ser un número entero.", parent=self)

    def save_binary_sensor_config(self):
        name = self.binary_sensor_name_entry.get()
        pin = self.binary_sensor_pin_entry.get()
        if name:
            self.db.set_setting("binary_sensor_name", name)
        if pin.isdigit() or pin == "":
            self.db.set_setting("binary_sensor_pin", pin)
        messagebox.showinfo("Guardado", "Configuración del sensor binario guardada.", parent=self)
        self.app.tabs['detail'].update_binary_indicator()
        
    def save_actuator_config(self):
        node_display = self.actuator_node_combo.get()
        start_cmd = self.actuator_start_cmd_entry.get()
        stop_cmd = self.actuator_stop_cmd_entry.get()
        duration = self.actuator_duration_entry.get()

        if not node_display or "No hay nodos" in node_display:
            messagebox.showerror("Error", "Debes seleccionar un nodo actuador.", parent=self)
            return
        if not duration.isdigit():
            messagebox.showerror("Error", "La duración debe ser un número (en segundos).", parent=self)
            return

        self.db.set_setting("actuator_node_display", node_display)
        self.db.set_setting("actuator_start_cmd", start_cmd)
        self.db.set_setting("actuator_stop_cmd", stop_cmd)
        self.db.set_setting("actuator_duration", duration)
        
        messagebox.showinfo("Guardado", "Configuración de la acción guardada.", parent=self)
        self.app.tabs['detail'].update_actuator_button_state()
        
    def update_actuator_node_list(self, node_list):
        self.node_list = node_list
        if hasattr(self, 'actuator_node_combo'):
            current_selection = self.actuator_node_combo.get()
            self.actuator_node_combo.configure(values=self.node_list)
            if current_selection in self.node_list:
                self.actuator_node_combo.set(current_selection)
            elif self.node_list:
                self.actuator_node_combo.set(self.node_list[0])
            else:
                self.actuator_node_combo.set("No hay nodos remotos")

    ## -------------------------------------------------------------------
    ## Pestaña Reglas del Bot
    ## -------------------------------------------------------------------
    def create_rules_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)
        
        add_frame_container = ctk.CTkFrame(tab)
        add_frame_container.grid(row=0, column=0, padx=10, pady=10, sticky="new")
        add_frame_container.grid_columnconfigure(0, weight=1)
        
        add_frame = ctk.CTkFrame(add_frame_container)
        add_frame.pack(fill="x")
        add_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(add_frame, text="Alias de la Regla:").grid(row=0, column=0, padx=10, pady=(10,5), sticky="w")
        self.rule_alias_entry = ctk.CTkEntry(add_frame, placeholder_text="Ej: Previsión de Lluvia")
        self.rule_alias_entry.grid(row=0, column=1, columnspan=3, padx=10, pady=(10,5), sticky="ew")

        self.conditions_frame = ctk.CTkFrame(add_frame, fg_color="transparent")
        self.conditions_frame.grid(row=1, column=0, columnspan=4, padx=10, pady=5, sticky="ew")
        self.conditions_frame.grid_columnconfigure(2, weight=1)

        ctk.CTkButton(add_frame, text="+ Añadir Condición", command=self.add_condition_row).grid(row=2, column=0, padx=10, pady=(5,10), sticky="w")
        
        action_frame = ctk.CTkFrame(add_frame)
        action_frame.grid(row=3, column=0, columnspan=4, padx=10, pady=10, sticky="ew")
        action_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(action_frame, text="Acción a Realizar:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, pady=5, padx=10, sticky="w")
        
        ctk.CTkLabel(action_frame, text="Notificar al Canal:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.action_channel_combo = ctk.CTkComboBox(action_frame, values=self.channel_names)
        self.action_channel_combo.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        if self.channel_names: self.action_channel_combo.set(self.channel_names[0])
        
        ctk.CTkLabel(action_frame, text="Mensaje de Alerta:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.action_message_entry = ctk.CTkEntry(action_frame, placeholder_text="T: {temperature}, H: {humidity}")
        self.action_message_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        
        ctk.CTkButton(add_frame, text="Guardar Nueva Regla", command=self.add_new_rule).grid(row=4, column=0, columnspan=4, pady=10)

        self.rules_list_frame = ctk.CTkScrollableFrame(tab, label_text="Reglas Activas")
        self.rules_list_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.rules_list_frame.grid_columnconfigure(0, weight=1)

        self.add_condition_row()

    def add_condition_row(self):
        row_index = len(self.condition_rows)
        metric_combo = ctk.CTkComboBox(self.conditions_frame, values=['temperature', 'humidity', 'pressure', 'iaq', 'battery'], width=140, command=lambda e, r=row_index: self.update_condition_units(r))
        metric_combo.grid(row=row_index, column=0, padx=(0,5), pady=5)
        op_combo = ctk.CTkComboBox(self.conditions_frame, values=['>', '<', '==', '!='], width=70)
        op_combo.grid(row=row_index, column=1, padx=5, pady=5)
        value_entry = ctk.CTkEntry(self.conditions_frame, placeholder_text="Valor")
        value_entry.grid(row=row_index, column=2, padx=5, pady=5, sticky="ew")
        unit_label = ctk.CTkLabel(self.conditions_frame, text="", width=40, anchor="w")
        unit_label.grid(row=row_index, column=3, padx=5, pady=5)
        del_button = ctk.CTkButton(self.conditions_frame, text="X", width=28, height=28, fg_color="red", hover_color="#8B0000", command=lambda r=row_index: self.remove_condition_row(r))
        del_button.grid(row=row_index, column=4, padx=5, pady=5)
        self.condition_rows.append({"metric": metric_combo, "op": op_combo, "value": value_entry, "unit": unit_label, "del_btn": del_button})
        self.update_condition_units(row_index)

    def update_condition_units(self, row_index):
        metric = self.condition_rows[row_index]['metric'].get()
        temp_unit = self.db.get_setting("unit_temp", "C")
        pressure_unit = self.db.get_setting("unit_pressure", "hPa")
        unit_map = {'temperature': f'°{temp_unit}', 'humidity': '%', 'pressure': pressure_unit, 'battery': '%', 'iaq': ''}
        self.condition_rows[row_index]['unit'].configure(text=unit_map.get(metric, ''))

    def remove_condition_row(self, row_index):
        if len(self.condition_rows) <= 1: return
        for widget in self.condition_rows[row_index].values():
            widget.destroy()
        del self.condition_rows[row_index]
        self.redraw_condition_rows()

    def redraw_condition_rows(self):
        for i, row_data in enumerate(self.condition_rows):
            row_data['metric'].grid(row=i, column=0)
            row_data['op'].grid(row=i, column=1)
            row_data['value'].grid(row=i, column=2, sticky="ew")
            row_data['unit'].grid(row=i, column=3)
            row_data['del_btn'].grid(row=i, column=4)
            row_data['del_btn'].configure(command=lambda r=i: self.remove_condition_row(r))
            row_data['metric'].configure(command=lambda e, r=i: self.update_condition_units(r))

    def add_new_rule(self):
        alias = self.rule_alias_entry.get()
        channel = self.action_channel_combo.get()
        message = self.action_message_entry.get()
        if not all([alias, channel, message]):
            messagebox.showerror("Error", "El alias, canal y mensaje de la acción son obligatorios.", parent=self)
            return
        conditions = []
        for row_data in self.condition_rows:
            try:
                value = float(row_data["value"].get())
                conditions.append({"metric": row_data["metric"].get(), "operator": row_data["op"].get(), "value": value})
            except ValueError:
                messagebox.showerror("Error", f"El valor '{row_data['value'].get()}' no es un número válido.", parent=self)
                return
        action = {"type": "notify_channel", "channel_name": channel, "message": message}
        self.db.add_bot_rule(alias, conditions, action)
        self.update_rules_list_view()
        self.rule_alias_entry.delete(0, 'end')
        self.action_message_entry.delete(0, 'end')
        for i in range(len(self.condition_rows) -1, 0, -1): self.remove_condition_row(i)
        self.condition_rows[0]['value'].delete(0, 'end')
        messagebox.showinfo("Éxito", "Regla añadida correctamente.", parent=self)

    def delete_rule(self, rule_id):
        if messagebox.askyesno("Confirmar", "¿Estás seguro de que quieres eliminar esta regla?", parent=self):
            self.db.delete_bot_rule(rule_id)
            self.update_rules_list_view()

    def update_rules_list_view(self):
        for widget in self.rules_list_frame.winfo_children():
            widget.destroy()
        rules = self.db.get_bot_rules()
        for rule_id, alias, conditions_json, action_json in rules:
            try:
                conditions = json.loads(conditions_json)
                action = json.loads(action_json)
                conditions_str = " Y ".join([f"{c['metric']} {c['operator']} {c['value']}" for c in conditions])
                action_str = f"-> Notificar a '{action['channel_name']}'"
                rule_text = f"'{alias}':  SI ({conditions_str}) ENTONCES {action_str}"
                rule_frame = ctk.CTkFrame(self.rules_list_frame)
                rule_frame.pack(fill="x", pady=2)
                ctk.CTkLabel(rule_frame, text=rule_text, wraplength=700, justify="left").pack(side="left", padx=10, pady=5, expand=True, fill="x")
                ctk.CTkButton(rule_frame, text="Eliminar", width=80, fg_color="#d62728", hover_color="#a01f1f", command=lambda r_id=rule_id: self.delete_rule(r_id)).pack(side="right", padx=10)
            except json.JSONDecodeError:
                continue

    ## -------------------------------------------------------------------
    ## Pestaña Apariencia y Unidades
    ## -------------------------------------------------------------------
    def create_appearance_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(tab, text="Tema de la Aplicación", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20,10), padx=20, anchor="w")
        self.mode_var = ctk.StringVar(value=self.db.get_setting("appearance_mode", "dark"))
        ctk.CTkRadioButton(tab, text="Oscuro", variable=self.mode_var, value="dark", command=self.change_appearance_mode).pack(anchor="w", padx=20, pady=5)
        ctk.CTkRadioButton(tab, text="Claro", variable=self.mode_var, value="light", command=self.change_appearance_mode).pack(anchor="w", padx=20, pady=5)
        ctk.CTkLabel(tab, text="Color de Acento", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(30,10), padx=20, anchor="w")
        self.color_var = ctk.StringVar(value=self.db.get_setting("color_theme", "green"))
        colors = ["green", "blue", "dark-blue"]
        for color in colors:
            ctk.CTkRadioButton(tab, text=color.replace("-", " ").title(), variable=self.color_var, value=color, command=self.change_color_theme).pack(anchor="w", padx=20, pady=5)

    def change_appearance_mode(self):
        mode = self.mode_var.get()
        ctk.set_appearance_mode(mode)
        self.db.set_setting("appearance_mode", mode)

    def change_color_theme(self):
        theme = self.color_var.get()
        self.db.set_setting("color_theme", theme)
        messagebox.showinfo("Reinicio Necesario", "El cambio de color se aplicará completamente la próxima vez que inicies la aplicación.", parent=self)

    def create_units_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(tab, text="Unidades de Medida", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20,10), padx=20, anchor="w")
        ctk.CTkLabel(tab, text="Temperatura:").pack(pady=(10, 5), padx=20, anchor="w")
        self.temp_unit_var = ctk.StringVar(value=self.db.get_setting("unit_temp", "C"))
        ctk.CTkRadioButton(tab, text="Celsius (°C)", variable=self.temp_unit_var, value="C", command=self.save_units).pack(anchor="w", padx=40)
        ctk.CTkRadioButton(tab, text="Fahrenheit (°F)", variable=self.temp_unit_var, value="F", command=self.save_units).pack(anchor="w", padx=40)
        ctk.CTkLabel(tab, text="Presión Atmosférica:").pack(pady=(20, 5), padx=20, anchor="w")
        self.pressure_unit_var = ctk.StringVar(value=self.db.get_setting("unit_pressure", "hPa"))
        ctk.CTkRadioButton(tab, text="Hectopascales (hPa)", variable=self.pressure_unit_var, value="hPa", command=self.save_units).pack(anchor="w", padx=40)
        ctk.CTkRadioButton(tab, text="Pulgadas de Mercurio (inHg)", variable=self.pressure_unit_var, value="inHg", command=self.save_units).pack(anchor="w", padx=40)

    def save_units(self):
        self.db.set_setting("unit_temp", self.temp_unit_var.get())
        self.db.set_setting("unit_pressure", self.pressure_unit_var.get())
        self.app.tabs['detail'].update_ui(self.app.tabs['detail'].latest_sensor_data.get(self.app.selected_node_id, {}))
        self.app.tabs['dashboard'].update_all_widgets()