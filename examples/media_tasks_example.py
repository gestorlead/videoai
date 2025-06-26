"""
Exemplo Completo do Sistema de Tarefas de Mídia
Demonstra todas as funcionalidades do sistema assíncrono
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Dict, Any, List

# URLs da API (ajuste conforme necessário)
API_BASE_URL = "http://localhost:8000/api/v1/media"
AUTH_TOKEN = "your-jwt-token-here"  # Substitua por um token válido

class MediaTasksClient:
    """Cliente para interagir com a API de tarefas de mídia"""
    
    def __init__(self, base_url: str, auth_token: str):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    async def create_image_generation_task(self, prompt: str, webhook_url: str = None) -> Dict[str, Any]:
        """Cria uma tarefa de geração de imagem"""
        payload = {
            "prompt": prompt,
            "style": "realistic",
            "size": "1024x1024",
            "quality": "hd",
            "n": 1,
            "webhook_url": webhook_url,
            "priority": "medium",
            "metadata": {
                "created_by": "example_script",
                "category": "demo"
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/images/generate",
                headers=self.headers,
                json=payload
            ) as response:
                return await response.json()
    
    async def create_video_generation_task(self, prompt: str, webhook_url: str = None) -> Dict[str, Any]:
        """Cria uma tarefa de geração de vídeo"""
        payload = {
            "prompt": prompt,
            "duration": 5,
            "style": "cinematic",
            "fps": 24,
            "resolution": "1280x720",
            "webhook_url": webhook_url,
            "priority": "high",
            "metadata": {
                "created_by": "example_script",
                "category": "demo_video"
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/videos/generate",
                headers=self.headers,
                json=payload
            ) as response:
                return await response.json()
    
    async def create_audio_transcription_task(self, audio_url: str, webhook_url: str = None) -> Dict[str, Any]:
        """Cria uma tarefa de transcrição de áudio"""
        payload = {
            "audio_url": audio_url,
            "language": "pt",
            "model": "whisper-1",
            "response_format": "json",
            "webhook_url": webhook_url,
            "priority": "medium",
            "metadata": {
                "created_by": "example_script",
                "source": "demo_audio"
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/audio/transcribe",
                headers=self.headers,
                json=payload
            ) as response:
                return await response.json()
    
    async def create_subtitle_generation_task(self, text: str, webhook_url: str = None) -> Dict[str, Any]:
        """Cria uma tarefa de geração de legendas"""
        payload = {
            "text": text,
            "target_language": "en",
            "format": "srt",
            "timing_mode": "auto",
            "webhook_url": webhook_url,
            "priority": "low",
            "metadata": {
                "created_by": "example_script",
                "translation_type": "demo"
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/subtitles/generate",
                headers=self.headers,
                json=payload
            ) as response:
                return await response.json()
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Obtém o status de uma tarefa"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/tasks/{task_id}",
                headers=self.headers
            ) as response:
                return await response.json()
    
    async def list_tasks(self, task_type: str = None, status: str = None) -> List[Dict[str, Any]]:
        """Lista tarefas do usuário"""
        params = {}
        if task_type:
            params["task_type"] = task_type
        if status:
            params["status"] = status
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/tasks",
                headers=self.headers,
                params=params
            ) as response:
                return await response.json()
    
    async def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """Cancela uma tarefa"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/tasks/{task_id}/cancel",
                headers=self.headers
            ) as response:
                return await response.json()
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Obtém estatísticas das tarefas"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/statistics",
                headers=self.headers
            ) as response:
                return await response.json()
    
    async def create_batch_tasks(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Cria múltiplas tarefas em lote"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/batch",
                headers=self.headers,
                json=tasks
            ) as response:
                return await response.json()
    
    async def health_check(self) -> Dict[str, Any]:
        """Verifica status dos serviços"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/health",
                headers=self.headers
            ) as response:
                return await response.json()


async def exemplo_basico():
    """Exemplo básico: criar uma tarefa e monitorar status"""
    print("=== Exemplo Básico ===")
    
    client = MediaTasksClient(API_BASE_URL, AUTH_TOKEN)
    
    # 1. Criar tarefa de geração de imagem
    print("1. Criando tarefa de geração de imagem...")
    task = await client.create_image_generation_task(
        prompt="Um gato robô futurista em um jardim cyberpunk",
        webhook_url="https://example.com/webhook"
    )
    
    task_id = task["id"]
    print(f"   Tarefa criada: {task_id}")
    print(f"   Status inicial: {task['status']}")
    
    # 2. Monitorar progresso
    print("\n2. Monitorando progresso...")
    while True:
        status = await client.get_task_status(task_id)
        print(f"   Status: {status['status']} | Progresso: {status.get('progress', 0)*100:.1f}%")
        
        if status["status"] in ["completed", "failed", "cancelled"]:
            break
        
        await asyncio.sleep(2)
    
    # 3. Resultado final
    print(f"\n3. Resultado final:")
    if status["status"] == "completed":
        print(f"   ✅ Sucesso! Duração: {status.get('actual_duration', 0):.2f}s")
        if status.get("output_data"):
            print(f"   📄 Dados de saída: {json.dumps(status['output_data'], indent=2)}")
    else:
        print(f"   ❌ Falhou: {status.get('error_message', 'Erro desconhecido')}")


async def exemplo_multiplas_tarefas():
    """Exemplo: criar múltiplas tarefas diferentes"""
    print("\n=== Exemplo Múltiplas Tarefas ===")
    
    client = MediaTasksClient(API_BASE_URL, AUTH_TOKEN)
    
    # 1. Criar várias tarefas
    print("1. Criando várias tarefas...")
    
    tasks = []
    
    # Imagem
    image_task = await client.create_image_generation_task(
        "Uma paisagem digital minimalista"
    )
    tasks.append(("Imagem", image_task["id"]))
    
    # Vídeo
    video_task = await client.create_video_generation_task(
        "Um drone voando sobre uma cidade"
    )
    tasks.append(("Vídeo", video_task["id"]))
    
    # Transcrição (URL de exemplo)
    audio_task = await client.create_audio_transcription_task(
        "https://example.com/audio.mp3"
    )
    tasks.append(("Transcrição", audio_task["id"]))
    
    # Legenda
    subtitle_task = await client.create_subtitle_generation_task(
        "Olá mundo! Este é um teste de legendas."
    )
    tasks.append(("Legenda", subtitle_task["id"]))
    
    print(f"   Criadas {len(tasks)} tarefas")
    
    # 2. Monitorar todas simultaneamente
    print("\n2. Monitorando todas as tarefas...")
    
    completed_tasks = set()
    
    while len(completed_tasks) < len(tasks):
        print(f"\n   Status das tarefas ({len(completed_tasks)}/{len(tasks)} completas):")
        
        for task_type, task_id in tasks:
            if task_id in completed_tasks:
                continue
            
            status = await client.get_task_status(task_id)
            progress = status.get('progress', 0) * 100
            
            print(f"   {task_type:12} | {status['status']:10} | {progress:5.1f}%")
            
            if status["status"] in ["completed", "failed", "cancelled"]:
                completed_tasks.add(task_id)
        
        if len(completed_tasks) < len(tasks):
            await asyncio.sleep(3)
    
    print("\n3. Todas as tarefas finalizadas!")


async def exemplo_batch_processing():
    """Exemplo: processamento em lote"""
    print("\n=== Exemplo Batch Processing ===")
    
    client = MediaTasksClient(API_BASE_URL, AUTH_TOKEN)
    
    # 1. Preparar lote de tarefas
    print("1. Preparando lote de tarefas...")
    
    batch_tasks = [
        {
            "task_type": "image_generation",
            "input_data": {
                "prompt": f"Arte abstrata número {i}",
                "style": "artistic",
                "size": "512x512"
            },
            "priority": "medium"
        }
        for i in range(1, 6)
    ]
    
    # 2. Enviar lote
    print(f"2. Enviando lote de {len(batch_tasks)} tarefas...")
    batch_result = await client.create_batch_tasks(batch_tasks)
    
    batch_id = batch_result["batch_id"]
    task_ids = batch_result["task_ids"]
    
    print(f"   Lote criado: {batch_id}")
    print(f"   IDs das tarefas: {task_ids}")
    
    # 3. Monitorar lote
    print("\n3. Monitorando lote...")
    
    completed = 0
    total = len(task_ids)
    
    while completed < total:
        completed = 0
        failed = 0
        
        for task_id in task_ids:
            status = await client.get_task_status(task_id)
            if status["status"] == "completed":
                completed += 1
            elif status["status"] == "failed":
                failed += 1
        
        print(f"   Progresso: {completed}/{total} completas, {failed} falharam")
        
        if completed + failed >= total:
            break
        
        await asyncio.sleep(5)
    
    print(f"\n4. Lote finalizado: {completed} sucessos, {failed} falhas")


async def exemplo_monitoring():
    """Exemplo: monitoramento e estatísticas"""
    print("\n=== Exemplo Monitoramento ===")
    
    client = MediaTasksClient(API_BASE_URL, AUTH_TOKEN)
    
    # 1. Health check
    print("1. Verificando saúde dos serviços...")
    health = await client.health_check()
    print(f"   Status geral: {health['status']}")
    print(f"   Serviços ativos: {list(health['services'].keys())}")
    
    # 2. Estatísticas do usuário
    print("\n2. Estatísticas do usuário...")
    stats = await client.get_statistics()
    print(f"   Total de tarefas: {stats.get('total_tasks', 0)}")
    print(f"   Taxa de sucesso: {stats.get('success_rate', 0)*100:.1f}%")
    print(f"   Custo total: ${stats.get('total_cost', 0):.2f}")
    
    # 3. Listar tarefas recentes
    print("\n3. Tarefas recentes...")
    recent_tasks = await client.list_tasks()
    
    if recent_tasks:
        for task in recent_tasks[:5]:  # Últimas 5
            created = task['created_at'][:19]  # Remove timezone
            print(f"   {task['id'][:8]}... | {task['task_type']} | {task['status']} | {created}")
    else:
        print("   Nenhuma tarefa encontrada")


async def exemplo_webhook_server():
    """Exemplo: servidor webhook simples para receber notificações"""
    from aiohttp import web
    import aiohttp_cors
    
    async def webhook_handler(request):
        """Handler para receber webhooks"""
        try:
            data = await request.json()
            
            print(f"\n🔔 Webhook recebido:")
            print(f"   Evento: {data.get('event_type')}")
            print(f"   Tarefa: {data.get('task_id')}")
            print(f"   Timestamp: {data.get('timestamp')}")
            print(f"   Dados: {json.dumps(data.get('data', {}), indent=2)}")
            
            return web.json_response({"status": "received"})
        
        except Exception as e:
            print(f"❌ Erro ao processar webhook: {e}")
            return web.json_response({"error": str(e)}, status=400)
    
    # Configura servidor
    app = web.Application()
    
    # CORS para desenvolvimento
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods="*"
        )
    })
    
    app.router.add_post('/webhook', webhook_handler)
    
    # Adiciona CORS a todas as rotas
    for route in list(app.router.routes()):
        cors.add(route)
    
    print("\n=== Servidor Webhook ===")
    print("Iniciando servidor webhook em http://localhost:8080/webhook")
    print("Use esta URL nas suas tarefas para receber notificações")
    print("Pressione Ctrl+C para parar\n")
    
    # Inicia servidor
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()
    
    try:
        # Mantém rodando
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Parando servidor webhook...")
    finally:
        await runner.cleanup()


async def main():
    """Executa todos os exemplos"""
    print("🤖 Exemplos do Sistema de Tarefas de Mídia")
    print("=" * 50)
    
    try:
        # Exemplos básicos
        await exemplo_basico()
        await exemplo_multiplas_tarefas()
        await exemplo_batch_processing()
        await exemplo_monitoring()
        
        # Pergunta se quer rodar o servidor webhook
        print("\n" + "=" * 50)
        print("Os exemplos básicos foram executados!")
        print("\nDeseja iniciar o servidor webhook para testar notificações? (s/n)")
        
        # Para demo, vamos pular a entrada do usuário
        print("Iniciando servidor webhook...")
        await exemplo_webhook_server()
        
    except Exception as e:
        print(f"❌ Erro nos exemplos: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Instruções de uso
    print("📋 Instruções de Uso:")
    print("1. Certifique-se que a API está rodando em localhost:8000")
    print("2. Substitua AUTH_TOKEN por um token JWT válido")
    print("3. Execute: python media_tasks_example.py")
    print()
    
    # Executa exemplos
    asyncio.run(main()) 