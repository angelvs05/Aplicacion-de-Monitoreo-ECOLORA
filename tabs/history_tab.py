# =============================================================================
# ### ARCHIVO: tabs/history_tab.py ###
# =============================================================================
import customtkinter as ctk
from tkinter import messagebox  # <-- ¡CORRECCIÓN AÑADIDA AQUÍ!
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
from datetime import datetime
import csv

class HistoryTab(ctk.CTkFrame):
    def __init__(self, master, app_instance):
        super().__init__(master, fg_color="transparent")
        self.app = app_instance
        self.db = app_instance.db_manager

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        # --- Controles Superiores ---
        controls_frame = ctk.CTkFrame(self)
        controls_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        ctk.CTkLabel(controls_frame, text="Nodo:").pack(side="left", padx=10)
        self.history_node_selector = ctk.CTkComboBox(controls_frame, values=[], command=self.load_historical_data)
        self.history_node_selector.pack(side="left", padx=10)
        
        ctk.CTkLabel(controls_frame, text="Periodo:").pack(side="left", padx=20)
        self.history_period_selector = ctk.CTkSegmentedButton(controls_frame, values=["24 Horas", "7 Días", "30 Días"], command=self.load_historical_data)
        self.history_period_selector.set("24 Horas")
        self.history_period_selector.pack(side="left")
        
        self.export_button = ctk.CTkButton(controls_frame, text="Exportar a CSV", command=self.export_to_csv)
        self.export_button.pack(side="right", padx=10)

        # --- Gráfico ---
        history_graph_frame = ctk.CTkFrame(self)
        history_graph_frame.grid(row=1, column=0, padx=10, pady=(0,5), sticky="nsew")
        history_graph_frame.grid_columnconfigure(0, weight=1)
        history_graph_frame.grid_rowconfigure(0, weight=1)
        self.create_matplotlib_graph(history_graph_frame)

        # --- Log de Texto ---
        self.history_log = ctk.CTkTextbox(self, state="disabled", height=150, font=ctk.CTkFont(family="monospace"))
        self.history_log.grid(row=2, column=0, padx=10, pady=(5,10), sticky="nsew")

    def create_matplotlib_graph(self, parent):
        self.history_fig = Figure(figsize=(5, 4), dpi=100, facecolor="#2b2b2b")
        self.history_ax_temp = self.history_fig.add_subplot(111)
        self.history_fig.subplots_adjust(right=0.85, top=0.95, bottom=0.15, left=0.1)
        
        self.history_ax_temp.set_facecolor("#2b2b2b")
        self.history_ax_temp.tick_params(axis='y', labelcolor='#ff6347', colors='white')
        self.history_ax_temp.spines['left'].set_color('#ff6347')
        self.history_ax_temp.spines['right'].set_color('gray')
        self.history_ax_temp.spines['top'].set_color('gray')
        self.history_ax_temp.spines['bottom'].set_color('white')
        self.history_ax_temp.tick_params(axis='x', colors='white')
        self.history_ax_temp.set_ylabel("Temperatura (°C)", color='#ff6347', fontsize=12)
        
        self.history_ax_hum = self.history_ax_temp.twinx()
        self.history_ax_hum.tick_params(axis='y', labelcolor='#1f77b4', colors='white')
        self.history_ax_hum.spines['left'].set_color('#ff6347')
        self.history_ax_hum.spines['right'].set_color('#1f77b4')
        self.history_ax_hum.spines['top'].set_color('gray')
        self.history_ax_hum.spines['bottom'].set_color('white')
        self.history_ax_hum.set_ylabel("Humedad (%)", color='#1f77b4', fontsize=12)
        
        self.history_ax_temp.grid(True, linestyle='--', alpha=0.5, color='gray')
        
        self.history_canvas = FigureCanvasTkAgg(self.history_fig, master=parent)
        self.history_canvas.get_tk_widget().pack(side="top", fill="both", expand=True)

    def load_historical_data(self, event=None):
        selected_node = self.history_node_selector.get()
        selected_period = self.history_period_selector.get()
        
        self.history_ax_temp.clear()
        self.history_ax_hum.clear()
        self.history_ax_temp.grid(True, linestyle='--', alpha=0.7, color='gray')
        self.history_log.configure(state="normal")
        self.history_log.delete("1.0", "end")
        
        if not selected_node or not selected_period:
            self.history_canvas.draw()
            self.history_log.configure(state="disabled")
            return

        days = {"24 Horas": 1, "7 Días": 7, "30 Días": 30}[selected_period]
        try:
            full_node_id = self.app.get_full_node_id_from_display(selected_node)
        except (IndexError, AttributeError):
            self.history_canvas.draw()
            self.history_log.configure(state="disabled")
            return
            
        if not full_node_id: return
        data = self.db.get_historical_data(full_node_id, days)

        if not data:
            self.history_log.insert("1.0", "No hay datos históricos para este nodo en el período seleccionado.")
        else:
            timestamps, temps, hums, press = zip(*data)
            timestamps_dt = [datetime.fromisoformat(ts) for ts in timestamps]
            
            line_temp, = self.history_ax_temp.plot(timestamps_dt, temps, '-', label="Temperatura (°C)", color="#ff6347", markersize=2)
            line_hum, = self.history_ax_hum.plot(timestamps_dt, hums, '-', label="Humedad (%)", color="#1f77b4", markersize=2)
            
            legend = self.history_ax_temp.legend(handles=[line_temp, line_hum], loc='upper left', facecolor='#3c3c3c', edgecolor='white')
            for text in legend.get_texts(): text.set_color("white")
            
            log_header = f"{'Fecha':<20} {'Hora':<15} {'Temp (°C)':<15} {'Humedad (%)':<15} {'Presión (hPa)':<15}\n"
            log_header += "-" * 85 + "\n"
            self.history_log.insert("1.0", log_header)
            for ts, t, h, p in data:
                dt_obj = datetime.fromisoformat(ts)
                t_str = f"{t:.2f}" if t is not None else '--'
                h_str = f"{h:.1f}" if h is not None else '--'
                p_str = f"{p:.1f}" if p is not None else '--'
                log_line = f"{dt_obj.strftime('%Y-%m-%d'):<20} {dt_obj.strftime('%H:%M:%S'):<15} {t_str:<15} {h_str:<15} {p_str:<15}\n"
                self.history_log.insert("end", log_line)

        self.history_log.configure(state="disabled")
        self.history_fig.autofmt_xdate()
        self.history_ax_temp.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m %H:%M'))
        self.history_canvas.draw()

    def update_node_selector(self, node_list):
        current_selection = self.history_node_selector.get()
        self.history_node_selector.configure(values=node_list)
        if current_selection in node_list:
            self.history_node_selector.set(current_selection)
        elif node_list:
            self.history_node_selector.set(node_list[0])
            self.load_historical_data()

    def export_to_csv(self):
        selected_node = self.history_node_selector.get()
        selected_period = self.history_period_selector.get()
        
        if not selected_node or not selected_period:
            messagebox.showwarning("Sin Selección", "Por favor, selecciona un nodo y un período para exportar.")
            return

        full_node_id = self.app.get_full_node_id_from_display(selected_node)
        if not full_node_id: return
        
        days = {"24 Horas": 1, "7 Días": 7, "30 Días": 30}[selected_period]
        data = self.db.get_historical_data(full_node_id, days)

        if not data:
            messagebox.showinfo("Sin Datos", "No hay datos para exportar en la selección actual.")
            return

        file_path = ctk.filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")],
            title="Guardar datos históricos como...",
            initialfile=f"ecolora_export_{full_node_id[-4:]}_{days}d.csv"
        )
        
        if not file_path: return

        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['timestamp', 'temperature_c', 'humidity_percent', 'pressure_hpa'])
                writer.writerows(data)
            messagebox.showinfo("Éxito", f"Datos exportados correctamente a:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error de Exportación", f"No se pudo guardar el archivo.\n\nError: {e}")