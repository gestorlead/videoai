#!/usr/bin/env python3
"""
Script para criar a primeira API key de administrador
Use quando não tiver interface web disponível
"""

import sys
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Adiciona o diretório raiz ao path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from src.models.user import User
from src.models.api_key import ApiKey
from src.utils.database import check_db_connection

def create_admin_api_key():
    """Cria uma API key para o primeiro usuário admin"""
    
    print("🔑 Criando API key de administrador...")
    
    # Verificar conexão com banco
    if not check_db_connection():
        print("❌ Erro: Não foi possível conectar ao banco de dados")
        print("   Verifique se o PostgreSQL está rodando e as variáveis de ambiente estão corretas")
        return False
    
    try:
        # Buscar primeiro usuário admin
        admin_user = None
        users = User.get_all(active_only=False)
        
        for user in users:
            if user.is_admin:
                admin_user = user
                break
        
        if not admin_user:
            print("❌ Erro: Nenhum usuário administrador encontrado")
            print("   Crie um usuário admin primeiro:")
            print("   python create_admin_user.py")
            return False
        
        print(f"👤 Usuário admin encontrado: {admin_user.username}")
        
        # Verificar se já tem API keys
        existing_keys = ApiKey.get_by_user(admin_user.id)
        if existing_keys:
            print(f"⚠️  Usuário já possui {len(existing_keys)} API key(s):")
            for key in existing_keys:
                status = "ativa" if key.is_active else "inativa"
                print(f"   - {key.name}: {key.get_masked_key()} ({status})")
            
            response = input("\n🤔 Deseja criar uma nova API key mesmo assim? (s/N): ")
            if response.lower() not in ['s', 'sim', 'y', 'yes']:
                print("✅ Operação cancelada pelo usuário")
                return True
        
        # Criar nova API key
        api_key_name = "Admin API Key"
        if existing_keys:
            api_key_name = f"Admin API Key {len(existing_keys) + 1}"
        
        api_key = ApiKey.create(admin_user.id, api_key_name)
        
        if not api_key:
            print("❌ Erro ao criar API key")
            return False
        
        print("\n✅ API key criada com sucesso!")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"🔑 Nome: {api_key.name}")
        print(f"🔑 Chave: {api_key.key}")
        print(f"👤 Usuário: {admin_user.username}")
        print(f"📅 Criada em: {api_key.created_at}")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("\n⚠️  IMPORTANTE:")
        print("   • Guarde esta chave em local seguro")
        print("   • Ela não será mostrada novamente")
        print("   • Use no header: X-API-Key: " + api_key.key)
        print("\n🚀 Exemplo de uso:")
        print(f"   curl -H 'X-API-Key: {api_key.key}' \\")
        print("        http://localhost:5000/api/v1/admin/settings")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao criar API key: {e}")
        return False

def create_admin_user():
    """Cria um usuário administrador se não existir"""
    print("👤 Criando usuário administrador...")
    
    try:
        # Verificar se já existe admin
        users = User.get_all(active_only=False)
        for user in users:
            if user.is_admin:
                print(f"✅ Usuário admin já existe: {user.username}")
                return True
        
        # Criar novo admin
        username = input("📝 Username do admin: ") or "admin"
        email = input("📧 Email do admin: ") or "admin@videoai.com"
        password = input("🔒 Senha do admin: ") or "admin123"
        
        user = User.create(
            username=username,
            password=password,
            email=email,
            full_name="Administrador",
            is_active=True,
            is_admin=True
        )
        
        if user:
            print(f"✅ Usuário admin criado: {username}")
            return True
        else:
            print("❌ Erro ao criar usuário admin")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao criar usuário: {e}")
        return False

def main():
    """Função principal"""
    print("🚀 VideoAI - Configuração Inicial da API")
    print("═══════════════════════════════════════\n")
    
    # Verificar se precisa criar usuário admin
    users = User.get_all(active_only=False) if check_db_connection() else []
    admin_exists = any(user.is_admin for user in users)
    
    if not admin_exists:
        print("ℹ️  Nenhum usuário administrador encontrado")
        if not create_admin_user():
            sys.exit(1)
        print()
    
    # Criar API key
    if create_admin_api_key():
        print("\n🎉 Configuração concluída com sucesso!")
        print("   Agora você pode usar a API apenas com a chave criada")
    else:
        print("\n💥 Falha na configuração")
        sys.exit(1)

if __name__ == "__main__":
    main() 