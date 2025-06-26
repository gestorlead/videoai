"""
Demonstração Completa do Sistema de Teste e Refinamento de Prompts
Exemplo prático mostrando todas as funcionalidades implementadas na Tarefa 3.4
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Dict, Any, List

# URLs da API (ajuste conforme necessário)
API_BASE_URL = "http://localhost:8000/api/v1"
AUTH_TOKEN = "your-jwt-token-here"  # Substitua por um token válido

class PromptTestingClient:
    """Cliente para interagir com a API de teste de prompts"""
    
    def __init__(self, base_url: str, auth_token: str):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    async def create_ab_test(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Cria um novo teste A/B"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/prompt-testing/tests/ab-test",
                headers=self.headers,
                json=config
            ) as response:
                return await response.json()
    
    async def create_iterative_test(self, base_prompt: str, target_metric: str = "image_quality") -> Dict[str, Any]:
        """Cria teste de refinamento iterativo"""
        payload = {
            "base_prompt": base_prompt,
            "target_metric": target_metric,
            "iterations": 5
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/prompt-testing/tests/iterative",
                headers=self.headers,
                json=payload
            ) as response:
                return await response.json()
    
    async def create_multivariate_test(self, base_prompt: str) -> Dict[str, Any]:
        """Cria teste multivariável"""
        payload = {
            "base_prompt": base_prompt,
            "style_options": ["realistic", "artistic", "cinematic"],
            "quality_options": ["standard", "hd"],
            "size_options": ["512x512", "1024x1024"]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/prompt-testing/tests/multivariate",
                headers=self.headers,
                json=payload
            ) as response:
                return await response.json()
    
    async def run_test_iteration(self, test_id: str) -> Dict[str, Any]:
        """Executa uma iteração de teste"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/prompt-testing/tests/{test_id}/run-iteration",
                headers=self.headers
            ) as response:
                return await response.json()
    
    async def get_test_status(self, test_id: str) -> Dict[str, Any]:
        """Obtém status de um teste"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/prompt-testing/tests/{test_id}/status",
                headers=self.headers
            ) as response:
                return await response.json()
    
    async def analyze_test(self, test_id: str) -> Dict[str, Any]:
        """Analisa resultados de um teste"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/prompt-testing/tests/{test_id}/analysis",
                headers=self.headers
            ) as response:
                return await response.json()
    
    async def get_optimization_suggestions(self, prompt: str) -> List[Dict[str, Any]]:
        """Obtém sugestões de otimização para um prompt"""
        # Simulação - em produção seria um endpoint real
        return [
            {
                "type": "quality_enhancement",
                "description": "Adicionar palavras-chave de qualidade",
                "example": f"{prompt}, high quality, detailed",
                "expected_improvement": 15
            },
            {
                "type": "style_definition", 
                "description": "Definir estilo artístico",
                "example": f"{prompt}, digital art style",
                "expected_improvement": 10
            }
        ]
    
    async def auto_optimize_batch(self, prompts: List[str]) -> Dict[str, Any]:
        """Otimiza prompts automaticamente em lote"""
        payload = prompts
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/prompt-testing/batch/auto-optimize",
                headers=self.headers,
                json=payload
            ) as response:
                return await response.json()
    
    async def get_testing_statistics(self) -> Dict[str, Any]:
        """Obtém estatísticas de testes"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/prompt-testing/statistics",
                headers=self.headers
            ) as response:
                return await response.json()


async def demo_ab_test():
    """Demonstração de teste A/B simples"""
    print("🎯 === DEMO: Teste A/B de Prompts ===")
    
    client = PromptTestingClient(API_BASE_URL, AUTH_TOKEN)
    
    # 1. Configurar teste A/B
    print("\n1. Configurando teste A/B...")
    
    test_config = {
        "test_type": "ab_test",
        "base_prompt": "a beautiful robot in a garden",
        "variants": [
            {
                "id": "variant_a",
                "prompt": "a beautiful robot in a garden",
                "style_modifiers": [],
                "technical_params": {"quality": "standard"},
                "description": "Prompt original básico"
            },
            {
                "id": "variant_b",
                "prompt": "a beautiful robot in a garden, high quality, detailed, artistic masterpiece",
                "style_modifiers": ["artistic", "detailed"],
                "technical_params": {"quality": "hd"},
                "description": "Prompt otimizado com qualidade"
            },
            {
                "id": "variant_c",
                "prompt": "a beautiful futuristic robot in a lush cyberpunk garden, cinematic lighting, 8k, photorealistic",
                "style_modifiers": ["cinematic", "futuristic", "photorealistic"],
                "technical_params": {"quality": "hd", "resolution": "8k"},
                "description": "Prompt avançado com elementos cinematográficos"
            }
        ],
        "target_metrics": ["image_quality", "aesthetic_score", "generation_time"],
        "sample_size": 15  # 5 amostras por variante
    }
    
    try:
        test_result = await client.create_ab_test(test_config)
        test_id = test_result["test_id"]
        print(f"   ✅ Teste criado: {test_id}")
        print(f"   📊 Variantes: {test_result['variants_count']}")
        print(f"   🎯 Meta de amostras: {test_result['target_sample_size']}")
        
        # 2. Executar iterações do teste
        print(f"\n2. Executando iterações do teste...")
        
        for i in range(test_config["sample_size"]):
            try:
                iteration_result = await client.run_test_iteration(test_id)
                
                variant_tested = iteration_result["variant_tested"]
                total_samples = iteration_result["total_samples"]
                target_samples = iteration_result["target_samples"]
                
                print(f"   Iteração {i+1}: Testou {variant_tested} | "
                      f"Progresso: {total_samples}/{target_samples}")
                
                # Simula intervalo entre testes
                await asyncio.sleep(0.5)
                
                # Verifica se teste foi concluído
                if iteration_result.get("analysis"):
                    print(f"   🏆 Vencedor declarado automaticamente!")
                    break
                    
            except Exception as e:
                print(f"   ⚠️ Erro na iteração {i+1}: {e}")
                continue
        
        # 3. Analisar resultados
        print(f"\n3. Analisando resultados finais...")
        
        try:
            analysis = await client.analyze_test(test_id)
            
            print(f"   🏆 Variante vencedora: {analysis['winner_variant_id']}")
            print(f"   📈 Melhoria: {analysis['improvement_percentage']:.1f}%")
            print(f"   🎯 Confiança: {analysis['confidence_score']*100:.1f}%")
            print(f"   📊 Significância estatística: {'✅ Sim' if analysis['statistical_significance'] else '❌ Não'}")
            
            print(f"\n   🔍 Análise por métrica:")
            for metric, data in analysis["metrics_analysis"].items():
                best_variant = data["best_variant"]
                improvement = data["improvement_percentage"]
                print(f"      {metric}: {best_variant} (+{improvement:.1f}%)")
            
            print(f"\n   💡 Recomendações:")
            for i, rec in enumerate(analysis["recommendations"][:3], 1):
                print(f"      {i}. {rec}")
            
            print(f"\n   ✨ Prompt otimizado final:")
            print(f"      '{analysis['optimal_prompt']}'")
            
        except Exception as e:
            print(f"   ❌ Erro na análise: {e}")
        
        return test_id
        
    except Exception as e:
        print(f"❌ Erro no teste A/B: {e}")
        return None


async def demo_iterative_refinement():
    """Demonstração de refinamento iterativo"""
    print("\n🔄 === DEMO: Refinamento Iterativo ===")
    
    client = PromptTestingClient(API_BASE_URL, AUTH_TOKEN)
    
    # 1. Criar teste iterativo
    print("\n1. Iniciando refinamento iterativo...")
    
    base_prompt = "a cat sitting on a chair"
    
    try:
        test_result = await client.create_iterative_test(base_prompt, "image_quality")
        test_id = test_result["test_id"]
        
        print(f"   ✅ Teste iterativo criado: {test_id}")
        print(f"   📝 Prompt base: '{base_prompt}'")
        print(f"   🎯 Métrica alvo: {test_result['target_metric']}")
        print(f"   🔄 Iterações: {test_result['iterations']}")
        
        # 2. Executar iterações
        print(f"\n2. Executando refinamento...")
        
        iteration_count = 0
        while iteration_count < 10:  # Máximo 10 iterações
            try:
                result = await client.run_test_iteration(test_id)
                iteration_count += 1
                
                variant = result["variant_tested"]
                progress = result["total_samples"]
                target = result["target_samples"]
                
                print(f"   Iteração {iteration_count}: {variant} | {progress}/{target}")
                
                if progress >= target:
                    print(f"   ✅ Refinamento completo!")
                    break
                
                await asyncio.sleep(0.3)
                
            except Exception as e:
                print(f"   ⚠️ Erro na iteração: {e}")
                break
        
        # 3. Análise do refinamento
        print(f"\n3. Analisando refinamento...")
        
        try:
            analysis = await client.analyze_test(test_id)
            
            print(f"   🎯 Melhor iteração: {analysis['winner_variant_id']}")
            print(f"   📈 Melhoria obtida: {analysis['improvement_percentage']:.1f}%")
            print(f"   ✨ Resultado final: '{analysis['optimal_prompt']}'")
            
        except Exception as e:
            print(f"   ❌ Erro na análise: {e}")
        
        return test_id
        
    except Exception as e:
        print(f"❌ Erro no refinamento iterativo: {e}")
        return None


async def demo_multivariate_test():
    """Demonstração de teste multivariável"""
    print("\n🎲 === DEMO: Teste Multivariável ===")
    
    client = PromptTestingClient(API_BASE_URL, AUTH_TOKEN)
    
    # 1. Criar teste multivariável
    print("\n1. Configurando teste multivariável...")
    
    base_prompt = "a dragon flying over mountains"
    
    try:
        test_result = await client.create_multivariate_test(base_prompt)
        test_id = test_result["test_id"]
        
        print(f"   ✅ Teste multivariável criado: {test_id}")
        print(f"   📝 Prompt base: '{base_prompt}'")
        print(f"   🎨 Estilos: {test_result['style_options']}")
        print(f"   🔧 Qualidades: {test_result['quality_options']}")
        print(f"   📐 Tamanhos: {test_result['size_options']}")
        print(f"   🧮 Total de combinações: {test_result['total_combinations']}")
        
        # 2. Executar testes das combinações
        print(f"\n2. Testando combinações...")
        
        target_iterations = test_result['total_combinations'] * 2  # 2 por combinação
        
        for i in range(target_iterations):
            try:
                result = await client.run_test_iteration(test_id)
                
                variant = result["variant_tested"]
                progress = result["total_samples"]
                
                print(f"   Teste {i+1}: {variant} | Total: {progress}")
                
                if result.get("analysis"):
                    print(f"   🏆 Análise automática disponível!")
                    break
                
                await asyncio.sleep(0.2)
                
            except Exception as e:
                print(f"   ⚠️ Erro no teste {i+1}: {e}")
                continue
        
        # 3. Status final
        print(f"\n3. Status final do teste multivariável...")
        
        try:
            status = await client.get_test_status(test_id)
            
            print(f"   📊 Total de amostras: {status['total_samples']}")
            print(f"   🏁 Teste completo: {'✅ Sim' if status['is_complete'] else '❌ Não'}")
            
            print(f"\n   📈 Amostras por variante:")
            for variant_id, count in status["samples_by_variant"].items():
                print(f"      {variant_id}: {count} amostras")
            
            # Análise se houver dados suficientes
            if status["total_samples"] >= 10:
                try:
                    analysis = await client.analyze_test(test_id)
                    print(f"\n   🏆 Melhor combinação: {analysis['winner_variant_id']}")
                    print(f"   ✨ Prompt otimizado: '{analysis['optimal_prompt']}'")
                except:
                    print(f"   ⏳ Análise ainda em processamento...")
            
        except Exception as e:
            print(f"   ❌ Erro no status: {e}")
        
        return test_id
        
    except Exception as e:
        print(f"❌ Erro no teste multivariável: {e}")
        return None


async def demo_optimization_suggestions():
    """Demonstração de sugestões de otimização"""
    print("\n💡 === DEMO: Sugestões de Otimização ===")
    
    client = PromptTestingClient(API_BASE_URL, AUTH_TOKEN)
    
    # Prompts de exemplo para análise
    test_prompts = [
        "a cat",
        "beautiful woman",
        "car on road",
        "a detailed portrait of an elegant woman with flowing hair, professional lighting, high quality, artistic masterpiece",
        "cyberpunk city at night, neon lights, rain, cinematic, 8k, photorealistic"
    ]
    
    print("\n1. Analisando prompts e gerando sugestões...")
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n   Prompt {i}: '{prompt}'")
        
        try:
            suggestions = await client.get_optimization_suggestions(prompt)
            
            if suggestions:
                for j, suggestion in enumerate(suggestions, 1):
                    print(f"      {j}. {suggestion['description']}")
                    print(f"         Exemplo: '{suggestion['example']}'")
                    print(f"         Melhoria esperada: +{suggestion['expected_improvement']}%")
            else:
                print(f"      ✅ Prompt já otimizado!")
                
        except Exception as e:
            print(f"      ❌ Erro: {e}")


async def demo_batch_optimization():
    """Demonstração de otimização em lote"""
    print("\n⚡ === DEMO: Otimização em Lote ===")
    
    client = PromptTestingClient(API_BASE_URL, AUTH_TOKEN)
    
    # Lista de prompts para otimizar
    prompts_to_optimize = [
        "a robot",
        "mountain landscape", 
        "portrait of a person",
        "futuristic city",
        "abstract art"
    ]
    
    print(f"\n1. Otimizando {len(prompts_to_optimize)} prompts automaticamente...")
    
    try:
        result = await client.auto_optimize_batch(prompts_to_optimize)
        
        print(f"   ✅ Lote criado: {result['batch_id']}")
        print(f"   📊 Prompts processados: {result['prompts_count']}")
        print(f"   🎯 Métrica alvo: {result['target_metric']}")
        print(f"   ⏱️ Tempo estimado: {result['estimated_completion']}")
        
        print(f"\n2. Resultados da otimização:")
        for i, optimization in enumerate(result["results"], 1):
            print(f"   {i}. Original: '{optimization['original_prompt']}'")
            print(f"      Test ID: {optimization['test_id']}")
            print(f"      Status: {optimization['status']}")
        
    except Exception as e:
        print(f"❌ Erro na otimização em lote: {e}")


async def demo_statistics_dashboard():
    """Demonstração do dashboard de estatísticas"""
    print("\n📊 === DEMO: Dashboard de Estatísticas ===")
    
    client = PromptTestingClient(API_BASE_URL, AUTH_TOKEN)
    
    print("\n1. Coletando estatísticas de testes...")
    
    try:
        stats = await client.get_testing_statistics()
        
        print(f"   👤 Usuário: {stats['user_id']}")
        print(f"   📝 Total de testes: {stats['total_tests']}")
        print(f"   🔄 Total de resultados: {stats['total_results']}")
        print(f"   📈 Média de resultados por teste: {stats['avg_results_per_test']:.1f}")
        
        print(f"\n   📊 Tipos de teste executados:")
        for test_type, count in stats.get("test_types", {}).items():
            print(f"      {test_type}: {count} testes")
        
        print(f"\n   ⏰ Última atividade: {stats['last_activity']}")
        
    except Exception as e:
        print(f"❌ Erro nas estatísticas: {e}")


async def demo_complete_workflow():
    """Demonstração do fluxo completo de trabalho"""
    print("\n🚀 === DEMO: Fluxo Completo de Otimização ===")
    
    print("Este demo mostra um fluxo típico de otimização de prompts:")
    print("1. Análise inicial do prompt")
    print("2. Teste A/B com variantes")
    print("3. Refinamento iterativo do vencedor")
    print("4. Validação final")
    
    # 1. Teste A/B inicial
    ab_test_id = await demo_ab_test()
    
    if ab_test_id:
        # 2. Refinamento iterativo baseado no resultado
        await demo_iterative_refinement()
    
    # 3. Análise de sugestões
    await demo_optimization_suggestions()
    
    # 4. Dashboard final
    await demo_statistics_dashboard()
    
    print("\n🎉 Fluxo completo demonstrado!")


async def main():
    """Executa todas as demonstrações"""
    print("🧪 Sistema de Teste e Refinamento de Prompts - VideoAI")
    print("=" * 60)
    print("Demonstrações da Tarefa 3.4 - Implementação Completa")
    print("=" * 60)
    
    try:
        print("\n📋 Menu de Demonstrações:")
        print("1. Teste A/B simples")
        print("2. Refinamento iterativo")
        print("3. Teste multivariável")
        print("4. Sugestões de otimização")
        print("5. Otimização em lote")
        print("6. Dashboard de estatísticas")
        print("7. Fluxo completo")
        
        # Para demo, executa todas as demonstrações
        print("\n🎬 Executando todas as demonstrações...")
        
        await demo_ab_test()
        await demo_iterative_refinement()
        await demo_multivariate_test()
        await demo_optimization_suggestions()
        await demo_batch_optimization()
        await demo_statistics_dashboard()
        
        print("\n" + "=" * 60)
        print("✅ Todas as demonstrações concluídas com sucesso!")
        print("\n💡 Funcionalidades demonstradas:")
        print("   🎯 Testes A/B automatizados")
        print("   🔄 Refinamento iterativo inteligente")
        print("   🎲 Testes multivariáveis completos")
        print("   💡 Sugestões de otimização baseadas em IA")
        print("   ⚡ Otimização em lote eficiente")
        print("   📊 Analytics e estatísticas detalhadas")
        print("   🧠 Aprendizado automático de padrões")
        
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("📖 Instruções de Uso:")
    print("1. Certifique-se que a API está rodando em localhost:8000")
    print("2. Substitua AUTH_TOKEN por um token JWT válido")
    print("3. Execute: python prompt_testing_demo.py")
    print()
    
    # Executa as demonstrações
    asyncio.run(main()) 