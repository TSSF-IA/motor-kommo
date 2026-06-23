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
    mensaje_texto = ""
    
    try:
        if request.form:
            form_data = request.form
            print(f"📡 Disparo crudo recibido de Kommo: {dict(form_data)}", flush=True)
            
            # 1. Extractor Universal (Soporta leads, message y messages en plural)
            for key, val in form_data.items():
                if ('leads' in key or 'message' in key) and '[id]' in key and 'custom_fields' not in key and 'tags' not in key:
                    lead_id = val
                elif '[element_id]' in key:
                    lead_id = val
                
                # Capturar el texto del chat directo desde el cuerpo del Webhook
                if '[text]' in key:
                    mensaje_texto = val
            
            # 2. Buscar Vehículo por el formulario tradicional si viene mapeado directamente
            for key, val in form_data.items():
                if str(val) == str(FIELD_ORIGEN_VEHICULO_ID) and '[id]' in key:
                    llave_valor = key.replace('[id]', '[values][0][value]')
                    texto_vehiculo_bruto = form_data.get(llave_valor)
                    break

            # 3. Escáner Láser sobre el mensaje de chat interceptado
            if mensaje_texto and ("Tipo de Vehículo a Cotizar:" in mensaje_texto or "Completé el formulario" in mensaje_texto):
                print("📩 ¡Texto de formulario detectado en el chat! Procesando escáner...", flush=True)
                
                # Extraer Vehículo
                match_v = re.search(r"Tipo de Veh[íi]culo a Cotizar:\s*(.+)", str(mensaje_texto))
                if match_v:
                    texto_vehiculo_bruto = match_v.group(1).strip()
                    print(f"Láser detectó vehículo en chat: {texto_vehiculo_bruto}", flush=True)
                    
                # Extraer Nombre
                match_n = re.search(r"Full name:\s*(.+)", str(mensaje_texto))
                if match_n:
                    primer_nombre = match_n.group(1).strip().split()[0].capitalize()
                    print(f"Láser detectó nombre en chat: {primer_nombre}", flush=True)

        if not lead_id:
            print("Aviso: Disparo recibido sin ID de lead procesable.", flush=True)
            return jsonify({"status": "recibido", "nota": "Ping vacío"}), 200

        print(f"🎯 Lead ID Activo: {lead_id}", flush=True)
        headers = {
            "Authorization": f"Bearer {KOMMO_TOKEN.strip()}" if KOMMO_TOKEN else "",
            "Content-Type": "application/json"
        }

        # 4. Canal de Respaldo Histórico (Si faltan datos en el disparo directo)
        if not texto_vehiculo_bruto or not primer_nombre:
            print("🔍 Buscando datos adicionales en el historial de notas del Lead...", flush=True)
            url_notes = f"https://{KOMMO_DOMAIN}/api/v4/leads/{lead_id}/notes"
            notes_resp = requests.get(url_notes, headers=headers)
            
            if notes_resp.status_code == 200:
                notes_data = notes_resp.json()
                if '_embedded' in notes_data and 'notes' in notes_data['_embedded']:
                    for note in notes_data['_embedded']['notes']:
                        texto_nota = note.get('params', {}).get('text', '')
                        if texto_nota and "Tipo de Vehículo a Cotizar:" in texto_nota:
                            print("✅ ¡Mensaje localizado en el historial de notas!", flush=True)
                            match_v = re.search(r"Tipo de Veh[íi]culo a Cotizar:\s*(.+)", str(texto_nota))
                            if match_v and not texto_vehiculo_bruto:
                                texto_vehiculo_bruto = match_v.group(1).strip()
                            
                            match_n = re.search(r"Full name:\s*(.+)", str(texto_nota))
                            if match_n and not primer_nombre:
                                primer_nombre = match_n.group(1).strip().split()[0].capitalize()
                            break
            elif notes_resp.status_code == 204:
                print("ℹ️ El historial de notas está vacío en este milisegundo (204 No Content).", flush=True)
            else:
                print(f"⚠️ Nota de API (Código {notes_resp.status_code}): {notes_resp.text}", flush=True)

        # 5. Traducción final del Vehículo y localización de Contacto
        texto_vehiculo_limpio = traducir_vehiculo(texto_vehiculo_bruto)
        
        url_lead = f"https://{KOMMO_DOMAIN}/api/v4/leads/{lead_id}?with=contacts"
        lead_resp = requests.get(url_lead, headers=headers)
        
        if lead_resp.status_code == 200:
            lead_data = lead_resp.json()
            if not texto_vehiculo_limpio and 'custom_fields_values' in lead_data and lead_data['custom_fields_values']:
                for field in lead_data['custom_fields_values']:
                    if str(field.get('field_id')) == str(FIELD_ORIGEN_VEHICULO_ID):
                        if field.get('values') and len(field['values']) > 0:
                            val_bruto = field['values'][0].get('value')
                            texto_vehiculo_limpio = traducir_vehiculo(val_bruto)
                            break
                            
            if '_embedded' in lead_data and 'contacts' in lead_data['_embedded'] and lead_data['_embedded']['contacts']:
                contact_id = lead_data['_embedded']['contacts'][0].get('id')

        # 6. Guardado en la tarjeta del Lead (Lista desplegable + Texto limpio)
        if texto_vehiculo_limpio:
            payload_v = {
                "custom_fields_values": [
                    {"field_id": FIELD_DESTINO_VEHICULO_ID, "values": [{"value": str(texto_vehiculo_limpio)}]},
                    {"field_id": FIELD_ORIGEN_VEHICULO_ID, "values": [{"value": str(texto_vehiculo_limpio)}]}
                ]
            }
            requests.patch(f"https://{KOMMO_DOMAIN}/api/v4/leads/{lead_id}", json=payload_v, headers=headers)
            print(f"✅ Campos de vehículo actualizados con éxito: '{texto_vehiculo_limpio}'", flush=True)

        # 7. Guardado en el Contacto (Nombre de pila limpio)
        if contact_id:
            contact_resp = requests.get(f"https://{KOMMO_DOMAIN}/api/v4/contacts/{contact_id}", headers=headers)
            if contact_resp.status_code == 200:
                if not primer_nombre:
                    nombre_completo = contact_resp.json().get('name', '')
                    if nombre_completo and nombre_completo.strip() and nombre_completo.lower() != "contacto":
                        primer_nombre = nombre_completo.split()[0].capitalize()
                
                if primer_nombre:
                    payload_n = {"custom_fields_values": [{"field_id": FIELD_DESTINO_NOMBRE_ID, "values": [{"value": str(primer_nombre)}]}]}
                    requests.patch(f"https://{KOMMO_DOMAIN}/api/v4/contacts/{contact_id}", json=payload_n, headers=headers)
                    print(f"✅ 1er Nombre guardado con éxito: '{primer_nombre}'", flush=True)

        return jsonify({"status": "procesado", "lead_id": lead_id}), 200
    except Exception as e:
        print(f"❌ Error interno manejado: {e}", flush=True)
        return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
