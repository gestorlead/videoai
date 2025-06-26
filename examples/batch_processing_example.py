#!/usr/bin/env python3
"""
Exemplo de uso do sistema de batch processing para geração de imagens em massa.

Este exemplo demonstra:
1. Submissão de jobs em batch
2. Monitoramento de progresso
3. Análise de métricas de performance
4. Uso do sistema de cache
"""

import asyncio
import aiohttp
import json
from typing import List, Dict, Any
import time

# Configuração da API
API_BASE = "http://localhost:5000/api/v1/images"
API_KEY = "your-api-key"  # Configure sua API key

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

async def submit_batch_job(session: aiohttp.ClientSession, requests: List[Dict[str, Any]], provider_id: str = None) -> str:
    """Submete um job em batch"""
    payload = {
        "requests": requests,
        "provider_id": provider_id,
        "priority": 5,
        "metadata": {
            "description": "Batch de exemplo",
            "source": "batch_processing_example.py"
        }
    }
    
    async with session.post(f"{API_BASE}/batch", json=payload, headers=HEADERS) as response:
        if response.status == 200:
            result = await response.json()
            print(f"✅ Batch job submetido: {result['job_id']}")
            return result['job_id']
        else:
            error = await response.text()
            print(f"❌ Erro ao submeter batch: {error}")
            return None

async def check_job_status(session: aiohttp.ClientSession, job_id: str) -> Dict[str, Any]:
    """Verifica status de um job"""
    async with session.get(f"{API_BASE}/batch/{job_id}", headers=HEADERS) as response:
        if response.status == 200:
            return await response.json()
        else:
            return None

async def wait_for_completion(session: aiohttp.ClientSession, job_id: str, max_wait: int = 300):
    """Aguarda conclusão de um job com progresso"""
    start_time = time.time()
    last_progress = {}
    
    print(f"🔄 Aguardando conclusão do job {job_id}...")
    
    while time.time() - start_time < max_wait:
        status = await check_job_status(session, job_id)
        if not status:
            print("❌ Erro ao verificar status")
            break
        
        progress = status['progress']
        if progress != last_progress:
            completed = progress.get('completed', 0)
            failed = progress.get('failed', 0)
            total = status['total_items']
            
            print(f"📊 Progresso: {completed}/{total} concluídos, {failed} falharam")
            
            if status.get('estimated_time_remaining'):
                eta = status['estimated_time_remaining']
                print(f"⏱️  Tempo estimado restante: {eta:.1f}s")
            
            last_progress = progress
        
        if status['status'] in ['completed', 'failed', 'partial']:
            print(f"✅ Job finalizado com status: {status['status']}")
            print(f"💰 Custo total: ${status['total_cost']:.4f}")
            break
        
        await asyncio.sleep(2)
    
    return status

async def get_system_metrics(session: aiohttp.ClientSession) -> Dict[str, Any]:
    """Obtém métricas do sistema"""
    async with session.get(f"{API_BASE}/metrics", headers=HEADERS) as response:
        if response.status == 200:
            return await response.json()
        return {}

async def get_cache_stats(session: aiohttp.ClientSession) -> Dict[str, Any]:
    """Obtém estatísticas do cache"""
    async with session.get(f"{API_BASE}/cache/stats", headers=HEADERS) as response:
        if response.status == 200:
            return await response.json()
        return {}

async def get_provider_performance(session: aiohttp.ClientSession, provider_id: str) -> Dict[str, Any]:
    """Obtém performance de um provider"""
    async with session.get(f"{API_BASE}/providers/{provider_id}/performance", headers=HEADERS) as response:
        if response.status == 200:
            return await response.json()
        return {}

