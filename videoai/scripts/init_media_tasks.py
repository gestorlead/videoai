#!/usr/bin/env python3
"""
Script de Inicialização do Sistema de Tarefas de Mídia
Configura banco de dados, serviços e demonstra funcionamento
"""

import asyncio
import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao Python path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from app.database.session import create_tables, engine
from app.services.task_manager import universal_task_manager
from app.services.webhook_service import webhook_service
from app.services.provider_registry import provider_registry
from app.models.base_task import TaskType, TaskStatus, TaskPriority
from app.schemas.tasks import TaskCreateRequest


async def setup_database():
    """Configura o banco de dados"""
    print("🗄️  Configurando banco de dados...")
    
    try:
        # Cria as tabelas
        create_tables()
        print("   ✅ Tabelas criadas com sucesso")
        
        # Testa conexão
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            print(f"   ✅ Conexão testada: {result.fetchone()}")
        
    except Exception as e:
        print(f"   ❌ Erro ao configurar banco: {e}")
        return False
    
    return True


async def setup_services():
    """Configura os serviços"""
    print("\n🔧 Configurando serviços...")
    
    try:
        # Inicia o webhook service
        webhook_service.start_delivery_worker()
        print("   ✅ Webhook service iniciado")
        
        # Verifica o provider registry
        stats = provider_registry.get_registry_stats()
        print(f"   ✅ Provider registry: {stats['active_providers']}/{stats['total_providers']} ativos")
        
        # Health check dos provedores
        health = await provider_registry.health_check_all()
        active_providers = sum(1 for status in health.values() if status.value == "active")
        print(f"   ✅ Health check: {active_providers} provedores ativos")
        
    except Exception as e:
        print(f"   ❌ Erro ao configurar serviços: {e}")
        return False
    
    return True


