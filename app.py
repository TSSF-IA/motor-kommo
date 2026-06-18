import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

KOMMO_DOMAIN = "asesoresintegrales03.kommo.com"
KOMMO_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6ImVmZDY4MThjYTllMmJiNTA1ODFkY2ExZTE4NWVmOWM3Njc0N2U3MzYzYTVkYjY3ZjBiMmUyODI3Nzk4NWVhNWU1NDk4YjM0ZDkyMTIzYTk0In0.eyJhdWQiOiI3ZmQ5Yjc4Yy0zNTU3LTRhNDAtOTI3My1iNjk3NWU3NDJkNGQiLCJqdGkiOiJlZmQ2ODE4Y2E5ZTJiYjUwNTgxZGNhMWUxODVlZjljNzY3NDdlNzM2M2E1ZGI2N2YwYjJlMjgyNzc5ODVlYTVlNTQ5OGIzNGQ5MjEyM2E5NCIsImlhdCI6MTc4MTgwMzk1NiwibmJmIjoxNzgxODAzOTU2LCJleHAiOjE5MjQ5MDU2MDAsInN1YiI6Ijk1MDE4NjciLCJncmFudF90eXBlIjoiIiwiYWNjb3VudF9pZCI6MzExODA3OTEsImJhc2VfZG9tYWluIjoia29tbW8uY29tIiwidmVyc2lvbiI6Miwic2NvcGVzIjpbImNybSIsImZpbGVzIiwiZmlsZXNfZGVsZXRlIiwibm90aWZpY2F0aW9ucyIsInB1c2hfbm90aWZpY2F0aW9ucyIsInVzZXJzX2FjdGl2YXRlIiwidXNlcnNfYWRkIiwidXNlcnNfZGVhY3RpdmF0ZSJdLCJoYXNoX3V1aWQiOiJlMzNhMmM2NC03YTllLTQ1NzYtODQ1Yy1kZjBlODQyMmUxNmYiLCJhcGlfZG9tYWluIjoiYXBpLWcua29tbW8uY29tIn0.H0BJhLb8ofc9vVDM_Q7IwkfhgQ2RdBbZbbpZHHyFWqdZsVZpnoF7VqRe0tm_CpkTgQZdgu2C5uWo3fPZsQJDwU0pY1IQi86TQJiDyhVN9aHZUSakY6RznhPz9t_O1hOqgR8h99dAfhr-a0oDUSLPsxd7EPV4hQNSQwGS3TCMh6g9Lvi8JySW4RFGJIJ8Im-Dh2FJ8C8vFCyF_Q4LHvRXI9aYEYgl-21JU9GrXVT11ansHf_bTdgcXvZBrGFLKWZt6Z3B5J5K05j0ALEgOyIfbiklymN6xJnbVPlnMo4hj3x1E8cPt5LkaFWuy_wd3dmuFsfao-PsMhn1hxzMtWv7xw"

FIELD_ORIGEN_VEHICULO_ID = 1386779   # DATOS DE VEHICULOS (Facebook Ads)
FIELD_DESTINO_VEHICULO_ID = 1386855  # Tipo de Vehículo (Tarificador)
FIELD_DESTINO_NOMBRE_ID = 740646     # 1er Nombre (Para Salesbot)

