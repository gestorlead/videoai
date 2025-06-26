#!/usr/bin/env python3
"""
Teste de Integração Completa do Sistema de Compliance
"""

import asyncio
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app

def test_compliance_integration():
    """Testa integração completa do sistema de compliance"""
    print("🧪 Testando Integração Completa do Sistema de Compliance...")
    
    # Criar cliente de teste
    client = TestClient(app)
    
    # Teste 1: Health Check
    print("\n📊 Teste 1: Health Check")
    try:
        response = client.get("/health")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Service: {data.get('service')}")
            print(f"✅ Version: {data.get('version')}")
            print(f"✅ Redis: {data.get('redis')}")
            
            # Verificar compliance
            compliance = data.get('compliance', {})
            print(f"✅ Privacy Manager: {compliance.get('privacy_manager')}")
            print(f"✅ Content Moderation: {compliance.get('content_moderation')}")
            print(f"✅ Audit Logger: {compliance.get('audit_logger')}")
            print(f"✅ GDPR Compliant: {compliance.get('gdpr_compliant')}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False
    
    # Teste 2: Compliance Health Check
    print("\n🔒 Teste 2: Compliance Health Check")
    try:
        response = client.get("/api/v1/compliance/health")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Compliance Status: {data.get('status')}")
            print(f"✅ Services: {data.get('services')}")
        else:
            print(f"❌ Compliance health check failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Compliance health check error: {e}")
    
    # Teste 3: Moderação de Conteúdo
    print("\n🛡️ Teste 3: Moderação de Conteúdo")
    try:
        test_data = {
            "content": "I hate this stupid system and want to kill it",
            "content_type": "text_prompt",
            "user_id": "test_user_123"
        }
        
        response = client.post("/api/v1/compliance/content/moderate", json=test_data)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            result = data.get('moderation_result', {})
            print(f"✅ Resultado: {result.get('result')}")
            print(f"✅ Nível de Ameaça: {result.get('threat_level')}")
            print(f"✅ Aprovado: {result.get('approved')}")
        else:
            print(f"❌ Content moderation failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Content moderation error: {e}")
    
    # Teste 4: Política de Privacidade
    print("\n📋 Teste 4: Política de Privacidade")
    try:
        response = client.get("/api/v1/compliance/privacy/policy")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Policy Version: {data.get('policy_version')}")
            print(f"✅ Data Controller: {data.get('data_controller', {}).get('name')}")
            print(f"✅ User Rights: {len(data.get('user_rights', []))} rights")
        else:
            print(f"❌ Privacy policy failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Privacy policy error: {e}")
    
    # Teste 5: Estatísticas de Moderação
    print("\n📈 Teste 5: Estatísticas de Moderação")
    try:
        response = client.get("/api/v1/compliance/moderation/stats?hours=24")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            stats = data.get('stats', {})
            print(f"✅ Total Content: {stats.get('total_moderated', 0)}")
            print(f"✅ Approved: {stats.get('approved', 0)}")
            print(f"✅ Rejected: {stats.get('rejected', 0)}")
        else:
            print(f"❌ Moderation stats failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Moderation stats error: {e}")
    
    print("\n🎉 Teste de Integração Completo!")
    return True

if __name__ == "__main__":
    success = test_compliance_integration()
    exit(0 if success else 1)
