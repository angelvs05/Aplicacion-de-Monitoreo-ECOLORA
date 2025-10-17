# =============================================================================
# ### ARCHIVO: tabs/history_tab.py (CORREGIDO) ###
# =============================================================================
import customtkinter as ctk
from tkinter import ttk, filedialog
from tkcalendar import DateEntry
import pandas as pd
from datetime import datetime

class HistoryTab(ctk.CTkFrame):
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db_manager = db_manager

        # --- CONTENEDOR DE FILTROS ---
        filter_frame = ctk.CTkFrame(self)
        filter_frame.pack(pady=10, padx=10, fill="x")

        ctk.CTkLabel(filter_frame, text="Nodo:").pack(side="left", padx=(10, 5))
        self.node_id_combobox = ctk.CTkComboBox(filter_frame, values=["Todos"], command=self.filter_data)
        self.node_id_combobox.pack(side="left", padx=5)
        self.node_id_combobox.set("Todos")
        
        ctk.CTkLabel(filter_frame, text="Desde:").pack(side="left", padx=(20, 5))
        self.start_date_entry = DateEntry(filter_frame, date_pattern='y-mm-dd')
        self.start_date_entry.pack(side="left", padx=5)

        ctk.CTkLabel(filter_frame, text="Hasta:").pack(side="left", padx=(10, 5))
        self.end_date_entry = DateEntry(filter_frame, date_pattern='y-mm-dd')
        self.end_date_entry.pack(side="left", padx=5)

        self.filter_button = ctk.CTkButton(filter_frame, text="Filtrar", command=self.filter_data)
        self.filter_button.pack(side="left", padx=10)

        self.export_button = ctk.CTkButton(filter_frame, text="Exportar a CSV", command=self.export_to_csv)
        self.export_button.pack(side="right", padx=10)


        # --- TABLA DE DATOS ---
        self.tree = ttk.Treeview(self, columns=("ID", "Timestamp", "Node ID", "Alias", "Temp", "Hum", "Pres", "Bat", "Lat", "Lon"), show="headings")
        
        # Definir encabezados y anchos
        headers = {"ID": 50, "Timestamp": 160, "Node ID": 100, "Alias": 100, "Temp": 80, "Hum": 80, "Pres": 80, "Bat": 80, "Lat": 120, "Lon": 120}
        for col, width in headers.items():
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor="center")

        self.tree.pack(expand=True, fill="both", padx=10, pady=(0, 10))
        
        self.load_node_ids()
        self.filter_data()

    def load_node_ids(self):
        nodes = self.db_manager.get_all_nodes()
        node_ids = ["Todos"] + [node[1][-4:] for node in nodes]
        self.node_id_combobox.configure(values=list(set(node_ids))) # Usar set para evitar duplicados

    def filter_data(self, event=None):
        node_id_suffix = self.node_id_combobox.get()
        start_date = self.start_date_entry.get_date().strftime("%Y-%m-%d 00:00:00")
        end_date = self.end_date_entry.get_date().strftime("%Y-%m-%d 23:59:59")
        
        # Limpiar la tabla antes de cargar nuevos datos
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Obtener y mostrar los datos
        data = self.db_manager.get_telemetry_history(
            node_id_suffix=None if node_id_suffix == "Todos" else node_id_suffix,
            start_date=start_date,
            end_date=end_date
        )
        
        for row in data:
            # Formatear el alias para que sea legible
            node_alias = self.db_manager.get_node_alias(row[2]) or "N/A"
            # Reemplazar None con "N/A" para una mejor visualización
            display_row = [f"{v:.2f}" if isinstance(v, float) else ("N/A" if v is None else v) for v in row]
            display_row[3] = node_alias # Insertar alias en la posición correcta
            self.tree.insert("", "end", values=display_row)

    def export_to_csv(self):
        # Obtener los datos actualmente mostrados en la tabla
        data = []
        columns = [self.tree.heading(col)["text"] for col in self.tree["columns"]]
        for item in self.tree.get_children():
            data.append(self.tree.item(item)["values"])

        if not data:
            print("No hay datos para exportar.")
            return

        # Pedir al usuario que elija la ubicación del archivo
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Guardar historial como CSV"
        )
        if not file_path:
            return

        # Usar pandas para crear y guardar el CSV
        try:
            df = pd.DataFrame(data, columns=columns)
            df.to_csv(file_path, index=False)
            print(f"Datos exportados exitosamente a {file_path}")
        except Exception as e:
            print(f"Error al exportar a CSV: {e}")

    def on_tab_selected(self):
        """Llamado cuando la pestaña se hace visible."""
        print("Pestaña de historial seleccionada. Recargando datos...")
        self.load_node_ids()
        self.filter_data()