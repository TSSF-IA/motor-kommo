import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

KOMMO_DOMAIN = "asesoresintegrales03.kommo.com"
KOMMO_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6ImVmZDY4MThjYTllMmJiNTA1ODFkY2ExZTE4NWVmOWM3Njc0N2U3MzYzYTVkYjY3ZjBiMmUyODI3Nzk4NWVhNWU1NDk4YjM0ZDkyMTIzYTk0In0.eyJhdWQiOiI3ZmQ5Yjc4Yy0zNTU3LTRhNDAtOTI3My1iNjk3NWU3NDJkNGQiLCJqdGkiOiJlZmQ2ODE4Y2E5ZTJiYjUwNTgxZGNhMWUxODVlZjljNzY3NDdlNzM2M2E1ZGI2N2YwYjJlMjgyNzc5ODVlYTVlNTQ5OGIzNGQ5MjEyM2E5NCIsImlhdCI6MTheader8M...[Token Completo Sigue Aquí]" # Se mantiene el token largo que envió
FIELD_DESTINO_ID = 1386855  # Tipo de Vehículo

@app.route('/webhook', methods=['GET', 'POST'])
def procesar_lead():
    print(f"¡ALERTA!: Entró disparo por {request.method}", flush=True)
    
    try:
        lead_id = None
        texto_vehiculo = None
        
        # 1. CAPTURA DESDE JSON (Salesbot)
        if request.is_json:
            json_data = request.get_json()
            print(f"JSON Recibido: {json_data}", flush=True)
            
            # Extraer ID del lead
            if 'leads' in json_data:
                if 'update' in json_data['leads'] and len(json_data['leads']['update']) > 0:
                    lead_data = json_data['leads']['update'][0]
                    lead_id = lead_data.get('id')
                    
                    # Buscar el valor que viene en los campos personalizados del JSON
                    if 'custom_fields' in lead_data:
                        for field in lead_data['custom_fields']:
                            # Lee cualquier campo que tenga valores y toma el primero texto que encuentre
                            if 'values' in field and len(field['values']) > 0:
                                # Capturamos el valor dinámico que viene de FB Ads (ej: "Pick Up")
                                texto_vehiculo = field['values'][0].get('value')
                                break
            
            if not lead_id:
                lead_id = json_data.get('id') or json_data.get('lead_id')

        # 2. CAPTURA DESDE FORMULARIO (Webhook Directo)
        elif request.form:
            form_data = request.form
            print(f"Formulario Recibido: {dict(form_data)}", flush=True)
            for key in form_data.keys():
                if 'leads' in key and '[id]' in key:
                    lead_id = form_data[key]
                # Buscar el valor del campo personalizado en el formulario
                if 'custom_fields' in key and '[values][0][value]' in key:
                    texto_vehiculo = form_data[key]

        # Si no detectamos ID, cerramos con éxito para no bloquear a Kommo
        if not lead_id:
            return jsonify({"status": "recibido", "nota": "Sin ID"}), 200

        # Si no se encontró texto en el disparo, dejamos un respaldo por si acaso
        if not texto_vehiculo:
            texto_vehiculo = "Particular" 

        print(f"Procesando Lead: {lead_id} | Valor a copiar: {texto_vehiculo}", flush=True)

        # 3. ENVIAR ACTUALIZACIÓN IDENTICA A KOMMO
        url = f"https://{KOMMO_DOMAIN}/api/v4/leads/{lead_id}"
        headers = {
            "Authorization": f"Bearer {KOMMO_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "custom_fields_values": [
                {
                    "field_id": FIELD_DESTINO_ID,
                    "values": [{"value": str(texto_vehiculo)}] # Inyecta exactamente el mismo texto leído
                }
            ]
        }

        response = requests.patch(url, json=payload, headers=headers)
        print(f"Respuesta API Kommo: Código {response.status_code}", flush=True)
        
        return jsonify({"status": "exito", "lead_id": lead_id, "valor_copiado": texto_vehiculo}), 200

    except Exception as e:
        print(f"Error crítico: {e}", flush=True)
        return jsonify({"status": "error", "detalle": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
