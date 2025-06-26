import secrets
import string
import datetime
from src.utils.database import execute_query

class ApiKey:
    def __init__(self, id=None, user_id=None, name=None, key=None, 
                 is_active=True, last_used_at=None, created_at=None):
        self.id = id
        self.user_id = user_id
        self.name = name
        self.key = key
        self.is_active = is_active
        self.last_used_at = last_used_at
        self.created_at = created_at
    
    @staticmethod
    def generate_key():
        """Gera uma chave API segura"""
        # Gerar chave no formato: ak_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        alphabet = string.ascii_letters + string.digits
        random_part = ''.join(secrets.choice(alphabet) for _ in range(32))
        return f"ak_{random_part}"
    
    @staticmethod
    def create(user_id, name):
        """Cria uma nova API key para um usuário"""
        key = ApiKey.generate_key()
        
        # Verificar se já existe uma key com o mesmo nome para o usuário
        existing = ApiKey.get_by_user_and_name(user_id, name)
        if existing:
            return None
        
        query = """
        INSERT INTO api_keys (user_id, name, key, is_active)
        VALUES (%s, %s, %s, %s)
        RETURNING id;
        """
        
        result = execute_query(
            query,
            params=(user_id, name, key, True),
            fetchone=True
        )
        
        if result:
            return ApiKey.get_by_id(result['id'])
        return None
    
    @staticmethod
    def get_by_id(api_key_id):
        """Busca uma API key pelo ID"""
        query = "SELECT * FROM api_keys WHERE id = %s;"
        result = execute_query(query, params=(api_key_id,), fetchone=True)
        
        if result:
            return ApiKey(
                id=result['id'],
                user_id=result['user_id'],
                name=result['name'],
                key=result['key'],
                is_active=result['is_active'],
                last_used_at=result['last_used_at'],
                created_at=result['created_at']
            )
        return None
    
    @staticmethod
    def get_by_key(key):
        """Busca uma API key pela chave"""
        query = "SELECT * FROM api_keys WHERE key = %s AND is_active = true;"
        result = execute_query(query, params=(key,), fetchone=True)
        
        if result:
            api_key = ApiKey(
                id=result['id'],
                user_id=result['user_id'],
                name=result['name'],
                key=result['key'],
                is_active=result['is_active'],
                last_used_at=result['last_used_at'],
                created_at=result['created_at']
            )
            # Atualizar último uso
            api_key.update_last_used()
            return api_key
        return None
    
    @staticmethod
    def get_by_user(user_id):
        """Busca todas as API keys de um usuário"""
        query = "SELECT * FROM api_keys WHERE user_id = %s ORDER BY created_at DESC;"
        results = execute_query(query, params=(user_id,), fetchall=True)
        
        api_keys = []
        for result in results:
            api_keys.append(ApiKey(
                id=result['id'],
                user_id=result['user_id'],
                name=result['name'],
                key=result['key'],
                is_active=result['is_active'],
                last_used_at=result['last_used_at'],
                created_at=result['created_at']
            ))
        
        return api_keys
    
    @staticmethod
    def get_by_user_and_name(user_id, name):
        """Busca uma API key específica de um usuário pelo nome"""
        query = "SELECT * FROM api_keys WHERE user_id = %s AND name = %s;"
        result = execute_query(query, params=(user_id, name), fetchone=True)
        
        if result:
            return ApiKey(
                id=result['id'],
                user_id=result['user_id'],
                name=result['name'],
                key=result['key'],
                is_active=result['is_active'],
                last_used_at=result['last_used_at'],
                created_at=result['created_at']
            )
        return None
    
    def update_last_used(self):
        """Atualiza o timestamp de último uso"""
        query = "UPDATE api_keys SET last_used_at = %s WHERE id = %s;"
        now = datetime.datetime.now()
        execute_query(query, params=(now, self.id))
        self.last_used_at = now
    
    def toggle_status(self):
        """Ativa/desativa a API key"""
        new_status = not self.is_active
        query = "UPDATE api_keys SET is_active = %s WHERE id = %s;"
        execute_query(query, params=(new_status, self.id))
        self.is_active = new_status
        return new_status
    
    def delete(self):
        """Remove a API key"""
        query = "DELETE FROM api_keys WHERE id = %s;"
        execute_query(query, params=(self.id,))
        return True
    
    def update_name(self, new_name):
        """Atualiza o nome da API key"""
        # Verificar se já existe outra key com o mesmo nome para o usuário
        existing = ApiKey.get_by_user_and_name(self.user_id, new_name)
        if existing and existing.id != self.id:
            return False
        
        query = "UPDATE api_keys SET name = %s WHERE id = %s;"
        execute_query(query, params=(new_name, self.id))
        self.name = new_name
        return True
    
    def get_masked_key(self):
        """Retorna a chave mascarada para exibição"""
        if not self.key:
            return ""
        
        # Mostrar apenas os primeiros 8 caracteres e mascarar o resto
        if len(self.key) > 12:
            return f"{self.key[:8]}{'*' * (len(self.key) - 12)}{self.key[-4:]}"
        else:
            return f"{self.key[:4]}{'*' * (len(self.key) - 4)}"
    
    @staticmethod
    def get_active_count(user_id):
        """Retorna o número de API keys ativas de um usuário"""
        query = "SELECT COUNT(*) as count FROM api_keys WHERE user_id = %s AND is_active = true;"
        result = execute_query(query, params=(user_id,), fetchone=True)
        
        return result['count'] if result else 0 