import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

KOMMO_DOMAIN = "asesoresintegrales03.kommo.com"
KOMMO_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6ImVmZDY4MThjYTllMmJiNTA1ODFkY2ExZTE4NWVmOWM3Njc0N2U3MzYzYTVkYjY3ZjBiMmUyODI3Nzk4NWVhNWU1NDk4YjM0ZDkyMTIzYTk0In0.eyJhdWQiOiI3ZmQ5Yjc4Yy0zNTU3LTRhNDAtOTI3My1iNjk3NWU3NDJkNGQiLCJqdGkiOiJlZmQ2ODE4Y2E5ZTJiYjUwNTgxZGNhMWUxODVlZjljNzY3NDdlNzM2M2E1ZGI2N2YwYjJlMjgyNzc5ODVlYTVlNTQ5OGIzNGQ5MjEyM2E5NCIsImlhdCI6MTc4MTgwMzk1NiwibmJmIjoxNzgxODAzOTU2LCJleHAiOjE5MjQ5MDU2MDAsInN1YiI6Ijk1MDE4NjciLCJncmFudF90eXBlIjoiIiwiYWNjb3VudF9pZCI6MzExODA3OTEsImJhc2VfZG9tYWluIjoia29tbW8uY29tIiwidmVyc2lvbiI6Miwic2NvcGVzIjpbImNybSIsImZpbGVzIiwiZmlsZXNfZGVsZXRlIiwibm90aWZpY2F0aW9ucyIsInB1c2hfbm90aWZpY2F0aW9ucyIsInVzZXJzX2FjdGl2YXRlIiwidXNlcnNfYWRkIiwidXNlcnNfZGVhY3RpdmF0ZSJdLCJoYXNoX3V1aWQiOiJlMzNhMmM2NC03YTllLTQ1NzYtODQ1Yy1kZjBlODQyMmUxNmYiLCJhcGlfZG9tYWluIjoiYXBpLWcua29tbW8uY29tIn0.H0BJhLb8ofc9vVDM_Q7IwkfhgQ2RdBbZbbpZHHyFWqdZsVZpnoF7VqRe0tm_CpkTgQZdgu2C5uWo3fPZsQJDwU0pY1IQi86TQJiDyhVN9aHZUSakY6RznhPz9t_O1hOqgR8h99dAfhr-a0oDUSLPsxd7EPV4hQNSQwGS3TCMh6g9Lvi8JySW4RFGJIJ8Im-Dh2FJ8C8vFCyF_Q4LHvRXI9aYEYgl-21JU9GrXVT11ansHf_bTdgcXvZBrGFLKWZt6Z3B5J5K05j0ALEgOyIfbiklymN6xJnbVPlnMo4hj3x1E8cPt5LkaFWuy_wd3dmuFsfao-PsMhn1hxzMtWv7xw"
FIELD_VEHICULO_ID = 1386855

@app.route('/webhook', methods=['GET', 'POST'])
def procesar_lead():
    print(f"¡ALERTA MÁXIMA!: Entró un disparo a Render usando el método: {request.method}", flush=True)
    
    try:
        lead_id = None
        
        # 1. Intentar capturar datos si vienen metidos en los parámetros de la URL (Método GET típico de Kommo)
        if request.args:
            args_data = request.args
            print(f"Datos recibidos por GET (URL): {dict(args_data)}", flush=True)
            for key in args_data.keys():
                if 'leads' in key and '[id]' in key:
                    lead_id = args_data[key]
                    break
            if not lead_id:
                lead_id = args_data.get('id') or args_data.get('lead_id')

        # 2. Si no es GET, revisar si viene por POST tradicional como formulario
        if not lead_id and request.form:
            form_data = request.form
            print(f"Datos recibidos por POST (Formulario): {dict(form_data)}", flush=True)
            for key in form_data.keys():
                if 'leads' in key and '[id]' in key:
                    lead_id = form_data[key]
                    break

        # 3. Revisar si viene por POST estructurado como JSON (Salesbot moderno)
        if not lead_id and request.is_json:
            json_data = request.get_json()
            print(f"Datos recibidos por POST (JSON): {json_data}", flush=True)
            if 'leads' in json_data:
                if 'update' in json_data['leads'] and len(json_data['leads']['update']) > 0:
                    lead_id = json_data['leads']['update'][0].get('id')
                elif isinstance(json_data['leads'], list) and len(json_data['leads']) > 0:
                    lead_id = json_data['leads'][0].get('id')
            if not lead_id:
                lead_id = json_data.get('id') or json_data.get('lead_id')

        # Respuesta siempre exitosa (Código 200) para blindar el Webhook de Kommo
        if not lead_id:
            print("Aviso: Conexión establecida con éxito, pero la estructura no traía un ID válido.", flush=True)
            return jsonify({"status": "recibido", "nota": "Método aceptado correctamente"}), 200

        print(f"¡ID de Lead localizado!: {lead_id}", flush=True)

        # Regla de unificación provisional
        vehiculo_final = "Particular Hasta 800 kg. de peso"

        # Conexión directa a Kommo para reescribir el campo
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
        print(f"Resultado en Kommo: Código {response.status_code}", flush=True)
        
        return jsonify({"status": "exito", "lead_id": lead_id}), 200

    except Exception as e:
        print(f"Error crítico interno: {e}", flush=True)
        return jsonify({"status": "error", "detalle": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
