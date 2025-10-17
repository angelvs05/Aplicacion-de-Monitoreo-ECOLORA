# =============================================================================
# ### ARCHIVO: serial_manager.py (CORREGIDO) ###
# =============================================================================
import serial
import serial.tools.list_ports
import threading
import time
import json
import meshtastic
import meshtastic.serial_interface
from pubsub import pub

class SerialManager:
    def __init__(self, gui_queue, log_queue):
        self.gui_queue = gui_queue
        self.log_queue = log_queue
        self.serial_port = None
        self.interface = None
        self.running = False
        self.thread = None
        self.is_meshtastic_device = False
        self.callbacks_registered = False

    def get_available_ports(self):
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]

    def connect(self, port):
        self.log_queue.put(('INFO', f"Iniciando proceso de conexión en el puerto {port}..."))
        try:
            # Primero, intenta conectar como un dispositivo Meshtastic
            self.log_queue.put(('INFO', "Intentando conectar con la librería Meshtastic..."))
            self.interface = meshtastic.serial_interface.SerialInterface(port)
            
            # Si la línea anterior no lanza excepción, es un dispositivo Meshtastic
            self.is_meshtastic_device = True
            self.log_queue.put(('INFO', f"¡Conexión Meshtastic exitosa! Info:\n{self.interface.getMyNodeInfo()}"))
            
            # Registrar callbacks si no se han registrado antes
            if not self.callbacks_registered:
                pub.subscribe(self.on_receive, "meshtastic.receive")
                pub.subscribe(self.on_connection_status, "meshtastic.connection.status")
                self.callbacks_registered = True

            self.running = True
            self.thread = threading.Thread(target=self.meshtastic_loop, daemon=True)
            self.thread.start()
            self.gui_queue.put(('connection_status', (True, f"Conectado a Meshtastic en {port}")))

        except meshtastic.MeshtasticError as e:
            self.log_queue.put(('WARNING', f"No es un dispositivo Meshtastic ({e}). Intentando como puerto serial genérico..."))
            self.is_meshtastic_device = False
            self.interface = None # Asegurarse de que la interfaz esté limpia
            try:
                # Si falla, intenta abrir como un puerto serial estándar
                self.serial_port = serial.Serial(port, 9600, timeout=1)
                self.running = True
                self.thread = threading.Thread(target=self.read_from_port, daemon=True)
                self.thread.start()
                self.log_queue.put(('INFO', f"Conectado como puerto serial genérico en {port}."))
                self.gui_queue.put(('connection_status', (True, f"Conectado a {port}")))
            except serial.SerialException as serial_e:
                self.log_queue.put(('ERROR', f"No se pudo conectar al puerto {port}: {serial_e}"))
                self.gui_queue.put(('connection_status', (False, "Error de conexión")))
                return False
        return True

    # --- INICIO DE LA SECCIÓN CORREGIDA ---
    def read_from_port(self):
        """Bucle principal para leer datos del puerto serial."""
        while self.running:
            try:
                if self.serial_port and self.serial_port.is_open:
                    line = self.serial_port.readline()
                    if line:
                        try:
                            packet_str = line.decode('utf-8').strip()
                            self.gui_queue.put(packet_str) 
                            self.log_queue.put(('RECV', packet_str))
                        except UnicodeDecodeError:
                            pass # Ignorar líneas que no son utf-8
                else:
                    time.sleep(1)

            except serial.SerialException as e:
                # Esta es la lógica clave para manejar la desconexión
                self.log_queue.put(('ERROR', f"Error de puerto serial: {e}"))
                self.log_queue.put(('ERROR', "Dispositivo desconectado. Deteniendo hilo."))
                
                # Notifica a la GUI que la conexión se ha perdido
                self.gui_queue.put(('serial_disconnected', None))
                
                self.running = False # Detiene el bucle
                break # Sale del bucle while
            
            except Exception as e:
                self.log_queue.put(('ERROR', f"Error inesperado en read_from_port: {e}"))
                self.running = False
                break
    # --- FIN DE LA SECCIÓN CORREGIDA ---

    def meshtastic_loop(self):
        """Bucle para mantener viva la conexión de Meshtastic."""
        while self.running:
            time.sleep(1)
        self.log_queue.put(("INFO", "Bucle de Meshtastic detenido."))

    def on_receive(self, packet, interface):
        """Callback para cuando se recibe un paquete de Meshtastic."""
        self.log_queue.put(('RECV', f"Recibido paquete de {packet.get('fromId', 'N/A')}"))
        try:
            # Enviar el paquete completo a la GUI para ser procesado
            self.gui_queue.put(packet)
        except Exception as e:
            self.log_queue.put(('ERROR', f"Error al procesar paquete en on_receive: {e}"))

    def on_connection_status(self, status):
        """Callback para cambios en el estado de la conexión."""
        self.log_queue.put(('INFO', f"Estado de conexión Meshtastic: {status}"))
    
    def send_command(self, command):
        """Envía un comando al dispositivo."""
        if self.is_meshtastic_device and self.interface:
            try:
                self.interface.sendText(command)
                self.log_queue.put(('SENT', f"Enviando '{command}' a ^all"))
            except Exception as e:
                 self.log_queue.put(('ERROR', f"Error al enviar por Meshtastic: {e}"))
        elif self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.write(command.encode('utf-8'))
                self.log_queue.put(('SENT', f"Enviando '{command}' a {self.serial_port.port}"))
            except Exception as e:
                 self.log_queue.put(('ERROR', f"Error al enviar por serial: {e}"))
        else:
            self.log_queue.put(('ERROR', "No hay conexión para enviar el comando."))

    def send_message_to_channel_by_name(self, channel_name, message):
        if not self.is_meshtastic_device or not self.interface:
            self.log_queue.put(("ERROR", "No se puede enviar mensaje, no es un dispositivo Meshtastic válido."))
            return
        
        try:
            channel_index = -1
            for ch in self.interface.channels:
                if ch.settings.name == channel_name:
                    channel_index = ch.index
                    break

            if channel_index != -1:
                self.interface.sendText(message, channelIndex=channel_index)
                self.log_queue.put(("SENT", f"Alerta enviada al canal '{channel_name}': {message}"))
            else:
                self.log_queue.put(("ERROR", f"No se encontró el canal '{channel_name}' para enviar el mensaje."))

        except Exception as e:
            self.log_queue.put(("ERROR", f"Error enviando mensaje al canal: {e}"))
    
    def stop(self):
        """Detiene el hilo de lectura y cierra el puerto serial."""
        self.running = False
        if self.thread is not None and self.thread.is_alive():
            self.thread.join(timeout=2)
        
        if self.is_meshtastic_device and self.interface:
            self.interface.close()
            self.log_queue.put(('INFO', "Conexión Meshtastic cerrada."))
        
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            self.log_queue.put(('INFO', f"Puerto {self.serial_port.port} cerrado."))