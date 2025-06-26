#!/usr/bin/env python3
"""
Script de teste de performance para Celery
Executa diferentes cenários e mede métricas
"""

import time
import json
import statistics
from datetime import datetime
from typing import List, Dict
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tasks.simple_tasks import simple_add, simple_multiply, simple_hello
from app.tasks.ai_tasks import translate_text, analyze_content
from app.tasks.video_tasks import process_video
from app.tasks.maintenance_tasks import health_check_services


class PerformanceTest:
    def __init__(self):
        self.results = {
            "test_date": datetime.now().isoformat(),
            "tests": {},
            "summary": {}
        }
    
    def measure_task(self, task_func, args, task_name: str, iterations: int = 10) -> Dict:
        """Mede performance de uma tarefa específica"""
        print(f"\n🔍 Testando: {task_name}")
        print(f"   Iterações: {iterations}")
        
        execution_times = []
        success_count = 0
        failed_count = 0
        
        for i in range(iterations):
            start_time = time.time()
            try:
                # Envia a tarefa
                result = task_func.delay(*args)
                
                # Aguarda resultado com timeout
                task_result = result.get(timeout=30)
                
                end_time = time.time()
                execution_time = end_time - start_time
                execution_times.append(execution_time)
                success_count += 1
                
                print(f"   ✅ Iteração {i+1}: {execution_time:.3f}s")
                
            except Exception as e:
                failed_count += 1
                print(f"   ❌ Iteração {i+1}: Falhou - {str(e)}")
        
        # Calcular estatísticas
        if execution_times:
            stats = {
                "task_name": task_name,
                "iterations": iterations,
                "success_count": success_count,
                "failed_count": failed_count,
                "min_time": min(execution_times),
                "max_time": max(execution_times),
                "avg_time": statistics.mean(execution_times),
                "median_time": statistics.median(execution_times),
                "std_dev": statistics.stdev(execution_times) if len(execution_times) > 1 else 0,
                "success_rate": (success_count / iterations) * 100
            }
        else:
            stats = {
                "task_name": task_name,
                "iterations": iterations,
                "success_count": 0,
                "failed_count": iterations,
                "error": "Todas as execuções falharam"
            }
        
        return stats
    
    def test_simple_tasks(self):
        """Testa tarefas simples para baseline"""
        print("\n📊 TESTE 1: Tarefas Simples (Baseline)")
        print("=" * 50)
        
        tests = [
            (simple_add, (10, 20), "simple_add"),
            (simple_multiply, (5, 8), "simple_multiply"),
            (simple_hello, ("Performance Test",), "simple_hello")
        ]
        
        for task_func, args, name in tests:
            stats = self.measure_task(task_func, args, name, iterations=20)
            self.results["tests"][name] = stats
    
    def test_concurrent_tasks(self):
        """Testa execução concorrente"""
        print("\n📊 TESTE 2: Execução Concorrente")
        print("=" * 50)
        
        concurrent_counts = [10, 50, 100]
        
        for count in concurrent_counts:
            print(f"\n🚀 Enviando {count} tarefas simultaneamente...")
            start_time = time.time()
            
            # Enviar todas as tarefas
            tasks = []
            for i in range(count):
                task = simple_add.delay(i, i+1)
                tasks.append(task)
            
            # Aguardar todas completarem
            completed = 0
            failed = 0
            
            for task in tasks:
                try:
                    task.get(timeout=30)
                    completed += 1
                except Exception:
                    failed += 1
            
            end_time = time.time()
            total_time = end_time - start_time
            
            stats = {
                "concurrent_tasks": count,
                "completed": completed,
                "failed": failed,
                "total_time": total_time,
                "avg_time_per_task": total_time / count,
                "throughput": count / total_time  # tarefas por segundo
            }
            
            self.results["tests"][f"concurrent_{count}"] = stats
            print(f"   ✅ Completas: {completed}/{count}")
            print(f"   ⏱️  Tempo total: {total_time:.2f}s")
            print(f"   📈 Throughput: {stats['throughput']:.2f} tarefas/s")
    
    def test_queue_priorities(self):
        """Testa sistema de prioridades"""
        print("\n📊 TESTE 3: Prioridades de Filas")
        print("=" * 50)
        
        # Enviar tarefas para diferentes filas
        print("Enviando tarefas para filas com diferentes prioridades...")
        
        # Alta prioridade (AI)
        ai_task = analyze_content.delay("Test content for priority check")
        
        # Baixa prioridade (maintenance)
        maint_task = health_check_services.delay()
        
        # Medir qual completa primeiro
        start_time = time.time()
        
        ai_completed = False
        maint_completed = False
        
        while time.time() - start_time < 30:
            if not ai_completed and ai_task.ready():
                ai_time = time.time() - start_time
                ai_completed = True
                print(f"   🧠 AI task completou em: {ai_time:.2f}s")
            
            if not maint_completed and maint_task.ready():
                maint_time = time.time() - start_time
                maint_completed = True
                print(f"   🔧 Maintenance task completou em: {maint_time:.2f}s")
            
            if ai_completed and maint_completed:
                break
            
            time.sleep(0.1)
        
        self.results["tests"]["queue_priorities"] = {
            "ai_completed": ai_completed,
            "maintenance_completed": maint_completed,
            "priority_working": ai_completed and (not maint_completed or ai_time < maint_time)
        }
    
    def generate_report(self):
        """Gera relatório com recomendações"""
        print("\n📊 RELATÓRIO DE PERFORMANCE")
        print("=" * 50)
        
        # Análise de tarefas simples
        simple_tasks = ["simple_add", "simple_multiply", "simple_hello"]
        avg_times = []
        
        for task in simple_tasks:
            if task in self.results["tests"]:
                stats = self.results["tests"][task]
                if "avg_time" in stats:
                    avg_times.append(stats["avg_time"])
                    print(f"\n{task}:")
                    print(f"  Tempo médio: {stats['avg_time']:.3f}s")
                    print(f"  Taxa de sucesso: {stats.get('success_rate', 0):.1f}%")
        
        # Análise de concorrência
        print("\n\n🚀 Análise de Concorrência:")
        for key, stats in self.results["tests"].items():
            if key.startswith("concurrent_"):
                print(f"\n{stats['concurrent_tasks']} tarefas simultâneas:")
                print(f"  Throughput: {stats['throughput']:.2f} tarefas/s")
                print(f"  Tempo médio por tarefa: {stats['avg_time_per_task']:.3f}s")
        
        # Recomendações
        print("\n\n💡 RECOMENDAÇÕES DE OTIMIZAÇÃO:")
        print("=" * 50)
        
        recommendations = []
        
        # Baseado no tempo médio das tarefas simples
        if avg_times:
            overall_avg = statistics.mean(avg_times)
            if overall_avg > 1.0:
                recommendations.append("⚠️  Latência alta detectada. Considere:")
                recommendations.append("   - Aumentar recursos do Redis")
                recommendations.append("   - Verificar latência de rede")
            else:
                recommendations.append("✅ Latência está boa para tarefas simples")
        
        # Baseado no throughput
        if "concurrent_100" in self.results["tests"]:
            throughput = self.results["tests"]["concurrent_100"]["throughput"]
            if throughput < 10:
                recommendations.append("\n⚠️  Throughput baixo. Considere:")
                recommendations.append("   - Aumentar número de workers")
                recommendations.append("   - Aumentar concorrência por worker")
                recommendations.append("   - Otimizar prefetch_multiplier")
            else:
                recommendations.append(f"\n✅ Throughput adequado: {throughput:.2f} tarefas/s")
        
        # Imprimir recomendações
        for rec in recommendations:
            print(rec)
        
        # Salvar resultados
        self.save_results()
    
    def save_results(self):
        """Salva resultados em arquivo JSON"""
        filename = f"performance_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(os.path.dirname(__file__), filename)
        
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n\n📁 Resultados salvos em: {filename}")
    
    def run_all_tests(self):
        """Executa todos os testes"""
        print("🚀 INICIANDO TESTES DE PERFORMANCE CELERY")
        print("=" * 50)
        
        self.test_simple_tasks()
        self.test_concurrent_tasks()
        self.test_queue_priorities()
        self.generate_report()


if __name__ == "__main__":
    # Verificar se o Celery está acessível
    try:
        # Teste rápido
        result = simple_add.delay(1, 1)
        result.get(timeout=5)
        print("✅ Celery está funcionando!\n")
        
        # Executar testes
        tester = PerformanceTest()
        tester.run_all_tests()
        
    except Exception as e:
        print(f"❌ Erro ao conectar com Celery: {e}")
        print("\nCertifique-se de que:")
        print("1. O worker Celery está rodando")
        print("2. RabbitMQ e Redis estão acessíveis")
        print("3. As configurações estão corretas") 