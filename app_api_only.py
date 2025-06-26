#!/usr/bin/env python3
"""
VideoAI API - Servidor apenas da API REST
Para ser usado quando a interface web for separada
"""

import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

from api.routes import api_bp
from api.admin_routes import admin_bp
from src.utils.database import check_db_connection

# Versão da API
API_VERSION = "1.1.0"

# Carrega as variáveis de ambiente
load_dotenv()

# Configurações da aplicação
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', '/app/uploads')
SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'sua_chave_secreta')

# Cria e configura a aplicação Flask (apenas API)
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB max upload

# Configurar CORS para permitir acesso de frontends externos
CORS(app, origins=[
    'http://localhost:3000',      # Desenvolvimento React/Vue
    'http://localhost:3001',      # Desenvolvimento alternativo
    'http://localhost:8080',      # Desenvolvimento Vue CLI
    'https://videoai.com',        # Produção principal
    'https://app.videoai.com',    # Produção app
    'https://www.videoai.com'     # Produção www
])

# Registrar Blueprints da API
app.register_blueprint(api_bp)
app.register_blueprint(admin_bp)

# Cria a pasta de uploads se não existir
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    """Endpoint raiz da API."""
    return {
        'message': 'VideoAI API',
        'version': API_VERSION,
        'status': 'running',
        'api_prefix': '/api/v1',
        'admin_prefix': '/api/v1/admin',
        'docs': '/api/v1/docs',
        'available_endpoints': [
            '/api/v1/health',
            '/api/v1/video/process',
            '/api/v1/video/process-with-overlay',
            '/api/v1/admin/settings',
            '/api/v1/admin/api-keys'
        ]
    }

@app.route('/health')
def health_check():
    """Health check da API."""
    try:
        db_status = check_db_connection()
        return {
            'status': 'healthy' if db_status else 'unhealthy',
            'database': 'connected' if db_status else 'disconnected',
            'version': API_VERSION,
            'service': 'videoai-api'
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'version': API_VERSION,
            'service': 'videoai-api'
        }, 500

@app.errorhandler(404)
def not_found(error):
    """Handler para rotas não encontradas."""
    return {
        'error': 'Endpoint not found',
        'message': 'Use /api/v1/ prefix for API endpoints',
        'available_endpoints': [
            '/api/v1/videos',
            '/api/v1/subtitles',
            '/api/v1/video/process',
            '/api/v1/video/process-with-overlay',
            '/api/v1/admin/settings',
            '/api/v1/admin/api-keys'
        ]
    }, 404

@app.errorhandler(500)
def internal_error(error):
    """Handler para erros internos."""
    return {
        'error': 'Internal server error',
        'message': 'An unexpected error occurred',
        'service': 'videoai-api'
    }, 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"🚀 VideoAI API v{API_VERSION} starting...")
    print(f"📡 Listening on port {port}")
    print(f"🔧 Debug mode: {debug}")
    print(f"🔑 Admin endpoints: /api/v1/admin/*")
    
    app.run(host='0.0.0.0', port=port, debug=debug) 