async def example_1_simple_batch():
    """Exemplo 1: Batch simples com múltiplas imagens"""
    print("\n" + "="*60)
    print("📋 EXEMPLO 1: Batch Simples")
    print("="*60)
    
    requests = [
        {
            "prompt": "A beautiful sunset over the ocean",
            "width": 1024,
            "height": 1024,
            "num_images": 1,
            "style": "realistic"
        },
        {
            "prompt": "A futuristic city with flying cars",
            "width": 1024,
            "height": 1024,
            "num_images": 1,
            "style": "artistic"
        },
        {
            "prompt": "A cute cartoon cat wearing a hat",
            "width": 512,
            "height": 512,
            "num_images": 2,
            "style": "anime"
        }
    ]
    
    async with aiohttp.ClientSession() as session:
        job_id = await submit_batch_job(session, requests)
        if job_id:
            final_status = await wait_for_completion(session, job_id)
            print(f"📈 Status final: {json.dumps(final_status, indent=2)}")

async def example_2_provider_comparison():
    """Exemplo 2: Comparação entre providers"""
    print("\n" + "="*60)
    print("🔄 EXEMPLO 2: Comparação de Providers")
    print("="*60)
    
    # Mesma request para providers diferentes
    base_request = {
        "prompt": "A professional headshot photo of a business person",
        "width": 512,
        "height": 512,
        "num_images": 1,
        "style": "realistic"
    }
    
    providers = ["openai", "piapi", "stable-diffusion"]
    
    async with aiohttp.ClientSession() as session:
        jobs = {}
        
        # Submete jobs para cada provider
        for provider in providers:
            job_id = await submit_batch_job(session, [base_request], provider)
            if job_id:
                jobs[provider] = job_id
        
        # Aguarda conclusão de todos
        results = {}
        for provider, job_id in jobs.items():
            print(f"\n🔍 Verificando {provider}...")
            status = await wait_for_completion(session, job_id, max_wait=120)
            results[provider] = status
        
        # Compara resultados
        print("\n📊 COMPARAÇÃO DE RESULTADOS:")
        print("-" * 40)
        for provider, result in results.items():
            if result:
                cost = result.get('total_cost', 0)
                time_taken = result.get('estimated_time_remaining', 0)
                print(f"{provider:15} | ${cost:.4f} | {time_taken:.1f}s")

async def example_3_cache_performance():
    """Exemplo 3: Demonstração de cache"""
    print("\n" + "="*60)
    print("🗄️  EXEMPLO 3: Performance do Cache")
    print("="*60)
    
    # Request que será repetida para testar cache
    repeated_request = {
        "prompt": "A red apple on a wooden table",
        "width": 512,
        "height": 512,
        "num_images": 1,
        "seed": 12345  # Seed fixo para garantir cache hit
    }
    
    async with aiohttp.ClientSession() as session:
        # Primeira execução (cache miss)
        print("🔄 Primeira execução (cache miss esperado)...")
        start_time = time.time()
        job_id1 = await submit_batch_job(session, [repeated_request])
        if job_id1:
            await wait_for_completion(session, job_id1)
        first_time = time.time() - start_time
        
        # Segunda execução (cache hit)
        print("\n🔄 Segunda execução (cache hit esperado)...")
        start_time = time.time()
        job_id2 = await submit_batch_job(session, [repeated_request])
        if job_id2:
            await wait_for_completion(session, job_id2)
        second_time = time.time() - start_time
        
        # Estatísticas do cache
        cache_stats = await get_cache_stats(session)
        print(f"\n📈 PERFORMANCE:")
        print(f"Primeira execução: {first_time:.2f}s")
        print(f"Segunda execução: {second_time:.2f}s")
        print(f"Melhoria: {(first_time/second_time):.1f}x mais rápido")
        
        print(f"\n🗄️  ESTATÍSTICAS DO CACHE:")
        if cache_stats:
            metrics = cache_stats.get('metrics', {})
            print(f"Hit rate: {metrics.get('hit_rate', 0):.1%}")
            print(f"Total hits: {metrics.get('hits', 0)}")
            print(f"Total misses: {metrics.get('misses', 0)}")

