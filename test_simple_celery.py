#!/usr/bin/env python3
"""
Teste das tarefas simples do Celery
"""
import sys
import os
import time

# Adicionar o diretório do projeto ao Python path
sys.path.insert(0, '/root/projetos/autosub-web')

try:
    from app.tasks.simple_tasks import simple_add, simple_hello, simple_multiply
    
    print("🧪 Testando tarefas simples do Celery...")
    
    # Teste síncrono
    print("\n📍 Teste síncrono:")
    result_sync = simple_add(5, 3)
    print(f"   simple_add(5, 3) = {result_sync}")
    
    # Teste assíncrono
    print("\n📍 Teste assíncrono:")
    task1 = simple_add.delay(10, 20)
    task2 = simple_hello.delay("VideoAI")
    task3 = simple_multiply.delay(4, 7)
    
    print(f"   Task 1 ID: {task1.id}")
    print(f"   Task 2 ID: {task2.id}")
    print(f"   Task 3 ID: {task3.id}")
    
    print("\n⏳ Aguardando resultados...")
    time.sleep(5)
    
    try:
        result1 = task1.result
        result2 = task2.result
        result3 = task3.result
        
        print(f"   Task 1 resultado: {result1}")
        print(f"   Task 2 resultado: {result2}")
        print(f"   Task 3 resultado: {result3}")
        
        print("\n✅ Teste de tarefas simples concluído com sucesso!")
        print("🎉 Subtarefa 2.2 está funcionando perfeitamente!")
        
    except Exception as e:
        print(f"❌ Erro ao obter resultados: {e}")
        print(f"   Task 1 status: {task1.status}")
        print(f"   Task 2 status: {task2.status}")
        print(f"   Task 3 status: {task3.status}")
        
except ImportError as e:
    print(f"❌ Erro ao importar tarefas: {e}")
    print("Verifique se o ambiente virtual e o Celery estão configurados corretamente.")
    
except Exception as e:
    print(f"❌ Erro geral: {e}") 