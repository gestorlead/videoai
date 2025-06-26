#!/usr/bin/env python3
"""
Teste do Sistema de Compliance
"""

import asyncio
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import redis
    from app.core.privacy import init_privacy_manager, get_privacy_manager
    from app.services.compliance.content_moderation import init_content_moderation_service, get_content_moderation_service, ContentCategory
    from app.services.compliance.audit_logger import init_audit_logger, get_audit_logger, AuditEventType, ComplianceLevel
except ImportError as e:
    print(f"❌ Erro de importação: {e}")
    print("💡 Certifique-se de que está no diretório videoai/")
    sys.exit(1)

async def test_compliance_system():
    """Testa sistema de compliance"""
    print("🔒 Testando Sistema de Compliance...")
    
    # Conectar ao Redis
    try:
        redis_client = redis.Redis(host='localhost', port=6379, db=0)
        redis_client.ping()
        print("✅ Conexão Redis estabelecida")
    except Exception as e:
        print(f"❌ Erro ao conectar Redis: {e}")
        print("💡 Certifique-se de que o Redis está rodando (docker-compose up -d)")
        return False
    
    # Inicializar serviços
    try:
        init_privacy_manager(redis_client)
        init_content_moderation_service(redis_client)
        init_audit_logger(redis_client)
        print("✅ Serviços de compliance inicializados")
    except Exception as e:
        print(f"❌ Erro ao inicializar serviços: {e}")
        return False
    
    # Teste 1: Privacy Manager
    print("\n📝 Teste 1: Privacy Manager")
    try:
        privacy_manager = get_privacy_manager()
        
        # Teste com dados pessoais
        test_prompt = "Meu nome é João Silva e meu email é joao@email.com"
        result = privacy_manager.process_prompt(test_prompt, "user_123")
        
        print(f"Prompt original: {test_prompt}")
        print(f"Prompt processado: {result['processed_prompt']}")
        print(f"Dados pessoais detectados: {result['personal_data_detected']}")
        print(f"Tipos encontrados: {result['personal_data_types']}")
        print("✅ Privacy Manager funcionando")
        
    except Exception as e:
        print(f"❌ Erro no Privacy Manager: {e}")
        return False
    
    # Teste 2: Content Moderation
    print("\n🛡️ Teste 2: Content Moderation")
    try:
        moderation_service = get_content_moderation_service()
        
        # Teste com conteúdo problemático
        test_content = "I hate this stupid system and want to kill it"
        result = await moderation_service.moderate_content(
            content=test_content,
            content_type=ContentCategory.TEXT_PROMPT,
            user_id="user_123"
        )
        
        print(f"Conteúdo testado: {test_content}")
        print(f"Resultado: {result['result']}")
        print(f"Nível de ameaça: {result['threat_level']}")
        print(f"Aprovado: {result['approved']}")
        print("✅ Content Moderation funcionando")
        
    except Exception as e:
        print(f"❌ Erro no Content Moderation: {e}")
        return False
    
    # Teste 3: Audit Logger
    print("\n📊 Teste 3: Audit Logger")
    try:
        audit_logger = get_audit_logger()
        
        # Log de evento de teste
        event_id = audit_logger.log_event(
            event_type=AuditEventType.CONTENT_GENERATION,
            user_id="user_123",
            compliance_level=ComplianceLevel.COMPLIANT,
            details={"test": "compliance_system"},
            metadata={"source": "test_script"}
        )
        
        print(f"Evento de auditoria criado: {event_id}")
        
        # Recuperar trilha do usuário
        trail = audit_logger.get_user_audit_trail("user_123", limit=5)
        print(f"Eventos encontrados na trilha: {len(trail)}")
        print("✅ Audit Logger funcionando")
        
    except Exception as e:
        print(f"❌ Erro no Audit Logger: {e}")
        return False
    
    print("\n🎉 Todos os testes passaram! Sistema de compliance funcionando.")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_compliance_system())
    exit(0 if success else 1)