async def example_4_monitoring():
    """Exemplo 4: Monitoramento do sistema"""
    print("\n" + "="*60)
    print("📊 EXEMPLO 4: Monitoramento do Sistema")
    print("="*60)
    
    async with aiohttp.ClientSession() as session:
        # Métricas gerais
        metrics = await get_system_metrics(session)
        print("📈 MÉTRICAS GERAIS:")
        print(f"Total processado: {metrics.get('total_processed', 0)}")
        print(f"Total falharam: {metrics.get('total_failed', 0)}")
        print(f"Custo total: ${metrics.get('total_cost', 0):.4f}")
        print(f"Tempo médio: {metrics.get('avg_generation_time', 0):.2f}s")
        print(f"Jobs ativos: {metrics.get('active_jobs', 0)}")
        
        # Tamanho das filas
        queue_sizes = metrics.get('queue_sizes', {})
        if queue_sizes:
            print(f"\n📋 FILAS:")
            for provider, size in queue_sizes.items():
                print(f"{provider}: {size} itens na fila")
        
        # Performance por provider
        providers = ["openai", "piapi", "stable-diffusion"]
        print(f"\n🔍 PERFORMANCE POR PROVIDER:")
        for provider in providers:
            perf = await get_provider_performance(session, provider)
            if perf.get('performance'):
                p = perf['performance']
                print(f"{provider}:")
                print(f"  Taxa de sucesso: {p.get('success_rate', 0):.1%}")
                print(f"  Tempo médio: {p.get('avg_response_time', 0):.2f}s")
                print(f"  Total requests: {p.get('total_requests', 0)}")

async def example_5_large_batch():
    """Exemplo 5: Batch grande com monitoramento"""
    print("\n" + "="*60)
    print("🚀 EXEMPLO 5: Batch Grande (50 imagens)")
    print("="*60)
    
    # Gera 50 requests variadas
    prompts = [
        "A beautiful landscape", "Portrait of a person", "Abstract art",
        "Cute animal", "Technology concept", "Nature scene",
        "Urban photography", "Fantasy creature", "Food photography",
        "Architecture design"
    ]
    
    requests = []
    for i in range(50):
        prompt = prompts[i % len(prompts)]
        requests.append({
            "prompt": f"{prompt} #{i+1}",
            "width": 512,
            "height": 512,
            "num_images": 1,
            "seed": i  # Seed único para cada
        })
    
    async with aiohttp.ClientSession() as session:
        print(f"📤 Submetendo batch com {len(requests)} requests...")
        job_id = await submit_batch_job(session, requests)
        
        if job_id:
            # Monitoramento detalhado
            start_time = time.time()
            last_check = 0
            
            while True:
                status = await check_job_status(session, job_id)
                if not status:
                    break
                
                current_time = time.time()
                if current_time - last_check >= 5:  # Update a cada 5s
                    progress = status['progress']
                    completed = progress.get('completed', 0)
                    failed = progress.get('failed', 0)
                    processing = progress.get('processing', 0)
                    pending = progress.get('pending', 0)
                    
                    elapsed = current_time - start_time
                    
                    print(f"\n⏱️  {elapsed:.0f}s | "
                          f"✅ {completed} | "
                          f"🔄 {processing} | "
                          f"⏳ {pending} | "
                          f"❌ {failed}")
                    
                    if status.get('estimated_time_remaining'):
                        eta = status['estimated_time_remaining']
                        print(f"🎯 ETA: {eta:.0f}s")
                    
                    last_check = current_time
                
                if status['status'] in ['completed', 'failed', 'partial']:
                    final_time = time.time() - start_time
                    print(f"\n🏁 FINALIZADO em {final_time:.1f}s")
                    print(f"💰 Custo total: ${status['total_cost']:.4f}")
                    print(f"📊 Taxa de sucesso: {completed/(completed+failed)*100:.1f}%")
                    break
                
                await asyncio.sleep(1)

async def main():
    """Executa todos os exemplos"""
    print("🎨 SISTEMA DE BATCH PROCESSING - EXEMPLOS")
    print("==========================================")
    
    try:
        await example_1_simple_batch()
        await example_2_provider_comparison()
        await example_3_cache_performance()
        await example_4_monitoring()
        await example_5_large_batch()
        
        print("\n✅ Todos os exemplos executados com sucesso!")
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 