# =============================================================================
# ### ARCHIVO: data_processor.py ###
# =============================================================================
import collections
from datetime import datetime, timedelta
import json

class DataProcessor:
    def __init__(self, db_manager, log_queue):
        self.db_manager = db_manager
        self.log_queue = log_queue # Guardar referencia a la cola
        self.node_data_history = {}
        self.window_size = 5
        self.last_battery_check = {}

    def evaluate_rules(self, data, serial_manager):
        """Evalúa reglas multi-condicionales y ejecuta acciones."""
        node_id = data.get('node_id')
        if not node_id: return

        rules = self.db_manager.get_bot_rules()
        self.log_queue.put(("DEBUG", f"Evaluando {len(rules)} reglas para el nodo {node_id[-4:]}"))

        for rule_id, alias, conditions_json, action_json in rules:
            try:
                conditions = json.loads(conditions_json)
                action = json.loads(action_json)
                
                all_conditions_met = True
                for condition in conditions:
                    metric = condition['metric']
                    operator = condition['operator']
                    value = float(condition['value'])
                    
                    if metric not in data or data[metric] is None:
                        all_conditions_met = False
                        break
                    
                    current_value = data[metric]
                    
                    match = False
                    if operator == '>' and current_value > value: match = True
                    elif operator == '<' and current_value < value: match = True
                    elif operator == '==' and current_value == value: match = True
                    elif operator == '!=' and current_value != value: match = True
                    
                    if not match:
                        all_conditions_met = False
                        break
                
                if all_conditions_met:
                    # --- NUEVO LOG ---
                    self.log_queue.put(("INFO", f"¡Regla '{alias}' cumplida! Ejecutando acción."))
                    self.execute_action(action, data, serial_manager)

            except (json.JSONDecodeError, KeyError, ValueError) as e:
                serial_manager.log_queue.put(("ERROR", f"Error procesando regla ID {rule_id}: {e}"))
                continue
        
        if 'battery' in data and data['battery'] is not None:
            self.check_battery_drain_rate(node_id, data['battery'])

    def execute_action(self, action, data, serial_manager):
        action_type = action.get('type')

        if action_type == 'notify_channel':
            channel_name = action.get('channel_name')
            message_template = action.get('message')

            if not channel_name or not message_template:
                serial_manager.log_queue.put(("ERROR", f"Acción 'notify_channel' no tiene parámetros."))
                return

            formatted_message = message_template.format(
                node_alias=data.get('alias', data.get('node_id', '')[-4:]),
                temperature=data.get('temperature', 'N/A'),
                humidity=data.get('humidity', 'N/A'),
                pressure=data.get('pressure', 'N/A'),
                battery=data.get('battery', 'N/A')
            )
            
            serial_manager.send_message_to_channel_by_name(channel_name, formatted_message)

    def check_battery_drain_rate(self, node_id, current_battery):
        now = datetime.now()
        
        if node_id not in self.last_battery_check:
            self.last_battery_check[node_id] = {"level": current_battery, "time": now}
            return

        last_check = self.last_battery_check[node_id]
        time_diff = now - last_check["time"]

        if time_diff > timedelta(minutes=50):
            drain_rate = last_check["level"] - current_battery
            
            if drain_rate > 15:
                last_alert = self.db_manager.get_last_alert_for_node(node_id)
                if not last_alert or "Descarga rápida de batería" not in last_alert[0]:
                    message = f"Descarga rápida de batería detectada ({drain_rate}% en ~1 hora)."
                    self.db_manager.insert_alert(node_id, message, "WARNING")
            
            self.last_battery_check[node_id] = {"level": current_battery, "time": now}
            
    def get_bot_analysis_message(self, data):
        alias = data.get('alias', data.get('node_id', 'desconocido')[-4:])
        temp = data.get('temperature')
        hum = data.get('humidity')

        if temp is None and hum is None:
            return f"[{alias}] No hay datos de sensores para analizar."

        parts = []
        if temp is not None: parts.append(f"T:{temp}°C")
        if hum is not None: parts.append(f"H:{hum}%")
        base_message = f"[{alias}] {', '.join(parts)}."
        
        return f"{base_message} Rangos normales."