#!/usr/bin/env python3
"""
Rotas administrativas da API AutoSub
Endpoints para gerenciar configurações, usuários e API keys
"""

from flask import Blueprint, request, jsonify
from src.models.api_key import ApiKey
from src.models.settings import Settings
from src.models.user import User
from functools import wraps
import jwt
import datetime
import os

admin_bp = Blueprint('admin', __name__, url_prefix='/api/v1/admin')

def admin_required(f):
    """Decorator para verificar se o usuário é admin"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Verificar se a API key pertence a um usuário admin
        if not hasattr(request, 'api_key'):
            return jsonify({'error': 'Acesso negado'}), 403
        
        # Buscar usuário da API key
        user = User.get_by_id(request.api_key.user_id)
        if not user or not user.is_admin:
            return jsonify({'error': 'Acesso restrito a administradores'}), 403
        
        request.admin_user = user
        return f(*args, **kwargs)
    return decorated

# ===============================
# GERENCIAMENTO DE CONFIGURAÇÕES
# ===============================

@admin_bp.route('/settings', methods=['GET'])
@admin_required
def get_settings():
    """Lista todas as configurações do sistema"""
    try:
        settings = Settings.get_all()
        
        # Organizar por categoria
        organized_settings = {}
        for category, settings_list in settings.items():
            organized_settings[category] = {}
            for setting in settings_list:
                # Mascarar valores sensíveis
                value = setting.value
                if 'api_key' in setting.key.lower() or 'password' in setting.key.lower():
                    if value and len(value) > 8:
                        value = f"{value[:8]}{'*' * (len(value) - 8)}"
                    elif value:
                        value = "*****"
                
                organized_settings[category][setting.key] = {
                    'value': value,
                    'description': setting.description,
                    'category': setting.category
                }
        
        return jsonify({
            'settings': organized_settings,
            'categories': list(organized_settings.keys())
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao buscar configurações: {str(e)}'}), 500

@admin_bp.route('/settings', methods=['POST'])
@admin_required
def update_settings():
    """Atualiza múltiplas configurações do sistema"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        updated_settings = []
        
        for key, value in data.items():
            # Validações específicas
            if key == 'transcription_service' and value not in ['autosub', 'openai_whisper']:
                return jsonify({'error': f'Valor inválido para {key}. Use: autosub ou openai_whisper'}), 400
            
            # Determinar categoria baseada na chave
            category = 'general'
            description = f'Configuração {key}'
            
            if 'api_key' in key:
                category = 'api_service'
                if 'google' in key:
                    description = 'Chave da API do Google Translate'
                elif 'openai' in key:
                    description = 'Chave da API da OpenAI'
            elif 'prompt' in key:
                category = 'prompts'
                if 'instagram' in key:
                    description = 'Prompt para gerar legendas do Instagram'
                elif 'tiktok' in key:
                    description = 'Prompt para gerar legendas do TikTok'
            elif 'model' in key:
                category = 'models'
                if 'transcription' in key:
                    description = 'Modelo OpenAI para transcrição'
                elif 'text' in key:
                    description = 'Modelo OpenAI para geração de texto'
            elif key in ['logo_size', 'subtitle_height_offset']:
                category = 'video'
                description = f'Configuração de vídeo: {key.replace("_", " ").title()}'
            
            # Atualizar configuração
            Settings.set(key, str(value), category, description)
            updated_settings.append(key)
        
        return jsonify({
            'message': f'{len(updated_settings)} configurações atualizadas',
            'updated_keys': updated_settings
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao atualizar configurações: {str(e)}'}), 500

@admin_bp.route('/settings/<setting_key>', methods=['GET'])
@admin_required
def get_setting(setting_key):
    """Busca uma configuração específica"""
    try:
        setting = Settings.get_by_key(setting_key)
        if not setting:
            return jsonify({'error': 'Configuração não encontrada'}), 404
        
        # Mascarar valor se sensível
        value = setting.value
        if 'api_key' in setting_key.lower() or 'password' in setting_key.lower():
            if value and len(value) > 8:
                value = f"{value[:8]}{'*' * (len(value) - 8)}"
            elif value:
                value = "*****"
        
        return jsonify({
            'key': setting.key,
            'value': value,
            'category': setting.category,
            'description': setting.description
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao buscar configuração: {str(e)}'}), 500

@admin_bp.route('/settings/<setting_key>', methods=['PUT'])
@admin_required
def update_setting(setting_key):
    """Atualiza uma configuração específica"""
    try:
        data = request.get_json()
        if not data or 'value' not in data:
            return jsonify({'error': 'Valor é obrigatório'}), 400
        
        value = data['value']
        category = data.get('category', 'general')
        description = data.get('description', f'Configuração {setting_key}')
        
        # Validações específicas
        if setting_key == 'transcription_service' and value not in ['autosub', 'openai_whisper']:
            return jsonify({'error': 'Valor inválido para transcription_service. Use: autosub ou openai_whisper'}), 400
        
        Settings.set(setting_key, str(value), category, description)
        
        return jsonify({
            'key': setting_key,
            'value': value,
            'message': 'Configuração atualizada com sucesso'
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao atualizar configuração: {str(e)}'}), 500

# ===============================
# GERENCIAMENTO DE API KEYS
# ===============================

@admin_bp.route('/api-keys', methods=['GET'])
@admin_required
def list_api_keys():
    """Lista todas as API keys do usuário"""
    try:
        user_id = request.admin_user.id
        api_keys = ApiKey.get_by_user(user_id)
        
        keys_data = []
        for key in api_keys:
            keys_data.append({
                'id': key.id,
                'name': key.name,
                'masked_key': key.get_masked_key(),
                'is_active': key.is_active,
                'last_used_at': key.last_used_at.isoformat() if key.last_used_at else None,
                'created_at': key.created_at.isoformat() if key.created_at else None
            })
        
        return jsonify({
            'api_keys': keys_data,
            'total': len(keys_data)
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao listar API keys: {str(e)}'}), 500

@admin_bp.route('/api-keys', methods=['POST'])
@admin_required
def create_api_key():
    """Cria uma nova API key"""
    try:
        data = request.get_json()
        
        if not data or 'name' not in data:
            return jsonify({'error': 'Nome da API key é obrigatório'}), 400
        
        name = data['name'].strip()
        if not name:
            return jsonify({'error': 'Nome não pode estar vazio'}), 400
        
        user_id = request.admin_user.id
        api_key = ApiKey.create(user_id, name)
        
        if not api_key:
            return jsonify({'error': 'Erro ao criar API key. Nome já existe?'}), 400
        
        return jsonify({
            'id': api_key.id,
            'name': api_key.name,
            'key': api_key.key,  # Chave completa apenas na criação
            'is_active': api_key.is_active,
            'created_at': api_key.created_at.isoformat(),
            'message': 'API key criada com sucesso'
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Erro ao criar API key: {str(e)}'}), 500

@admin_bp.route('/api-keys/<int:key_id>', methods=['PATCH'])
@admin_required
def update_api_key(key_id):
    """Atualiza uma API key (ativar/desativar ou alterar nome)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        api_key = ApiKey.get_by_id(key_id)
        if not api_key or api_key.user_id != request.admin_user.id:
            return jsonify({'error': 'API key não encontrada'}), 404
        
        # Atualizar status se fornecido
        if 'is_active' in data:
            new_status = bool(data['is_active'])
            if new_status != api_key.is_active:
                api_key.toggle_status()
        
        # Atualizar nome se fornecido
        if 'name' in data:
            new_name = data['name'].strip()
            if not new_name:
                return jsonify({'error': 'Nome não pode estar vazio'}), 400
            
            if not api_key.update_name(new_name):
                return jsonify({'error': 'Nome já existe'}), 400
        
        return jsonify({
            'id': api_key.id,
            'name': api_key.name,
            'masked_key': api_key.get_masked_key(),
            'is_active': api_key.is_active,
            'message': 'API key atualizada com sucesso'
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao atualizar API key: {str(e)}'}), 500

@admin_bp.route('/api-keys/<int:key_id>', methods=['DELETE'])
@admin_required
def delete_api_key(key_id):
    """Exclui uma API key"""
    try:
        api_key = ApiKey.get_by_id(key_id)
        if not api_key or api_key.user_id != request.admin_user.id:
            return jsonify({'error': 'API key não encontrada'}), 404
        
        key_name = api_key.name
        api_key.delete()
        
        return jsonify({
            'message': f'API key "{key_name}" excluída com sucesso'
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao excluir API key: {str(e)}'}), 500

# ===============================
# GERENCIAMENTO DE USUÁRIOS
# ===============================

@admin_bp.route('/users', methods=['GET'])
@admin_required
def list_users():
    """Lista todos os usuários"""
    try:
        users = User.get_all(active_only=False)
        
        users_data = []
        for user in users:
            users_data.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name,
                'is_active': user.is_active,
                'is_admin': user.is_admin,
                'created_at': user.created_at.isoformat() if user.created_at else None
            })
        
        return jsonify({
            'users': users_data,
            'total': len(users_data)
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao listar usuários: {str(e)}'}), 500

@admin_bp.route('/users', methods=['POST'])
@admin_required
def create_user():
    """Cria um novo usuário"""
    try:
        data = request.get_json()
        required_fields = ['username', 'password', 'email']
        
        for field in required_fields:
            if not data or field not in data:
                return jsonify({'error': f'{field} é obrigatório'}), 400
        
        username = data['username'].strip()
        password = data['password']
        email = data['email'].strip()
        full_name = data.get('full_name', '').strip()
        is_active = data.get('is_active', True)
        is_admin = data.get('is_admin', False)
        
        user = User.create(username, password, email, full_name, is_active, is_admin)
        
        if not user:
            return jsonify({'error': 'Erro ao criar usuário. Username ou email já existem?'}), 400
        
        return jsonify({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'is_active': user.is_active,
            'is_admin': user.is_admin,
            'message': 'Usuário criado com sucesso'
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Erro ao criar usuário: {str(e)}'}), 500

@admin_bp.route('/users/<int:user_id>', methods=['PATCH'])
@admin_required
def update_user(user_id):
    """Atualiza um usuário"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        user = User.get_by_id(user_id)
        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        # Atualizar campos
        username = data.get('username', user.username)
        email = data.get('email', user.email)
        full_name = data.get('full_name', user.full_name)
        is_active = data.get('is_active', user.is_active)
        is_admin = data.get('is_admin', user.is_admin)
        
        user.update(username, email, full_name, is_active, is_admin)
        
        # Atualizar senha se fornecida
        if 'password' in data and data['password']:
            user.change_password(data['password'])
        
        return jsonify({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'is_active': user.is_active,
            'is_admin': user.is_admin,
            'message': 'Usuário atualizado com sucesso'
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao atualizar usuário: {str(e)}'}), 500

# ===============================
# SISTEMA DE AUTENTICAÇÃO JWT
# ===============================

@admin_bp.route('/auth/login', methods=['POST'])
def login():
    """Login com username/password, retorna JWT token"""
    try:
        data = request.get_json()
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({'error': 'Username e password são obrigatórios'}), 400
        
        username = data['username']
        password = data['password']
        
        user = User.authenticate(username, password)
        if not user:
            return jsonify({'error': 'Credenciais inválidas'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'Usuário desativado'}), 401
        
        # Gerar JWT token
        payload = {
            'user_id': user.id,
            'username': user.username,
            'is_admin': user.is_admin,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)  # 7 dias
        }
        
        secret_key = os.environ.get('FLASK_SECRET_KEY', 'sua_chave_secreta')
        token = jwt.encode(payload, secret_key, algorithm='HS256')
        
        return jsonify({
            'token': token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name,
                'is_admin': user.is_admin
            },
            'expires_in': 7 * 24 * 60 * 60  # 7 dias em segundos
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro no login: {str(e)}'}), 500

@admin_bp.route('/auth/validate', methods=['GET'])
def validate_token():
    """Valida um JWT token"""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Token não fornecido'}), 401
        
        token = auth_header.split(' ')[1]
        secret_key = os.environ.get('FLASK_SECRET_KEY', 'sua_chave_secreta')
        
        try:
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            user = User.get_by_id(payload['user_id'])
            
            if not user or not user.is_active:
                return jsonify({'error': 'Usuário inválido'}), 401
            
            return jsonify({
                'valid': True,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'full_name': user.full_name,
                    'is_admin': user.is_admin
                }
            })
            
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expirado'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token inválido'}), 401
        
    except Exception as e:
        return jsonify({'error': f'Erro na validação: {str(e)}'}), 500 