# =============================================================================
# ### ARCHIVO: database_manager.py ###
# =============================================================================
import sqlite3
from datetime import datetime, timedelta
import json

class DatabaseManager:
    def __init__(self, db_name):
        self.db_name = db_name
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.check_and_update_tables()
        print("Base de datos configurada correctamente.")

    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS nodes (
                node_id TEXT PRIMARY KEY, alias TEXT, last_seen TEXT
            )''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT, node_id TEXT, timestamp TEXT,
                temperature REAL, humidity REAL, pressure REAL, iaq REAL,
                FOREIGN KEY (node_id) REFERENCES nodes (node_id)
            )''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT, from_id TEXT, to_id TEXT,
                channel INTEGER, text TEXT, timestamp TEXT, is_direct INTEGER
            )''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS binary_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT, node_id TEXT, timestamp TEXT,
                sensor_name TEXT, state INTEGER,
                FOREIGN KEY (node_id) REFERENCES nodes (node_id)
            )''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY, value TEXT
            )''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT, node_id TEXT, message TEXT, severity TEXT,
                is_read INTEGER DEFAULT 0,
                FOREIGN KEY (node_id) REFERENCES nodes (node_id)
            )''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS network_links (
                source_node_id TEXT, target_node_id TEXT, last_snr REAL, last_seen TEXT,
                PRIMARY KEY (source_node_id, target_node_id)
            )''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alias TEXT,
                conditions_json TEXT,
                action_json TEXT
            )''')
        self.conn.commit()

    def check_and_update_tables(self):
        try:
            self.cursor.execute("PRAGMA table_info(nodes)")
            columns = [info[1] for info in self.cursor.fetchall()]
            
            node_cols_to_add = {
                "battery": "INTEGER", "snr": "REAL", "rssi": "INTEGER",
                "hops": "INTEGER", "latitude": "REAL", "longitude": "REAL",
                "ui_prefs": "TEXT"
            }
            for col, col_type in node_cols_to_add.items():
                if col not in columns:
                    self.cursor.execute(f"ALTER TABLE nodes ADD COLUMN {col} {col_type}")
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error al actualizar la base de datos: {e}")

    def register_node(self, node_id, alias):
        with self.conn:
            self.cursor.execute("INSERT OR IGNORE INTO nodes (node_id, alias) VALUES (?, ?)", (node_id, alias))

    def update_node_alias(self, node_id, new_alias):
        with self.conn:
            self.cursor.execute("UPDATE nodes SET alias = ? WHERE node_id = ?", (new_alias, node_id))
            
    def update_node_ui_prefs(self, node_id, prefs_dict):
        with self.conn:
            self.cursor.execute("UPDATE nodes SET ui_prefs = ? WHERE node_id = ?", (json.dumps(prefs_dict), node_id))

    def get_node(self, node_id):
        self.cursor.execute("SELECT node_id, alias, last_seen, battery, snr, rssi, hops, latitude, longitude, ui_prefs FROM nodes WHERE node_id = ?", (node_id,))
        return self.cursor.fetchone()

    def get_nodes(self):
        self.cursor.execute("SELECT node_id, alias, last_seen, battery, snr, rssi, hops, latitude, longitude, ui_prefs FROM nodes ORDER BY last_seen DESC")
        return self.cursor.fetchall()
    
    def update_node_stats(self, node_id, battery, snr, rssi, hops):
        with self.conn:
            self.cursor.execute("UPDATE nodes SET last_seen = ?, battery = COALESCE(?, battery), snr = COALESCE(?, snr), rssi = COALESCE(?, rssi), hops = COALESCE(?, hops) WHERE node_id = ?", (datetime.now().isoformat(), battery, snr, rssi, hops, node_id))
    
    def update_node_position(self, node_id, lat, lon):
        with self.conn:
            self.cursor.execute("UPDATE nodes SET latitude = ?, longitude = ? WHERE node_id = ?", (lat, lon, node_id))

    def insert_reading(self, data):
        with self.conn:
            self.cursor.execute("INSERT INTO readings (node_id, timestamp, temperature, humidity, pressure, iaq) VALUES (?, ?, ?, ?, ?, ?)", (data.get('node_id'), datetime.now().isoformat(), data.get('temperature'), data.get('humidity'), data.get('pressure'), data.get('iaq')))
    
    def get_last_reading(self, node_id):
        self.cursor.execute("SELECT temperature, humidity, pressure, iaq FROM readings WHERE node_id = ? ORDER BY timestamp DESC LIMIT 1", (node_id,))
        row = self.cursor.fetchone()
        if row: return {'temperature': row[0], 'humidity': row[1], 'pressure': row[2], 'iaq': row[3]}
        return None

    def get_historical_data(self, node_id, days=1):
        start_date = datetime.now() - timedelta(days=days)
        self.cursor.execute("SELECT timestamp, temperature, humidity, pressure FROM readings WHERE node_id = ? AND timestamp >= ? ORDER BY timestamp ASC", (node_id, start_date.isoformat()))
        return self.cursor.fetchall()
        
    def get_recent_readings(self, node_id, limit=100):
        self.cursor.execute("SELECT timestamp, temperature, humidity FROM readings WHERE node_id = ? AND temperature IS NOT NULL AND humidity IS NOT NULL ORDER BY timestamp DESC LIMIT ?", (node_id, limit))
        return self.cursor.fetchall()[::-1]

    def insert_binary_reading(self, node_id, sensor_name, state):
        with self.conn:
            self.cursor.execute("INSERT INTO binary_readings (node_id, timestamp, sensor_name, state) VALUES (?, ?, ?, ?)", (node_id, datetime.now().isoformat(), sensor_name, state))

    def get_last_binary_reading(self, node_id, sensor_name):
        self.cursor.execute("SELECT state FROM binary_readings WHERE node_id = ? AND sensor_name = ? ORDER BY timestamp DESC LIMIT 1", (node_id, sensor_name))
        return self.cursor.fetchone()

    def save_message(self, from_id, to_id, channel, text, is_direct):
        with self.conn:
            self.cursor.execute("INSERT INTO messages (from_id, to_id, channel, text, timestamp, is_direct) VALUES (?, ?, ?, ?, ?, ?)", (from_id, to_id, channel, text, datetime.now().isoformat(), 1 if is_direct else 0))

    def get_messages(self, limit=100):
        self.cursor.execute("SELECT from_id, to_id, text, timestamp, is_direct, channel FROM messages ORDER BY timestamp DESC LIMIT ?", (limit,))
        return self.cursor.fetchall()[::-1]

    def get_setting(self, key, default=None):
        self.cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        result = self.cursor.fetchone()
        return result[0] if result else default

    def set_setting(self, key, value):
        with self.conn:
            self.cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))

    def insert_alert(self, node_id, message, severity):
        with self.conn:
            self.cursor.execute("INSERT INTO alerts (timestamp, node_id, message, severity) VALUES (?, ?, ?, ?)",
                                (datetime.now().isoformat(), node_id, message, severity))

    def get_alerts(self, limit=200):
        self.cursor.execute("SELECT a.timestamp, n.alias, a.message, a.severity, a.is_read FROM alerts a LEFT JOIN nodes n ON a.node_id = n.node_id ORDER BY a.timestamp DESC LIMIT ?", (limit,))
        return self.cursor.fetchall()
        
    def get_unread_alert_count(self):
        self.cursor.execute("SELECT COUNT(*) FROM alerts WHERE is_read = 0")
        return self.cursor.fetchone()[0]

    def mark_alerts_as_read(self):
        with self.conn:
            self.cursor.execute("UPDATE alerts SET is_read = 1 WHERE is_read = 0")

    def get_last_alert_for_node(self, node_id):
        self.cursor.execute("SELECT message, timestamp FROM alerts WHERE node_id = ? ORDER BY timestamp DESC LIMIT 1", (node_id,))
        return self.cursor.fetchone()

    def update_link(self, source, target, snr):
        with self.conn:
            self.cursor.execute("""
                INSERT OR REPLACE INTO network_links (source_node_id, target_node_id, last_snr, last_seen)
                VALUES (?, ?, ?, ?)
            """, (source, target, snr, datetime.now().isoformat()))

    def get_all_links(self):
        self.cursor.execute("SELECT source_node_id, target_node_id, last_snr FROM network_links")
        return self.cursor.fetchall()

    def add_bot_rule(self, alias, conditions_list, action_dict):
        with self.conn:
            self.cursor.execute("""
                INSERT INTO bot_rules (alias, conditions_json, action_json)
                VALUES (?, ?, ?)
            """, (alias, json.dumps(conditions_list), json.dumps(action_dict)))

    def get_bot_rules(self):
        self.cursor.execute("SELECT id, alias, conditions_json, action_json FROM bot_rules")
        return self.cursor.fetchall()

    def delete_bot_rule(self, rule_id):
        with self.conn:
            self.cursor.execute("DELETE FROM bot_rules WHERE id = ?", (rule_id,))

    def close(self):
        self.conn.close()