import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

KOMMO_DOMAIN = "asesoresintegrales03.kommo.com"
KOMMO_TOKEN = "PEGA_AQUI_TU_TOKEN_LARGO_DE_KOMMO"
FIELD_VEHICULO_ID = 1386855

@app.route('/webhook', methods=['POST'])
def procesar_lead():
    try:
        lead_id = None
        
        # 1. DETECTAR EL FORMATO AUTOMÁTICAMENTE
        if request.is_json:
            # Si viene de Salesbot (JSON)
            json_data = request.get_json()
            # Buscar ID en las rutas típicas de JSON de Kommo
            if 'leads' in json_data:
                if isinstance(json_data['leads'], list) and len(json_data['leads']) > 0:
                    lead_id = json_data['leads'][0].get('id')
                elif isinstance(json_data['leads'], dict):
                    lead_id = json_data['leads'].get('id') or json_data['leads'].get('update', [{}])[0].get('id')
            if not lead_id:
                lead_id = json_data.get('lead_id') or json_data.get('id')
        else:
            # Si viene de Webhook Directo (Formulario)
            form_data = request.form
            for key in form_data.keys():
                if 'leads' in key and '[id]' in key:
                    lead_id = form_data[key]
                    break
            if not lead_id:
                lead_id = form_data.get('lead_id') or form_data.get('id')

        # Si no hay ID, registramos qué tipo de datos llegaron para auditar
        if not lead_id:
            print(f"Aviso recibido pero sin ID. Datos: {request.get_data(as_text=True)}")
            return jsonify({"status": "ignorado", "error": "No se detectó ID"}), 200

        print(f"¡ID Detectado con éxito!: {lead_id}")

        # 2. REGLA DE UNIFICACIÓN
        vehiculo_final = "Particular Hasta 800 kg. de peso"

        # 3. ENVIAR ACTUALIZACIÓN A KOMMO
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

        response = requests.patch(url, json=payload, headers=headers)
        print(f"Lead {lead_id} procesado. Código de respuesta de Kommo: {response.status_code}")
        
        return jsonify({"status": "exito", "lead_id": lead_id}), 200

    except Exception as e:
        print(f"Error crítico en el proceso: {e}")
        return jsonify({"status": "error", "detalle": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
