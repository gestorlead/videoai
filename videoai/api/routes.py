from flask import Blueprint, request, jsonify, send_file
from api.queue_service import QueueService
from api.redis_service import RedisService
from src.models.api_key import ApiKey
import os
import validators
from datetime import datetime
import uuid

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

# Middleware para autenticação por API key
def require_api_key():
    """Verifica se a API key é válida"""
    api_key = request.headers.get('X-API-Key')
    
    if not api_key:
        return jsonify({'error': 'API key ausente. Use o header X-API-Key.'}), 401
    
    # Verificar no banco de dados
    try:
        api_key_obj = ApiKey.get_by_key(api_key)
        if not api_key_obj:
            return jsonify({'error': 'API key inválida.'}), 401
        
        if not api_key_obj.is_active:
            return jsonify({'error': 'API key desativada.'}), 401
        
        # Armazenar informações da API key no contexto da requisição
        request.api_key = api_key_obj
        return None
        
    except Exception as e:
        return jsonify({'error': 'Erro ao validar API key.'}), 500

@api_bp.before_request
def check_api_key():
    """Middleware para verificar API key em todas as rotas da API"""
    # Permitir endpoints públicos sem autenticação
    public_endpoints = ['health', 'download_video_public']
    if request.endpoint:
        for public_endpoint in public_endpoints:
            if public_endpoint in request.endpoint:
                return None
    
    auth_result = require_api_key()
    if auth_result:
        return auth_result

@api_bp.route('/health', methods=['GET'])
def api_health():
    """Health check da API"""
    redis_service = RedisService()
    queue_service = QueueService()
    
    health_status = {
        'status': 'ok',
        'api_version': '1.0',
        'services': {
            'redis': redis_service.test_connection(),
            'rabbitmq': queue_service.test_connection()
        }
    }
    
    # Se algum serviço estiver offline, retornar status degraded
    if not all(health_status['services'].values()):
        health_status['status'] = 'degraded'
        return jsonify(health_status), 503
    
    queue_service.close()
    return jsonify(health_status)

@api_bp.route('/audio/process', methods=['POST'])
def process_audio():
    """Endpoint principal para processar áudio"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'JSON inválido ou ausente'}), 400
        
        # Validar parâmetros obrigatórios
        audio_url = data.get('audio_url')
        if not audio_url:
            return jsonify({'error': 'audio_url é obrigatório'}), 400
        
        # Validar URL
        if not validators.url(audio_url):
            return jsonify({'error': 'audio_url deve ser uma URL válida'}), 400
        
        # Parâmetros opcionais
        transcript = data.get('transcript')
        webhook_url = data.get('webhook_url')
        priority = data.get('priority', False)
        target_language = data.get('target_language', 'pt')  # padrão português
        
        # Validar target_language
        if target_language not in ['en', 'pt', 'pt-BR', 'pt-PT']:
            return jsonify({'error': 'target_language deve ser "en", "pt", "pt-BR" ou "pt-PT"'}), 400
        
        # Validar webhook_url se fornecido
        if webhook_url and not validators.url(webhook_url):
            return jsonify({'error': 'webhook_url deve ser uma URL válida'}), 400
        
        # Validar transcript se fornecido
        if transcript and len(transcript.strip()) == 0:
            return jsonify({'error': 'transcript não pode estar vazio'}), 400
        
        # Publicar job na fila
        queue_service = QueueService()
        try:
            job_id = queue_service.publish_job(
                audio_url=audio_url,
                transcript=transcript,
                webhook_url=webhook_url,
                priority=priority,
                target_language=target_language
            )
        except Exception as e:
            return jsonify({'error': f'Erro ao processar requisição: {str(e)}'}), 500
        finally:
            queue_service.close()
        
        # Inicializar status no Redis
        redis_service = RedisService()
        redis_service.set_job_status(job_id, 'queued', progress=0)
        
        return jsonify({
            'job_id': job_id,
            'status': 'queued',
            'message': 'Áudio enviado para processamento com sucesso'
        }), 202
        
    except Exception as e:
        return jsonify({'error': f'Erro interno do servidor: {str(e)}'}), 500

@api_bp.route('/audio/status/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Consulta status de um job"""
    try:
        redis_service = RedisService()
        status = redis_service.get_job_status(job_id)
        
        if not status:
            return jsonify({'error': 'Job não encontrado'}), 404
        
        return jsonify(status)
        
    except Exception as e:
        return jsonify({'error': f'Erro ao consultar status: {str(e)}'}), 500

