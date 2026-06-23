import os
import re
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- CREDENCIALES SEGURAS ---
KOMMO_DOMAIN = "asesoresintegrales03.kommo.com"
KOMMO_TOKEN = os.environ.get("KOMMO_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# --- IDS DE CAMPOS ---
FIELD_ORIGEN_VEHICULO_ID = 1386779   
FIELD_DESTINO_VEHICULO_ID = 1386855  
FIELD_DESTINO_NOMBRE_ID = 740646     

MAPEO_VEHICULOS = {
    "rustico_ó_más_de_800_kg._de_peso": "Rustico ó Más de 800 kg. de peso",
    "particular_hasta_800_kg._de_peso": "Particular Hasta 800 kg. de peso",
    "pick_up": "Pick Up",
    "panel": "Panel",
    "motos": "Motos",
    "buses": "Buses",
    "carga_hasta_2_tm._de_capacidad": "Carga Hasta 2 TM. de capacidad",
    "carga_más_de_2_y_hasta_5_tm._de_capacidad": "Carga Más de 2 y hasta 5 TM. de capacidad",
    "carga_más_de_5_y_hasta_8_tm._de_capacidad": "Carga Más de 5 y hasta 8 TM. de capacidad",
    "carga_más_de_8_y_hasta_12_tm._de_capacidad": "Carga Más de 8 y hasta 12 TM. de capacidad",
    "carga_más_de_12_tm._de_capacidad": "Carga Más de 12 TM. de capacidad",
    "taxi_-_placa_amarilla": "Taxi - Placa Amarilla"
}

def traducir_vehiculo(valor_fb):
    if not valor_fb:
        return None
    clave = str(valor_fb).strip().lower().replace(" ", "_")
    if clave in MAPEO_VEHICULOS:
        return MAPEO_VEHICULOS[clave]
    return str(valor_fb).replace("_", " ").title()

@app.route('/webhook', methods=['GET', 'POST'])
def procesar_lead():
    print("\n=== 🚀 MOTOR CENTRAL: EXTRACCIÓN Y SINCRONIZACIÓN ===", flush=True)
    lead_id = None
    texto_vehiculo_bruto = None
    primer_nombre = None
    contact_id = None
    
    try:
        if request.form:
            form_data = request.form
            print(f"📡 Disparo recibido de Kommo...", flush=True)
            
            # 1. Buscar ID del Lead (Detecta tanto Leads nuevos como mensajes de WhatsApp)
            for key, val in form_data.items():
                if 'leads' in key and '[id]' in key and 'custom_fields' not in key and 'tags' not in key:
                    lead_id = val
                    break
                if 'message[add]' in key and '[element_id]' in key:
                    lead_id = val
                    break
            
            # 2. Intentar buscar Vehículo por el formulario tradicional
            for key, val in form_data.items():
                if str(val) == str(FIELD_ORIGEN_VEHICULO_ID) and '[id]' in key:
                    llave_valor = key.replace('[id]', '[values][0][value]')
                    texto_vehiculo_bruto = form_data.get(llave_valor)
                    break

        if not lead_id:
            return jsonify({"status": "recibido", "nota": "Ping vacío"}), 200

        print(f"🎯 Lead ID Detectado: {lead_id}", flush=True)
        
        headers = {
            "Authorization": f"Bearer {KOMMO_TOKEN.strip()}" if KOMMO_TOKEN else "",
            "Content-Type": "application/json"
        }

        # 3. LECTURA DE HISTORIAL: Si el webhook no trajo el vehículo, vamos a buscarlo al chat
        if not texto_vehiculo_bruto:
            print("🔍 Activando lectura profunda del historial de chat del Lead...", flush=True)
            url_notes = f"https://{KOMMO_DOMAIN}/api/v4/leads/{lead_id}/notes"
            notes_resp = requests.get(url_notes, headers=headers)
            
            if notes_resp.status_code == 200:
                notes_data = notes_resp.json()
                if '_embedded' in notes_data and 'notes' in notes_data['_embedded']:
                    for note in notes_data['_embedded']['notes']:
                        # Extraemos el texto de la nota/chat
                        texto_nota = note.get('params', {}).get('text', '')
                        
                        if texto_nota and "Tipo de Vehículo a Cotizar:" in texto_nota:
                            print("✅ ¡Mensaje de WhatsApp interceptado!", flush=True)
                            
                            # Escáner Láser para Vehículo
                            match_v = re.search(r"Tipo de Veh[íi]culo a Cotizar:\s*(.+)", str(texto_nota))
                            if match_v:
                                texto_vehiculo_bruto = match_v.group(1).strip()
                                
                            # Escáner Láser para Nombre
                            match_n = re.search(r"Full name:\s*(.+)", str(texto_nota))
                            if match_n:
                                # Toma solo la primera palabra y la capitaliza
                                primer_nombre = match_n.group(1).strip().split()[0].capitalize()
                            break # Salimos del ciclo al encontrar el primer mensaje válido
            else:
                print(f"⚠️ Error al leer historial: {notes_resp.text}", flush=True)

        # 4. Traducción y Conexión Estructural
        texto_vehiculo_limpio = traducir_vehiculo(texto_vehiculo_bruto)
        
        url_lead = f"https://{KOMMO_DOMAIN}/api/v4/leads/{lead_id}?with=contacts"
        lead_resp = requests.get(url_lead, headers=headers)
        
        if lead_resp.status_code == 200:
            lead_data = lead_resp.json()
            # Respaldo final si no se encontró en el chat
            if not texto_vehiculo_limpio and 'custom_fields_values' in lead_data and lead_data['custom_fields_values']:
                for field in lead_data['custom_fields_values']:
                    if str(field.get('field_id')) == str(FIELD_ORIGEN_VEHICULO_ID):
                        if field.get('values') and len(field['values']) > 0:
                            val_bruto = field['values'][0].get('value')
                            texto_vehiculo_limpio = traducir_vehiculo(val_bruto)
                            break
                            
            if '_embedded' in lead_data and 'contacts' in lead_data['_embedded'] and lead_data['_embedded']['contacts']:
                contact_id = lead_data['_embedded']['contacts'][0].get('id')

        # 5. INYECCIÓN EN LA TARJETA DEL LEAD (Vehículo y Limpieza)
        if texto_vehiculo_limpio:
            payload_v = {
                "custom_fields_values": [
                    {"field_id": FIELD_DESTINO_VEHICULO_ID, "values": [{"value": str(texto_vehiculo_limpio)}]},
                    {"field_id": FIELD_ORIGEN_VEHICULO_ID, "values": [{"value": str(texto_vehiculo_limpio)}]}
                ]
            }
            requests.patch(f"https://{KOMMO_DOMAIN}/api/v4/leads/{lead_id}", json=payload_v, headers=headers)
            print(f"✅ Campos de vehículo actualizados: '{texto_vehiculo_limpio}'", flush=True)

        # 6. INYECCIÓN EN EL CONTACTO (Nombre)
        if contact_id:
            contact_resp = requests.get(f"https://{KOMMO_DOMAIN}/api/v4/contacts/{contact_id}", headers=headers)
            if contact_resp.status_code == 200:
                # Si el láser no encontró el nombre en el chat, busca el del perfil de WhatsApp
                if not primer_nombre:
                    nombre_completo = contact_resp.json().get('name', '')
                    if nombre_completo and nombre_completo.strip() and nombre_completo.lower() != "contacto":
                        primer_nombre = nombre_completo.split()[0].capitalize()
                
                if primer_nombre:
                    payload_n = {"custom_fields_values": [{"field_id": FIELD_DESTINO_NOMBRE_ID, "values": [{"value": str(primer_nombre)}]}]}
                    requests.patch(f"https://{KOMMO_DOMAIN}/api/v4/contacts/{contact_id}", json=payload_n, headers=headers)
                    print(f"✅ 1er Nombre guardado: '{primer_nombre}'", flush=True)

        return jsonify({"status": "procesado", "lead_id": lead_id}), 200
    except Exception as e:
        print(f"❌ Error interno manejado: {e}", flush=True)
        return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
