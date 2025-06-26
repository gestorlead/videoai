#!/usr/bin/env python3
"""
Migração para adicionar tabela de API keys
"""

import os
import sys
from src.utils.database import execute_query, check_db_connection

def check_if_api_keys_table_exists():
    """Verifica se a tabela api_keys já existe"""
    query = """
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'api_keys'
    );
    """
    result = execute_query(query, fetchone=True)
    return result[0] if result else False

def create_api_keys_table():
    """Cria a tabela api_keys"""
    print("Criando tabela api_keys...")
    
    api_keys_table = """
    CREATE TABLE IF NOT EXISTS api_keys (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        name VARCHAR(100) NOT NULL,
        key VARCHAR(100) UNIQUE NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        last_used_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, name)
    );
    """
    execute_query(api_keys_table)
    
    # Criar índices para performance
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_api_keys_key ON api_keys(key);",
        "CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active);"
    ]
    
    for index in indexes:
        execute_query(index)
    
    print("Tabela api_keys criada com sucesso!")

def migrate_api_keys():
    """Executa a migração das API keys"""
    if not check_db_connection():
        print("Erro: Não foi possível conectar ao banco de dados")
        return False
    
    if check_if_api_keys_table_exists():
        print("Tabela api_keys já existe. Pulando migração...")
        return True
    
    try:
        create_api_keys_table()
        print("Migração de API keys concluída com sucesso!")
        return True
    except Exception as e:
        print(f"Erro durante a migração: {e}")
        return False

if __name__ == "__main__":
    success = migrate_api_keys()
    sys.exit(0 if success else 1) 