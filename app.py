import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

KOMMO_DOMAIN = "asesoresintegrales03.kommo.com"
KOMMO_TOKEN = os.environ.get("KOMMO_TOKEN")

FIELD_ORIGEN_VEHICULO_ID = 1386779   # Origen Facebook
FIELD_DESTINO_VEHICULO_ID = 1386855  # Destino Lead (Lista Desplegable)
FIELD_DESTINO_NOMBRE_ID = 740646     # ¡OJO! REEMPLAZAR ESTE NÚMERO POR EL ID REAL DE "1er Nombre" EN CONTACTOS

@app.route('/webhook', methods=['GET', 'POST'])
def procesar_lead():
    print("\n=== 🚀 MOTOR DE SINCRONIZACIÓN INICIADO ===", flush=True)
    lead_id = None
    texto_vehiculo = None
    primer_nombre = None
    contact_id = None
    
    try:
        # 1. Extracción desde Formulario
        if request.form:
            form_data = request.form
            for key, val in form_data.items():
                if 'leads' in key and '[id]' in key and 'custom_fields' not in key and 'tags' not in key:
                    lead_id = val
                    break
            for key, val in form_data.items():
                if str(val) == str(FIELD_ORIGEN_VEHICULO_ID) and '[id]' in key:
                    llave_valor = key.replace('[id]', '[values][0][value]')
                    texto_vehiculo = form_data.get(llave_valor)
                    break

        if not lead_id:
            return jsonify({"status": "recibido", "nota": "Ping"}), 200

        print(f"Lead ID: {lead_id}", flush=True)
        headers = {
            "Authorization": f"Bearer {KOMMO_TOKEN.strip()}",
            "Content-Type": "application/json"
        }

        # 2. Consultar API para Contacto y datos faltantes
        url_lead = f"https://{KOMMO_DOMAIN}/api/v4/leads/{lead_id}?with=contacts"
        lead_resp = requests.get(url_lead, headers=headers)
        
        if lead_resp.status_code == 200:
            lead_data = lead_resp.json()
            
            if not texto_vehiculo and 'custom_fields_values' in lead_data and lead_data['custom_fields_values']:
                for field in lead_data['custom_fields_values']:
                    if str(field.get('field_id')) == str(FIELD_ORIGEN_VEHICULO_ID):
                        if field.get('values') and len(field['values']) > 0:
                            texto_vehiculo = field['values'][0].get('value')
                            break
                            
            if '_embedded' in lead_data and 'contacts' in lead_data['_embedded'] and lead_data['_embedded']['contacts']:
                contact_id = lead_data['_embedded']['contacts'][0].get('id')
        
        # 3. FASE LEAD: Inyectar Vehículo
        if texto_vehiculo:
            print(f"Intentando clonar Vehículo -> '{texto_vehiculo}'", flush=True)
            payload_v = {"custom_fields_values": [{"field_id": FIELD_DESTINO_VEHICULO_ID, "values": [{"value": str(texto_vehiculo)}]}]}
            resp_v = requests.patch(f"https://{KOMMO_DOMAIN}/api/v4/leads/{lead_id}", json=payload_v, headers=headers)
            
            if resp_v.status_code >= 400:
                print(f"⚠️ ALERTA VEHÍCULO: Kommo rechazó '{texto_vehiculo}'. Seguramente esta opción NO EXISTE escrita exactamente así en tu lista desplegable de Kommo.", flush=True)
            else:
                print("✅ Vehículo guardado con éxito.", flush=True)

        # 4. FASE CONTACTO: Inyectar Nombre
        if contact_id:
            contact_resp = requests.get(f"https://{KOMMO_DOMAIN}/api/v4/contacts/{contact_id}", headers=headers)
            if contact_resp.status_code == 200:
                nombre_completo = contact_resp.json().get('name', '')
                if nombre_completo and nombre_completo.strip():
                    primer_nombre = nombre_completo.split()[0].capitalize()
                    
                    print(f"Intentando guardar 1er Nombre -> '{primer_nombre}'", flush=True)
                    payload_n = {"custom_fields_values": [{"field_id": FIELD_DESTINO_NOMBRE_ID, "values": [{"value": str(primer_nombre)}]}]}
                    resp_n = requests.patch(f"https://{KOMMO_DOMAIN}/api/v4/contacts/{contact_id}", json=payload_n, headers=headers)
                    
                    if resp_n.status_code >= 400:
                        print(f"⚠️ ALERTA NOMBRE: Kommo rechazó el guardado. Confirma que el ID {FIELD_DESTINO_NOMBRE_ID} es realmente el campo de texto '1er Nombre' y no una lista.", flush=True)
                    else:
                        print("✅ 1er Nombre guardado con éxito.", flush=True)

        return jsonify({"status": "procesado", "lead_id": lead_id}), 200

    except Exception as e:
        print(f"❌ Error interno manejado: {e}", flush=True)
        return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
