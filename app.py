import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

KOMMO_DOMAIN = "asesoresintegrales03.kommo.com"
KOMMO_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6ImVmZDY4MThjYTllMmJiNTA1ODFkY2ExZTE4NWVmOWM3Njc0N2U3MzYzYTVkYjY3ZjBiMmUyODI3Nzk4NWVhNWU1NDk4YjM0ZDkyMTIzYTk0In0.eyJhdWQiOiI3ZmQ5Yjc4Yy0zNTU3LTRhNDAtOTI3My1iNjk3NWU3NDJkNGQiLCJqdGkiOiJlZmQ2ODE4Y2E5ZTJiYjUwNTgxZGNhMWUxODVlZjljNzY3NDdlNzM2M2E1ZGI2N2YwYjJlMjgyNzc5ODVlYTVlNTQ5OGIzNGQ5MjEyM2E5NCIsImlhdCI6MTc4MTgwMzk1NiwibmJmIjoxNzgxODAzOTU2LCJleHAiOjE5MjQ5MDU2MDAsInN1YiI6Ijk1MDE4NjciLCJncmFudF90eXBlIjoiIiwiYWNjb3VudF9pZCI6MzExODA3OTEsImJhc2VfZG9tYWluIjoia29tbW8uY29tIiwidmVyc2lvbiI6Miwic2NvcGVzIjpbImNybSIsImZpbGVzIiwiZmlsZXNfZGVsZXRlIiwibm90aWZpY2F0aW9ucyIsInB1c2hfbm90aWZpY2F0aW9ucyIsInVzZXJzX2FjdGl2YXRlIiwidXNlcnNfYWRkIiwidXNlcnNfZGVhY3RpdmF0ZSJdLCJoYXNoX3V1aWQiOiJlMzNhMmM2NC03YTllLTQ1NzYtODQ1Yy1kZjBlODQyMmUxNmYiLCJhcGlfZG9tYWluIjoiYXBpLWcua29tbW8uY29tIn0.H0BJhLb8ofc9vVDM_Q7IwkfhgQ2RdBbZbbpZHHyFWqdZsVZpnoF7VqRe0tm_CpkTgQZdgu2C5uWo3fPZsQJDwU0pY1IQi86TQJiDyhVN9aHZUSakY6RznhPz9t_O1hOqgR8h99dAfhr-a0oDUSLPsxd7EPV4hQNSQwGS3TCMh6g9Lvi8JySW4RFGJIJ8Im-Dh2FJ8C8vFCyF_Q4LHvRXI9aYEYgl-21JU9GrXVT11ansHf_bTdgcXvZBrGFLKWZt6Z3B5J5K05j0ALEgOyIfbiklymN6xJnbVPlnMo4hj3x1E8cPt5LkaFWuy_wd3dmuFsfao-PsMhn1hxzMtWv7xw"

FIELD_ORIGEN_ID = 1386779   # DATOS DE VEHICULOS (Facebook Ads)
FIELD_DESTINO_ID = 1386855  # Tipo de Vehículo (Tarificador)

@app.route('/webhook', methods=['GET', 'POST'])
def procesar_lead():
    print(f"¡ALERTA MÁXIMA!: Disparo recibido por {request.method}", flush=True)
    try:
        lead_id = None
        
        # 1. Extraer el ID del Lead sin importar el formato de entrada
        if request.is_json:
            json_data = request.get_json()
            if 'leads' in json_data:
                if 'update' in json_data['leads'] and len(json_data['leads']['update']) > 0:
                    lead_id = json_data['leads']['update'][0].get('id')
                elif isinstance(json_data['leads'], list) and len(json_data['leads']) > 0:
                    lead_id = json_data['leads'][0].get('id')
            if not lead_id:
                lead_id = json_data.get('id') or json_data.get('lead_id')
        elif request.form:
            form_data = request.form
            for key in form_data.keys():
                if 'leads' in key and '[id]' in key:
                    lead_id = form_data[key]
                    break
        if not lead_id and request.args:
            lead_id = request.args.get('id') or request.args.get('lead_id')

        # Si es una petición vacía o de diagnóstico, respondemos éxito para proteger el webhook
        if not lead_id:
            return jsonify({"status": "recibido", "nota": "Ping sin ID verificado"}), 200

        print(f"Conectando a Kommo para leer el Lead: {lead_id}", flush=True)

        # 2. Consultar directamente a Kommo para extraer el valor real del origen
        headers = {
            "Authorization": f"Bearer {KOMMO_TOKEN}",
            "Content-Type": "application/json"
        }
        url_api = f"https://{KOMMO_DOMAIN}/api/v4/leads/{lead_id}"
        get_response = requests.get(url_api, headers=headers)
        
        texto_vehiculo = None
        if get_response.status_code == 200:
            lead_data = get_response.json()
            if 'custom_fields_values' in lead_data and lead_data['custom_fields_values']:
                for field in lead_data['custom_fields_values']:
                    if field.get('field_id') == FIELD_ORIGEN_ID:
                        if field.get('values') and len(field['values']) > 0:
                            texto_vehiculo = field['values'][0].get('value')
                            break

        if not texto_vehiculo:
            print(f"Aviso: El campo origen {FIELD_ORIGEN_ID} está vacío en el lead {lead_id}.", flush=True)
            return jsonify({"status": "ignorado", "nota": "Campo origen sin datos"}), 200

        print(f"Valor detectado en origen: '{texto_vehiculo}'. Clonando al campo destino...", flush=True)

        # 3. Escribir exactamente el mismo valor en el campo destino
        payload = {
            "custom_fields_values": [
                {
                    "field_id": FIELD_DESTINO_ID,
                    "values": [{"value": str(texto_vehiculo)}]
                }
            ]
        }
        patch_response = requests.patch(url_api, json=payload, headers=headers)
        print(f"Resultado de la sincronización en Kommo: Código {patch_response.status_code}", flush=True)
        
        return jsonify({"status": "exito", "lead_id": lead_id, "valor_sincronizado": texto_vehiculo}), 200

    except Exception as e:
        print(f"Error crítico en el proceso: {e}", flush=True)
        return jsonify({"status": "error", "detalle": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
