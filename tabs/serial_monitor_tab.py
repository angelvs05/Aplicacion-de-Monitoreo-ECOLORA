# =============================================================================
# ### ARCHIVO: tabs/serial_monitor_tab.py ###
# =============================================================================
import customtkinter as ctk
import queue
from datetime import datetime

class SerialMonitorTab(ctk.CTkFrame):
    def __init__(self, master, app_instance):
        super().__init__(master, fg_color="transparent")
        self.app = app_instance
        self.log_queue = app_instance.log_queue # Referencia directa a la cola

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.serial_monitor_textbox = ctk.CTkTextbox(self, state="disabled", font=ctk.CTkFont(family="monospace", size=12))
        self.serial_monitor_textbox.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

    def process_log_queue(self):
        try:
            while not self.log_queue.empty():
                message = self.log_queue.get_nowait()
                self.serial_monitor_textbox.configure(state="normal")
                self.serial_monitor_textbox.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
                self.serial_monitor_textbox.configure(state="disabled")
                self.serial_monitor_textbox.see("end")
        except queue.Empty:
            pass