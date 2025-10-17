# =============================================================================
# ### ARCHIVO: tabs/analysis_tab.py ###
# =============================================================================
import customtkinter as ctk
from datetime import datetime
from tkinter import messagebox
import csv

class AnalysisTab(ctk.CTkFrame):
    def __init__(self, master, app_instance):
        super().__init__(master)
        self.app = app_instance
        self.db = app_instance.db_manager

        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # --- Frame Superior: Historial de Alertas ---
        alerts_frame = ctk.CTkFrame(self, fg_color="transparent")
        alerts_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        alerts_frame.grid_rowconfigure(1, weight=1)
        alerts_frame.grid_columnconfigure(0, weight=1)

        # --- NUEVO: Botón de Exportar ---
        alerts_controls = ctk.CTkFrame(alerts_frame)
        alerts_controls.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        self.export_button = ctk.CTkButton(alerts_controls, text="Exportar Alertas a CSV", command=self.export_alerts_to_csv)
        self.export_button.pack(side="right")

        self.alerts_list_frame = ctk.CTkScrollableFrame(alerts_frame, label_text="Historial de Alertas")
        self.alerts_list_frame.grid(row=1, column=0, sticky="nsew")
        self.alerts_list_frame.grid_columnconfigure(0, weight=1)

        # --- Frame Inferior: Log del Bot ---
        self.bot_log_textbox = ctk.CTkTextbox(self, state="disabled", font=ctk.CTkFont(size=14), height=200)
        self.bot_log_textbox.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        self.load_alerts()

    def export_alerts_to_csv(self):
        alerts = self.db.get_alerts()
        if not alerts:
            messagebox.showinfo("Sin Datos", "No hay alertas para exportar.")
            return

        file_path = ctk.filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")],
            title="Guardar alertas como...",
            initialfile="ecolora_alerts_export.csv"
        )
        if not file_path: return

        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['timestamp', 'node_alias', 'message', 'severity', 'is_read'])
                writer.writerows(alerts)
            messagebox.showinfo("Éxito", f"Alertas exportadas correctamente a:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error de Exportación", f"No se pudo guardar el archivo.\n\nError: {e}")

    def load_alerts(self):
        for widget in self.alerts_list_frame.winfo_children():
            widget.destroy()
            
        alerts = self.db.get_alerts()
        
        if not alerts:
            ctk.CTkLabel(self.alerts_list_frame, text="No hay alertas registradas.", text_color="gray").pack(pady=20)
            return

        for alert in alerts:
            timestamp, alias, message, severity, is_read = alert
            dt_obj = datetime.fromisoformat(timestamp)
            time_str = dt_obj.strftime('%Y-%m-%d %H:%M:%S')
            
            color, icon = ("white", "ℹ️")
            if severity == 'WARNING': color, icon = ("#FFA500", "⚠️")
            elif severity == 'CRITICAL': color, icon = ("#d62728", "🚨")

            alert_frame = ctk.CTkFrame(self.alerts_list_frame, border_width=1, border_color="gray25")
            alert_frame.pack(fill="x", pady=3, padx=5)

            full_message = f"{icon} [{time_str}] [{alias}] - {message}"
            label = ctk.CTkLabel(alert_frame, text=full_message, text_color=color, anchor="w", justify="left")
            label.pack(side="left", padx=10, pady=5, fill="x", expand=True)

    def update_log(self, message):
        if not message: return
        self.bot_log_textbox.configure(state="normal")
        self.bot_log_textbox.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.bot_log_textbox.configure(state="disabled")
        self.bot_log_textbox.see("end")