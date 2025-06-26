import pika
import json
import uuid
import os
import time
import traceback
from dotenv import load_dotenv

load_dotenv()

class QueueService:
    def __init__(self):
        # Configurações do RabbitMQ
        rabbitmq_url = os.getenv('RABBITMQ_URL', 'amqp://admin:admin123@rabbitmq:5672/')
        self.connection_params = pika.URLParameters(rabbitmq_url)
        self.connection = None
        self.channel = None
        self.queue_name = 'audio_processing'
        self.video_queue_name = 'video_processing'
        
        # Configurações de retry
        self.max_retries = 10
        self.initial_delay = 1
        self.max_delay = 60
        self.backoff_factor = 2
    
    def connect_with_retry(self):
        """Conecta ao RabbitMQ com retry e backoff exponencial"""
        delay = self.initial_delay
        
        for attempt in range(1, self.max_retries + 1):
            try:
                print(f"🔄 Tentativa {attempt}/{self.max_retries} de conexão com RabbitMQ...")
                
                self.connection = pika.BlockingConnection(self.connection_params)
                self.channel = self.connection.channel()
                
                # Declarar fila de áudio como durável (persiste reinicializações)
                self.channel.queue_declare(queue=self.queue_name, durable=True)
                
                # Declarar fila de vídeo como durável (persiste reinicializações)
                self.channel.queue_declare(queue=self.video_queue_name, durable=True)
                
                print(f"✅ Conectado ao RabbitMQ - filas: {self.queue_name}, {self.video_queue_name}")
                return True
                
            except Exception as e:
                print(f"❌ Tentativa {attempt} falhou: {e}")
                
                if attempt == self.max_retries:
                    print(f"🚨 Falha após {self.max_retries} tentativas. Não foi possível conectar ao RabbitMQ.")
                    return False
                
                print(f"⏳ Aguardando {delay} segundos antes da próxima tentativa...")
                time.sleep(delay)
                
                # Aumentar delay com backoff exponencial, limitado ao max_delay
                delay = min(delay * self.backoff_factor, self.max_delay)
        
        return False

    def connect(self):
        """Estabelece conexão com RabbitMQ (método legado, mantido para compatibilidade)"""
        try:
            self.connection = pika.BlockingConnection(self.connection_params)
            self.channel = self.connection.channel()
            
            # Declarar fila de áudio como durável (persiste reinicializações)
            self.channel.queue_declare(queue=self.queue_name, durable=True)
            
            # Declarar fila de vídeo como durável (persiste reinicializações)
            self.channel.queue_declare(queue=self.video_queue_name, durable=True)
            
            print(f"Conectado ao RabbitMQ - filas: {self.queue_name}, {self.video_queue_name}")
            return True
        except Exception as e:
            print(f"Erro ao conectar ao RabbitMQ: {e}")
            return False
    
    def publish_job(self, audio_url, transcript=None, webhook_url=None, priority=False, target_language='pt'):
        """Publica job na fila"""
        if not self.connection or self.connection.is_closed:
            if not self.connect():
                raise Exception("Não foi possível conectar ao RabbitMQ")
        
        job_id = str(uuid.uuid4())
        
        message = {
            'job_id': job_id,
            'audio_url': audio_url,
            'transcript': transcript,
            'webhook_url': webhook_url,
            'priority': priority,
            'target_language': target_language,
            'timestamp': time.time()
        }
        
        try:
            # Publicar mensagem com propriedades de persistência
            self.channel.basic_publish(
                exchange='',
                routing_key=self.queue_name,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Tornar mensagem persistente
                    priority=10 if priority else 1  # Prioridade alta para jobs prioritários
                )
            )
            
            print(f"Job {job_id} publicado na fila")
            return job_id
            
        except Exception as e:
            print(f"Erro ao publicar job: {e}")
            raise
    
    def close(self):
        """Fecha conexão"""
        try:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
        except Exception as e:
            print(f"Erro ao fechar conexão: {e}")
    
    def test_connection(self):
        """Testa conexão com RabbitMQ"""
        try:
            test_connection = pika.BlockingConnection(self.connection_params)
            test_connection.close()
            return True
        except Exception as e:
            print(f"Erro de conexão com RabbitMQ: {e}")
            return False
    
    def get_queue_info(self):
        """Retorna informações da fila"""
        if not self.connection or self.connection.is_closed:
            if not self.connect():
                return None
        
        try:
            method = self.channel.queue_declare(queue=self.queue_name, durable=True, passive=True)
            return {
                'queue': self.queue_name,
                'message_count': method.method.message_count,
                'consumer_count': method.method.consumer_count
            }
        except Exception as e:
            print(f"Erro ao obter info da fila: {e}")
            return None
    
    def setup_consumer(self, callback):
        """Configura o consumidor da fila"""
        if not self.connection or self.connection.is_closed:
            if not self.connect():
                raise Exception("Não foi possível conectar ao RabbitMQ")
        
        try:
            # Configurar QoS - processar uma mensagem por vez
            self.channel.basic_qos(prefetch_count=1)
            
            # Configurar consumidor
            self.channel.basic_consume(
                queue=self.queue_name,
                on_message_callback=callback,
                auto_ack=False  # Acknowledgment manual
            )
            
            print(f"Consumidor configurado para fila: {self.queue_name}")
            
        except Exception as e:
            print(f"Erro ao configurar consumidor: {e}")
            raise
    
    def start_consuming(self):
        """Inicia o consumo de mensagens"""
        if not self.channel:
            raise Exception("Canal não configurado. Execute setup_consumer() primeiro.")
        
        try:
            print("Iniciando consumo de mensagens...")
            self.channel.start_consuming()
        except Exception as e:
            print(f"Erro ao iniciar consumo: {e}")
            raise
    
    def stop_consuming(self):
        """Para o consumo de mensagens"""
        if self.channel:
            try:
                self.channel.stop_consuming()
                print("Consumo de mensagens parado")
            except Exception as e:
                print(f"Erro ao parar consumo: {e}")

    # ===== MÉTODOS PARA PROCESSAMENTO DE VÍDEO =====
    
    def publish_video_job(self, video_job_data):
        """Publica job de vídeo na fila"""
        if not self.connection or self.connection.is_closed:
            if not self.connect():
                raise Exception("Não foi possível conectar ao RabbitMQ")
        
        try:
            # Publicar mensagem com propriedades de persistência
            self.channel.basic_publish(
                exchange='',
                routing_key=self.video_queue_name,
                body=json.dumps(video_job_data),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Tornar mensagem persistente
                    priority=10 if video_job_data.get('priority', False) else 1
                )
            )
            
            print(f"Job de vídeo {video_job_data['job_id']} publicado na fila")
            return video_job_data['job_id']
            
        except Exception as e:
            print(f"Erro ao publicar job de vídeo: {e}")
            raise
    
    def get_video_queue_info(self):
        """Retorna informações da fila de vídeo"""
        if not self.connection or self.connection.is_closed:
            if not self.connect():
                return None
        
        try:
            method = self.channel.queue_declare(queue=self.video_queue_name, durable=True, passive=True)
            return {
                'queue': self.video_queue_name,
                'message_count': method.method.message_count,
                'consumer_count': method.method.consumer_count
            }
        except Exception as e:
            print(f"Erro ao obter info da fila de vídeo: {e}")
            return None
    
    def setup_video_consumer(self, callback):
        """Configura o consumidor da fila de vídeo"""
        if not self.connection or self.connection.is_closed:
            if not self.connect():
                raise Exception("Não foi possível conectar ao RabbitMQ")
        
        try:
            # Configurar QoS - processar uma mensagem por vez
            self.channel.basic_qos(prefetch_count=1)
            
            # Configurar consumidor
            self.channel.basic_consume(
                queue=self.video_queue_name,
                on_message_callback=callback,
                auto_ack=False  # Acknowledgment manual
            )
            
            print(f"Consumidor configurado para fila de vídeo: {self.video_queue_name}")
            
        except Exception as e:
            print(f"Erro ao configurar consumidor de vídeo: {e}")
            raise

    # ===== MÉTODOS PARA PROCESSAMENTO DE TAKES =====
    
    def publish_takes_job(self, takes_job_data):
        """Publica job de takes na fila"""
        if not self.connection or self.connection.is_closed:
            if not self.connect():
                raise Exception("Não foi possível conectar ao RabbitMQ")
        
        try:
            # Usar a mesma fila de vídeo para takes (extensão do processamento de vídeo)
            self.channel.basic_publish(
                exchange='',
                routing_key=self.video_queue_name,
                body=json.dumps(takes_job_data),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Tornar mensagem persistente
                    priority=10 if takes_job_data.get('priority', False) else 1
                )
            )
            
            print(f"Job de takes {takes_job_data['job_id']} publicado na fila")
            return takes_job_data['job_id']
            
        except Exception as e:
            print(f"Erro ao publicar job de takes: {e}")
            raise

    # ===== MÉTODOS PARA CORTE E JUNÇÃO DE VÍDEOS =====
    
    def publish_trim_join_job(self, job_data):
        """Publica job de corte e junção de vídeos na fila"""
        if not self.connection or self.connection.is_closed:
            if not self.connect():
                raise Exception("Não foi possível conectar ao RabbitMQ")
        
        try:
            # Usar a mesma fila de vídeo para corte e junção
            self.channel.basic_publish(
                exchange='',
                routing_key=self.video_queue_name,
                body=json.dumps(job_data),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Tornar mensagem persistente
                    priority=10 if job_data.get('priority', False) else 1
                )
            )
            
            print(f"Job de corte e junção {job_data['job_id']} publicado na fila")
            return job_data['job_id']
            
        except Exception as e:
            print(f"Erro ao publicar job de corte e junção: {e}")
            raise 