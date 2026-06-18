import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

KOMMO_DOMAIN = "asesoresintegrales03.kommo.com"
KOMMO_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6ImVmZDY4MThjYTllMmJiNTA1ODFkY2ExZTE4NWVmOWM3Njc0N2U3MzYzYTVkYjY3ZjBiMmUyODI3Nzk4NWVhNWU1NDk4YjM0ZDkyMTIzYTk0In0.eyJhdWQiOiI3ZmQ5Yjc4Yy0zNTU3LTRhNDAtOTI3My1iNjk3NWU3NDJkNGQiLCJqdGkiOiJlZmQ2ODE4Y2E5ZTJiYjUwNTgxZGNhMWUxODVlZjljNzY3NDdlNzM2M2E1ZGI2N2YwYjJlMjgyNzc5ODVlYTVlNTQ5OGIzNGQ5MjEyM2E5NCIsImlhdCI6MTc4MTgwMzk1NiwibmJmIjoxNzgxODAzOTU2LCleHAiOjE5MjQ5MDU2MDAsInN1YiI6Ijk1MDE4NjciLCJncmFudF90eXBlIjoiIiwiYWNjb3VudF9pZCI6MzExODA3OTEsImJhc2VfZG9tYWluIjoia29tbW8uY29tIiwidmVyc2lvbiI6Miwic2NvcGVzIjpbImNybSIsImZpbGVzIiwiZmlsZXNfZGVsZXRlIiwibm90aWZpY2F0aW9ucyIsInB1c2hfbm90aWZpY2F0aW9ucyIsInVzZXJzX2FjdGl2YXRlIiwidXNlcnNfYWRkIiwidXNlcnNfZGVhY3RpdmF0ZSJdLCJoYXNoX3V1aWQiOiJlMzNhMmM2NC03YTllLTQ1NzYtODQ1Yy1kZjBlODQyMmUxNmYiLCJhcGlfZG9tYWluIjoiYXBpLWcua29tbW8uY29tIn0.H0BJhLb8ofc9vVDM_Q7IwkfhgQ2RdBbZbbpZHHyFWqdZsVZpnoF7VqRe0tm_CpkTgQZdgu2C5uWo3fPZsQJDwU0pY1IQi86TQJiDyhVN9aHZUSakY6RznhPz9t_O1hOqgR8h99dAfhr-a0oDUSLPsxd7EPV4hQNSQwGS3TCMh6g9Lvi8JySW4RFGJIJ8Im-Dh2FJ8C8vFCyF_Q4LHvRXI9aYEYgl-21JU9GrXVT11ansHf_bTdgcXvZBrGFLKWZt6Z3B5J5K05j0ALEgOyIfbiklymN6xJnbVPlnMo4hj3x1E8cPt5LkaFWuy_wd3dmuFsfao-PsMhn1hxzMtWv7xw"

FIELD_ORIGEN_VEHICULO_ID = 1386779   # DATOS DE VEHICULOS
FIELD_DESTINO_VEHICULO_ID = 1386855  # Tipo de Vehículo
FIELD_DESTINO_NOMBRE_ID = 740646     # 1er Nombre

@app.route('/webhook', methods=['GET', 'POST'])
def procesar_lead():
    print(f"¡ALERTA MÁXIMA!: Disparo recibido por {request.method}", flush=True)
    try:
        lead_id = None
        
        # 1. Extraer el ID del Lead
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

        if not lead_id:
            return jsonify({"status": "recibido", "nota": "Ping sin ID"}), 200

        print(f"Consultando información del Lead: {lead_id}", flush=True)

        headers = {
            "Authorization": f"Bearer {KOMMO_TOKEN}",
            "Content-Type": "application/json"
        }
        
        # 2. Obtener los datos del Lead incluyendo la relación de contactos
        url_lead = f"https://{KOMMO_DOMAIN}/api/v4/leads/{lead_id}?with=contacts"
        lead_response = requests.get(url_lead, headers=headers)
        
        texto_vehiculo = None
        primer_nombre = None
        contact_id = None
        
        if lead_response.status_code == 200:
            lead_data = lead_response.json()
            
            # Extraer el valor del vehículo del Lead
            if 'custom_fields_values' in lead_data and lead_data['custom_fields_values']:
                for field in lead_data['custom_fields_values']:
                    if field.get('field_id') == FIELD_ORIGEN_VEHICULO_ID:
                        if field.get('values') and len(field['values']) > 0:
                            texto_vehiculo = field['values'][0].get('value')
                            break
            
            # Obtener el ID del contacto vinculado
            if '_embedded' in lead_data and 'contacts' in lead_data['_embedded'] and lead_data['_embedded']['contacts']:
                contact_id = lead_data['_embedded']['contacts'][0].get('id')

        # 3. Si hay un contacto vinculado, consultar su ficha propia para extraer el Nombre real
        if contact_id:
            print(f"Contacto localizado (ID: {contact_id}). Buscando nombre oficial...", flush=True)
            url_contact = f"https://{KOMMO_DOMAIN}/api/v4/contacts/{contact_id}"
            contact_response = requests.get(url_contact, headers=headers)
            
            if contact_response.status_code == 200:
                contact_data = contact_response.json()
                nombre_completo = contact_data.get('name', '')
                if nombre_completo and nombre_completo.strip():
                    # Corta en el primer espacio y capitaliza correctamente
                    primer_nombre = nombre_completo.split()[0].capitalize()
                    print(f"Nombre de contacto extraído con éxito: {primer_nombre}", flush=True)

        # 4. Construir el paquete de actualización
        campos_a_actualizar = []
        if texto_vehiculo:
            campos_a_actualizar.append({
                "field_id": FIELD_DESTINO_VEHICULO_ID,
                "values": [{"value": str(texto_vehiculo)}]
            })
        if primer_nombre:
            campos_a_actualizar.append({
                "field_id": FIELD_DESTINO_NOMBRE_ID,
                "values": [{"value": str(primer_nombre)}]
            })

        if not campos_a_actualizar:
            print(f"Aviso: Ningún dato encontrado para actualizar en el lead {lead_id}.", flush=True)
            return jsonify({"status": "sin_cambios"}), 200

        # 5. Ejecutar la actualización en Kommo
        url_patch = f"https://{KOMMO_DOMAIN}/api/v4/leads/{lead_id}"
        payload = {"custom_fields_values": campos_a_actualizar}
        patch_response = requests.patch(url_patch, json=payload, headers=headers)
        
        print(f"Sincronización finalizada. Código respuesta Kommo: {patch_response.status_code}", flush=True)
        return jsonify({"status": "exito", "lead_id": lead_id, "nombre": primer_nombre, "vehiculo": texto_vehiculo}), 200

    except Exception as e:
        print(f"Error crítico en ejecución: {e}", flush=True)
        return jsonify({"status": "error", "detalle": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
