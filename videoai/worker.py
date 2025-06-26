#!/usr/bin/env python3
"""
Worker para processar jobs de áudio de forma assíncrona
"""
import os
import sys
import time
import threading
import logging
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Adiciona o diretório atual ao path do Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.queue_service import QueueService
from api.redis_service import RedisService
from api.audio_processor import AudioProcessor

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Worker:
    def __init__(self):
        self.queue_service = QueueService()
        self.redis_service = RedisService()
        self.audio_processor = AudioProcessor()
        self.running = True
        
    def process_job(self, job_data):
        """Processa um job individual"""
        job_id = job_data.get('job_id')
        audio_url = job_data.get('audio_url')
        transcript = job_data.get('transcript')
        webhook_url = job_data.get('webhook_url')
        target_language = job_data.get('target_language', 'pt')
        
        logger.info(f"Processando job {job_id}: {audio_url} (target: {target_language})")
        
        try:
            # Atualizar status para processing
            self.redis_service.set_job_status(job_id, 'processing', progress=10)
            
            # Processar áudio
            result = self.audio_processor.process_audio(
                job_id=job_id,
                audio_url=audio_url,
                transcript=transcript,
                target_language=target_language,
                progress_callback=lambda p: self.redis_service.update_job_progress(job_id, p)
            )
            
            if result:
                # Sucesso
                self.redis_service.set_job_status(job_id, 'completed', progress=100, result=result)
                logger.info(f"Job {job_id} completado com sucesso")
                
                # Enviar webhook se configurado
                if webhook_url:
                    self.send_webhook(webhook_url, job_id, 'completed', result)
                    
            else:
                # Erro no processamento
                self.redis_service.set_job_status(job_id, 'error', progress=0, 
                                                error='Erro no processamento do áudio')
                logger.error(f"Erro ao processar job {job_id}")
                
        except Exception as e:
            logger.error(f"Erro inesperado ao processar job {job_id}: {str(e)}")
            self.redis_service.set_job_status(job_id, 'error', progress=0, 
                                            error=f'Erro inesperado: {str(e)}')
            
    def send_webhook(self, webhook_url, job_id, status, result=None):
        """Envia webhook de notificação"""
        try:
            import requests
            payload = {
                'job_id': job_id,
                'status': status,
                'timestamp': time.time()
            }
            if result:
                payload['result'] = result
                
            response = requests.post(webhook_url, json=payload, timeout=10)
            logger.info(f"Webhook enviado para {webhook_url}: {response.status_code}")
        except Exception as e:
            logger.error(f"Erro ao enviar webhook: {str(e)}")
            
    def run(self):
        """Loop principal do worker"""
        logger.info("🚀 Worker de áudio iniciado")
        
        # Conectar com retry
        if not self.queue_service.connect_with_retry():
            logger.error("❌ Não foi possível conectar ao RabbitMQ após múltiplas tentativas")
            return
        
        def consume_callback(ch, method, properties, body):
            try:
                import json
                job_data = json.loads(body)
                self.process_job(job_data)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                logger.error(f"Erro ao processar mensagem: {str(e)}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        
        # Configurar consumidor
        self.queue_service.setup_consumer(consume_callback)
        
        try:
            logger.info("⏳ Aguardando jobs...")
            self.queue_service.start_consuming()
        except KeyboardInterrupt:
            logger.info("🛑 Worker interrompido pelo usuário")
            self.stop()
        except Exception as e:
            logger.error(f"Erro no worker: {str(e)}")
        finally:
            self.cleanup()
            
    def stop(self):
        """Para o worker"""
        self.running = False
        self.queue_service.stop_consuming()
        
    def cleanup(self):
        """Limpa recursos"""
        try:
            self.queue_service.close()
            logger.info("✅ Worker finalizado")
        except Exception as e:
            logger.error(f"Erro na limpeza: {str(e)}")

def main():
    """Função principal"""
    worker = Worker()
    
    # Thread para manter o worker rodando
    worker_thread = threading.Thread(target=worker.run)
    worker_thread.daemon = True
    worker_thread.start()
    
    try:
        # Manter o processo principal vivo
        while worker.running:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Interrupção recebida, finalizando worker...")
        worker.stop()
        worker_thread.join(timeout=5)

if __name__ == '__main__':
    main() 