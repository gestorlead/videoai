#!/usr/bin/env python3
"""
Migração para adicionar tabela de configurações
"""
import sys
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Adiciona o diretório raiz ao path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.utils.database import execute_query

def check_if_settings_table_exists():
    """Verifica se a tabela settings já existe"""
    query = """
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'settings'
    );
    """
    result = execute_query(query, fetchone=True)
    return result['exists'] if result else False

def create_settings_table():
    """Cria a tabela settings"""
    print("Criando tabela settings...")
    
    settings_table = """
    CREATE TABLE IF NOT EXISTS settings (
        id SERIAL PRIMARY KEY,
        key VARCHAR(100) UNIQUE NOT NULL,
        value TEXT,
        category VARCHAR(50) NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    execute_query(settings_table)
    
    # Criar índices
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(key);",
        "CREATE INDEX IF NOT EXISTS idx_settings_category ON settings(category);"
    ]
    
    for index in indexes:
        execute_query(index)
    
    print("Tabela settings criada com sucesso!")

def insert_default_settings():
    """Insere configurações padrão"""
    print("Inserindo configurações padrão...")
    
    defaults = [
        # Configurações Gerais
        ('transcription_service', 'autosub', 'general', 'Serviço de transcrição (autosub ou openai_whisper)'),
        
        # Serviços de API
        ('google_translate_api_key', '', 'api_service', 'Chave da API do Google Translate'),
        ('openai_api_key', '', 'api_service', 'Chave da API da OpenAI'),
        
        # Prompts
        ('instagram_prompt', 'Crie uma legenda envolvente para Instagram baseada nesta transcrição. Use hashtags relevantes e mantenha um tom casual e atrativo.', 'prompts', 'Prompt para gerar legendas do Instagram'),
        ('tiktok_prompt', 'Crie uma legenda viral para TikTok baseada nesta transcrição. Use linguagem jovem, emojis e hashtags trending.', 'prompts', 'Prompt para gerar legendas do TikTok'),
        
                    # Modelos OpenAI
            ('openai_model_transcription', 'whisper-1', 'models', 'Modelo OpenAI para transcrição'),
            ('openai_model_text', 'gpt-4o-mini', 'models', 'Modelo OpenAI para geração de texto (opções: gpt-4o-mini, gpt-4o, gpt-4.1, gpt-4.1-mini, o3, gpt-3.5-turbo)'),
    ]
    
    for key, value, category, description in defaults:
        # Verificar se já existe
        check_query = "SELECT COUNT(*) as count FROM settings WHERE key = %s;"
        result = execute_query(check_query, (key,), fetchone=True)
        
        if result['count'] == 0:
            insert_query = """
            INSERT INTO settings (key, value, category, description) 
            VALUES (%s, %s, %s, %s);
            """
            execute_query(insert_query, (key, value, category, description))
            print(f"  ✅ Configuração '{key}' adicionada")
        else:
            print(f"  ⏭️ Configuração '{key}' já existe")

def migrate_settings():
    """Executa a migração da tabela settings"""
    try:
        print("🔄 Iniciando migração da tabela settings...")
        
        if check_if_settings_table_exists():
            print("Tabela settings já existe. Pulando criação...")
        else:
            create_settings_table()
        
        insert_default_settings()
        
        print("✅ Migração da tabela settings concluída com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro na migração da tabela settings: {e}")
        return False

if __name__ == "__main__":
    success = migrate_settings() 