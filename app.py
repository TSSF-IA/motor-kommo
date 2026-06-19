import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

KOMMO_DOMAIN = "asesoresintegrales03.kommo.com"
# El motor lee la llave directamente desde el sistema de Render, garantizando cero errores de copia
KOMMO_TOKEN = os.environ.get("KOMMO_TOKEN")

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
        # 1. Extracción del ID desde el formulario (Soporta estructuras add y update)
        if request.form:
            form_data = request.form
            print(f"Formulario recibido: {dict(form_data)}", flush=True)
            
            # Localizar ID del Lead
            for key, val in form_data.items():
                if 'leads' in key and '[id]' in key and 'custom_fields' not in key and 'tags' not in key:
                    lead_id = val
                    break
            
            # Localizar vehículo si viene en el cuerpo del disparo
            for key, val in form_data.items():
                if str(val) == str(FIELD_ORIGEN_VEHICULO_ID) and '[id]' in key:
                    llave_valor = key.replace('[id]', '[values][0][value]')
                    texto_vehiculo = form_data.get(llave_valor)
                    break

        if not lead_id:
            print("No se detectó un ID de lead válido en el disparo.", flush=True)
            return jsonify({"status": "recibido", "nota": "Ping sin datos de proceso"}), 200

        print(f"ID del Lead detectado: {lead_id}", flush=True)
        
        if not KOMMO_TOKEN:
            print("⚠️ Error Crítico: La variable de entorno KOMMO_TOKEN no está configurada en Render.", flush=True)
            return jsonify({"status": "error_config", "detalle": "Falta el Token en Render"}), 500

        headers = {
            "Authorization": f"Bearer {KOMMO_TOKEN.strip()}",
            "Content-Type": "application/json"
        }

        # 2. Conexión de respaldo mediante la API para extraer el contacto vinculado
        url_lead = f"https://{KOMMO_DOMAIN}/api/v4/leads/{lead_id}?with=contacts"
        lead_resp = requests.get(url_lead, headers=headers)
        
        if lead_resp.status_code == 200:
            lead_data = lead_resp.json()
            
            # Si el webhook no trajo el vehículo (típico en eventos 'add'), se obtiene por API
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
                    # Obtener los datos nativos del contacto para extraer el nombre
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

        # 3. Empaquetar y ejecutar actualización en un solo movimiento
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
            print("No se encontraron datos nuevos para modificar en esta ejecución.", flush=True)
            return jsonify({"status": "sin_cambios"}), 200

    except Exception as e:
        print(f"Error en ejecución del proceso: {e}", flush=True)
        return jsonify({"status": "error", "detalle": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