@api_bp.route('/audio/download/<job_id>', methods=['GET'])
def download_subtitle(job_id):
    """Download de legendas geradas"""
    try:
        # Parâmetro de idioma (padrão: inglês)
        lang = request.args.get('lang', 'en')
        
        if lang not in ['en', 'pt']:
            return jsonify({'error': 'Idioma deve ser "en" ou "pt"'}), 400
        
        # Buscar status do job
        redis_service = RedisService()
        job_data = redis_service.get_job_status(job_id)
        
        if not job_data:
            return jsonify({'error': 'Job não encontrado'}), 404
        
        if job_data['status'] != 'completed':
            return jsonify({
                'error': f'Job não está completo. Status atual: {job_data["status"]}',
                'status': job_data['status'],
                'progress': job_data.get('progress', 0)
            }), 400
        
        # Obter caminho do arquivo
        result = job_data.get('result', {})
        file_key = f'{lang}_subtitle_path'
        file_path = result.get(file_key)
        
        if not file_path:
            return jsonify({'error': f'Legenda em {lang} não encontrada'}), 404
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'Arquivo não encontrado no servidor'}), 404
        
        # Determinar nome do arquivo para download
        filename = f'subtitle_{lang}_{job_id}.srt'
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='text/plain'
        )
        
    except Exception as e:
        return jsonify({'error': f'Erro no download: {str(e)}'}), 500

@api_bp.route('/audio/queue/info', methods=['GET'])
def get_queue_info():
    """Retorna informações sobre a fila de processamento"""
    try:
        from api.queue_service import QueueService
        queue_service = QueueService()
        
        audio_info = queue_service.get_queue_info()
        video_info = queue_service.get_video_queue_info()
        
        queue_service.close()
        
        return jsonify({
            'audio_queue': audio_info,
            'video_queue': video_info,
            'total_pending': (audio_info.get('message_count', 0) if audio_info else 0) + 
                           (video_info.get('message_count', 0) if video_info else 0)
        })
        
    except Exception as e:
        return jsonify({'error': f'Erro ao obter informações da fila: {str(e)}'}), 500