async def run_demo_tasks():
    """Executa tarefas de demonstração"""
    print("\n🎭 Executando tarefas de demonstração...")
    
    try:
        # Mock de sessão de banco
        class MockDB:
            def commit(self): pass
            def rollback(self): pass
            def close(self): pass
            def add(self, obj): 
                # Simula salvar no banco
                obj.id = f"demo_{int(asyncio.get_event_loop().time())}"
                return obj
            def query(self, model): 
                class MockQuery:
                    def filter(self, *args): return self
                    def first(self): return None
                    def all(self): return []
                    def count(self): return 0
                return MockQuery()
        
        mock_db = MockDB()
        
        # Demonstração 1: Geração de Imagem
        print("\n   📸 Teste: Geração de Imagem")
        image_request = TaskCreateRequest(
            task_type=TaskType.IMAGE_GENERATION,
            input_data={
                "prompt": "Um robô pintando um quadro em um ateliê futurista",
                "style": "realistic",
                "size": "1024x1024"
            },
            priority=TaskPriority.MEDIUM,
            metadata={"demo": True}
        )
        
        image_task = await universal_task_manager.create_task(
            task_request=image_request,
            user_id="demo_user",
            db=mock_db
        )
        print(f"      ✅ Tarefa criada: {image_task.id}")
        print(f"      📊 Status: {image_task.status}")
        
        # Demonstração 2: Transcrição de Áudio
        print("\n   🎵 Teste: Transcrição de Áudio")
        audio_request = TaskCreateRequest(
            task_type=TaskType.AUDIO_TRANSCRIPTION,
            input_data={
                "audio_url": "https://example.com/audio.mp3",
                "language": "pt-BR",
                "model": "whisper-1"
            },
            priority=TaskPriority.HIGH,
            webhook_url="https://example.com/webhook",
            metadata={"demo": True}
        )
        
        audio_task = await universal_task_manager.create_task(
            task_request=audio_request,
            user_id="demo_user",
            db=mock_db
        )
        print(f"      ✅ Tarefa criada: {audio_task.id}")
        print(f"      📊 Status: {audio_task.status}")
        print(f"      🔗 Webhook: {audio_task.webhook_url}")
        
        # Demonstração 3: Lote de Tarefas
        print("\n   📦 Teste: Lote de Tarefas")
        batch_requests = [
            TaskCreateRequest(
                task_type=TaskType.SUBTITLE_GENERATION,
                input_data={
                    "text": f"Esta é a frase número {i} para demonstração",
                    "target_language": "en",
                    "format": "srt"
                },
                priority=TaskPriority.LOW,
                metadata={"batch": True, "index": i}
            )
            for i in range(1, 4)
        ]
        
        batch_tasks = []
        for request in batch_requests:
            task = await universal_task_manager.create_task(
                task_request=request,
                user_id="demo_user",
                db=mock_db
            )
            batch_tasks.append(task)
        
        print(f"      ✅ Lote criado: {len(batch_tasks)} tarefas")
        for task in batch_tasks:
            print(f"         - {task.id}: {task.task_type.value}")
        
    except Exception as e:
        print(f"   ❌ Erro nas demonstrações: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


async def show_system_info():
    """Mostra informações do sistema"""
    print("\n📋 Informações do Sistema")
    print("=" * 50)
    
    # Provider Registry Stats
    registry_stats = provider_registry.get_registry_stats()
    print(f"🔌 Provedores Registrados: {registry_stats['total_providers']}")
    print(f"   Ativos: {registry_stats['active_providers']}")
    
    print("\n📊 Provedores por Tipo de Tarefa:")
    for task_type, stats in registry_stats['by_task_type'].items():
        print(f"   {task_type:20} | Total: {stats['total']:2d} | Ativos: {stats['active']:2d}")
    
    # Webhook Stats
    webhook_stats = webhook_service.get_webhooks_stats()
    print(f"\n🔔 Webhooks:")
    print(f"   Total: {webhook_stats['total_webhooks']}")
    print(f"   Taxa de Sucesso: {webhook_stats['success_rate']*100:.1f}%")
    print(f"   Worker Ativo: {'✅ Sim' if webhook_stats['worker_running'] else '❌ Não'}")
    
    # Database Info
    print(f"\n🗄️  Banco de Dados:")
    print(f"   Engine: {engine.url}")
    print(f"   Tabelas Criadas: ✅ Sim")


async def cleanup():
    """Limpa recursos"""
    print("\n🧹 Limpando recursos...")
    
    try:
        # Para o webhook service
        webhook_service.stop_delivery_worker()
        print("   ✅ Webhook service parado")
        
        # Limpa registros antigos
        cleaned = webhook_service.cleanup_old_deliveries(days=0)  # Limpa tudo para demo
        print(f"   ✅ {cleaned} registros de webhook removidos")
        
    except Exception as e:
        print(f"   ⚠️  Erro na limpeza: {e}")


async def main():
    """Função principal"""
    print("🚀 Inicializando Sistema de Tarefas de Mídia")
    print("=" * 50)
    
    success = True
    
    # Setup do banco
    if not await setup_database():
        success = False
    
    # Setup dos serviços
    if success and not await setup_services():
        success = False
    
    # Demonstrações
    if success:
        await run_demo_tasks()
    
    # Informações do sistema
    await show_system_info()
    
    # Cleanup
    await cleanup()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Sistema inicializado com sucesso!")
        print("\n🎯 Próximos passos:")
        print("   1. Execute a API: uvicorn app.main:app --reload")
        print("   2. Acesse a documentação: http://localhost:8000/docs")
        print("   3. Teste os endpoints com o exemplo: python examples/media_tasks_example.py")
        print("   4. Configure suas API keys de provedores reais")
    else:
        print("❌ Falha na inicialização!")
        return 1
    
    return 0


if __name__ == "__main__":
    print("📱 Sistema de Tarefas de Mídia - VideoAI")
    print("   Versão: 1.0.0")
    print("   Autor: VideoAI Team")
    print()
    
    # Executa
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 