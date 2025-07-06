from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import threading
import time

app = Flask(__name__)
# Tüm kaynaklardan gelen isteklere izin ver (geliştirme için basit bir yol)
# Üretimde daha kısıtlı CORS ayarları yapılması önerilir!
CORS(app) 

# Telemetri verilerini geçici olarak saklayacağımız dosya
# Render'da ephemeral (geçici) dosya sistemini kullanacağız.
# Eğer kalıcı depolama istenirse, Redis veya PostgreSQL gibi bir veritabanı gerekir.
TELEMETRY_DATA_FILE = 'data.json'
# Dosyanın bulunduğu dizin (Render'da backend klasörü içinde olacak)
DATA_DIR = os.path.dirname(os.path.abspath(__file__)) 
TELEMETRY_FULL_PATH = os.path.join(DATA_DIR, TELEMETRY_DATA_FILE)

# Son gelen telemetri verisini bellekte tutmak için
current_telemetry_data = {}
# Veriye erişimde senkronizasyon için kilit
data_lock = threading.Lock()

# Uygulama başladığında veya her istekle dosyadan veriyi yüklemek yerine
# Veriyi bir kez yükleyip bellekte tutmak daha performanslıdır.
# Ancak Render'da dosya sistemi geçici olduğu için, uygulama yeniden başladığında sıfırlanacaktır.
# Kalıcılık için veritabanı veya Redis daha iyi bir çözümdür.
def load_initial_data():
    global current_telemetry_data
    if os.path.exists(TELEMETRY_FULL_PATH):
        with data_lock:
            try:
                with open(TELEMETRY_FULL_PATH, 'r', encoding='utf-8') as f:
                    current_telemetry_data = json.load(f)
                print(f"Initial data loaded from {TELEMETRY_FULL_PATH}")
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Error loading initial data: {e}")
                current_telemetry_data = {}
    else:
        print(f"Data file not found: {TELEMETRY_FULL_PATH}, starting with empty data.")
        current_telemetry_data = {}

# Uygulama başladığında veriyi yükle
with app.app_context():
    load_initial_data()

# Telemetri verilerini almak için POST endpoint'i
@app.route('/api/telemetry', methods=['POST'])
def receive_telemetry():
    if not request.is_json:
        return jsonify({"msg": "Missing JSON in request"}), 400
    
    telemetry_data = request.get_json()
    print(f"Received telemetry data: {telemetry_data}")

    with data_lock:
        global current_telemetry_data
        current_telemetry_data = telemetry_data
        
        # Veriyi dosyaya yaz (Render'da bu geçici depolamadır)
        try:
            with open(TELEMETRY_FULL_PATH, 'w', encoding='utf-8') as f:
                json.dump(current_telemetry_data, f, indent=4)
            print("Telemetry data saved to file.")
        except Exception as e:
            print(f"Error saving telemetry data to file: {e}")

    return jsonify({"msg": "Telemetry data received successfully", "data": telemetry_data}), 200

# En son telemetri verisini sağlamak için GET endpoint'i
@app.route('/api/telemetry', methods=['GET'])
def get_telemetry():
    with data_lock:
        return jsonify(current_telemetry_data), 200

# Basit bir ana sayfa (isteğe bağlı)
@app.route('/')
def home():
    return "Telemetry API is running! Use /api/telemetry to post or get data."

if __name__ == '__main__':
    # Render'da Gunicorn ile çalışacağı için bu kısım doğrudan kullanılmaz.
    # Yerel test için kullanışlıdır.
    app.run(debug=True, host='0.0.0.0', port=5000)
