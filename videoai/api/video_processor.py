import os
import subprocess
import requests
import tempfile
import uuid
from datetime import datetime
from urllib.parse import urlparse
from api.redis_service import RedisService
from src.utils.settings_helper import SettingsHelper

class VideoProcessor:
    def __init__(self):
        self.upload_folder = os.environ.get('UPLOAD_FOLDER', '/app/uploads')
        self.temp_folder = os.path.join(self.upload_folder, 'temp')
        self.output_folder = os.path.join(self.upload_folder, 'processed_videos')
        
        # Criar pastas se não existirem
        os.makedirs(self.temp_folder, exist_ok=True)
        os.makedirs(self.output_folder, exist_ok=True)
    
    def process_video_with_overlay(self, video_url, language, caption_id=None, subtitle_content=None, logo_url=None, subtitle_config=None, text_overlay_config=None):
        """Processa vídeo adicionando logo e legendas"""
        
        # Gerar ID único para este processamento
        process_id = str(uuid.uuid4())
        print(f"Iniciando processamento de vídeo: {process_id}")
        
        try:
            # 1. Baixar o vídeo
            video_path = self._download_video(video_url, process_id)
            
            # 2. Obter arquivo de legendas
            subtitle_path = self._get_subtitle_file(caption_id, subtitle_content, language, process_id)
            
            # 3. Obter logo (da URL fornecida ou das configurações)
            logo_path = self._get_logo(logo_url, process_id)
            
            # 4. Processar vídeo com FFmpeg
            output_path = self._process_with_ffmpeg(
                video_path, subtitle_path, logo_path, process_id, subtitle_config, text_overlay_config
            )
            
            # 5. Preparar resultado
            result = {
                'process_id': process_id,
                'output_video_url': self._get_download_url(output_path),
                'original_video_url': video_url,
                'language': language if language else 'custom',
                'subtitle_source': 'caption_id' if caption_id else 'direct_content',
                'caption_id': caption_id,
                'has_logo': logo_path is not None,
                'processed_at': datetime.now().isoformat()
            }
            
            # 6. Limpar arquivos temporários
            self._cleanup_temp_files(video_path, logo_path if logo_url else None, subtitle_path)
            
            return result
            
        except Exception as e:
            # Limpar arquivos em caso de erro
            self._cleanup_temp_files(
                f"{self.temp_folder}/video_{process_id}.*",
                f"{self.temp_folder}/logo_{process_id}.*"
            )
            raise e
    
    def _download_video(self, video_url, process_id):
        """Baixa o vídeo da URL fornecida"""
        print(f"Baixando vídeo: {video_url}")
        
        # Detectar extensão do vídeo
        parsed_url = urlparse(video_url)
        file_extension = os.path.splitext(parsed_url.path)[1] or '.mp4'
        
        video_path = os.path.join(self.temp_folder, f"video_{process_id}{file_extension}")
        
        # Baixar vídeo
        response = requests.get(video_url, stream=True)
        response.raise_for_status()
        
        with open(video_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"Vídeo baixado: {video_path}")
        return video_path
    
    def _get_subtitle_file(self, caption_id, subtitle_content, language, process_id):
        """Obtém o arquivo de legendas baseado no caption_id ou conteúdo direto"""
        
        # Criar arquivo SRT temporário
        # Se language não for fornecido (caso subtitle_content), usar 'custom'
        lang_suffix = language if language else 'custom'
        subtitle_filename = f"subtitle_{lang_suffix}_{process_id}.srt"
        subtitle_path = os.path.join(self.temp_folder, subtitle_filename)
        
        if subtitle_content:
            # Usar conteúdo fornecido diretamente
            print(f"Usando conteúdo de legenda fornecido diretamente")
            
            with open(subtitle_path, 'w', encoding='utf-8') as f:
                f.write(subtitle_content)
            
            print(f"Arquivo de legendas criado a partir do conteúdo direto: {subtitle_path}")
            return subtitle_path
            
        elif caption_id:
            # Usar caption_id para buscar no Redis (comportamento original)
            print(f"Buscando legendas para caption_id: {caption_id}, idioma: {language}")
            
            # Buscar legendas no Redis usando o caption_id (job_id)
            redis_service = RedisService()
            job_data = redis_service.get_job_status(caption_id)
            
            if not job_data:
                raise Exception(f"Caption ID {caption_id} não encontrado")
            
            if job_data['status'] != 'completed':
                raise Exception(f"Legendas não estão prontas. Status: {job_data['status']}")
            
            # Obter estrutura de legendas
            result = job_data.get('result', {})
            subtitles = result.get('subtitles', {})
            
            if not subtitles:
                raise Exception("Nenhuma legenda encontrada no job")
            
            # Mapear idioma para chave do resultado
            # Normalizar idiomas pt-BR e pt-PT para 'pt'
            lang_key = 'en' if language == 'en' else 'pt'
            
            subtitle_data = subtitles.get(lang_key)
            if not subtitle_data:
                available_langs = list(subtitles.keys())
                raise Exception(f"Arquivo de legenda em {language} não encontrado. Idiomas disponíveis: {available_langs}")
            
            # Obter conteúdo da legenda
            subtitle_content = subtitle_data.get('content')
            if not subtitle_content:
                raise Exception(f"Conteúdo da legenda em {language} está vazio")
            
            with open(subtitle_path, 'w', encoding='utf-8') as f:
                f.write(subtitle_content)
            
            print(f"Arquivo de legendas criado a partir do Redis: {subtitle_path}")
            return subtitle_path
        
        else:
            raise Exception("Nem caption_id nem subtitle_content foram fornecidos")
    
    def _get_logo(self, logo_url, process_id):
        """Obtém o logo (da URL ou das configurações)"""
        if logo_url:
            # Usar logo da URL fornecida
            return self._download_logo(logo_url, process_id)
        else:
            # Usar logo das configurações do sistema
            if SettingsHelper.has_logo():
                logo_path = SettingsHelper.get_logo_path()
                if os.path.exists(logo_path):
                    print(f"Usando logo das configurações: {logo_path}")
                    return logo_path
                else:
                    print("Logo configurado não existe no sistema de arquivos")
            else:
                print("Nenhum logo configurado no sistema")
        
        return None
    
    def _download_logo(self, logo_url, process_id):
        """Baixa o logo da URL fornecida"""
        print(f"Baixando logo: {logo_url}")
        
        # Detectar extensão do logo
        parsed_url = urlparse(logo_url)
        file_extension = os.path.splitext(parsed_url.path)[1] or '.png'
        
        logo_path = os.path.join(self.temp_folder, f"logo_{process_id}{file_extension}")
        
        # Baixar logo
        response = requests.get(logo_url)
        response.raise_for_status()
        
        with open(logo_path, 'wb') as f:
            f.write(response.content)
        
        print(f"Logo baixado: {logo_path}")
        return logo_path
    
    def _process_with_ffmpeg(self, video_path, subtitle_path, logo_path, process_id, subtitle_config, text_overlay_config):
        """Processa o vídeo usando FFmpeg"""
        print("Iniciando processamento com FFmpeg...")
        
        # Arquivo de saída
        output_filename = f"processed_{process_id}.mp4"
        output_path = os.path.join(self.output_folder, output_filename)
        
        # Construir comando FFmpeg
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', video_path,  # Vídeo de entrada
            '-y',  # Sobrescrever arquivo de saída
        ]
        
        # Configurar filtros
        filters = []
        
        # Adicionar legendas
        if subtitle_path:
            # Obter configurações de legendas (customizadas ou padrão)
            subtitle_style = self._build_subtitle_style(subtitle_config)
            
            # Escapar caracteres especiais no caminho
            escaped_subtitle_path = subtitle_path.replace('\\', '\\\\').replace(':', '\\:')
            filters.append(f"subtitles='{escaped_subtitle_path}':force_style='{subtitle_style}'")
        
        # Adicionar logo se disponível
        if logo_path:
            logo_position = SettingsHelper.get_logo_position()
            logo_size = SettingsHelper.get_logo_size()
            logo_opacity = SettingsHelper.get_logo_opacity() / 100.0  # Converter para decimal
            
            # Mapear posição para coordenadas FFmpeg
            position_map = {
                'top-left': '10:10',
                'top-right': 'W-w-10:10',
                'bottom-left': '10:H-h-10',
                'bottom-right': 'W-w-10:H-h-10',
                'center': '(W-w)/2:(H-h)/2'
            }
            
            position = position_map.get(logo_position, 'W-w-10:10')
            
            # Calcular escala do logo baseado no tamanho configurado
            # logo_size está em porcentagem (1-50), vamos aplicar como fração da largura do vídeo
            scale_factor = logo_size / 100.0
            
            # Adicionar logo como overlay
            if filters:
                # Se já há filtros (legendas), adicionar logo como segundo input
                ffmpeg_cmd.extend(['-i', logo_path])
                # Aplicar escala e transparência ao logo, depois overlay
                logo_filter = f"[1:v]scale=iw*{scale_factor}:ih*{scale_factor},format=rgba,colorchannelmixer=aa={logo_opacity}[logo]"
                combined_filter = f"[0:v]{filters[0]}[v1];{logo_filter};[v1][logo]overlay={position}:format=auto,format=yuv420p"
                filters = [combined_filter]
            else:
                # Apenas logo, sem legendas
                ffmpeg_cmd.extend(['-i', logo_path])
                logo_filter = f"[1:v]scale=iw*{scale_factor}:ih*{scale_factor},format=rgba,colorchannelmixer=aa={logo_opacity}[logo]"
                filters.append(f"{logo_filter};[0:v][logo]overlay={position}:format=auto,format=yuv420p")
        
        # Aplicar filtros se existirem
        if filters:
            ffmpeg_cmd.extend(['-filter_complex', ';'.join(filters)])
        
        # Configurações de saída
        ffmpeg_cmd.extend([
            '-c:v', 'libx264',  # Codec de vídeo
            '-c:a', 'aac',      # Codec de áudio
            '-preset', 'medium', # Velocidade de encoding
            '-crf', '23',       # Qualidade (18-28, menor = melhor qualidade)
            output_path
        ])
        
        print(f"Comando FFmpeg: {' '.join(ffmpeg_cmd)}")
        
        # Executar FFmpeg
        try:
            result = subprocess.run(
                ffmpeg_cmd,
                check=True,
                capture_output=True,
                text=True
            )
            print("FFmpeg executado com sucesso")
            print(f"Vídeo processado salvo em: {output_path}")
            
        except subprocess.CalledProcessError as e:
            print(f"Erro no FFmpeg: {e.stderr}")
            raise Exception(f"Erro ao processar vídeo com FFmpeg: {e.stderr}")
        
        return output_path
    
    def _build_subtitle_style(self, subtitle_config):
        """Constrói o estilo das legendas baseado nas configurações"""
        
        # Configurações padrão (das configurações do sistema ou valores default)
        default_font_size = SettingsHelper.get_subtitle_font_size()
        default_font_family = SettingsHelper.get_subtitle_font_family()
        default_font_color = SettingsHelper.get_subtitle_font_color()
        default_background_color = SettingsHelper.get_subtitle_background_color()
        default_background_opacity = SettingsHelper.get_subtitle_background_opacity()
        default_outline_color = SettingsHelper.get_subtitle_outline_color()
        default_outline_width = SettingsHelper.get_subtitle_outline_width()
        default_position = SettingsHelper.get_subtitle_position()
        
        # Aplicar configurações customizadas se fornecidas
        if subtitle_config:
            font_size = subtitle_config.get('font_size', default_font_size)
            font_family = subtitle_config.get('font_family', default_font_family)
            font_color = subtitle_config.get('font_color', default_font_color)
            background_color = subtitle_config.get('background_color', default_background_color)
            background_opacity = subtitle_config.get('background_opacity', default_background_opacity)
            outline_color = subtitle_config.get('outline_color', default_outline_color)
            outline_width = subtitle_config.get('outline_width', default_outline_width)
            position = subtitle_config.get('position', default_position)
            subtitle_height = subtitle_config.get('subtitle_height')  # Nova configuração
        else:
            font_size = default_font_size
            font_family = default_font_family
            font_color = default_font_color
            background_color = default_background_color
            background_opacity = default_background_opacity
            outline_color = default_outline_color
            outline_width = default_outline_width
            position = default_position
            subtitle_height = None
        
        # Converter cores hex para formato ASS (BGR com &H prefix)
        def hex_to_ass_color(hex_color):
            # Remove # se presente
            hex_color = hex_color.replace('#', '')
            # Converter RGB para BGR e adicionar &H prefix
            if len(hex_color) == 6:
                r = hex_color[0:2]
                g = hex_color[2:4]
                b = hex_color[4:6]
                return f"&H{b}{g}{r}"
            return "&H000000"  # fallback para preto
        
        # Converter cores
        primary_colour = hex_to_ass_color(font_color)
        outline_colour = hex_to_ass_color(outline_color)
        back_colour = hex_to_ass_color(background_color)
        
        # Calcular opacidade do fundo (0-255, onde 0 é opaco e 255 é transparente)
        # FFmpeg usa o inverso: 0=opaco, 255=transparente
        back_alpha = int(255 - (background_opacity * 255 / 100))
        
        # Mapear posição para alinhamento ASS
        alignment_map = {
            'bottom-left': '1',
            'bottom-center': '2', 
            'bottom-right': '3',
            'top-left': '7',
            'top-center': '8',
            'top-right': '9'
        }
        alignment = alignment_map.get(position, '2')  # default bottom-center
        
        # Ajustar margem vertical baseado em subtitle_height ou posição padrão
        margin_v = 0
        
        if subtitle_height is not None:
            # Usar altura customizada fornecida via API
            if isinstance(subtitle_height, str) and subtitle_height.endswith('%'):
                # Porcentagem da altura do vídeo (H = altura total do vídeo no FFmpeg)
                percentage = float(subtitle_height[:-1])
                # Converter para pixels baseado na altura do vídeo
                # Para ASS, MarginV é a distância da borda inferior/superior
                if alignment in ['1', '2', '3']:  # posições bottom
                    # Para bottom, MarginV é distância da borda inferior
                    margin_v = f"(H*{(100-percentage)/100})"  # FFmpeg expression
                    print(f"Altura customizada: {subtitle_height} -> MarginV: {margin_v} (bottom)")
                else:  # posições top
                    # Para top, MarginV é distância da borda superior  
                    margin_v = f"(H*{percentage/100})"
                    print(f"Altura customizada: {subtitle_height} -> MarginV: {margin_v} (top)")
            else:
                # Valor em pixels direto
                pixels = int(subtitle_height)
                if alignment in ['1', '2', '3']:  # posições bottom
                    # Para bottom, distância da borda inferior
                    margin_v = pixels
                    print(f"Altura customizada: {subtitle_height}px -> MarginV: {margin_v}px (bottom)")
                else:  # posições top
                    # Para top, distância da borda superior
                    margin_v = pixels
                    print(f"Altura customizada: {subtitle_height}px -> MarginV: {margin_v}px (top)")
        else:
            # Usar margem padrão baseada na posição
            if position.startswith('bottom'):
                margin_v = 60  # Subir legendas inferiores 60px da borda
            elif position.startswith('top'):
                margin_v = 20   # Afastar legendas superiores 20px da borda
        
        # Construir string de estilo ASS
        style_parts = [
            f"FontSize={font_size}",
            f"FontName={font_family}",
            f"PrimaryColour={primary_colour}",
            f"OutlineColour={outline_colour}",
            f"Outline={outline_width}",
            f"Alignment={alignment}",
            f"MarginV={margin_v}"
        ]
        
        # Adicionar background apenas se a opacidade for maior que 0
        if background_opacity > 0:
            style_parts.extend([
                f"BackColour={back_colour}",
                f"BackColourAlpha=&H{back_alpha:02x}",
                f"BorderStyle=4",  # Força background box
                f"Shadow=0",      # Remove sombra para melhor contraste
                f"MarginL=10",    # Margem lateral para não grudar na borda
                f"MarginR=10"     # Margem lateral direita
            ])
        else:
            style_parts.extend([
                "BorderStyle=1",  # Apenas contorno
                f"Shadow=1",      # Adiciona sombra quando não há background
                f"MarginL=10",
                f"MarginR=10"
            ])
        
        style_string = ','.join(style_parts)
        print(f"Estilo das legendas: {style_string}")
        
        return style_string
    
    def _get_download_url(self, file_path):
        """Gera URL para download do arquivo processado"""
        filename = os.path.basename(file_path)
        # Em produção, isso seria uma URL completa do servidor
        return f"/api/v1/video/download/{filename}"
    
    def _cleanup_temp_files(self, *file_paths):
        """Remove arquivos temporários"""
        for file_path in file_paths:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"Arquivo temporário removido: {file_path}")
                except Exception as e:
                    print(f"Erro ao remover arquivo {file_path}: {e}")

    def process_video_takes(self, job_id, takes_data):
        """Processa múltiplos takes de vídeo juntando-os em ordem, aplicando áudio, logo e legendas"""
        
        print(f"Iniciando processamento de takes: {job_id}")
        temp_files = []
        
        try:
            output_files = []
            
            # Processar cada take individualmente
            for take_idx, take_data in enumerate(takes_data):
                print(f"Processando take {take_idx + 1} de {len(takes_data)}")
                
                # 1. Baixar e concatenar vídeos do take
                video_urls = take_data['video_url']
                audio_url = take_data['audio_url']
                caption_url = take_data['caption_url']
                
                # Baixar todos os vídeos do take
                video_paths = []
                for video_idx, video_url in enumerate(video_urls):
                    video_path = self._download_video(video_url, f"{job_id}_take{take_idx}_video{video_idx}")
                    video_paths.append(video_path)
                    temp_files.append(video_path)
                
                # 2. Concatenar vídeos se há múltiplos
                if len(video_paths) > 1:
                    concatenated_video = self._concatenate_videos(video_paths, f"{job_id}_take{take_idx}_concat")
                    temp_files.append(concatenated_video)
                else:
                    concatenated_video = video_paths[0]
                
                # 3. Baixar áudio
                audio_path = self._download_audio(audio_url, f"{job_id}_take{take_idx}")
                temp_files.append(audio_path)
                
                # 4. Baixar legendas ASS
                subtitle_path = self._download_ass_subtitle(caption_url, f"{job_id}_take{take_idx}")
                temp_files.append(subtitle_path)
                
                # 5. Obter logo (das configurações)
                logo_path = self._get_logo(None, f"{job_id}_take{take_idx}")
                if logo_path and logo_path not in temp_files:
                    # Não adicionar logo das configurações aos temp_files
                    pass
                
                # 6. Processar vídeo final com áudio, legendas e logo
                output_path = self._process_take_with_ffmpeg(
                    concatenated_video, audio_path, subtitle_path, logo_path, 
                    f"{job_id}_take{take_idx}"
                )
                
                output_files.append(output_path)
            
            # Preparar resultado
            result = {
                'job_id': job_id,
                'output_files': output_files,
                'takes_count': len(takes_data),
                'processed_at': datetime.now().isoformat()
            }
            
            # Limpar arquivos temporários
            self._cleanup_temp_files(*temp_files)
            
            return result
            
        except Exception as e:
            # Limpar arquivos em caso de erro
            self._cleanup_temp_files(*temp_files)
            raise e

    def _concatenate_videos(self, video_paths, process_id):
        """Concatena múltiplos vídeos respeitando a ordem"""
        print(f"Concatenando {len(video_paths)} vídeos...")
        
        # Arquivo de saída da concatenação
        output_path = os.path.join(self.temp_folder, f"concatenated_{process_id}.mp4")
        
        # Criar arquivo de lista para FFmpeg
        list_file = os.path.join(self.temp_folder, f"concat_list_{process_id}.txt")
        
        with open(list_file, 'w') as f:
            for video_path in video_paths:
                # Escapar aspas no nome do arquivo
                escaped_path = video_path.replace("'", "'\"'\"'")
                f.write(f"file '{escaped_path}'\n")
        
        # Comando FFmpeg para concatenação
        ffmpeg_cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', list_file,
            '-c', 'copy',  # Copiar sem recodificar para ser mais rápido
            output_path
        ]
        
        print(f"Executando: {' '.join(ffmpeg_cmd)}")
        
        try:
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutos timeout
            )
            
            if result.returncode != 0:
                raise Exception(f"Erro no FFmpeg concatenação: {result.stderr}")
            
            # Limpar arquivo de lista
            os.remove(list_file)
            
            print(f"Concatenação concluída: {output_path}")
            return output_path
            
        except Exception as e:
            # Limpar arquivo de lista em caso de erro
            if os.path.exists(list_file):
                os.remove(list_file)
            raise e

    def _download_audio(self, audio_url, process_id):
        """Baixa o arquivo de áudio"""
        print(f"Baixando áudio: {audio_url}")
        
        # Detectar extensão do áudio
        parsed_url = urlparse(audio_url)
        file_extension = os.path.splitext(parsed_url.path)[1] or '.mp3'
        
        audio_path = os.path.join(self.temp_folder, f"audio_{process_id}{file_extension}")
        
        # Baixar áudio
        response = requests.get(audio_url, stream=True)
        response.raise_for_status()
        
        with open(audio_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"Áudio baixado: {audio_path}")
        return audio_path

    def _download_ass_subtitle(self, caption_url, process_id):
        """Baixa o arquivo de legendas ASS"""
        print(f"Baixando legendas ASS: {caption_url}")
        
        subtitle_path = os.path.join(self.temp_folder, f"subtitle_{process_id}.ass")
        
        # Baixar arquivo ASS
        response = requests.get(caption_url)
        response.raise_for_status()
        
        with open(subtitle_path, 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        print(f"Legendas ASS baixadas: {subtitle_path}")
        return subtitle_path

    def _process_take_with_ffmpeg(self, video_path, audio_path, subtitle_path, logo_path, process_id):
        """Processa um take completo com FFmpeg aplicando áudio, legendas ASS e logo"""
        print("Iniciando processamento final do take com FFmpeg...")
        
        # Arquivo de saída
        output_filename = f"processed_{process_id}.mp4"
        output_path = os.path.join(self.output_folder, output_filename)
        
        # Construir comando FFmpeg
        ffmpeg_cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-i', audio_path
        ]
        
        # Filtros de vídeo
        video_filters = []
        
        # Adicionar logo se disponível
        input_count = 2  # vídeo + áudio
        if logo_path:
            ffmpeg_cmd.extend(['-i', logo_path])
            input_count += 1
            
            # Configurações padrão do logo
            logo_size = SettingsHelper.get_logo_size() or 25
            logo_position = SettingsHelper.get_logo_position() or 'top-left'
            
            # Calcular posição do logo
            if logo_position == 'top-left':
                overlay_position = f"10:10"
            elif logo_position == 'top-right':
                overlay_position = f"W-w-10:10"
            elif logo_position == 'bottom-left':
                overlay_position = f"10:H-h-10"
            elif logo_position == 'bottom-right':
                overlay_position = f"W-w-10:H-h-10"
            elif logo_position == 'center':
                overlay_position = f"(W-w)/2:(H-h)/2"
            else:
                overlay_position = f"10:10"  # padrão
            
            # Filtro de logo
            scale_factor = logo_size / 100.0
            video_filters.append(f"[0:v][2:v]overlay={overlay_position}")
        
        # Combinar logo e legendas em um único filtro complexo
        if video_filters:
            # Se há logo, aplicar logo e depois legendas
            combined_filter = f"{video_filters[0]},ass={subtitle_path}"
            ffmpeg_cmd.extend(['-filter_complex', combined_filter])
        else:
            # Se não há logo, aplicar apenas legendas
            ffmpeg_cmd.extend(['-vf', f"ass={subtitle_path}"])
        
        # Mapear áudio do arquivo de áudio (substituir áudio original)
        ffmpeg_cmd.extend([
            '-map', '0:v',  # vídeo da entrada 0
            '-map', '1:a',  # áudio da entrada 1
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '128k',
            output_path
        ])
        
        print(f"Executando: {' '.join(ffmpeg_cmd)}")
        
        try:
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutos timeout
            )
            
            if result.returncode != 0:
                raise Exception(f"Erro no FFmpeg processamento: {result.stderr}")
            
            print(f"Processamento concluído: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"Erro no processamento: {e}")
            raise 

    def trim_and_join_videos(self, job_id, takes):
        """
        Corta vídeos para duração especificada e junta na ordem dos takes
        
        Args:
            job_id (str): ID do job
            takes (list): Lista de dicionários com take_number, video_url, final_clip_duration
        
        Returns:
            dict: Resultado com caminho do vídeo final
        """
        print(f"Iniciando processamento de corte e junção: {job_id}")
        print(f"Total de takes: {len(takes)}")
        
        try:
            # Lista para armazenar os vídeos cortados
            trimmed_videos = []
            temp_files = []  # Para limpeza posterior
            
            # Processar cada take
            for idx, take in enumerate(takes):
                take_number = take['take_number']
                video_url = take['video_url']
                duration = take['final_clip_duration']
                
                print(f"Processando take {take_number}: {video_url} (duração: {duration}s)")
                
                # Atualizar progresso no Redis
                progress = int((idx / len(takes)) * 80)  # 80% para downloads e cortes
                redis_service = RedisService()
                redis_service.update_trim_join_job_progress(job_id, progress)
                
                # Baixar vídeo
                video_path = self._download_video(video_url, f"{job_id}_take_{take_number}")
                temp_files.append(video_path)
                
                # Cortar vídeo para a duração especificada
                trimmed_video_path = self._trim_video(video_path, duration, job_id, take_number)
                trimmed_videos.append(trimmed_video_path)
                temp_files.append(trimmed_video_path)
            
            # Atualizar progresso - iniciando concatenação
            redis_service.update_trim_join_job_progress(job_id, 85)
            
            # Concatenar todos os vídeos
            final_output_path = self._concatenate_trimmed_videos(trimmed_videos, job_id)
            
            # Atualizar progresso - finalizado
            redis_service.update_trim_join_job_progress(job_id, 100)
            
            # Preparar resultado
            result = {
                'job_id': job_id,
                'output_path': final_output_path,
                'output_url': self._get_download_url(final_output_path),
                'takes_processed': len(takes),
                'total_duration': sum(take['final_clip_duration'] for take in takes),
                'processed_at': datetime.now().isoformat()
            }
            
            # Limpar arquivos temporários
            self._cleanup_temp_files(*temp_files)
            
            print(f"Processamento de corte e junção concluído: {job_id}")
            return result
            
        except Exception as e:
            print(f"Erro no processamento de corte e junção: {e}")
            # Tentar limpar arquivos em caso de erro
            try:
                if 'temp_files' in locals():
                    self._cleanup_temp_files(*temp_files)
            except:
                pass
            raise e

    def create_video_from_images(self, image_paths, output_path, fps=25, duration_per_image=2):
        """Cria um vídeo a partir de uma sequência de imagens"""
        print(f"Criando vídeo a partir de {len(image_paths)} imagens...")

        # Criar arquivo de lista para FFmpeg
        list_file = os.path.join(self.temp_folder, f"image_list_{uuid.uuid4()}.txt")
        with open(list_file, 'w') as f:
            for image_path in image_paths:
                f.write(f"file '{os.path.abspath(image_path)}'\n")
                f.write(f"duration {duration_per_image}\n")

        # Comando FFmpeg para criar vídeo a partir de imagens
        ffmpeg_cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', list_file,
            '-vf', f"fps={fps},format=yuv420p",
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-y',
            output_path
        ]

        print(f"Executando comando FFmpeg para criação de vídeo: {' '.join(ffmpeg_cmd)}")

        try:
            result = subprocess.run(
                ffmpeg_cmd,
                check=True,
                capture_output=True,
                text=True
            )
            print("FFmpeg executado com sucesso")
            print(f"Vídeo criado salvo em: {output_path}")
        except subprocess.CalledProcessError as e:
            print(f"Erro no FFmpeg: {e.stderr}")
            raise Exception(f"Erro ao criar vídeo com FFmpeg: {e.stderr}")
        finally:
            # Limpar arquivo de lista
            if os.path.exists(list_file):
                os.remove(list_file)

        return output_path
    
    def _trim_video(self, video_path, duration, job_id, take_number):
        """
        Corta um vídeo para a duração especificada
        
        Args:
            video_path (str): Caminho do vídeo original
            duration (float): Duração em segundos
            job_id (str): ID do job
            take_number (int): Número do take
        
        Returns:
            str: Caminho do vídeo cortado
        """
        # Arquivo de saída para o vídeo cortado
        trimmed_filename = f"trimmed_{job_id}_take_{take_number}.mp4"
        trimmed_path = os.path.join(self.temp_folder, trimmed_filename)
        
        # Comando FFmpeg para cortar o vídeo
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', video_path,
            '-t', str(duration),  # Duração do corte
            '-c', 'copy',  # Cópia rápida sem re-encoding quando possível
            '-avoid_negative_ts', 'make_zero',
            '-y',  # Sobrescrever arquivo de saída se existir
            trimmed_path
        ]
        
        print(f"Executando comando FFmpeg para corte: {' '.join(ffmpeg_cmd)}")
        
        # Executar comando
        result = subprocess.run(
            ffmpeg_cmd,
            capture_output=True,
            text=True,
            timeout=300  # Timeout de 5 minutos
        )
        
        if result.returncode != 0:
            error_msg = f"Erro no FFmpeg para corte do take {take_number}: {result.stderr}"
            print(error_msg)
            raise Exception(error_msg)
        
        print(f"Take {take_number} cortado com sucesso: {trimmed_path}")
        return trimmed_path
    
    def _concatenate_trimmed_videos(self, video_paths, job_id):
        """
        Concatena múltiplos vídeos em um único arquivo
        
        Args:
            video_paths (list): Lista de caminhos dos vídeos para concatenar
            job_id (str): ID do job
        
        Returns:
            str: Caminho do vídeo final concatenado
        """
        print(f"Concatenando {len(video_paths)} vídeos...")
        
        # Arquivo de saída final
        output_filename = f"trimmed_joined_{job_id}.mp4"
        output_path = os.path.join(self.output_folder, output_filename)
        
        # Criar arquivo de lista para FFmpeg
        concat_list_path = os.path.join(self.temp_folder, f"concat_list_{job_id}.txt")
        
        with open(concat_list_path, 'w') as f:
            for video_path in video_paths:
                # FFmpeg concat demux precisa de caminhos absolutos
                abs_path = os.path.abspath(video_path)
                f.write(f"file '{abs_path}'\n")
        
        # Comando FFmpeg para concatenação
        ffmpeg_cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_list_path,
            '-c', 'copy',  # Cópia sem re-encoding
            '-y',  # Sobrescrever arquivo de saída se existir
            output_path
        ]
        
        print(f"Executando comando FFmpeg para concatenação: {' '.join(ffmpeg_cmd)}")
        
        # Executar comando
        result = subprocess.run(
            ffmpeg_cmd,
            capture_output=True,
            text=True,
            timeout=600  # Timeout de 10 minutos para concatenação
        )
        
        if result.returncode != 0:
            error_msg = f"Erro no FFmpeg para concatenação: {result.stderr}"
            print(error_msg)
            raise Exception(error_msg)
        
        # Limpar arquivo de lista
        try:
            os.remove(concat_list_path)
        except:
            pass
        
        print(f"Concatenação concluída: {output_path}")
        return output_path

    def add_text_overlay(self, video_path, text, output_path, font_file=None, font_size=24, font_color='white', x='(w-text_w)/2', y='h-th-10', box=0, box_color='black', box_opacity=0.5):
        """Adiciona uma camada de texto a um vídeo usando FFmpeg."""
        print(f"Adicionando texto ao vídeo: {text}")

        # Escapar caracteres especiais para FFmpeg
        escaped_text = text.replace(':', '\\:').replace('\'', '\\\'').replace('"', '\\"')

        drawtext_cmd = f"fontfile='{font_file if font_file else 'sans-serif'}':"
        drawtext_cmd += f"text='{escaped_text}':"
        drawtext_cmd += f"fontcolor={font_color}:"
        drawtext_cmd += f"fontsize={font_size}:"
        drawtext_cmd += f"x={x}:y={y}:"
        drawtext_cmd += f"box={box}:"
        drawtext_cmd += f"boxcolor={box_color}@{{:.1f}}".format(box_opacity)

        ffmpeg_cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vf', f"drawtext={drawtext_cmd}",
            '-c:a', 'copy',
            '-y',
            output_path
        ]

        print(f"Comando FFmpeg para texto: {' '.join(ffmpeg_cmd)}")

        try:
            result = subprocess.run(
                ffmpeg_cmd,
                check=True,
                capture_output=True,
                text=True
            )
            print("Texto adicionado com sucesso")
        except subprocess.CalledProcessError as e:
            print(f"Erro ao adicionar texto: {e.stderr}")
            raise Exception(f"Erro ao adicionar texto ao vídeo: {e.stderr}")

        return output_path 