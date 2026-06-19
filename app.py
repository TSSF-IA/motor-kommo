import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

KOMMO_DOMAIN = "asesoresintegrales03.kommo.com"
# Lectura directa y hermética del token desde el sistema de Render
KOMMO_TOKEN = os.environ.get("KOMMO_TOKEN")

FIELD_ORIGEN_VEHICULO_ID = 1386779   # DATOS DE VEHICULOS (Origen)
FIELD_DESTINO_VEHICULO_ID = 1386855  # Tipo de Vehículo (Destino)
FIELD_DESTINO_NOMBRE_ID = 740646     # 1er Nombre (Destino)

@app.route('/webhook', methods=['GET', 'POST'])
def procesar_lead():
    print("\n=== 🚀 INICIANDO SINCRONIZACIÓN OPERATIVA BLINDADA ===", flush=True)
    lead_id = None
    texto_vehiculo = None
    primer_nombre = None
    
    try:
        # 1. Extracción de datos del formulario entrante (Estructuras add y update)
        if request.form:
            form_data = request.form
            
            # Capturar ID del Lead
            for key, val in form_data.items():
                if 'leads' in key and '[id]' in key and 'custom_fields' not in key and 'tags' not in key:
                    lead_id = val
                    break
            
            # Capturar Vehículo del formulario
            for key, val in form_data.items():
                if str(val) == str(FIELD_ORIGEN_VEHICULO_ID) and '[id]' in key:
                    llave_valor = key.replace('[id]', '[values][0][value]')
                    texto_vehiculo = form_data.get(llave_valor)
                    break

        if not lead_id:
            print("Aviso: Petición vacía o de diagnóstico recibida.", flush=True)
            return jsonify({"status": "recibido", "nota": "Ping controlado"}), 200

        print(f"Lead ID Detectado: {lead_id}", flush=True)
        
        if not KOMMO_TOKEN:
            print("⚠️ Error: La variable KOMMO_TOKEN no existe en el entorno de Render.", flush=True)
            return jsonify({"status": "error_config"}), 200

        headers = {
            "Authorization": f"Bearer {KOMMO_TOKEN.strip()}",
            "Content-Type": "application/json"
        }
        url_patch = f"https://{KOMMO_DOMAIN}/api/v4/leads/{lead_id}"

        # --- FASE A: ACTUALIZACIÓN INDEPENDIENTE DEL VEHÍCULO ---
        if texto_vehiculo:
            print(f"Procesando campo Vehículo -> Valor: '{texto_vehiculo}'", flush=True)
            payload_v = {
                "custom_fields_values": [
                    {
                        "field_id": FIELD_DESTINO_VEHICULO_ID,
                        "values": [{"value": str(texto_vehiculo)}]
                    }
                ]
            }
            try:
                resp_v = requests.patch(url_patch, json=payload_v, headers=headers)
                print(f"Respuesta API Vehículo: Código {resp_v.status_code}", flush=True)
                if resp_v.status_code >= 400:
                    print(f"⚠️ Detalles de rechazo en Vehículo: {resp_v.text}", flush=True)
            except Exception as ex_v:
                print(f"❌ Error de red en actualización de vehículo: {ex_v}", flush=True)

        # --- FASE B: CONSULTA DE RESPALDO PARA DETECTAR EL NOMBRE ---
        url_lead = f"https://{KOMMO_DOMAIN}/api/v4/leads/{lead_id}?with=contacts"
        try:
            lead_resp = requests.get(url_lead, headers=headers)
            if lead_resp.status_code == 200:
                lead_data = lead_resp.json()
                if '_embedded' in lead_data and 'contacts' in lead_data['_embedded'] and lead_data['_embedded']['contacts']:
                    contact_id = lead_data['_embedded']['contacts'][0].get('id')
                    
                    if contact_id:
                        url_contact = f"https://{KOMMO_DOMAIN}/api/v4/contacts/{contact_id}"
                        contact_resp = requests.get(url_contact, headers=headers)
                        if contact_resp.status_code == 200:
                            contact_data = contact_resp.json()
                            nombre_completo = contact_data.get('name', '')
                            if nombre_completo and nombre_completo.strip():
                                primer_nombre = nombre_completo.split()[0].capitalize()
        except Exception as ex_c:
            print(f"❌ Error de comunicación al buscar datos del contacto: {ex_c}", flush=True)

        # --- FASE C: ACTUALIZACIÓN INDEPENDIENTE DEL NOMBRE ---
        if primer_nombre:
            print(f"Procesando campo Nombre -> Valor: '{primer_nombre}'", flush=True)
            payload_n = {
                "custom_fields_values": [
                    {
                        "field_id": FIELD_DESTINO_NOMBRE_ID,
                        "values": [{"value": str(primer_nombre)}]
                    }
                ]
            }
            try:
                resp_n = requests.patch(url_patch, json=payload_n, headers=headers)
                print(f"Respuesta API Nombre: Código {resp_n.status_code}", flush=True)
                if resp_n.status_code >= 400:
                    print(f"⚠️ Detalles de rechazo en Nombre: {resp_n.text}", flush=True)
            except Exception as ex_n:
                print(f"❌ Error de red en actualización de nombre: {ex_n}", flush=True)

        # BLINDAJE OPERATIVO ABSOLUTO: Siempre devolvemos código 200 para que Kommo mantenga el bot activo
        print("Sincronización finalizada. Enviando confirmación de éxito al CRM.", flush=True)
        return jsonify({"status": "procesado", "lead_id": lead_id}), 200

    except Exception as e:
        print(f"Error general controlado en ejecución: {e}", flush=True)
        return jsonify({"status": "ok", "nota": "Excepción absorbida"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
