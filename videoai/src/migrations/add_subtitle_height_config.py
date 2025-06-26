#!/usr/bin/env python3
"""
Script para adicionar configuração de altura das legendas
"""

import os
import sys
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Adiciona o diretório raiz ao path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.utils.database import execute_query, check_db_connection
from src.models.settings import Settings

def add_subtitle_height_config():
    """Adiciona a configuração de altura das legendas"""
    if not check_db_connection():
        print("Erro: Não foi possível conectar ao banco de dados")
        return False
    
    try:
        print("🔄 Adicionando configuração de altura das legendas...")
        
        # Verificar se a configuração já existe
        existing = Settings.get_by_key('subtitle_height_offset')
        if existing:
            print("⏭️ Configuração 'subtitle_height_offset' já existe")
            return True
        
        # Adicionar nova configuração
        Settings.set('subtitle_height_offset', '80', 'subtitles', 
                    'Distância da borda em pixels para posição da legenda')
        
        print("✅ Configuração 'subtitle_height_offset' adicionada com sucesso!")
        
        # Atualizar também a configuração do logo para usar o valor padrão maior
        logo_size_setting = Settings.get_by_key('logo_size')
        if logo_size_setting and logo_size_setting.value == '10':
            Settings.set('logo_size', '25', 'video', 
                        'Tamanho do logo em porcentagem da largura do vídeo (1-100)')
            print("✅ Configuração 'logo_size' atualizada para 25%")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao adicionar configuração: {e}")
        return False

if __name__ == "__main__":
    success = add_subtitle_height_config()
    sys.exit(0 if success else 1) 