#!/usr/bin/env python3
"""
Script para executar todas as migrações necessárias na ordem correta
"""
import sys
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Adiciona o diretório raiz ao path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.utils.database import execute_query, check_db_connection
import time

def wait_for_db():
    """Aguarda até que o banco de dados esteja disponível."""
    MAX_RETRIES = 30
    RETRY_INTERVAL = 2  # segundos
    
    print("⏳ Aguardando conexão com o banco de dados...")
    for retry in range(MAX_RETRIES):
        if check_db_connection():
            print("✅ Conexão com o banco de dados estabelecida!")
            return True
        print(f"Tentativa {retry+1}/{MAX_RETRIES}. Tentando novamente em {RETRY_INTERVAL} segundos...")
        time.sleep(RETRY_INTERVAL)
    
    print("❌ Não foi possível conectar ao banco de dados. Verifique as configurações.")
    return False

def check_table_exists(table_name):
    """Verifica se uma tabela existe"""
    query = """
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = %s
    );
    """
    result = execute_query(query, (table_name,), fetchone=True)
    return result['exists'] if result else False

def run_migration(migration_name, migration_function):
    """Executa uma migração com tratamento de erro"""
    try:
        print(f"🔄 Executando migração: {migration_name}...")
        migration_function()
        print(f"✅ Migração '{migration_name}' concluída com sucesso!")
        return True
    except Exception as e:
        print(f"❌ Erro na migração '{migration_name}': {e}")
        return False

def run_setup_db():
    """Executa a migração básica (setup_db.py)"""
    from src.migrations.setup_db import setup_database
    setup_database()

def run_is_admin_migration():
    """Executa a migração da coluna is_admin"""
    from src.migrations.add_is_admin_column import migrate_is_admin_column
    migrate_is_admin_column()

def run_settings_migration():
    """Executa a migração da tabela settings"""
    from src.migrations.add_settings_table import migrate_settings
    migrate_settings()

def run_api_keys_migration():
    """Executa a migração da tabela api_keys"""
    from src.migrations.add_api_keys_table import migrate_api_keys
    migrate_api_keys()

def run_subtitle_height_migration():
    """Executa a migração da configuração de altura das legendas"""
    from src.migrations.add_subtitle_height_config import add_subtitle_height_config
    add_subtitle_height_config()

def initialize_settings():
    """Inicializa as configurações padrão"""
    try:
        from src.models.settings import Settings
        Settings.initialize_defaults()
        print("✅ Configurações padrão inicializadas!")
    except Exception as e:
        print(f"❌ Erro ao inicializar configurações: {e}")

def run_all_migrations():
    """Executa todas as migrações na ordem correta"""
    print("🚀 Iniciando execução de todas as migrações...")
    
    if not wait_for_db():
        sys.exit(1)
    
    migrations = [
        ("Configuração básica do banco", run_setup_db),
        ("Coluna is_admin", run_is_admin_migration),
        ("Tabela settings", run_settings_migration),
        ("Tabela api_keys", run_api_keys_migration),
        ("Configuração altura legendas", run_subtitle_height_migration),
    ]
    
    # Executar migrações
    success_count = 0
    for name, func in migrations:
        if run_migration(name, func):
            success_count += 1
    
    # Inicializar configurações
    print("⚙️ Inicializando configurações padrão...")
    initialize_settings()
    
    print(f"\n📊 Resumo: {success_count}/{len(migrations)} migrações executadas com sucesso")
    
    # Verificar tabelas criadas
    print("\n🔍 Verificando tabelas criadas:")
    tables = ["users", "videos", "subtitles", "sessions", "api_keys", "settings"]
    for table in tables:
        exists = check_table_exists(table)
        status = "✅" if exists else "❌"
        print(f"  {status} Tabela '{table}': {'existe' if exists else 'NÃO existe'}")
    
    # Verificar configurações
    try:
        count_query = "SELECT COUNT(*) as count FROM settings;"
        result = execute_query(count_query, fetchone=True)
        count = result['count'] if result else 0
        print(f"  ✅ Configurações na tabela settings: {count}")
    except Exception as e:
        print(f"  ❌ Erro ao verificar configurações: {e}")
    
    print("\n✅ Execução de migrações concluída!")

if __name__ == "__main__":
    run_all_migrations() 