import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

KOMMO_DOMAIN = "asesoresintegrales03.kommo.com"
KOMMO_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6ImVmZDY4MThjYTllMmJiNTA1ODFkY2ExZTE4NWVmOWM3Njc0N2U3MzYzYTVkYjY3ZjBiMmUyODI3Nzk4NWVhNWU1NDk4YjM0ZDkyMTIzYTk0In0.eyJhdWQiOiI3ZmQ5Yjc4Yy0zNTU3LTRhNDAtOTI3My1iNjk3NWU3NDJkNGQiLCJqdGkiOiJlZmQ2ODE4Y2E5ZTJiYjUwNTgxZGNhMWUxODVlZjljNzY3NDdlNzM2M2E1ZGI2N2YwYjJlMjgyNzc5ODVlYTVlNTQ5OGIzNGQ5MjEyM2E5NCIsImlhdCI6MTc4MTgwMzk1NiwibmJmIjoxNzgxODAzOTU2LCJleHAiOjE5MjQ5MDU2MDAsInN1YiI6Ijk1MDE4NjciLCJncmFudF90eXBlIjoiIiwiYWNjb3VudF9pZCI6MzExODA3OTEsImJhc2VfZG9tYWluIjoia29tbW8uY29tIiwidmVyc2lvbiI6Miwic2NvcGVzIjpbImNybSIsImZpbGVzIiwiZmlsZXNfZGVsZXRlIiwibm90aWZpY2F0aW9ucyIsInB1c2hfbm90aWZpY2F0aW9ucyIsInVzZXJzX2FjdGl2YXRlIiwidXNlcnNfYWRkIiwidXNlcnNfZGVhY3RpdmF0ZSJdLCJoYXNoX3V1aWQiOiJlMzNhMmM2NC03YTllLTQ1NzYtODQ1Yy1kZjBlODQyMmUxNmYiLCJhcGlfZG9tYWluIjoiYXBpLWcua29tbW8uY29tIn0.H0BJhLb8ofc9vVDM_Q7IwkfhgQ2RdBbZbbpZHHyFWqdZsVZpnoF7VqRe0tm_CpkTgQZdgu2C5uWo3fPZsQJDwU0pY1IQi86TQJiDyhVN9aHZUSakY6RznhPz9t_O1hOqgR8h99dAfhr-a0oDUSLPsxd7EPV4hQNSQwGS3TCMh6g9Lvi8JySW4RFGJIJ8Im-Dh2FJ8C8vFCyF_Q4LHvRXI9aYEYgl-21JU9GrXVT11ansHf_bTdgcXvZBrGFLKWZt6Z3B5J5K05j0ALEgOyIfbiklymN6xJnbVPlnMo4hj3x1E8cPt5LkaFWuy_wd3dmuFsfao-PsMhn1hxzMtWv7xw"

FIELD_ORIGEN_VEHICULO_ID = 1386779   # DATOS DE VEHICULOS (Origen)
FIELD_DESTINO_VEHICULO_ID = 1386855  # Tipo de Vehículo (Destino)
FIELD_DESTINO_NOMBRE_ID = 740646     # 1er Nombre (Destino)

