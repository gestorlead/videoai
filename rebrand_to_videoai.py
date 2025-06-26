#!/usr/bin/env python3
"""
Script para fazer rebranding completo de AutoSub para VideoAI
"""

import os
import re
from pathlib import Path

def replace_in_file(file_path, replacements):
    """Substitui texto em um arquivo"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        for old, new in replacements.items():
            content = content.replace(old, new)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Updated: {file_path}")
            return True
        return False
    except Exception as e:
        print(f"❌ Error updating {file_path}: {e}")
        return False

def main():
    print("🎬 Starting VideoAI rebranding...")
    
    # Definir substituições básicas primeiro
    replacements = {
        # Nomes principais
        "AutoSub": "VideoAI",
        "autosub": "videoai", 
        "AUTOSUB": "VIDEOAI",
        
        # Descrições
        "Geração Automática de Legendas": "AI Video Creation & Social Media Platform",
        "AutoSub API": "VideoAI API",
        
        # Docker containers
        "autosub-api": "videoai-api",
        "autosub-worker": "videoai-worker",
        "autosub-db": "videoai-db", 
        "autosub-redis": "videoai-redis",
        "autosub-rabbitmq": "videoai-rabbitmq",
        "autosub-healthcheck": "videoai-healthcheck",
        "autosub-api-network": "videoai-api-network",
        
        # Banco de dados
        "POSTGRES_DB=autosub": "POSTGRES_DB=videoai",
        
        # Secrets
        "autosub_secret_key_123": "videoai_secret_key_123",
        "autosub_salt": "videoai_salt",
        "autosub-theme-preference": "videoai-theme-preference",
    }
    
    # Processar arquivos principais
    videoai_dir = Path("videoai")
    files_to_process = []
    
    # Arquivos específicos importantes
    important_files = [
        "videoai/app.py",
        "videoai/app_api_only.py", 
        "videoai/docker-compose.yml",
        "videoai/docker-compose.api.yml",
        "videoai/Dockerfile.api",
        "videoai/src/templates/base.html"
    ]
    
    for file_path in important_files:
        if Path(file_path).exists():
            files_to_process.append(Path(file_path))
    
    updated_files = 0
    
    for file_path in files_to_process:
        if replace_in_file(file_path, replacements):
            updated_files += 1
    
    print(f"\n🎉 Rebranding inicial concluído!")
    print(f"📁 {updated_files} arquivos principais atualizados")

if __name__ == "__main__":
    main()
