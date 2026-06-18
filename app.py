import os
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/webhook', methods=['GET', 'POST'])
def sonar():
    print("=== 🚨 NUEVO DISPARO RECIBIDO EN RENDER 🚨 ===", flush=True)
    print(f"Método: {request.method}", flush=True)
    
    if request.is_json:
        print(f"JSON CRUDO: {request.get_json()}", flush=True)
    elif request.form:
        print(f"FORMULARIO CRUDO: {dict(request.form)}", flush=True)
    elif request.args:
        print(f"URL GET CRUDA: {dict(request.args)}", flush=True)
    else:
        print("Petición vacía o formato desconocido.", flush=True)
        
    print("==============================================", flush=True)
    return jsonify({"status": "recibido", "nota": "Modo Sonar Activo"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