@app.route('/webhook', methods=['GET', 'POST'])
def procesar_lead():
    print(f"¡ALERTA MÁXIMA!: Disparo entrante detectado por método {request.method}", flush=True)
    
    lead_id = None
    texto_vehiculo = None
    primer_nombre = None
    
    try:
        # 1. EXTRACCIÓN DE DATOS DESDE EL WEBHOOK (Método Seguro JSON/Salesbot)
        if request.is_json:
            json_data = request.get_json()
            print(f"Estructura de Datos JSON Recibida: {json_data}", flush=True)
            
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
                    lead_data = lead_list[0]
                    lead_id = lead_data.get('id')
                    
                    # Captura inmediata del vehículo si viene incrustado en el disparo
                    if 'custom_fields' in lead_data:
                        for field in lead_data['custom_fields']:
                            if str(field.get('id')) == str(FIELD_ORIGEN_VEHICULO_ID):
                                if 'values' in field and len(field['values']) > 0:
                                    texto_vehiculo = field['values'][0].get('value')
                                    print(f"Vehículo localizado en carga útil del Webhook: {texto_vehiculo}", flush=True)
                                    break
            
            if not lead_id:
                lead_id = json_data.get('id') or json_data.get('lead_id')

        # EXTRACCIÓN DESDE FORMULARIO (Webhook de etapa tradicional)
        elif request.form:
            form_data = request.form
            print(f"Estructura de Formulario Recibida: {dict(form_data)}", flush=True)
            for key in form_data.keys():
                if 'leads' in key and '[id]' in key:
                    lead_id = form_data[key]
                if str(FIELD_ORIGEN_VEHICULO_ID) in key and '[value]' in key:
                    texto_vehiculo = form_data[key]

        # EXTRACCIÓN DESDE PARÁMETROS URL (GET)
        if not lead_id and request.args:
            lead_id = request.args.get('id') or request.args.get('lead_id')

        # Blindaje contra pings vacíos de Kommo
        if not lead_id:
            print("Aviso: Petición de diagnóstico o ping vacío recibida correctamente.", flush=True)
            return jsonify({"status": "recibido", "nota": "Validación de ruta exitosa"}), 200

        print(f"Iniciando procesamiento para Lead ID: {lead_id}", flush=True)
        headers = {
            "Authorization": f"Bearer {KOMMO_TOKEN}",
            "Content-Type": "application/json"
        }

        # 2. CONSULTA RESPALDO A API DE KOMMO
        url_lead = f"https://{KOMMO_DOMAIN}/api/v4/leads/{lead_id}?with=contacts"
        lead_response = requests.get(url_lead, headers=headers)
        
        contact_id = None
        if lead_response.status_code == 200:
            lead_api_data = lead_response.json()
            
            if not texto_vehiculo:
                if 'custom_fields_values' in lead_api_data and lead_api_data['custom_fields_values']:
                    for field in lead_api_data['custom_fields_values']:
                        if str(field.get('field_id')) == str(FIELD_ORIGEN_VEHICULO_ID):
                            if field.get('values') and len(field['values']) > 0:
                                texto_vehiculo = field['values'][0].get('value')
                                print(f"Vehículo extraído desde API del Lead: {texto_vehiculo}", flush=True)
                                break
            
            # Localizar ID del Contacto vinculado
            if '_embedded' in lead_api_data and 'contacts' in lead_api_data['_embedded'] and lead_api_data['_embedded']['contacts']:
                contact_id = lead_api_data['_embedded']['contacts'][0].get('id')
                print(f"ID de Contacto Vinculado detectado: {contact_id}", flush=True)
        else:
            print(f"Aviso: Error en consulta API de Lead ({lead_response.status_code}): {lead_response.text}", flush=True)

        # 3. CONSULTA DIRECTA A LA ENTIDAD CONTACTOS PARA OBTENER EL NOMBRE
        if contact_id:
            url_contact = f"https://{KOMMO_DOMAIN}/api/v4/contacts/{contact_id}"
            contact_response = requests.get(url_contact, headers=headers)
            if contact_response.status_code == 200:
                contact_data = contact_response.json()
                nombre_completo = contact_data.get('name', '')
                if nombre_completo and nombre_completo.strip():
                    primer_nombre = nombre_completo.split()[0].capitalize()
                    print(f"Nombre de contacto formateado con éxito: '{primer_nombre}'", flush=True)
            else:
                print(f"Aviso: Error en consulta API de Contacto: {contact_response.text}", flush=True)

        # 4. CONSTRUCCIÓN DEL PAQUETE UNIFICADO DE ACTUALIZACIÓN
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
            print(f"Finalizado: No se localizaron datos válidos para modificar en el Lead {lead_id}.", flush=True)
            return jsonify({"status": "sin_cambios"}), 200

        # 5. INYECCIÓN DE DATOS EN UN SOLO MOVIMIENTO
        url_patch = f"https://{KOMMO_DOMAIN}/api/v4/leads/{lead_id}"
        payload_patch = {"custom_fields_values": campos_a_actualizar}
        
        print(f"Enviando actualización final a Kommo: {payload_patch}", flush=True)
        patch_response = requests.patch(url_patch, json=payload_patch, headers=headers)
        print(f"Respuesta de Guardado en Kommo: Código {patch_response.status_code}", flush=True)
        
        if patch_response.status_code in [200, 201, 204]:
            return jsonify({
                "status": "exito",
                "lead_id": lead_id,
                "vehiculo_procesado": texto_vehiculo,
                "nombre_procesado": primer_nombre
            }), 200
        else:
            print(f"Fallo en guardado API Kommo: {patch_response.text}", flush=True)
            return jsonify({"status": "error_guardado", "detalle": patch_response.text}), 400

    except Exception as e:
        print(f"Error crítico en ejecución interna: {e}", flush=True)
        return jsonify({"status": "error_interno", "detalle": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