@api_bp.route('/video/process-with-overlay', methods=['POST'])
def process_video_with_overlay():
    """Processa vídeo adicionando logo e legendas usando FFmpeg"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'JSON inválido ou ausente'}), 400
        
        # Validar parâmetros obrigatórios
        video_url = data.get('video_url')
        language = data.get('language')
        caption_id = data.get('caption_id')
        subtitle_content = data.get('subtitle_content')  # Nova opção
        
        if not video_url:
            return jsonify({'error': 'video_url é obrigatório'}), 400
        
        # Verificar se pelo menos um dos dois foi fornecido
        if not caption_id and not subtitle_content:
            return jsonify({'error': 'caption_id ou subtitle_content é obrigatório'}), 400
        
        # Não permitir ambos simultaneamente para evitar confusão
        if caption_id and subtitle_content:
            return jsonify({'error': 'Forneça apenas caption_id OU subtitle_content, não ambos'}), 400
        
        # Validar language apenas quando caption_id é usado
        if caption_id and not language:
            return jsonify({'error': 'language é obrigatório quando caption_id é usado'}), 400
        
        # Validar URL do vídeo
        if not validators.url(video_url):
            return jsonify({'error': 'video_url deve ser uma URL válida'}), 400
        
        # Validar idioma se fornecido
        if language and language not in ['en', 'pt', 'pt-BR', 'pt-PT']:
            return jsonify({'error': 'language deve ser "en", "pt", "pt-BR" ou "pt-PT"'}), 400
        
        # Validar subtitle_content se fornecido
        if subtitle_content:
            if not isinstance(subtitle_content, str) or len(subtitle_content.strip()) == 0:
                return jsonify({'error': 'subtitle_content deve ser uma string não vazia'}), 400
            
            # Validação básica de formato SRT
            if not _validate_srt_format(subtitle_content):
                return jsonify({'error': 'subtitle_content deve estar no formato SRT válido'}), 400
        
        # Parâmetro opcional: logo_url
        logo_url = data.get('logo_url')
        if logo_url and not validators.url(logo_url):
            return jsonify({'error': 'logo_url deve ser uma URL válida'}), 400
        
        # Parâmetros opcionais para customização das legendas
        subtitle_config = data.get('subtitle_config', {})
        
        # Validar configurações de legendas se fornecidas
        if subtitle_config:
            valid_fonts = ['Arial', 'Helvetica', 'Times', 'Verdana', 'Impact']
            valid_positions = ['top-left', 'top-center', 'top-right', 'bottom-left', 'bottom-center', 'bottom-right']
            
            if 'font_family' in subtitle_config and subtitle_config['font_family'] not in valid_fonts:
                return jsonify({'error': f'font_family deve ser um dos: {", ".join(valid_fonts)}'}), 400
            
            if 'position' in subtitle_config and subtitle_config['position'] not in valid_positions:
                return jsonify({'error': f'position deve ser um dos: {", ".join(valid_positions)}'}), 400
            
            # Validar font_size (aceita string ou número)
            if 'font_size' in subtitle_config:
                try:
                    size = _convert_to_number(subtitle_config['font_size'])
                    if size < 10 or size > 40:
                        return jsonify({'error': 'font_size deve estar entre 10 e 40'}), 400
                    # Converter de volta para número na configuração
                    subtitle_config['font_size'] = size
                except (ValueError, TypeError):
                    return jsonify({'error': 'font_size deve ser um número válido (10-40)'}), 400
            
            # Validar background_opacity (aceita string ou número)
            if 'background_opacity' in subtitle_config:
                try:
                    opacity = _convert_to_number(subtitle_config['background_opacity'])
                    if opacity < 0 or opacity > 100:
                        return jsonify({'error': 'background_opacity deve estar entre 0 e 100'}), 400
                    # Converter de volta para número na configuração
                    subtitle_config['background_opacity'] = opacity
                except (ValueError, TypeError):
                    return jsonify({'error': 'background_opacity deve ser um número válido (0-100)'}), 400
            
            # Validar outline_width (aceita string ou número)
            if 'outline_width' in subtitle_config:
                try:
                    width = _convert_to_number(subtitle_config['outline_width'])
                    if width < 0 or width > 3:
                        return jsonify({'error': 'outline_width deve estar entre 0 e 3'}), 400
                    # Converter de volta para número na configuração
                    subtitle_config['outline_width'] = width
                except (ValueError, TypeError):
                    return jsonify({'error': 'outline_width deve ser um número válido (0-3)'}), 400
            
            # Validar nova configuração de altura personalizada
            if 'subtitle_height' in subtitle_config:
                subtitle_height = subtitle_config['subtitle_height']
                
                # Aceitar tanto pixels (número/string) quanto porcentagem (string com %)
                if isinstance(subtitle_height, str) and subtitle_height.endswith('%'):
                    try:
                        percentage = float(subtitle_height[:-1])
                        if percentage < 0 or percentage > 100:
                            return jsonify({'error': 'subtitle_height em porcentagem deve estar entre 0% e 100%'}), 400
                    except ValueError:
                        return jsonify({'error': 'subtitle_height em porcentagem deve ser um número válido (ex: "85%")'}), 400
                else:
                    # Tratar como pixels (aceita string ou número)
                    try:
                        pixels = _convert_to_number(subtitle_height)
                        if pixels < 0 or pixels > 2160:  # até 4K
                            return jsonify({'error': 'subtitle_height em pixels deve estar entre 0 e 2160'}), 400
                        # Converter de volta para número na configuração
                        subtitle_config['subtitle_height'] = pixels
                    except (ValueError, TypeError):
                        return jsonify({'error': 'subtitle_height deve ser um número válido (pixels) ou string com % (porcentagem)'}), 400
            
            # Validar cores em formato hexadecimal
            color_fields = ['font_color', 'background_color', 'outline_color']
            for color_field in color_fields:
                if color_field in subtitle_config:
                    color_value = subtitle_config[color_field]
                    if not _validate_hex_color(color_value):
                        return jsonify({'error': f'{color_field} deve estar no formato hexadecimal (ex: #FFFFFF ou #000000)'}), 400
        
        # Iniciar processamento do vídeo
        from api.video_processor import VideoProcessor
        from api.queue_service import QueueService
        
        try:
            # Usar sistema de filas para processamento assíncrono
            queue_service = QueueService()
            
            # Gerar job_id único para o processamento de vídeo
            job_id = str(uuid.uuid4())
            
            # Publicar job de vídeo na fila
            video_job_data = {
                'job_id': job_id,
                'job_type': 'video_processing',
                'video_url': video_url,
                'language': language,
                'caption_id': caption_id,
                'subtitle_content': subtitle_content,
                'logo_url': logo_url,
                'subtitle_config': subtitle_config,
                'priority': False,  # Vídeos não são prioritários por padrão
                'created_at': datetime.now().isoformat()
            }
            
            # Tentar publicar na fila
            try:
                queue_service.publish_video_job(video_job_data)
                
                # Retornar imediatamente com job_id para acompanhamento
                return jsonify({
                    'success': True,
                    'message': 'Vídeo enviado para processamento com sucesso',
                    'job_id': job_id,
                    'status': 'queued',
                    'estimated_time': '30-60 segundos',
                    'status_url': f'/api/v1/video/status/{job_id}',
                    'download_url': f'/api/v1/video/download/{job_id}'
                }), 202  # 202 Accepted - processamento assíncrono
                
            except Exception as queue_error:
                # Fallback para processamento síncrono se a fila falhar
                print(f"Erro na fila, processando sincronicamente: {queue_error}")
                
                processor = VideoProcessor()
                result = processor.process_video_with_overlay(
                    video_url=video_url,
                    language=language,
                    caption_id=caption_id,
                    subtitle_content=subtitle_content,
                    logo_url=logo_url,
                    subtitle_config=subtitle_config
                )
                
                return jsonify({
                    'success': True,
                    'message': 'Vídeo processado com sucesso (modo síncrono)',
                    'result': result
                }), 200
                
        finally:
            # Fechar conexão com a fila
            try:
                queue_service.close()
            except:
                pass
        
    except Exception as e:
        return jsonify({'error': f'Erro interno do servidor: {str(e)}'}), 500

def _convert_to_number(value):
    """Converte um valor para número, aceitando tanto strings quanto números"""
    if isinstance(value, (int, float)):
        return value
    elif isinstance(value, str):
        try:
            # Tentar converter para int primeiro, depois float
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            raise ValueError(f"Não foi possível converter '{value}' para número")
    else:
        raise TypeError(f"Tipo inválido: {type(value)}. Esperado string ou número")

def _validate_hex_color(color):
    """Valida se a cor está no formato hexadecimal válido"""
    import re
    
    if not isinstance(color, str):
        return False
    
    # Regex para validar formato hexadecimal: #RRGGBB ou #RGB
    hex_pattern = r'^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$'
    return re.match(hex_pattern, color) is not None

def _validate_srt_format(content):
    """Valida se o conteúdo está no formato SRT básico"""
    import re
    
    # Regex para validar formato SRT básico
    # Deve conter: número, timestamp (HH:MM:SS,mmm --> HH:MM:SS,mmm), texto
    srt_pattern = r'\d+\s*\n\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}\s*\n.+?(?=\n\d+\s*\n|\Z)'
    
    # Verificar se há pelo menos uma entrada SRT válida
    matches = re.findall(srt_pattern, content, re.DOTALL | re.MULTILINE)
    return len(matches) > 0

@api_bp.route('/video/download/<filename>', methods=['GET'])
def download_processed_video(filename):
    """Download de vídeo processado"""
    try:
        upload_folder = os.environ.get('UPLOAD_FOLDER', '/app/uploads')
        output_folder = os.path.join(upload_folder, 'processed_videos')
        file_path = os.path.join(output_folder, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'Arquivo não encontrado'}), 404
        
        # Verificar se o arquivo está na pasta segura
        if not file_path.startswith(output_folder):
            return jsonify({'error': 'Acesso negado'}), 403
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='video/mp4'
        )
        
    except Exception as e:
        return jsonify({'error': f'Erro no download: {str(e)}'}), 500

@api_bp.route('/video/status/<job_id>', methods=['GET'])
def get_video_job_status(job_id):
    """Verifica o status de um job de processamento de vídeo"""
    try:
        from api.redis_service import RedisService
        redis_service = RedisService()
        
        job_data = redis_service.get_video_job_status(job_id)
        
        if not job_data:
            return jsonify({'error': 'Job não encontrado'}), 404
        
        # Adicionar URLs de download se completado
        if job_data['status'] == 'completed' and 'result' in job_data:
            result = job_data['result']
            if 'output_video_url' in result:
                # Extrair filename da URL para criar URL de download
                output_url = result['output_video_url']
                filename = output_url.split('/')[-1]
                result['download_url'] = f'/api/v1/video/download/{filename}'
        
        return jsonify(job_data)
        
    except Exception as e:
        return jsonify({'error': f'Erro ao verificar status: {str(e)}'}), 500

@api_bp.route('/video/download/<job_id>', methods=['GET'])
def download_video_by_job_id(job_id):
    """Download de vídeo processado usando job_id"""
    try:
        from api.redis_service import RedisService
        redis_service = RedisService()
        
        job_data = redis_service.get_video_job_status(job_id)
        
        if not job_data:
            return jsonify({'error': 'Job não encontrado'}), 404
        
        if job_data['status'] != 'completed':
            return jsonify({
                'error': 'Vídeo ainda não está pronto',
                'status': job_data['status'],
                'message': 'Tente novamente em alguns instantes'
            }), 202
        
        # Obter caminho do arquivo a partir do resultado
        result = job_data.get('result', {})
        output_video_url = result.get('output_video_url')
        
        if not output_video_url:
            return jsonify({'error': 'URL do vídeo não encontrada no resultado'}), 404
        
        # Extrair filename da URL
        filename = output_video_url.split('/')[-1]
        
        # Chamar endpoint de download por filename
        return download_processed_video(filename)
        
    except Exception as e:
        return jsonify({'error': f'Erro no download: {str(e)}'}), 500

@api_bp.route('/video/process-takes', methods=['POST'])
def process_video_takes():
    """
    Processa múltiplos takes de vídeo juntando-os em ordem,
    aplicando áudio, logo e legendas ASS
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': 'Request body não pode estar vazio'
            }), 400
        
        # Aceitar tanto objeto individual quanto array de objetos
        if isinstance(data, dict):
            # Se é um objeto individual, converter para array
            data = [data]
        elif isinstance(data, list):
            # Se já é array, usar como está
            if len(data) == 0:
                return jsonify({
                    'error': 'Array não pode estar vazio'
                }), 400
        else:
            return jsonify({
                'error': 'Request body deve ser um objeto ou array de objetos'
            }), 400
        
        job_id = str(uuid.uuid4())
        
        # Validar entrada
        for idx, item in enumerate(data):
            if not isinstance(item, dict):
                return jsonify({
                    'error': f'Item {idx} deve ser um objeto'
                }), 400
            
            required_fields = ['audio_url', 'video_url', 'caption_url']
            for field in required_fields:
                if field not in item:
                    return jsonify({
                        'error': f'Campo obrigatório ausente no item {idx}: {field}'
                    }), 400
            
            if not isinstance(item['video_url'], list) or len(item['video_url']) == 0:
                return jsonify({
                    'error': f'video_url no item {idx} deve ser um array não vazio'
                }), 400
            
            # Validar URLs
            if not validators.url(item['audio_url']):
                return jsonify({
                    'error': f'audio_url no item {idx} deve ser uma URL válida'
                }), 400
            
            if not validators.url(item['caption_url']):
                return jsonify({
                    'error': f'caption_url no item {idx} deve ser uma URL válida'
                }), 400
            
            for video_idx, video_url in enumerate(item['video_url']):
                if not validators.url(video_url):
                    return jsonify({
                        'error': f'video_url[{video_idx}] no item {idx} deve ser uma URL válida'
                    }), 400
        
        # Processar via fila assíncrona
        from api.queue_service import QueueService
        
        try:
            queue_service = QueueService()
            
            # Dados do job para processamento de takes
            takes_job_data = {
                'job_id': job_id,
                'job_type': 'video_takes_processing',
                'takes_data': data,
                'priority': False,
                'created_at': datetime.now().isoformat()
            }
            
            # Publicar na fila
            queue_service.publish_takes_job(takes_job_data)
            
            # Inicializar status no Redis
            redis_service = RedisService()
            redis_service.set_takes_job_status(job_id, 'queued', progress=0)
            
            return jsonify({
                'job_id': job_id,
                'status': 'queued',
                'message': 'Takes enviados para processamento com sucesso',
                'estimated_time': '2-5 minutos',
                'status_url': f'/api/v1/video/takes/status/{job_id}',
                'download_url': f'/api/v1/video/takes/download/{job_id}',
                'public_download_url': f'/api/v1/public/video/{job_id}',
                'takes_count': len(data)
            }), 202
            
        except Exception as queue_error:
            # Fallback para processamento síncrono se a fila falhar
            print(f"Erro na fila, processando takes sincronicamente: {queue_error}")
            
            from api.video_processor import VideoProcessor
            processor = VideoProcessor()
            result = processor.process_video_takes(job_id, data)
            
            # Salvar resultado no Redis para o download público funcionar
            redis_service = RedisService()
            redis_service.set_takes_job_status(job_id, 'completed', 100, result)
            
            return jsonify({
                'job_id': job_id,
                'status': 'completed',
                'message': 'Takes processados com sucesso (modo síncrono)',
                'result': result,
                'public_download_url': f'/api/v1/public/video/{job_id}'
            }), 200
            
        finally:
            try:
                queue_service.close()
            except:
                pass
        
    except Exception as e:
        return jsonify({
            'error': f'Erro interno do servidor: {str(e)}'
        }), 500

