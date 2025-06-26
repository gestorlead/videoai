#!/usr/bin/env python3
"""
Worker para processar jobs de vídeo de forma assíncrona
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
from api.video_processor import VideoProcessor

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VideoWorker:
    def __init__(self):
        self.queue_service = QueueService()
        self.redis_service = RedisService()
        self.video_processor = VideoProcessor()
        self.running = True
        
    def process_video_job(self, job_data):
        """Processa um job de vídeo individual"""
        job_id = job_data.get('job_id')
        job_type = job_data.get('job_type', 'video_processing')
        
        logger.info(f"Processando job {job_type} {job_id}")
        
        try:
            if job_type == 'video_trim_join':
                # Processar job de corte e junção
                self._process_trim_join_job(job_data)
            elif job_type == 'video_takes_processing':
                # Processar job de takes
                self._process_takes_job(job_data)
            else:
                # Processar job de vídeo tradicional (overlay)
                self._process_overlay_job(job_data)
                
        except Exception as e:
            logger.error(f"Erro inesperado ao processar job {job_type} {job_id}: {str(e)}")
            if job_type == 'video_trim_join':
                self.redis_service.set_trim_join_job_status(job_id, 'error', progress=0, error=f'Erro inesperado: {str(e)}')
            elif job_type == 'video_takes_processing':
                self.redis_service.set_takes_job_status(job_id, 'error', progress=0, error=f'Erro inesperado: {str(e)}')
            else:
                self.redis_service.set_video_job_status(job_id, 'error', progress=0, error=f'Erro inesperado: {str(e)}')
    
    def _process_overlay_job(self, job_data):
        """Processa job de vídeo com overlay (comportamento original)"""
        job_id = job_data.get('job_id')
        video_url = job_data.get('video_url')
        language = job_data.get('language')
        caption_id = job_data.get('caption_id')
        subtitle_content = job_data.get('subtitle_content')
        logo_url = job_data.get('logo_url')
        subtitle_config = job_data.get('subtitle_config')
        
        logger.info(f"Processando job de vídeo overlay {job_id}: {video_url}")
        
        try:
            # Atualizar status para processing
            self.redis_service.set_video_job_status(job_id, 'processing', progress=10)
            
            # Processar vídeo
            result = self.video_processor.process_video_with_overlay(
                video_url=video_url,
                language=language,
                caption_id=caption_id,
                subtitle_content=subtitle_content,
                logo_url=logo_url,
                subtitle_config=subtitle_config
            )
            
            if result:
                # Sucesso
                self.redis_service.set_video_job_status(job_id, 'completed', progress=100, result=result)
                logger.info(f"Job de vídeo overlay {job_id} completado com sucesso")
                    
            else:
                # Erro no processamento
                self.redis_service.set_video_job_status(job_id, 'error', progress=0, 
                                                       error='Erro no processamento do vídeo')
                logger.error(f"Erro ao processar job de vídeo overlay {job_id}")
                
        except Exception as e:
            logger.error(f"Erro ao processar job de vídeo overlay {job_id}: {str(e)}")
            self.redis_service.set_video_job_status(job_id, 'error', progress=0, 
                                                   error=f'Erro no processamento: {str(e)}')
    
    def _process_trim_join_job(self, job_data):
        """Processa job de corte e junção de vídeos"""
        job_id = job_data.get('job_id')
        takes = job_data.get('takes', [])
        
        logger.info(f"Processando job de corte e junção {job_id}: {len(takes)} takes")
        
        try:
            # Atualizar status para processing
            self.redis_service.set_trim_join_job_status(job_id, 'processing', progress=5)
            
            # Processar vídeos (cortar e juntar)
            result = self.video_processor.trim_and_join_videos(job_id, takes)
            
            if result:
                # Sucesso
                self.redis_service.set_trim_join_job_status(job_id, 'completed', progress=100, result=result)
                logger.info(f"Job de corte e junção {job_id} completado com sucesso")
                    
            else:
                # Erro no processamento
                self.redis_service.set_trim_join_job_status(job_id, 'error', progress=0, 
                                                          error='Erro no processamento de corte e junção')
                logger.error(f"Erro ao processar job de corte e junção {job_id}")
                
        except Exception as e:
            logger.error(f"Erro ao processar job de corte e junção {job_id}: {str(e)}")
            self.redis_service.set_trim_join_job_status(job_id, 'error', progress=0, 
                                                       error=f'Erro no processamento: {str(e)}')
    
    def _process_takes_job(self, job_data):
        """Processa job de takes de vídeo"""
        job_id = job_data.get('job_id')
        takes_data = job_data.get('takes_data', [])
        
        logger.info(f"Processando job de takes {job_id}: {len(takes_data)} takes")
        
        try:
            # Atualizar status para processing
            self.redis_service.set_takes_job_status(job_id, 'processing', progress=5)
            
            # Processar takes
            result = self.video_processor.process_video_takes(job_id, takes_data)
            
            if result:
                # Sucesso
                self.redis_service.set_takes_job_status(job_id, 'completed', progress=100, result=result)
                logger.info(f"Job de takes {job_id} completado com sucesso")
                    
            else:
                # Erro no processamento
                self.redis_service.set_takes_job_status(job_id, 'error', progress=0, 
                                                       error='Erro no processamento de takes')
                logger.error(f"Erro ao processar job de takes {job_id}")
                
        except Exception as e:
            logger.error(f"Erro ao processar job de takes {job_id}: {str(e)}")
            self.redis_service.set_takes_job_status(job_id, 'error', progress=0, 
                                                   error=f'Erro no processamento: {str(e)}')
            
    def run(self):
        """Loop principal do worker de vídeo"""
        logger.info("🎥 Worker de vídeo iniciado")
        
        # Conectar com retry
        if not self.queue_service.connect_with_retry():
            logger.error("❌ Não foi possível conectar ao RabbitMQ após múltiplas tentativas")
            return
        
        def consume_video_callback(ch, method, properties, body):
            try:
                import json
                job_data = json.loads(body)
                self.process_video_job(job_data)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                logger.error(f"Erro ao processar mensagem de vídeo: {str(e)}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        
        # Configurar consumidor de vídeo
        self.queue_service.setup_video_consumer(consume_video_callback)
        
        try:
            logger.info("⏳ Aguardando jobs de vídeo...")
            self.queue_service.start_consuming()
        except KeyboardInterrupt:
            logger.info("🛑 Worker de vídeo interrompido pelo usuário")
            self.stop()
        except Exception as e:
            logger.error(f"Erro no worker de vídeo: {str(e)}")
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
            logger.info("✅ Worker de vídeo finalizado")
        except Exception as e:
            logger.error(f"Erro na limpeza: {str(e)}")

def main():
    """Função principal"""
    worker = VideoWorker()
    
    # Thread para manter o worker rodando
    worker_thread = threading.Thread(target=worker.run)
    worker_thread.daemon = True
    worker_thread.start()
    
    try:
        # Manter o processo principal vivo
        while worker.running:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Interrupção recebida, finalizando worker de vídeo...")
        worker.stop()
        worker_thread.join(timeout=5)

if __name__ == '__main__':
    main() 