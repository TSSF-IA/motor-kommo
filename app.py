import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

KOMMO_DOMAIN = "asesoresintegrales03.kommo.com"
KOMMO_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6ImVmZDY4MThjYTllMmJiNTA1ODFkY2ExZTE4NWVmOWM3Njc0N2U3MzYzYTVkYjY3ZjBiMmUyODI3Nzk4NWVhNWU1NDk4YjM0ZDkyMTIzYTk0In0.eyJhdWQiOiI3ZmQ5Yjc4Yy0zNTU3LTRhNDAtOTI3My1iNjk3NWU3NDJkNGQiLCJqdGkiOiJlZmQ2ODE4Y2E5ZTJiYjUwNTgxZGNhMWUxODVlZjljNzY3NDdlNzM2M2E1ZGI2N2YwYjJlMjgyNzc5ODVlYTVlNTQ5OGIzNGQ5MjEyM2E5NCIsImlhdCI6MTc4MTgwMzk1NiwibmJmIjoxNzgxODAzOTU2LCJleHAiOjE5MjQ5MDU2MDAsInN1YiI6Ijk1MDE4NjciLCJncmFudF90eXBlIjoiIiwiYWNjb3VudF9pZCI6MzExODA3OTEsImJhc2VfZG9tYWluIjoia29tbW8uY29tIiwidmVyc2lvbiI6Miwic2NvcGVzIjpbImNybSIsImZpbGVzIiwiZmlsZXNfZGVsZXRlIiwibm90aWZpY2F0aW9ucyIsInB1c2hfbm90aWZpY2F0aW9ucyIsInVzZXJzX2FjdGl2YXRlIiwidXNlcnNfYWRkIiwidXNlcnNfZGVhY3RpdmF0ZSJdLCJoYXNoX3V1aWQiOiJlMzNhMmM2NC03YTllLTQ1NzYtODQ1Yy1kZjBlODQyMmUxNmYiLCJhcGlfZG9tYWluIjoiYXBpLWcua29tbW8uY29tIn0.H0BJhLb8ofc9vVDM_Q7IwkfhgQ2RdBbZbbpZHHyFWqdZsVZpnoF7VqRe0tm_CpkTgQZdgu2C5uWo3fPZsQJDwU0pY1IQi86TQJiDyhVN9aHZUSakY6RznhPz9t_O1hOqgR8h99dAfhr-a0oDUSLPsxd7EPV4hQNSQwGS3TCMh6g9Lvi8JySW4RFGJIJ8Im-Dh2FJ8C8vFCyF_Q4LHvRXI9aYEYgl-21JU9GrXVT11ansHf_bTdgcXvZBrGFLKWZt6Z3B5J5K05j0ALEgOyIfbiklymN6xJnbVPlnMo4hj3x1E8cPt5LkaFWuy_wd3dmuFsfao-PsMhn1hxzMtWv7xw"

FIELD_ORIGEN_VEHICULO_ID = 1386779   
FIELD_DESTINO_VEHICULO_ID = 1386855  
FIELD_DESTINO_NOMBRE_ID = 740646     

@app.route('/webhook', methods=['GET', 'POST'])
def procesar_lead():
    print("\n=== 🚀 INICIANDO MOTOR DE SINCRONIZACIÓN ===", flush=True)
    lead_id = None
    texto_vehiculo = None
    primer_nombre = None
    
    try:
        # 1. EXTRACCIÓN MILIMÉTRICA BASADA EN EL LOG DEL SONAR
        if request.form:
            form_data = request.form
            
            # Buscamos el ID de la tarjeta
            for key, val in form_data.items():
                if 'leads' in key and '[id]' in key and 'custom_fields' not in key and 'tags' not in key:
                    lead_id = val
                    break
            
            # Buscamos el vehículo utilizando la estructura exacta que demostró el Sonar
            for key, val in form_data.items():
                if val == str(FIELD_ORIGEN_VEHICULO_ID) and '[id]' in key:
                    # Encontramos la llave del ID. Ahora construimos el nombre de la llave hermana que tiene el valor real.
                    llave_del_valor = key.replace('[id]', '[values][0][value]')
                    texto_vehiculo = form_data.get(llave_del_valor)
                    break

        if not lead_id:
            print("No se detectó un ID de prospecto válido. Ignorando.", flush=True)
            return jsonify({"status": "ok", "nota": "Disparo vacío o de prueba"}), 200

        print(f"✅ Lead ID Atrapado: {lead_id}", flush=True)
        if texto_vehiculo:
            print(f"✅ Vehículo Origen Atrapado: {texto_vehiculo}", flush=True)

        # 2. CONEXIÓN MAESTRA A KOMMO PARA SACAR EL CONTACTO
        headers = {
            "Authorization": f"Bearer {KOMMO_TOKEN}",
            "Content-Type": "application/json"
        }
        
        url_lead = f"https://{KOMMO_DOMAIN}/api/v4/leads/{lead_id}?with=contacts"
        lead_resp = requests.get(url_lead, headers=headers)
        
        if lead_resp.status_code == 200:
            lead_data = lead_resp.json()
            
            # Si el webhhok falló en traer el vehículo, lo sacamos directo de la API
            if not texto_vehiculo and 'custom_fields_values' in lead_data and lead_data['custom_fields_values']:
                for field in lead_data['custom_fields_values']:
                    if str(field.get('field_id')) == str(FIELD_ORIGEN_VEHICULO_ID):
                        if field.get('values') and len(field['values']) > 0:
                            texto_vehiculo = field['values'][0].get('value')
                            print(f"✅ Vehículo extraído por API: {texto_vehiculo}", flush=True)
                            break
            
            # Ubicar el Contacto
            contact_id = None
            if '_embedded' in lead_data and 'contacts' in lead_data['_embedded'] and lead_data['_embedded']['contacts']:
                contact_id = lead_data['_embedded']['contacts'][0].get('id')
                
            # Extraer el Nombre del Contacto
            if contact_id:
                url_contact = f"https://{KOMMO_DOMAIN}/api/v4/contacts/{contact_id}"
                contact_resp = requests.get(url_contact, headers=headers)
                if contact_resp.status_code == 200:
                    c_data = contact_resp.json()
                    nombre_completo = c_data.get('name', '')
                    if nombre_completo and nombre_completo.strip():
                        # Capitalizamos la primera palabra (Ej: "jUan pErez" -> "Juan")
                        primer_nombre = nombre_completo.split()[0].capitalize()
                        print(f"✅ 1er Nombre limpio y formateado: {primer_nombre}", flush=True)
        else:
            print(f"⚠️ Error de Token/Conexión con Kommo: {lead_resp.text}", flush=True)

        # 3. EMPAQUETADO Y CLONACIÓN
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
            
        if campos_a_actualizar:
            url_patch = f"https://{KOMMO_DOMAIN}/api/v4/leads/{lead_id}"
            patch_resp = requests.patch(url_patch, json={"custom_fields_values": campos_a_actualizar}, headers=headers)
            print(f"🏁 Resultado de Escritura en Kommo: CÓDIGO {patch_resp.status_code}", flush=True)
            return jsonify({"status": "exito", "lead": lead_id}), 200
        else:
            print("⚠️ No se encontraron ni el Vehículo ni el Contacto para actualizar.", flush=True)
            return jsonify({"status": "sin_datos"}), 200

    except Exception as e:
        print(f"❌ Error crítico en ejecución: {e}", flush=True)
        return jsonify({"status": "error_interno", "detalle": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
