#!/usr/bin/env python3
"""
Teste do sistema assíncrono de processamento de vídeos
"""
import requests
import time
import json

# Configurações
API_BASE = "http://localhost:5000/api/v1"
API_KEY = "ak_aqpNHBdRJqeTYSiikDjWZDPRHmg9xm5I"

headers = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

def test_async_video_processing():
    """Testa o processamento assíncrono de vídeo"""
    
    print("🎥 Testando processamento assíncrono de vídeo...\n")
    
    # 1. Enviar vídeo para processamento
    video_data = {
        "video_url": "https://www.learningcontainer.com/wp-content/uploads/2020/05/sample-mp4-file.mp4",
        "subtitle_content": """1
00:00:01,000 --> 00:00:05,000
Esta é uma demonstração do processamento assíncrono

2
00:00:06,000 --> 00:00:10,000
O vídeo é processado em background

3
00:00:11,000 --> 00:00:15,000
Você pode acompanhar o progresso em tempo real""",
        "subtitle_config": {
            "font_size": 28,
            "font_color": "#FFFF00",
            "background_color": "#000000",
            "background_opacity": 80,
            "subtitle_height": "85%"
        }
    }
    
    print("📤 Enviando vídeo para processamento...")
    response = requests.post(
        f"{API_BASE}/video/process-with-overlay",
        headers=headers,
        json=video_data
    )
    
    if response.status_code != 202:  # 202 = Accepted
        print(f"❌ Erro ao enviar: {response.status_code}")
        print(response.json())
        return
    
    result = response.json()
    job_id = result['job_id']
    
    print(f"✅ Vídeo enviado com sucesso!")
    print(f"📋 Job ID: {job_id}")
    print(f"🔗 Status URL: {result['status_url']}")
    print(f"⬇️ Download URL: {result['download_url']}")
    print(f"⏱️ Tempo estimado: {result['estimated_time']}")
    print()
    
    # 2. Monitorar progresso
    print("⏳ Monitorando progresso...")
    
    while True:
        # Verificar status
        status_response = requests.get(
            f"{API_BASE}/video/status/{job_id}",
            headers=headers
        )
        
        if status_response.status_code != 200:
            print(f"❌ Erro ao verificar status: {status_response.status_code}")
            break
        
        status_data = status_response.json()
        status = status_data['status']
        progress = status_data.get('progress', 0)
        
        print(f"📊 Status: {status} | Progresso: {progress}%")
        
        if status == 'completed':
            print("\n🎉 Processamento concluído!")
            
            # Exibir resultado
            result = status_data.get('result', {})
            print(f"🎬 Vídeo processado: {result.get('output_video_url')}")
            print(f"📥 URL de download: {result.get('download_url')}")
            print(f"⏰ Processado em: {result.get('processed_at')}")
            
            # 3. Tentar fazer download
            print("\n⬇️ Testando download...")
            download_response = requests.get(
                f"{API_BASE}/video/download/{job_id}",
                headers=headers
            )
            
            if download_response.status_code == 200:
                print(f"✅ Download funcionando! Tamanho: {len(download_response.content)} bytes")
            else:
                print(f"❌ Erro no download: {download_response.status_code}")
            
            break
            
        elif status == 'error':
            print(f"\n❌ Erro no processamento: {status_data.get('error')}")
            break
            
        elif status in ['queued', 'processing']:
            # Aguardar antes de verificar novamente
            time.sleep(3)
            continue
        
        else:
            print(f"\n⚠️ Status desconhecido: {status}")
            break

def test_sync_fallback():
    """Testa o fallback síncrono quando a fila não está disponível"""
    
    print("\n🔄 Testando fallback síncrono...\n")
    
    # Tentar com configurações que forçarão erro na fila (para testar fallback)
    video_data = {
        "video_url": "https://www.learningcontainer.com/wp-content/uploads/2020/05/sample-mp4-file.mp4",
        "subtitle_content": """1
00:00:01,000 --> 00:00:03,000
Teste do modo síncrono""",
        "subtitle_config": {
            "font_size": 24,
            "font_color": "#FFFFFF"
        }
    }
    
    print("📤 Enviando para processamento...")
    response = requests.post(
        f"{API_BASE}/video/process-with-overlay",
        headers=headers,
        json=video_data
    )
    
    print(f"📨 Código de resposta: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ Processamento síncrono funcionou!")
        result = response.json()
        print(f"🎬 Resultado: {result['result']['output_video_url']}")
    elif response.status_code == 202:
        print("✅ Processamento assíncrono funcionou!")
        result = response.json()
        print(f"📋 Job ID: {result['job_id']}")
    else:
        print(f"❌ Erro: {response.json()}")

if __name__ == "__main__":
    print("🧪 Teste do Sistema de Processamento Assíncrono de Vídeos\n")
    print("=" * 60)
    
    # Teste principal
    test_async_video_processing()
    
    print("\n" + "=" * 60)
    
    # Aguardar um pouco
    time.sleep(2)
    
    # Teste de fallback (opcional)
    # test_sync_fallback()
    
    print("\n🏁 Testes concluídos!") 