@api_bp.route('/video/takes/status/<job_id>', methods=['GET'])
def get_takes_job_status(job_id):
    """Verifica o status de um job de processamento de takes"""
    try:
        redis_service = RedisService()
        job_data = redis_service.get_takes_job_status(job_id)
        
        if not job_data:
            return jsonify({'error': 'Job não encontrado'}), 404
        
        # Adicionar URLs de download se completado
        if job_data['status'] == 'completed' and 'result' in job_data:
            result = job_data['result']
            if 'output_files' in result:
                result['download_urls'] = []
                for output_file in result['output_files']:
                    filename = output_file.split('/')[-1]
                    result['download_urls'].append({
                        'filename': filename,
                        'download_url': f'/api/v1/video/download/{filename}',
                        'public_url': f'/api/v1/public/video/{filename.replace("processed_", "").replace(".mp4", "")}'
                    })
        
        return jsonify(job_data)
        
    except Exception as e:
        return jsonify({'error': f'Erro ao verificar status: {str(e)}'}), 500

@api_bp.route('/video/takes/download/<job_id>', methods=['GET'])
def download_takes_by_job_id(job_id):
    """Download dos vídeos processados de takes usando job_id"""
    try:
        redis_service = RedisService()
        job_data = redis_service.get_takes_job_status(job_id)
        
        if not job_data:
            return jsonify({'error': 'Job não encontrado'}), 404
        
        if job_data['status'] != 'completed':
            return jsonify({
                'error': 'Vídeos ainda não estão prontos',
                'status': job_data['status'],
                'message': 'Tente novamente em alguns instantes'
            }), 202
        
        # Obter primeiro arquivo processado (compatibilidade)
        result = job_data.get('result', {})
        output_files = result.get('output_files', [])
        
        if not output_files:
            return jsonify({'error': 'Nenhum arquivo processado encontrado'}), 404
        
        # Retornar primeiro arquivo
        first_file = output_files[0]
        filename = first_file.split('/')[-1]
        
        return download_processed_video(filename)
        
    except Exception as e:
        return jsonify({'error': f'Erro no download: {str(e)}'}), 500

