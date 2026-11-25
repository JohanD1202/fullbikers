import os
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from controllers.catalogo_controller import catalogo_bp

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

app.register_blueprint(catalogo_bp)

@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "estado": "OK",
        "servicio": "API FullBikers",
        "modulo_activo": "Catalogo y Pagina Principal"
    }), 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)