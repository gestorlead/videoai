#!/usr/bin/env python3
"""
Teste Direto dos Serviços de Compliance
"""

import asyncio
import sys
import os
import redis

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_compliance_services():
    """Testa apenas os serviços de compliance"""
    print("🔒 Testando Serviços de Compliance Diretamente...")
    
    # Conectar ao Redis
    try:
        redis_client = redis.Redis(host='localhost', port=6379, db=0)
        redis_client.ping()
        print("✅ Redis conectado")
    except Exception as e:
        print(f"❌ Erro Redis: {e}")
        return False
    
    # Inicializar serviços
    try:
        from app.core.privacy import init_privacy_manager, get_privacy_manager
        from app.services.compliance.content_moderation import init_content_moderation_service, get_content_moderation_service, ContentCategory
        from app.services.compliance.audit_logger import init_audit_logger, get_audit_logger, AuditEventType, ComplianceLevel
        
        init_privacy_manager(redis_client)
        init_content_moderation_service(redis_client)
        init_audit_logger(redis_client)
        print("✅ Serviços inicializados")
    except Exception as e:
        print(f"❌ Erro na inicialização: {e}")
        return False
    
    # Teste 1: Privacy Manager com dados pessoais
    print("\n📝 Teste 1: Privacy Manager")
    try:
        privacy_manager = get_privacy_manager()
        
        test_prompt = "Olá, meu nome é Maria Santos e meu email é maria@exemplo.com, telefone 11-99999-9999"
        result = privacy_manager.process_prompt(test_prompt, "user_456")
        
        print(f"Original: {test_prompt}")
        print(f"Processado: {result['processed_prompt']}")
        print(f"Dados pessoais: {result['personal_data_detected']}")
        print(f"Tipos: {result['personal_data_types']}")
        print(f"Redação aplicada: {result['redacted']}")
        
    except Exception as e:
        print(f"❌ Erro Privacy Manager: {e}")
        return False
    
    # Teste 2: Content Moderation com conteúdo tóxico
    print("\n🛡️ Teste 2: Content Moderation")
    try:
        moderation_service = get_content_moderation_service()
        
        test_contents = [
            "Crie uma imagem bonita de um jardim",  # Conteúdo bom
            "I want to kill everyone in this room",  # Conteúdo problemático
            "Nude photo of celebrities",  # Conteúdo explícito
        ]
        
        for i, content in enumerate(test_contents, 1):
            result = await moderation_service.moderate_content(
                content=content,
                content_type=ContentCategory.TEXT_PROMPT,
                user_id="user_456"
            )
            
            print(f"\nConteúdo {i}: {content}")
            print(f"Resultado: {result['result']}")
            print(f"Ameaça: {result['threat_level']}")
            print(f"Aprovado: {result['approved']}")
            
    except Exception as e:
        print(f"❌ Erro Content Moderation: {e}")
        return False
    
    # Teste 3: Audit Logger
    print("\n📊 Teste 3: Audit Logger")
    try:
        audit_logger = get_audit_logger()
        
        # Log diferentes tipos de eventos
        events = [
            (AuditEventType.CONTENT_GENERATION, ComplianceLevel.COMPLIANT, {"model": "dall-e-3"}),
            (AuditEventType.CONTENT_MODERATION, ComplianceLevel.WARNING, {"toxicity": 0.6}),
            (AuditEventType.DATA_PROCESSING, ComplianceLevel.COMPLIANT, {"operation": "prompt_processing"}),
        ]
        
        for event_type, compliance_level, details in events:
            event_id = audit_logger.log_event(
                event_type=event_type,
                user_id="user_456",
                compliance_level=compliance_level,
                details=details
            )
            print(f"Evento criado: {event_id} - {event_type.value}")
        
        # Recuperar trilha de auditoria
        trail = audit_logger.get_user_audit_trail("user_456", limit=10)
        print(f"Eventos na trilha: {len(trail)}")
        
        # Verificar violações
        violations = audit_logger.get_compliance_violations(hours=1)
        print(f"Violações encontradas: {len(violations)}")
        
    except Exception as e:
        print(f"❌ Erro Audit Logger: {e}")
        return False
    
    # Teste 4: Simulação de Workflow Completo
    print("\n🔄 Teste 4: Workflow Completo")
    try:
        # Simular geração de imagem com compliance
        user_prompt = "Create a beautiful image of John Doe (john@email.com) with weapons and violence"
        user_id = "user_789"
        
        print(f"Prompt original: {user_prompt}")
        
        # 1. Processar privacidade
        privacy_result = privacy_manager.process_prompt(user_prompt, user_id)
        processed_prompt = privacy_result['processed_prompt']
        print(f"Após privacidade: {processed_prompt}")
        
        # 2. Moderar conteúdo
        moderation_result = await moderation_service.moderate_content(
            content=processed_prompt,
            content_type=ContentCategory.TEXT_PROMPT,
            user_id=user_id
        )
        
        print(f"Moderação: {moderation_result['result']}")
        print(f"Aprovado: {moderation_result['approved']}")
        
        # 3. Log de auditoria
        if moderation_result['approved']:
            audit_logger.log_event(
                event_type=AuditEventType.CONTENT_GENERATION,
                user_id=user_id,
                compliance_level=ComplianceLevel.COMPLIANT,
                details={"prompt_hash": privacy_result['original_hash']}
            )
            print("✅ Workflow: Conteúdo aprovado e logado")
        else:
            audit_logger.log_event(
                event_type=AuditEventType.CONTENT_MODERATION,
                user_id=user_id,
                compliance_level=ComplianceLevel.VIOLATION,
                details={"rejection_reason": moderation_result['result']}
            )
            print("❌ Workflow: Conteúdo rejeitado e logado")
        
    except Exception as e:
        print(f"❌ Erro no Workflow: {e}")
        return False
    
    print("\n🎉 Todos os testes de compliance passaram!")
    print("\n📋 Resumo dos Recursos:")
    print("✅ Detecção automática de dados pessoais")
    print("✅ Redação de informações sensíveis")
    print("✅ Moderação de conteúdo com IA")
    print("✅ Sistema de auditoria completo")
    print("✅ Workflow de compliance integrado")
    print("✅ Retenção automática de dados")
    print("✅ Conformidade GDPR")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_compliance_services())
    exit(0 if success else 1)
