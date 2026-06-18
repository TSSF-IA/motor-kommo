import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

KOMMO_DOMAIN = "asesoresintegrales03.kommo.com"
KOMMO_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6ImVmZDY4MThjYTllMmJiNTA1ODFkY2ExZTE4NWVmOWM3Njc0N2U3MzYzYTVkYjY3ZjBiMmUyODI3Nzk4NWVhNWU1NDk4YjM0ZDkyMTIzYTk0In0.eyJhdWQiOiI3ZmQ5Yjc4Yy0zNTU3LTRhNDAtOTI3My1iNjk3NWU3NDJkNGQiLCJqdGkiOiJlZmQ2ODE4Y2E5ZTJiYjUwNTgxZGNhMWUxODVlZjljNzY3NDdlNzM2M2E1ZGI2N2YwYjJlMjgyNzc5ODVlYTVlNTQ5OGIzNGQ5MjEyM2E5NCIsImlhdCI6MTc4MTgwMzk1NiwibmJmIjoxNzgxODAzOTU2LCVleHAiOjE5MjQ5MDU2MDAsInN1YiI6Ijk1MDE4NjciLCJncmFudF90eXBlIjoiIiwiYWNjb3VudF9pZCI6MzExODA3OTEsImJhc2VfZG9tYWluIjoia29tbW8uY29tIiwidmVyc2lvbiI6Miwic2NvcGVzIjpbImNybSIsImZpbGVzIiwiZmlsZXNfZGVsZXRlIiwibm90aWZpY2F0aW9ucyIsInB1c2hfbm90aWZpY2F0aW9ucyIsInVzZXJzX2FjdGl2YXRlIiwidXNlcnNfYWRkIiwidXNlcnNfZGVhY3RpdmF0ZSJdLCJoYXNoX3V1aWQiOiJlMzNhMmM2NC03YTllLTQ1NzYtODQ1Yy1kZjBlODQyMmUxNmYiLCJhcGlfZG9tYWluIjoiYXBpLWcua29tbW8uY29tIn0.H0BJhLb8ofc9vVDM_Q7IwkfhgQ2RdBbZbbpZHHyFWqdZsVZpnoF7VqRe0tm_CpkTgQZdgu2C5uWo3fPZsQJDwU0pY1IQi86TQJiDyhVN9aHZUSakY6RznhPz9t_O1hOqgR8h99dAfhr-a0oDUSLPsxd7EPV4hQNSQwGS3TCMh6g9Lvi8JySW4RFGJIJ8Im-Dh2FJ8C8vFCyF_Q4LHvRXI9aYEYgl-21JU9GrXVT11ansHf_bTdgcXvZBrGFLKWZt6Z3B5J5K05j0ALEgOyIfbiklymN6xJnbVPlnMo4hj3x1E8cPt5LkaFWuy_wd3dmuFsfao-PsMhn1hxzMtWv7xw"

FIELD_ORIGEN_VEHICULO_ID = 1386779   # DATOS DE VEHICULOS (Origen)
FIELD_DESTINO_VEHICULO_ID = 1386855  # Tipo de Vehículo (Destino)
FIELD_DESTINO_NOMBRE_ID = 740646     # 1er Nombre (Destino)

