# =============================================================================
# ### ARCHIVO: tabs/custom_dialogs.py ###
# =============================================================================
import customtkinter as ctk

class CustomDialog(ctk.CTkToplevel):
    """Clase base para centrar y hacer modales los diálogos."""
    def __init__(self, master, title, width=300, height=150):
        super().__init__(master)
        self.title(title)
        self.lift()
        self.attributes("-topmost", True)
        self.grab_set()

        master_x = master.winfo_x()
        master_y = master.winfo_y()
        master_width = master.winfo_width()
        master_height = master.winfo_height()
        x = master_x + (master_width - width) // 2
        y = master_y + (master_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

        self.result = None
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _on_closing(self):
        self.result = None
        self.grab_release()
        self.destroy()

    def wait_for_result(self):
        self.wait_window()
        return self.result

class AddWidgetDialog(CustomDialog):
    """Diálogo para seleccionar el tipo de widget con botones."""
    def __init__(self, master):
        super().__init__(master, "Añadir Widget", height=240)

        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        ctk.CTkLabel(main_frame, text="Selecciona el tipo de widget:", font=ctk.CTkFont(size=14)).pack(pady=(0, 15))

        # --- Textos mejorados ---
        ctk.CTkButton(main_frame, text="Resumen de Sensores", command=lambda: self._on_select("multi-gauge")).pack(fill="x", pady=5)
        ctk.CTkButton(main_frame, text="Indicador Individual (Gauge)", command=lambda: self._on_select("gauge")).pack(fill="x", pady=5)
        ctk.CTkButton(main_frame, text="Gráfica en Vivo", command=lambda: self._on_select("grafica")).pack(fill="x", pady=5)
        ctk.CTkButton(main_frame, text="Botón de Actuador", command=lambda: self._on_select("actuador")).pack(fill="x", pady=5)

    def _on_select(self, widget_type):
        self.result = widget_type
        self.grab_release()
        self.destroy()

class SelectNodeMetricDialog(CustomDialog):
    """Diálogo para seleccionar nodo y métrica con menús desplegables."""
    def __init__(self, master, node_list, metric_list):
        super().__init__(master, "Configurar Widget", height=220)

        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)
        main_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(main_frame, text="Selecciona el Nodo:").grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.node_combo = ctk.CTkComboBox(main_frame, values=node_list)
        self.node_combo.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        if node_list: self.node_combo.set(node_list[0])

        if metric_list: # Ocultar si no hay métricas que elegir
            ctk.CTkLabel(main_frame, text="Selecciona la Métrica:").grid(row=2, column=0, sticky="w", pady=(0, 2))
            self.metric_combo = ctk.CTkComboBox(main_frame, values=metric_list)
            self.metric_combo.grid(row=3, column=0, sticky="ew")
            if metric_list: self.metric_combo.set(metric_list[0])

        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.grid(row=4, column=0, sticky="ew", pady=(15, 0))
        button_frame.grid_columnconfigure((0,1), weight=1)

        ctk.CTkButton(button_frame, text="Aceptar", command=self._on_accept).grid(row=0, column=0, padx=(0,5))
        ctk.CTkButton(button_frame, text="Cancelar", fg_color="gray50", hover_color="gray40", command=self._on_closing).grid(row=0, column=1, padx=(5,0))

    def _on_accept(self):
        self.result = {
            "node_display": self.node_combo.get(),
            "metric": self.metric_combo.get() if hasattr(self, 'metric_combo') else None
        }
        self.grab_release()
        self.destroy()