import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

KOMMO_DOMAIN = "asesoresintegrales03.kommo.com"
KOMMO_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6ImVmZDY4MThjYTllMmJiNTA1ODFkY2ExZTE4NWVmOWM3Njc0N2U3MzYzYTVkYjY3ZjBiMmUyODI3Nzk4NWVhNWU1NDk4YjM0ZDkyMTIzYTk0In0.eyJhdWQiOiI3ZmQ5Yjc4Yy0zNTU3LTRhNDAtOTI3My1iNjk3NWU3NDJkNGQiLCJqdGkiOiJlZmQ2ODE4Y2E5ZTJiYjUwNTgxZGNhMWUxODVlZjljNzY3NDdlNzM2M2E1ZGI2N2YwYjJlMjgyNzc5ODVlYTVlNTQ5OGIzNGQ5MjEyM2E5NCIsImlhdCI6MTc4MTgwMzk1NiwibmJmIjoxNzgxODAzOTU2LCJleHAiOjE5MjQ5MDU2MDAsInN1YiI6Ijk1MDE4NjciLCJncmFudF90eXBlIjoiIiwiYWNjb3VudF9pZCI6MzExODA3OTEsImJhc2VfZG9tYWluIjoia29tbW8uY29tIiwidmVyc2lvbiI6Miwic2NvcGVzIjpbImNybSIsImZpbGVzIiwiZmlsZXNfZGVsZXRlIiwibm90aWZpY2F0aW9ucyIsInB1c2hfbm90aWZpY2F0aW9ucyIsInVzZXJzX2FjdGl2YXRlIiwidXNlcnNfYWRkIiwidXNlcnNfZGVhY3RpdmF0ZSJdLCJoYXNoX3V1aWQiOiJlMzNhMmM2NC03YTllLTQ1NzYtODQ1Yy1kZjBlODQyMmUxNmYiLCJhcGlfZG9tYWluIjoiYXBpLWcua29tbW8uY29tIn0.H0BJhLb8ofc9vVDM_Q7IwkfhgQ2RdBbZbbpZHHyFWqdZsVZpnoF7VqRe0tm_CpkTgQZdgu2C5uWo3fPZsQJDwU0pY1IQi86TQJiDyhVN9aHZUSakY6RznhPz9t_O1hOqgR8h99dAfhr-a0oDUSLPsxd7EPV4hQNSQwGS3TCMh6g9Lvi8JySW4RFGJIJ8Im-Dh2FJ8C8vFCyF_Q4LHvRXI9aYEYgl-21JU9GrXVT11ansHf_bTdgcXvZBrGFLKWZt6Z3B5J5K05j0ALEgOyIfbiklymN6xJnbVPlnMo4hj3x1E8cPt5LkaFWuy_wd3dmuFsfao-PsMhn1hxzMtWv7xw"
FIELD_VEHICULO_ID = 1386855

@app.route('/webhook', methods=['POST'])
def procesar_lead():
    print("¡ALERTA MÁXIMA!: Entró un disparo a Render", flush=True)
    
    try:
        lead_id = None
        
        # Procesar datos si vienen como formulario (Webhook directo)
        if request.form:
            form_data = request.form
            print(f"Datos de Formulario recibidos: {dict(form_data)}", flush=True)
            for key in form_data.keys():
                if 'leads' in key and '[id]' in key:
                    lead_id = form_data[key]
                    break
        
        # Procesar datos si vienen como JSON (Salesbot)
        elif request.is_json:
            json_data = request.get_json()
            print(f"Datos JSON recibidos: {json_data}", flush=True)
            if 'leads' in json_data:
                if isinstance(json_data['leads'], list) and len(json_data['leads']) > 0:
                    lead_id = json_data['leads'][0].get('id')
            if not lead_id:
                lead_id = json_data.get('lead_id') or json_data.get('id')

        # Respuesta segura 200 para que Kommo jamás desactive el Webhook
        if not lead_id:
            print("Aviso: Petición sin ID detectado (posible test de ReqBin).", flush=True)
            return jsonify({"status": "recibido", "nota": "Sin ID detectado"}), 200

        print(f"¡ID de Lead localizado!: {lead_id}", flush=True)

        # Regla de unificación provisional
        vehiculo_final = "Particular Hasta 800 kg. de peso"

        # Conexión directa a la API de Kommo
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
        print(f"Resultado en Kommo para Lead {lead_id}: Código {response.status_code}", flush=True)
        
        return jsonify({"status": "exito", "lead_id": lead_id}), 200

    except Exception as e:
        print(f"Error crítico interno: {e}", flush=True)
        return jsonify({"status": "error", "detalle": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
