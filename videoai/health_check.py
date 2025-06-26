#!/usr/bin/env python3
"""
Script de verificação de saúde dos workers e serviços
"""
import requests
import time
import sys
from api.redis_service import RedisService
from api.queue_service import QueueService

def check_redis():
    """Verifica se o Redis está funcionando"""
    try:
        redis_service = RedisService()
        if redis_service.test_connection():
            print("✅ Redis: Conectado")
            return True
        else:
            print("❌ Redis: Falha na conexão")
            return False
    except Exception as e:
        print(f"❌ Redis: Erro - {e}")
        return False

def check_rabbitmq():
    """Verifica se o RabbitMQ está funcionando"""
    try:
        queue_service = QueueService()
        if queue_service.test_connection():
            print("✅ RabbitMQ: Conectado")
            
            # Verificar filas
            audio_info = queue_service.get_queue_info()
            video_info = queue_service.get_video_queue_info()
            
            if audio_info:
                print(f"   📋 Fila de áudio: {audio_info['message_count']} mensagens")
            if video_info:
                print(f"   📋 Fila de vídeo: {video_info['message_count']} mensagens")
            
            queue_service.close()
            return True
        else:
            print("❌ RabbitMQ: Falha na conexão")
            return False
    except Exception as e:
        print(f"❌ RabbitMQ: Erro - {e}")
        return False

def check_api():
    """Verifica se a API está funcionando"""
    try:
        response = requests.get("http://localhost:5000/api/v1/health", timeout=5)
        if response.status_code == 200:
            print("✅ API: Funcionando")
            return True
        else:
            print(f"❌ API: Status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API: Erro - {e}")
        return False

def check_queue_endpoints():
    """Verifica se os endpoints de fila estão funcionando"""
    try:
        response = requests.get("http://localhost:5000/api/v1/audio/queue/info", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ Endpoints de fila: Funcionando")
            print(f"   📊 Total de jobs pendentes: {data.get('total_pending', 0)}")
            return True
        else:
            print(f"❌ Endpoints de fila: Status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Endpoints de fila: Erro - {e}")
        return False

def main():
    """Função principal de verificação"""
    print("🔍 Verificando saúde dos serviços...\n")
    
    checks = [
        ("Redis", check_redis),
        ("RabbitMQ", check_rabbitmq),
        ("API", check_api),
        ("Queue Endpoints", check_queue_endpoints)
    ]
    
    all_healthy = True
    
    for name, check_func in checks:
        try:
            if not check_func():
                all_healthy = False
        except Exception as e:
            print(f"❌ {name}: Erro inesperado - {e}")
            all_healthy = False
        print()
    
    if all_healthy:
        print("🎉 Todos os serviços estão funcionando!")
        sys.exit(0)
    else:
        print("⚠️ Alguns serviços apresentam problemas.")
        sys.exit(1)

if __name__ == "__main__":
    main() 