@app.route('/webhook', methods=['GET', 'POST'])
def procesar_lead():
    print(f"¡ALERTA MÁXIMA!: Disparo entrante detectado por método {request.method}", flush=True)
    
    lead_id = None
    texto_vehiculo = None
    primer_nombre = None
    
    try:
        # 1. ESCANEO DE PARÁMETROS URL (GET)
        if request.args:
            args_data = request.args
            for key, val in args_data.items():
                if 'leads' in key and '[id]' in key:
                    lead_id = val
                if str(FIELD_ORIGEN_VEHICULO_ID) in key:
                    texto_vehiculo = val
                if 'contacts' in key and '[name]' in key and val:
                    primer_nombre = val.split()[0].capitalize()

        # 2. ESCANEO DE DATOS DE FORMULARIO (POST Tradicional)
        if request.form:
            form_data = request.form
            for key, val in form_data.items():
                if 'leads' in key and '[id]' in key:
                    lead_id = val
                if str(FIELD_ORIGEN_VEHICULO_ID) in key:
                    texto_vehiculo = val
                if 'contacts' in key and '[name]' in key and val:
                    primer_nombre = val.split()[0].capitalize()

        # 3. ESCANEO DE ESTRUCTURA JSON (POST Moderno / Salesbot)
        if request.is_json:
            json_data = request.get_json()
            print(f"Lectura de payload JSON: {json_data}", flush=True)
            
            if 'leads' in json_data:
                leads_part = json_data['leads']
                lead_list = []
                if 'update' in leads_part:
                    lead_list = leads_part['update']
                elif 'add' in leads_part:
                    lead_list = leads_part['add']
                elif isinstance(leads_part, list):
                    lead_list = leads_part
                
                if lead_list and len(lead_list) > 0:
                    lead_id = lead_list[0].get('id')
                    if 'custom_fields' in lead_list[0]:
                        for field in lead_list[0]['custom_fields']:
                            if str(field.get('id')) == str(FIELD_ORIGEN_VEHICULO_ID):
                                if 'values' in field and len(field['values']) > 0:
                                    texto_vehiculo = field['values'][0].get('value')
                                    break
            
            if 'contacts' in json_data:
                contacts_part = json_data['contacts']
                contact_list = []
                if 'update' in contacts_part:
                    contact_list = contacts_part['update']
                elif 'add' in contacts_part:
                    contact_list = contacts_part['add']
                elif isinstance(contacts_part, list):
                    contact_list = contacts_part
                
                if contact_list and len(contact_list) > 0:
                    c_name = contact_list[0].get('name')
                    if c_name:
                        primer_nombre = c_name.split()[0].capitalize()

            if not lead_id:
                lead_id = json_data.get('id') or json_data.get('lead_id')

        # Control de pings de verificación para evitar caídas del webhook
        if not lead_id:
            print("Aviso: Conexión estructural establecida exitosamente.", flush=True)
            return jsonify({"status": "recibido", "nota": "Validación de ruta OK"}), 200

        print(f"Procesando Lead ID: {lead_id}", flush=True)
        headers = {
            "Authorization": f"Bearer {KOMMO_TOKEN}",
            "Content-Type": "application/json"
        }

        # 4. CANAL DE RESPALDO: CONSULTA DIRECTA A LA API DE KOMMO (Si faltan datos en el Webhook)
        if not texto_vehiculo or not primer_nombre:
            print("Datos incompletos en el disparo. Consultando base de datos interna de Kommo...", flush=True)
            url_lead = f"https://{KOMMO_DOMAIN}/api/v4/leads/{lead_id}?with=contacts"
            lead_response = requests.get(url_lead, headers=headers)
            
            if lead_response.status_code == 200:
                lead_api_data = lead_response.json()
                
                # Extraer vehículo si no se capturó en el webhook
                if not texto_vehiculo:
                    if 'custom_fields_values' in lead_api_data and lead_api_data['custom_fields_values']:
                        for field in lead_api_data['custom_fields_values']:
                            if str(field.get('field_id')) == str(FIELD_ORIGEN_VEHICULO_ID):
                                if field.get('values') and len(field['values']) > 0:
                                    texto_vehiculo = field['values'][0].get('value')
                                    break
                
                # Localizar contacto para extraer el nombre real
                if not primer_nombre:
                    if '_embedded' in lead_api_data and 'contacts' in lead_api_data['_embedded'] and lead_api_data['_embedded']['contacts']:
                        contact_id = lead_api_data['_embedded']['contacts'][0].get('id')
                        if contact_id:
                            url_contact = f"https://{KOMMO_DOMAIN}/api/v4/contacts/{contact_id}"
                            contact_response = requests.get(url_contact, headers=headers)
                            if contact_response.status_code == 200:
                                contact_data = contact_response.json()
                                nombre_completo = contact_data.get('name', '')
                                if nombre_completo and nombre_completo.strip():
                                    primer_nombre = nombre_completo.split()[0].capitalize()

        # 5. CONSTRUCCIÓN DE LA CARGA ÚTIL DE ACTUALIZACIÓN
        campos_a_actualizar = []
        if texto_vehiculo:
            campos_a_actualizar.append({
                "field_id": FIELD_DESTINO_VEHICULO_ID,
                "values": [{"value": str(texto_vehiculo)}]
            })
            print(f"Preparado para clonar Vehículo: '{texto_vehiculo}'", flush=True)
        if primer_nombre:
            campos_a_actualizar.append({
                "field_id": FIELD_DESTINO_NOMBRE_ID,
                "values": [{"value": str(primer_nombre)}]
            })
            print(f"Preparado para guardar 1er Nombre: '{primer_nombre}'", flush=True)

        if not campos_a_actualizar:
            print(f"Aviso: No se encontraron datos para modificar en el Lead {lead_id}.", flush=True)
            return jsonify({"status": "sin_cambios"}), 200

        # 6. GUARDADO EJECUTIVO EN KOMMO
        url_patch = f"https://{KOMMO_DOMAIN}/api/v4/leads/{lead_id}"
        patch_response = requests.patch(url_patch, json={"custom_fields_values": campos_a_actualizar}, headers=headers)
        print(f"Respuesta de la API de Kommo: Código {patch_response.status_code}", flush=True)
        
        if patch_response.status_code in [200, 201, 204]:
            return jsonify({"status": "exito", "lead_id": lead_id, "vehiculo": texto_vehiculo, "nombre": primer_nombre}), 200
        else:
            print(f"Error de escritura en Kommo: {patch_response.text}", flush=True)
            return jsonify({"status": "error_api", "detalle": patch_response.text}), 400

    except Exception as e:
        print(f"Error crítico en el proceso interno: {e}", flush=True)
        return jsonify({"status": "error_interno", "detalle": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