@app.route('/webhook', methods=['GET', 'POST'])
def procesar_lead():
    print("\n=== 🚀 INICIANDO SINCRONIZACIÓN OPERATIVA ===", flush=True)
    lead_id = None
    texto_vehiculo = None
    primer_nombre = None
    
    try:
        # 1. Extracción basada en la estructura del formulario real de Kommo
        if request.form:
            form_data = request.form
            print(f"Formulario recibido: {dict(form_data)}", flush=True)
            
            # Buscar ID del Lead
            for key, val in form_data.items():
                if 'leads' in key and '[id]' in key and 'custom_fields' not in key and 'tags' not in key:
                    lead_id = val
                    break
            
            # Buscar valor del vehículo mapeando las llaves del formulario de Kommo
            for key, val in form_data.items():
                if str(val) == str(FIELD_ORIGEN_VEHICULO_ID) and '[id]' in key:
                    llave_valor = key.replace('[id]', '[values][0][value]')
                    texto_vehiculo = form_data.get(llave_valor)
                    break

        if not lead_id:
            print("No se detectó un ID de lead válido en el disparo.", flush=True)
            return jsonify({"status": "recibido", "nota": "Ping sin datos de proceso"}), 200

        print(f"ID del Lead detectado: {lead_id}", flush=True)
        headers = {
            "Authorization": f"Bearer {KOMMO_TOKEN}",
            "Content-Type": "application/json"
        }

        # 2. Conexión mediante la API para extraer el contacto vinculado
        url_lead = f"https://{KOMMO_DOMAIN}/api/v4/leads/{lead_id}?with=contacts"
        lead_resp = requests.get(url_lead, headers=headers)
        
        if lead_resp.status_code == 200:
            lead_data = lead_resp.json()
            
            # Si el webhook no trajo el vehículo, se obtiene por API de respaldo
            if not texto_vehiculo and 'custom_fields_values' in lead_data and lead_data['custom_fields_values']:
                for field in lead_data['custom_fields_values']:
                    if str(field.get('field_id')) == str(FIELD_ORIGEN_VEHICULO_ID):
                        if field.get('values') and len(field['values']) > 0:
                            texto_vehiculo = field['values'][0].get('value')
                            break

            # Localizar el ID del Contacto principal vinculado
            if '_embedded' in lead_data and 'contacts' in lead_data['_embedded'] and lead_data['_embedded']['contacts']:
                contact_id = lead_data['_embedded']['contacts'][0].get('id')
                
                if contact_id:
                    # Consultar los datos nativos del contacto para extraer el nombre
                    url_contact = f"https://{KOMMO_DOMAIN}/api/v4/contacts/{contact_id}"
                    contact_resp = requests.get(url_contact, headers=headers)
                    if contact_resp.status_code == 200:
                        contact_data = contact_resp.json()
                        nombre_completo = contact_data.get('name', '')
                        if nombre_completo and nombre_completo.strip():
                            primer_nombre = nombre_completo.split()[0].capitalize()
                    else:
                        print(f"Error al consultar contacto ({contact_resp.status_code}): {contact_resp.text}", flush=True)
        else:
            print(f"Error de autenticación o consulta API de Lead ({lead_resp.status_code}): {lead_resp.text}", flush=True)

        # 3. Empaquetar y ejecutar actualización cruzada en Kommo
        campos_a_actualizar = []
        if texto_vehiculo:
            campos_a_actualizar.append({
                "field_id": FIELD_DESTINO_VEHICULO_ID,
                "values": [{"value": str(texto_vehiculo)}]
            })
            print(f"Vehículo listo para clonar: {texto_vehiculo}", flush=True)
            
        if primer_nombre:
            campos_a_actualizar.append({
                "field_id": FIELD_DESTINO_NOMBRE_ID,
                "values": [{"value": str(primer_nombre)}]
            })
            print(f"Primer Nombre listo para guardar: {primer_nombre}", flush=True)

        if campos_a_actualizar:
            url_patch = f"https://{KOMMO_DOMAIN}/api/v4/leads/{lead_id}"
            patch_resp = requests.patch(url_patch, json={"custom_fields_values": campos_a_actualizar}, headers=headers)
            print(f"Resultado de actualización API: Código {patch_resp.status_code}", flush=True)
            if patch_resp.status_code in [200, 201, 204]:
                return jsonify({"status": "exito", "lead_id": lead_id}), 200
            else:
                print(f"Error al guardar campos ({patch_resp.status_code}): {patch_resp.text}", flush=True)
                return jsonify({"status": "error_guardado", "detalle": patch_resp.text}), 400
        else:
            print("No se encontraron datos nuevos para procesar en esta ejecución.", flush=True)
            return jsonify({"status": "sin_cambios"}), 200

    except Exception as e:
        print(f"Error en ejecución del proceso: {e}", flush=True)
        return jsonify({"status": "error", "detalle": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
