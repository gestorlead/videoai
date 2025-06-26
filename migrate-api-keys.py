#!/usr/bin/env python3
"""
Script para executar a migração das API keys
"""

import sys
import os

# Adicionar o diretório atual ao Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.migrations.add_api_keys_table import migrate_api_keys

if __name__ == "__main__":
    print("Executando migração das API keys...")
    success = migrate_api_keys()
    
    if success:
        print("✅ Migração concluída com sucesso!")
        print("\nAgora você pode:")
        print("1. Acessar seu perfil na interface web")
        print("2. Ir para 'Gerenciar API Keys'")
        print("3. Criar suas chaves de API")
        print("4. Usar as chaves para acessar a API REST")
    else:
        print("❌ Falha na migração!")
        sys.exit(1) 