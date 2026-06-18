import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

KOMMO_DOMAIN = "asesoresintegrales03.kommo.com"
KOMMO_TOKEN = "TU_TOKEN_AQUI"
FIELD_VEHICULO_ID = 1386855

@app.route('/webhook', methods=['POST'])
def procesar_lead():
    try:
        data = request.form
        lead_id = None

        # Extracción forzada del ID
        for key in data.keys():
            if 'leads' in key and '[id]' in key:
                lead_id = data[key]
                break
        
        if not lead_id and 'lead_id' in data:
            lead_id = data['lead_id']

        if not lead_id:
            return jsonify({"status": "ignorado"}), 200

        # Regla del Director: Unificar a Particular
        vehiculo_final = "Particular Hasta 800 kg. de peso"

        # Actualizar Kommo
        url = f"https://{KOMMO_DOMAIN}/api/v4/leads/{lead_id}"
        headers = {
            "Authorization": f"Bearer {KOMMO_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "custom_fields_values": [
                {
                    "field_id": FIELD_VEHICULO_ID,
                    "values": [{"value": vehiculo_final}]
                }
            ]
        }

        requests.patch(url, json=payload, headers=headers)
        return jsonify({"status": "exito", "lead_id": lead_id}), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
