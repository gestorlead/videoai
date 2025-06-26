#!/usr/bin/env python3
"""
Script de teste para o endpoint de corte e junção de vídeos
"""
import requests
import time
import json

# Configurações
API_BASE_URL = "http://localhost:5000/api/v1"
API_KEY = "ak_eZM2SRS6eHHQ37Gl6qPnJkKzoWu29FuJ"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

def test_trim_join_endpoint():
    """Testa o endpoint de corte e junção"""
    print("🎬 Testando endpoint de corte e junção de vídeos")
    print("=" * 50)
    
    # Dados de teste (exemplo do usuário)
    test_data = [
        {
            "processed_takes": [
                {
                    "take_number": 1,
                    "video_url": "https://replicate.delivery/xezq/skbol2idXcJXGFC0MipotCAPzVWfek3TYJf2EoeWwlY9zroTB/tmpy6vr0lmx.mp4",
                    "final_clip_duration": 4.484
                },
                {
                    "take_number": 2,
                    "video_url": "https://replicate.delivery/xezq/tS18Rl6j2jIRLts2OfV2cPXQUWl6zi2VQf9meGcZH1Mp5V0pA/tmpv6t_1iwb.mp4",
                    "final_clip_duration": 4.728
                },
                {
                    "take_number": 3,
                    "video_url": "https://replicate.delivery/xezq/VAZWB5rdMqZAOhVJ4XVNhgkXBeeqNoWSEmKGLWpfGpVG6V0pA/tmpqtu2v2ro.mp4",
                    "final_clip_duration": 5
                }
            ]
        }
    ]
    
    # 1. Enviar requisição para processamento
    print("📤 Enviando requisição para corte e junção...")
    response = requests.post(
        f"{API_BASE_URL}/video/trim-join",
        headers=headers,
        json=test_data
    )
    
    if response.status_code != 202:
        print(f"❌ Erro ao enviar requisição: {response.status_code}")
        print(f"Resposta: {response.text}")
        return False
    
    result = response.json()
    job_id = result.get('job_id')
    
    print(f"✅ Job criado com sucesso!")
    print(f"📝 Job ID: {job_id}")
    print(f"📊 Status: {result.get('status')}")
    print(f"📈 Takes: {result.get('takes_count')}")
    print(f"⏱️  Tempo estimado: {result.get('estimated_time')}")
    print()
    
    # 2. Monitorar progresso
    print("📊 Monitorando progresso...")
    max_attempts = 30  # 5 minutos máximo
    
    for attempt in range(max_attempts):
        time.sleep(10)  # Aguardar 10 segundos entre verificações
        
        # Verificar status
        status_response = requests.get(
            f"{API_BASE_URL}/video/trim-join/status/{job_id}",
            headers=headers
        )
        
        if status_response.status_code != 200:
            print(f"❌ Erro ao verificar status: {status_response.status_code}")
            continue
        
        status_data = status_response.json()
        status = status_data.get('status')
        progress = status_data.get('progress', 0)
        
        print(f"   📈 Status: {status} | Progresso: {progress}%")
        
        if status == 'completed':
            print("\n🎉 Processamento concluído!")
            print(f"📥 URL de download: {status_data.get('result', {}).get('download_urls', {}).get('public_url')}")
            
            # 3. Testar download público
            public_url = f"{API_BASE_URL}/public/video/{job_id}"
            print(f"🔗 URL pública: {public_url}")
            
            download_response = requests.head(public_url)
            if download_response.status_code == 200:
                print("✅ Download público funciona!")
            else:
                print(f"❌ Erro no download público: {download_response.status_code}")
            
            return True
            
        elif status == 'error':
            error_msg = status_data.get('error', 'Erro desconhecido')
            print(f"\n❌ Erro no processamento: {error_msg}")
            return False
    
    print("\n⏰ Timeout - processamento demorou mais que o esperado")
    return False

def test_validation():
    """Testa validações do endpoint"""
    print("\n🔍 Testando validações...")
    print("=" * 30)
    
    # Teste 1: Array vazio
    print("📝 Teste 1: Array vazio")
    response = requests.post(
        f"{API_BASE_URL}/video/trim-join",
        headers=headers,
        json=[]
    )
    print(f"   Status: {response.status_code} (esperado: 400)")
    
    # Teste 2: Campo obrigatório ausente
    print("📝 Teste 2: Campo obrigatório ausente")
    invalid_data = [
        {
            "processed_takes": [
                {
                    "take_number": 1,
                    "video_url": "https://example.com/video.mp4"
                    # Faltando final_clip_duration
                }
            ]
        }
    ]
    response = requests.post(
        f"{API_BASE_URL}/video/trim-join",
        headers=headers,
        json=invalid_data
    )
    print(f"   Status: {response.status_code} (esperado: 400)")
    
    # Teste 3: URL inválida
    print("📝 Teste 3: URL inválida")
    invalid_data = [
        {
            "processed_takes": [
                {
                    "take_number": 1,
                    "video_url": "not-a-url",
                    "final_clip_duration": 5.0
                }
            ]
        }
    ]
    response = requests.post(
        f"{API_BASE_URL}/video/trim-join",
        headers=headers,
        json=invalid_data
    )
    print(f"   Status: {response.status_code} (esperado: 400)")

def main():
    """Função principal"""
    print("🚀 Iniciando testes do endpoint de corte e junção")
    print()
    
    # Primeiro testar validações
    test_validation()
    
    # Depois testar processamento real
    print("\n" + "="*60)
    success = test_trim_join_endpoint()
    
    print("\n" + "="*60)
    if success:
        print("🎉 TODOS OS TESTES PASSARAM!")
    else:
        print("❌ ALGUNS TESTES FALHARAM")

if __name__ == "__main__":
    main() 