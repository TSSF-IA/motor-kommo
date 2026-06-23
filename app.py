import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- CREDENCIALES SEGURAS ---
KOMMO_DOMAIN = "asesoresintegrales03.kommo.com"
KOMMO_TOKEN = os.environ.get("KOMMO_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# --- IDS DE CAMPOS ---
FIELD_ORIGEN_VEHICULO_ID = 1386779   # Texto Libre (El que viene sucio de FB)
FIELD_DESTINO_VEHICULO_ID = 1386855  # Lista Desplegable
FIELD_DESTINO_NOMBRE_ID = 740646     # 1er Nombre (Contacto)

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
    # Si viene algo nuevo de FB que no está en el mapa, lo limpia quitando guiones y capitalizando
    return str(valor_fb).replace("_", " ").title()

# ==========================================
# MÓDULO 1: IA Y GENERACIÓN DE RESPUESTAS (EN DESARROLLO)
# ==========================================
PROMPT_MAESTRO = """
Eres Rodolfo García Machado, Director General de la agencia Tu Seguro Sin Fronteras. Tienes más de 20 años de experiencia técnica en el mercado asegurador, especializándote en seguros patrimoniales y personales.
Estás hablando por WhatsApp con un prospecto. Tu objetivo es asesorar, rebatir objeciones de precio, aportar valor técnico y llevar al cliente hacia el cierre de la venta para que no sienta la necesidad de cotizar con la competencia.

REGLA DE ORO INQUEBRANTABLE: 
Al describir las coberturas de seguros básicos (como el RCV), debes ceñirte de forma estricta y absoluta a las condiciones oficiales de la tarifa. BAJO NINGUNA CIRCUNSTANCIA puedes inventar, sugerir o añadir beneficios extra que no estén explícitamente contemplados en la póliza básica oficial. Si hay dudas sobre coberturas ampliadas, aclara que requieren un análisis adicional.

Tono: Debe ser completamente imperceptible que eres una IA. Habla en primera persona, con un tono cercano, de cliente-asesor, demostrando autoridad técnica pero mucha empatía. 
"""

def consultar_gemini(mensaje_cliente):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": f"{PROMPT_MAESTRO}\n\nMensaje del cliente: {mensaje_cliente}\n\nEscribe tu respuesta como Rodolfo:"}]
        }]
    }
    
    try:
        respuesta = requests.post(url, json=payload, headers=headers)
        if respuesta.status_code == 200:
            datos = respuesta.json()
            return datos['candidates'][0]['content']['parts'][0]['text']
        else:
            return "Permíteme revisar el tarifario oficial un momento y te detallo esa información."
    except Exception as e:
        return "Tengo una interrupción en el sistema, dame un minuto y te sigo atendiendo."

@app.route('/chat', methods=['POST'])
def recibir_mensaje():
    print("\n=== 💬 NUEVO MENSAJE DE WHATSAPP RECIBIDO ===", flush=True)
    if not GEMINI_API_KEY:
        return jsonify({"status": "error", "detalle": "Sin API Key"}), 500

    if request.is_json:
        data = request.get_json()
        print(f"Datos del chat: {data}", flush=True)
        mensaje_prueba = data.get("mensaje", "")
        if mensaje_prueba:
            respuesta_ia = consultar_gemini(mensaje_prueba)
            print(f"🧠 Respuesta generada por la IA:\n{respuesta_ia}", flush=True)
            return jsonify({"status": "exito", "respuesta": respuesta_ia}), 200
            
    return jsonify({"status": "recibido"}), 200

# ==========================================
# MÓDULO 2: LIMPIEZA Y SINCRONIZACIÓN DE CAMPOS
# ==========================================
@app.route('/webhook', methods=['GET', 'POST'])
def procesar_lead():
    print("\n=== 🚀 MOTOR DE SINCRONIZACIÓN Y LIMPIEZA INICIADO ===", flush=True)
    lead_id = None
    texto_vehiculo_bruto = None
    primer_nombre = None
    contact_id = None
    
    try:
        if request.form:
            form_data = request.form
            for key, val in form_data.items():
                if 'leads' in key and '[id]' in key and 'custom_fields' not in key and 'tags' not in key:
                    lead_id = val
                    break
            for key, val in form_data.items():
                if str(val) == str(FIELD_ORIGEN_VEHICULO_ID) and '[id]' in key:
                    llave_valor = key.replace('[id]', '[values][0][value]')
                    texto_vehiculo_bruto = form_data.get(llave_valor)
                    break

        if not lead_id:
            return jsonify({"status": "recibido"}), 200

        # Traducimos y limpiamos el texto
        texto_vehiculo_limpio = traducir_vehiculo(texto_vehiculo_bruto)
        headers = {
            "Authorization": f"Bearer {KOMMO_TOKEN.strip()}" if KOMMO_TOKEN else "",
            "Content-Type": "application/json"
        }

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
        
        # INYECCIÓN DOBLE EN EL LEAD: Actualiza la Lista y sobreescribe el Texto con la versión limpia
        if texto_vehiculo_limpio:
            payload_v = {
                "custom_fields_values": [
                    {"field_id": FIELD_DESTINO_VEHICULO_ID, "values": [{"value": str(texto_vehiculo_limpio)}]},
                    {"field_id": FIELD_ORIGEN_VEHICULO_ID, "values": [{"value": str(texto_vehiculo_limpio)}]}
                ]
            }
            requests.patch(f"https://{KOMMO_DOMAIN}/api/v4/leads/{lead_id}", json=payload_v, headers=headers)
            print(f"✅ Campos de vehículo (Lista y Texto) limpios y actualizados: {texto_vehiculo_limpio}", flush=True)

        # INYECCIÓN EN EL CONTACTO
        if contact_id:
            contact_resp = requests.get(f"https://{KOMMO_DOMAIN}/api/v4/contacts/{contact_id}", headers=headers)
            if contact_resp.status_code == 200:
                nombre_completo = contact_resp.json().get('name', '')
                if nombre_completo and nombre_completo.strip():
                    primer_nombre = nombre_completo.split()[0].capitalize()
                    payload_n = {"custom_fields_values": [{"field_id": FIELD_DESTINO_NOMBRE_ID, "values": [{"value": str(primer_nombre)}]}]}
                    requests.patch(f"https://{KOMMO_DOMAIN}/api/v4/contacts/{contact_id}", json=payload_n, headers=headers)

        return jsonify({"status": "procesado", "lead_id": lead_id}), 200
    except Exception as e:
        print(f"❌ Error interno manejado: {e}", flush=True)
        return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