@api_bp.route('/audio/job/<job_id>', methods=['DELETE'])
def delete_job(job_id):
    """Remove um job (apenas se não estiver processando)"""
    try:
        redis_service = RedisService()
        job_data = redis_service.get_job_status(job_id)
        
        if not job_data:
            return jsonify({'error': 'Job não encontrado'}), 404
        
        # Não permitir remoção de jobs em processamento
        if job_data['status'] == 'processing':
            return jsonify({'error': 'Não é possível remover job em processamento'}), 400
        
        # Limpar arquivos se o job foi completado
        if job_data['status'] == 'completed':
            try:
                from api.audio_processor import AudioProcessor
                processor = AudioProcessor()
                processor.cleanup_job_files(job_id)
            except Exception as e:
                print(f"Erro ao limpar arquivos: {e}")
        
        # Remover do Redis
        redis_service.delete_job(job_id)
        
        return jsonify({'message': 'Job removido com sucesso'})
        
    except Exception as e:
        return jsonify({'error': f'Erro ao remover job: {str(e)}'}), 500

@api_bp.route('/public/video/<job_id>', methods=['GET'])
def download_video_public(job_id):
    """Download público de vídeo processado (sem autenticação)"""
    try:
        redis_service = RedisService()
        
        # Tentar buscar em diferentes tipos de job
        job_data = redis_service.get_video_job_status(job_id)
        if not job_data:
            job_data = redis_service.get_takes_job_status(job_id)
        
        if not job_data:
            job_data = redis_service.get_trim_join_job_status(job_id)
        
        if not job_data:
            return jsonify({'error': 'Job não encontrado'}), 404
        
        if job_data['status'] != 'completed':
            return jsonify({
                'error': 'Vídeo ainda não está pronto',
                'status': job_data['status'],
                'progress': job_data.get('progress', 0),
                'message': 'Tente novamente em alguns minutos'
            }), 202
        
        # Obter caminho do arquivo
        result = job_data.get('result', {})
        file_path = result.get('output_path')
        
        if not file_path:
            return jsonify({'error': 'Arquivo de saída não encontrado'}), 404
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'Arquivo não encontrado no servidor'}), 404
        
        # Download direto do arquivo
        filename = os.path.basename(file_path)
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='video/mp4'
        )
        
    except Exception as e:
        return jsonify({'error': f'Erro no download: {str(e)}'}), 500

