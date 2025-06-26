import redis
import json
import os
from datetime import datetime

class RedisService:
    def __init__(self):
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
        
        # Extrair host e porta da URL se necessário
        if redis_url.startswith('redis://'):
            # Parse simples da URL redis://host:port/db
            url_parts = redis_url.replace('redis://', '').split(':')
            host = url_parts[0]
            if len(url_parts) > 1:
                port_db = url_parts[1].split('/')
                port = int(port_db[0])
            else:
                port = 6379
        else:
            host = 'localhost'
            port = 6379
            
        self.redis = redis.Redis(
            host=host, 
            port=port, 
            db=0, 
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
    
    def set_job_status(self, job_id, status, progress=0, result=None, error=None):
        """Atualiza status do job no Redis"""
        data = {
            'job_id': job_id,
            'status': status,
            'progress': progress,
            'updated_at': datetime.now().isoformat()
        }
        
        if result:
            data['result'] = result
        if error:
            data['error'] = error
        
        try:
            # Expira em 7 dias (604800 segundos)
            self.redis.setex(f"job:{job_id}", 604800, json.dumps(data))
            print(f"Redis: Job {job_id} status updated to {status}")
        except Exception as e:
            print(f"Erro ao atualizar status no Redis: {e}")
    
    def update_job_progress(self, job_id, progress):
        """Atualiza apenas o progresso do job"""
        try:
            # Buscar dados existentes
            existing_data = self.get_job_status(job_id)
            if existing_data:
                existing_data['progress'] = progress
                existing_data['updated_at'] = datetime.now().isoformat()
                
                # Atualizar com novos dados
                self.redis.setex(f"job:{job_id}", 604800, json.dumps(existing_data))
                print(f"Redis: Job {job_id} progress updated to {progress}%")
            else:
                # Se não existe, criar com status processing
                self.set_job_status(job_id, 'processing', progress)
        except Exception as e:
            print(f"Erro ao atualizar progresso no Redis: {e}")
    
    def get_job_status(self, job_id):
        """Recupera status do job"""
        try:
            data = self.redis.get(f"job:{job_id}")
            return json.loads(data) if data else None
        except Exception as e:
            print(f"Erro ao buscar status no Redis: {e}")
            return None
    
    def delete_job(self, job_id):
        """Remove job do Redis"""
        try:
            self.redis.delete(f"job:{job_id}")
        except Exception as e:
            print(f"Erro ao deletar job do Redis: {e}")
    
    def test_connection(self):
        """Testa conexão com Redis"""
        try:
            self.redis.ping()
            return True
        except Exception as e:
            print(f"Erro de conexão com Redis: {e}")
            return False

    # ===== MÉTODOS PARA JOBS DE VÍDEO =====
    
    def set_video_job_status(self, job_id, status, progress=0, result=None, error=None):
        """Atualiza status do job de vídeo no Redis"""
        data = {
            'job_id': job_id,
            'job_type': 'video_processing',
            'status': status,
            'progress': progress,
            'updated_at': datetime.now().isoformat()
        }
        
        if result:
            data['result'] = result
        if error:
            data['error'] = error
        
        try:
            # Expira em 7 dias (604800 segundos)
            self.redis.setex(f"video_job:{job_id}", 604800, json.dumps(data))
            print(f"Redis: Job de vídeo {job_id} status updated to {status}")
        except Exception as e:
            print(f"Erro ao atualizar status do job de vídeo no Redis: {e}")
    
    def update_video_job_progress(self, job_id, progress):
        """Atualiza apenas o progresso do job de vídeo"""
        try:
            # Buscar dados existentes
            existing_data = self.get_video_job_status(job_id)
            if existing_data:
                existing_data['progress'] = progress
                existing_data['updated_at'] = datetime.now().isoformat()
                
                # Atualizar com novos dados
                self.redis.setex(f"video_job:{job_id}", 604800, json.dumps(existing_data))
                print(f"Redis: Job de vídeo {job_id} progress updated to {progress}%")
            else:
                # Se não existe, criar com status processing
                self.set_video_job_status(job_id, 'processing', progress)
        except Exception as e:
            print(f"Erro ao atualizar progresso do job de vídeo no Redis: {e}")
    
    def get_video_job_status(self, job_id):
        """Recupera status do job de vídeo"""
        try:
            data = self.redis.get(f"video_job:{job_id}")
            return json.loads(data) if data else None
        except Exception as e:
            print(f"Erro ao buscar status do job de vídeo no Redis: {e}")
            return None
    
    def delete_video_job(self, job_id):
        """Remove job de vídeo do Redis"""
        try:
            self.redis.delete(f"video_job:{job_id}")
        except Exception as e:
            print(f"Erro ao deletar job de vídeo do Redis: {e}")

    # ===== MÉTODOS PARA JOBS DE TAKES =====
    
    def set_takes_job_status(self, job_id, status, progress=0, result=None, error=None):
        """Atualiza status do job de takes no Redis"""
        data = {
            'job_id': job_id,
            'job_type': 'video_takes_processing',
            'status': status,
            'progress': progress,
            'updated_at': datetime.now().isoformat()
        }
        
        if result:
            data['result'] = result
        if error:
            data['error'] = error
        
        try:
            # Expira em 7 dias (604800 segundos)
            self.redis.setex(f"takes_job:{job_id}", 604800, json.dumps(data))
            print(f"Redis: Job de takes {job_id} status updated to {status}")
        except Exception as e:
            print(f"Erro ao atualizar status do job de takes no Redis: {e}")
    
    def update_takes_job_progress(self, job_id, progress):
        """Atualiza apenas o progresso do job de takes"""
        try:
            # Buscar dados existentes
            existing_data = self.get_takes_job_status(job_id)
            if existing_data:
                existing_data['progress'] = progress
                existing_data['updated_at'] = datetime.now().isoformat()
                
                # Atualizar com novos dados
                self.redis.setex(f"takes_job:{job_id}", 604800, json.dumps(existing_data))
                print(f"Redis: Job de takes {job_id} progress updated to {progress}%")
            else:
                # Se não existe, criar com status processing
                self.set_takes_job_status(job_id, 'processing', progress)
        except Exception as e:
            print(f"Erro ao atualizar progresso do job de takes no Redis: {e}")
    
    def get_takes_job_status(self, job_id):
        """Recupera status do job de takes"""
        try:
            data = self.redis.get(f"takes_job:{job_id}")
            return json.loads(data) if data else None
        except Exception as e:
            print(f"Erro ao buscar status do job de takes no Redis: {e}")
            return None
    
    def delete_takes_job(self, job_id):
        """Remove job de takes do Redis"""
        try:
            self.redis.delete(f"takes_job:{job_id}")
        except Exception as e:
            print(f"Erro ao deletar job de takes do Redis: {e}")

    # ===== MÉTODOS PARA JOBS DE CORTE E JUNÇÃO =====
    
    def set_trim_join_job_status(self, job_id, status, progress=0, result=None, error=None):
        """Atualiza status do job de corte e junção no Redis"""
        data = {
            'job_id': job_id,
            'job_type': 'video_trim_join',
            'status': status,
            'progress': progress,
            'updated_at': datetime.now().isoformat()
        }
        
        if result:
            data['result'] = result
        if error:
            data['error'] = error
        
        try:
            # Expira em 7 dias (604800 segundos)
            self.redis.setex(f"trim_join_job:{job_id}", 604800, json.dumps(data))
            print(f"Redis: Job de corte e junção {job_id} status updated to {status}")
        except Exception as e:
            print(f"Erro ao atualizar status do job de corte e junção no Redis: {e}")
    
    def update_trim_join_job_progress(self, job_id, progress):
        """Atualiza apenas o progresso do job de corte e junção"""
        try:
            # Buscar dados existentes
            existing_data = self.get_trim_join_job_status(job_id)
            if existing_data:
                existing_data['progress'] = progress
                existing_data['updated_at'] = datetime.now().isoformat()
                
                # Atualizar com novos dados
                self.redis.setex(f"trim_join_job:{job_id}", 604800, json.dumps(existing_data))
                print(f"Redis: Job de corte e junção {job_id} progress updated to {progress}%")
            else:
                # Se não existe, criar com status processing
                self.set_trim_join_job_status(job_id, 'processing', progress)
        except Exception as e:
            print(f"Erro ao atualizar progresso do job de corte e junção no Redis: {e}")
    
    def get_trim_join_job_status(self, job_id):
        """Recupera status do job de corte e junção"""
        try:
            data = self.redis.get(f"trim_join_job:{job_id}")
            return json.loads(data) if data else None
        except Exception as e:
            print(f"Erro ao buscar status do job de corte e junção no Redis: {e}")
            return None
    
    def delete_trim_join_job(self, job_id):
        """Remove job de corte e junção do Redis"""
        try:
            self.redis.delete(f"trim_join_job:{job_id}")
        except Exception as e:
            print(f"Erro ao deletar job de corte e junção do Redis: {e}") 