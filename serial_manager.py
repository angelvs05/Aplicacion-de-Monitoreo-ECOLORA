# =============================================================================
# ### ARCHIVO: serial_manager.py ###
# =============================================================================
import meshtastic
import meshtastic.serial_interface
from pubsub import pub
import serial.tools.list_ports

class SerialManager:
    def __init__(self, full_packet_queue, status_callback, log_queue, error_queue):
        self.interface = None
        self.full_packet_queue = full_packet_queue
        self.status_callback = status_callback
        self.log_queue = log_queue
        self.error_queue = error_queue
        self.local_node_num = None

        pub.subscribe(self.on_receive, "meshtastic.receive")
        pub.subscribe(self.on_connection_established, "meshtastic.connection.established")
        pub.subscribe(self.on_connection_lost, "meshtastic.connection.lost")

    def get_available_ports(self):
        return [port.device for port in serial.tools.list_ports.comports()]

    def find_meshtastic_port(self):
        for port in serial.tools.list_ports.comports():
            if port.vid == 0x10C4 and port.pid == 0xEA60: return port.device
            if port.vid == 0x1A86 and port.pid == 0x7523: return port.device
            if "Meshtastic" in port.description or "CP210x" in port.description or "CH9102" in port.description:
                return port.device
        return None

    def connect(self, port):
        self.log_queue.put(("INFO", f"Iniciando proceso de conexión en el puerto {port}..."))
        try:
            self.interface = meshtastic.serial_interface.SerialInterface(port)
            self.log_queue.put(("INFO", "Interfaz serial creada. Esperando confirmación del dispositivo..."))
        except Exception as e:
            error_message = f"FALLO LA CONEXIÓN: {e}"
            self.log_queue.put(("ERROR", error_message))
            self.error_queue.put(("Error de Conexión", f"No se pudo conectar al puerto {port}.\n\nAsegúrate de que el dispositivo esté bien conectado y que no esté siendo usado por otro programa.\n\nDetalle: {e}"))
            if self.status_callback:
                self.status_callback(f"Error al conectar", "red", False)
    
    def disconnect(self):
        if self.interface:
            self.log_queue.put(("INFO", "Desconectando..."))
            try:
                self.interface.close()
            except Exception as e:
                self.log_queue.put(("ERROR", f"Error al desconectar: {e}"))
            finally:
                self.interface = None
                self.local_node_num = None
                if self.status_callback:
                    self.status_callback("Desconectado", "white", False)

    def on_receive(self, packet, interface):
        self.full_packet_queue.put(packet)
        self.log_queue.put(("RECV", f"Recibido paquete de {packet.get('fromId', 'Unknown')}"))

    def on_connection_established(self, interface):
        try:
            node_info = interface.myInfo
            self.local_node_num = node_info.my_node_num
            self.log_queue.put(("INFO", f"¡Conexión exitosa! Info:\n{node_info}"))
            
            interface.sendText("!ECOLORA_SONDEO")

            if self.status_callback:
                self.status_callback(f"Conectado", "green", True, node_info.my_node_num)
        except Exception as e:
            self.log_queue.put(("ERROR", f"Error en on_connection_established: {e}"))
            self.error_queue.put(("Error de Conexión", f"Se estableció la conexión pero no se pudo leer la información del nodo.\n\nDetalle: {e}"))

    def on_connection_lost(self, interface):
        self.log_queue.put(("ERROR", "Conexión con el nodo perdida."))
        if self.status_callback:
            self.status_callback("Conexión perdida", "orange", False)

    def get_channels(self):
        if self.interface and hasattr(self.interface.localNode, 'channels') and self.interface.localNode.channels:
            return self.interface.localNode.channels
        return []

    def send_text_message(self, text, channel_index=0, destination_id="^all", want_ack=False):
        """Función de envío de mensajes actualizada para manejar confirmaciones (ACKs)."""
        if self.interface:
            try:
                # El parámetro wantAck=True le dice a la librería que espere confirmación
                self.interface.sendText(text=text, destinationId=destination_id, channelIndex=channel_index, wantAck=want_ack)
                
                log_msg = f"Enviando '{text}' a {destination_id}"
                if want_ack:
                    log_msg += " (esperando confirmación...)"
                self.log_queue.put(("SENT", log_msg))
                return True
            except Exception as e:
                # Si el tiempo de espera (ack_timeout) se agota, la librería lanza una excepción
                self.log_queue.put(("ERROR", f"Al enviar mensaje: {e}"))
                return False
        return False

    def send_message_to_channel_by_name(self, channel_name, text):
        if not self.interface:
            self.log_queue.put(("ERROR", "No se puede enviar mensaje, no hay conexión."))
            return

        channels = self.get_channels()
        target_channel_index = -1
        if channel_name.lower() == 'primary':
            target_channel_index = 0
        else:
            for i, ch in enumerate(channels):
                if hasattr(ch, 'settings') and ch.settings.name == channel_name:
                    target_channel_index = i
                    break
        
        if target_channel_index != -1:
            self.send_text_message(text, channel_index=target_channel_index)
            self.log_queue.put(("SENT", f"Alerta enviada al canal '{channel_name}': {text}"))
        else:
            self.log_queue.put(("ERROR", f"No se pudo enviar la alerta. Canal '{channel_name}' no encontrado."))

    def read_from_port(self):
        while self.running:
            try:
                # Tu lógica de lectura actual
                line = self.serial_port.readline()
                # ...
            except serial.SerialException:
                print("Error: Se perdió la conexión con el puerto serial.")
                self.gui_queue.put(('serial_disconnected', None)) # Notificar a la GUI
                self.running = False # Detener el hilo de forma segura
                break
            
    def set_node_config(self, setting_name, value):
        if self.interface and self.local_node_num:
            self.log_queue.put(("DEBUG", f"Configurando '{setting_name}' a '{value}'..."))
            try:
                setting_name_fixed = setting_name.replace('-', '_')
                parts = setting_name_fixed.split('.')
                if len(parts) == 2:
                    self.interface.localNode.setPref(parts[1], value)
                    self.interface.localNode.writeConfig()
                    self.log_queue.put(("INFO", f"Configuración '{setting_name}' aplicada y guardada en el nodo."))
                else:
                    self.log_queue.put(("ERROR", f"Nombre de config inválido: {setting_name}"))
            except Exception as e:
                self.log_queue.put(("ERROR", f"Al enviar config: {e}"))

    def request_all_positions(self):
        if self.interface:
            try:
                self.interface.sendText("!request_position")
                return True
            except Exception as e:
                self.log_queue.put(("ERROR", f"Fallo al enviar solicitud de posición: {e}"))
                return False
        return False
        
    def is_node_known(self, node_id):
        if self.interface and self.interface.nodes:
            return self.interface.getNode(node_id) is not None
        return False