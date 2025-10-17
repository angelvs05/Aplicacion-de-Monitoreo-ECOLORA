# =============================================================================
# ### ARCHIVO: tabs/messaging_tab.py ###
# =============================================================================
import customtkinter as ctk
from datetime import datetime
import re

class MessagingTab(ctk.CTkFrame):
    def __init__(self, master, app_instance):
        super().__init__(master, fg_color="transparent")
        self.app = app_instance
        self.db = app_instance.db_manager
        self.serial = app_instance.serial_manager

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.message_display = ctk.CTkTextbox(self, state="disabled", font=ctk.CTkFont(size=14))
        self.message_display.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.message_display.tag_config("canal_recibido", foreground="#1f77b4")
        self.message_display.tag_config("directo_recibido", foreground="#d62728")
        self.message_display.tag_config("enviado", foreground="#2ca02c")
        self.message_display.tag_config("info", foreground="gray")
        
        send_frame = ctk.CTkFrame(self, fg_color="transparent")
        send_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        send_frame.grid_columnconfigure(1, weight=1)
        
        self.msg_dest_selector = ctk.CTkComboBox(send_frame, values=["Canal Primario"])
        self.msg_dest_selector.grid(row=0, column=0, padx=(0, 10))
        
        self.msg_entry = ctk.CTkEntry(send_frame, placeholder_text="Escribir mensaje...")
        self.msg_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        self.msg_entry.bind("<Return>", self.send_message)
        
        ctk.CTkButton(send_frame, text="Enviar", command=self.send_message).grid(row=0, column=2)

    def send_message(self, event=None):
        text = self.msg_entry.get()
        if not text or not self.app.is_connected or not self.app.local_node_id:
            return

        dest_selection = self.msg_dest_selector.get()
        channel_index = 0
        match = re.search(r'\(Ch (\d+)\)', dest_selection)
        if match:
            channel_index = int(match.group(1))

        if self.serial.send_text_message(text, channel_index=channel_index):
            self.msg_entry.delete(0, 'end')
            self.db.save_message(self.app.local_node_id, '^all', channel_index, text, False) 
            self.display_message(self.app.local_node_id, '^all', text, datetime.now(), False, channel_index)
        else:
            self.app.log_queue.put("ERROR: No se pudo enviar el mensaje.")

    def handle_text_message(self, packet):
        from_id = packet['fromId']
        text = packet['decoded'].get('payload', b'').decode('utf-8', 'ignore')
        channel = packet.get('channel')
        to_id = f"!{packet.get('to'):x}"
        is_direct = packet.get('isDirect', False)
        
        self.db.save_message(from_id, to_id, channel, text, is_direct)
        self.display_message(from_id, to_id, text, datetime.now(), is_direct, channel)

    # === MÉTODOS AÑADIDOS PARA CORREGIR EL ERROR ===

    def load_message_history(self):
        self.message_display.configure(state="normal")
        self.message_display.delete("1.0", "end")
        messages = self.db.get_messages()
        for from_id, to_id, text, timestamp, is_direct, channel in messages:
            dt_obj = datetime.fromisoformat(timestamp)
            self.display_message(from_id, to_id, text, dt_obj, is_direct, channel)
        self.message_display.configure(state="disabled")

    def display_message(self, from_id, to_id, text, timestamp, is_direct, channel):
        node_info = self.db.get_node(from_id)
        sender_name = node_info[1] if node_info and node_info[1] else from_id
        
        self.message_display.configure(state="normal")
        time_str = f"[{timestamp.strftime('%H:%M:%S')}] "
        
        header, tag = "", ""
        if from_id == self.app.local_node_id:
            tag = "enviado"
            dest_name = "TODOS"
            if to_id != '^all':
                dest_node_info = self.db.get_node(to_id)
                dest_name = dest_node_info[1] if dest_node_info and dest_node_info[1] else to_id
            header = f"Tú a {dest_name}"
        else:
            if is_direct:
                tag = "directo_recibido"
                header = f"{sender_name} (Directo)"
            else:
                tag = "canal_recibido"
                channel_name = f"Canal #{channel}" 
                channels = self.serial.get_channels()
                if channels and channel is not None and channel < len(channels):
                    ch_settings = channels[channel].settings
                    if ch_settings and ch_settings.name:
                        channel_name = ch_settings.name
                header = f"{sender_name} ({channel_name})"
                
        self.message_display.insert("end", time_str, ("info",))
        self.message_display.insert("end", f"{header}: ", (tag,))
        self.message_display.insert("end", f"{text}\n")
        self.message_display.configure(state="disabled")
        self.message_display.see("end")

    def update_channel_list(self):
        channels = self.serial.get_channels()
        destinations = ["Canal Primario"]
        if channels:
            for i, ch in enumerate(channels):
                if i > 0 and hasattr(ch, 'settings') and ch.settings.name:
                    destinations.append(f"{ch.settings.name} (Ch {i})")
        self.msg_dest_selector.configure(values=destinations)
        if destinations:
            self.msg_dest_selector.set(destinations[0])