@api_bp.route('/video/trim-join', methods=['POST'])
def trim_join_videos():
    """
    Corta vídeos para duração especificada e junta na ordem dos takes
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': 'Request body não pode estar vazio'
            }), 400
        
        # Aceitar tanto o formato { "processed_takes": [...] } quanto [{ "processed_takes": [...] }]
        if isinstance(data, dict) and 'processed_takes' in data:
            # Formato: { "processed_takes": [...] }
            processed_takes = data['processed_takes']
            if not isinstance(processed_takes, list) or len(processed_takes) == 0:
                return jsonify({
                    'error': 'processed_takes deve ser um array não vazio'
                }), 400
            all_takes = processed_takes
            
        elif isinstance(data, list) and len(data) > 0:
            # Formato legacy: [{ "processed_takes": [...] }]
            all_takes = []
            for group_idx, group in enumerate(data):
                if not isinstance(group, dict):
                    return jsonify({
                        'error': f'Item {group_idx} deve ser um objeto'
                    }), 400
                
                processed_takes = group.get('processed_takes', [])
                if not isinstance(processed_takes, list) or len(processed_takes) == 0:
                    return jsonify({
                        'error': f'processed_takes no item {group_idx} deve ser um array não vazio'
                    }), 400
                
                all_takes.extend(processed_takes)
        else:
            return jsonify({
                'error': 'Request body deve conter "processed_takes" com array de takes ou ser um array de objetos processed_takes'
            }), 400
        
        job_id = str(uuid.uuid4())
        
        # Validar cada take
        for take_idx, take in enumerate(all_takes):
            if not isinstance(take, dict):
                return jsonify({
                    'error': f'Take {take_idx} deve ser um objeto'
                }), 400
            
            # Campos obrigatórios
            required_fields = ['take_number', 'video_url', 'final_clip_duration']
            for field in required_fields:
                if field not in take:
                    return jsonify({
                        'error': f'Campo obrigatório ausente no take {take_idx}: {field}'
                    }), 400
            
            # Validar tipos
            if not isinstance(take['take_number'], int) or take['take_number'] <= 0:
                return jsonify({
                    'error': f'take_number deve ser um inteiro positivo no take {take_idx}'
                }), 400
            
            if not validators.url(take['video_url']):
                return jsonify({
                    'error': f'video_url deve ser uma URL válida no take {take_idx}'
                }), 400
            
            if not isinstance(take['final_clip_duration'], (int, float)) or take['final_clip_duration'] <= 0:
                return jsonify({
                    'error': f'final_clip_duration deve ser um número positivo no take {take_idx}'
                }), 400
        
        # Ordenar takes por take_number
        all_takes.sort(key=lambda x: x['take_number'])
        
        # Verificar se não há take_numbers duplicados
        take_numbers = [take['take_number'] for take in all_takes]
        if len(take_numbers) != len(set(take_numbers)):
            return jsonify({
                'error': 'Números de take duplicados encontrados'
            }), 400
        
        # Processar via fila assíncrona
        from api.queue_service import QueueService
        
        try:
            queue_service = QueueService()
            
            # Dados do job para corte e junção
            trim_join_job_data = {
                'job_id': job_id,
                'job_type': 'video_trim_join',
                'takes': all_takes,
                'priority': False,
                'created_at': datetime.now().isoformat()
            }
            
            # Publicar na fila
            queue_service.publish_trim_join_job(trim_join_job_data)
            
            # Inicializar status no Redis
            redis_service = RedisService()
            redis_service.set_trim_join_job_status(job_id, 'queued', progress=0)
            
            return jsonify({
                'job_id': job_id,
                'status': 'queued',
                'message': 'Vídeos enviados para corte e junção com sucesso',
                'estimated_time': f'{len(all_takes) * 10}-{len(all_takes) * 20} segundos',
                'status_url': f'/api/v1/video/trim-join/status/{job_id}',
                'download_url': f'/api/v1/video/trim-join/download/{job_id}',
                'public_download_url': f'/api/v1/public/video/{job_id}',
                'takes_count': len(all_takes)
            }), 202
            
        except Exception as queue_error:
            # Fallback para processamento síncrono se a fila falhar
            print(f"Erro na fila, processando corte e junção sincronicamente: {queue_error}")
            
            try:
                from api.video_processor import VideoProcessor
                processor = VideoProcessor()
                result = processor.trim_and_join_videos(job_id, all_takes)
                
                # Salvar resultado no Redis para o download público funcionar
                redis_service = RedisService()
                redis_service.set_trim_join_job_status(job_id, 'completed', 100, result)
                
                return jsonify({
                    'job_id': job_id,
                    'status': 'completed',
                    'message': 'Vídeos processados com sucesso (modo síncrono)',
                    'result': result,
                    'public_download_url': f'/api/v1/public/video/{job_id}'
                }), 200
                
            except Exception as sync_error:
                return jsonify({
                    'error': f'Erro no processamento: {str(sync_error)}'
                }), 500
            
        finally:
            try:
                queue_service.close()
            except:
                pass
        
    except Exception as e:
        return jsonify({
            'error': f'Erro interno do servidor: {str(e)}'
        }), 500

@api_bp.route('/video/trim-join/status/<job_id>', methods=['GET'])
def get_trim_join_job_status(job_id):
    """Verifica o status de um job de corte e junção"""
    try:
        redis_service = RedisService()
        job_data = redis_service.get_trim_join_job_status(job_id)
        
        if not job_data:
            return jsonify({'error': 'Job não encontrado'}), 404
        
        # Adicionar URLs de download se completado
        if job_data['status'] == 'completed' and 'result' in job_data:
            result = job_data['result']
            if 'output_path' in result:
                filename = os.path.basename(result['output_path'])
                result['download_urls'] = {
                    'filename': filename,
                    'download_url': f'/api/v1/video/trim-join/download/{job_id}',
                    'public_url': f'/api/v1/public/video/{job_id}'
                }
        
        return jsonify(job_data)
        
    except Exception as e:
        return jsonify({'error': f'Erro ao verificar status: {str(e)}'}), 500

@api_bp.route('/video/trim-join/download/<job_id>', methods=['GET'])
def download_trim_join_by_job_id(job_id):
    """Download do vídeo processado de corte e junção usando job_id"""
    try:
        redis_service = RedisService()
        job_data = redis_service.get_trim_join_job_status(job_id)
        
        if not job_data:
            return jsonify({'error': 'Job não encontrado'}), 404
        
        if job_data['status'] != 'completed':
            return jsonify({
                'error': 'Vídeo ainda não está pronto',
                'status': job_data['status'],
                'progress': job_data.get('progress', 0),
                'message': 'Tente novamente em alguns instantes'
            }), 202
        
        # Obter caminho do arquivo
        result = job_data.get('result', {})
        file_path = result.get('output_path')
        
        if not file_path:
            return jsonify({'error': 'Arquivo processado não encontrado'}), 404
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'Arquivo não encontrado no servidor'}), 404
        
        # Download direto do arquivo
        filename = os.path.basename(file_path)
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='video/mp4'
        )
        
    except Exception as e:
        return jsonify({'error': f'Erro no download: {str(e)}'}), 500

# Tratamento de erros
@api_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint não encontrado'}), 404

@api_bp.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'error': 'Método não permitido'}), 405

@api_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Erro interno do servidor'}), 500

 