import os
import subprocess
import requests
from datetime import datetime
from urllib.parse import urlparse
import tempfile
import re

# Adicionar import para tradução alternativa
try:
    from googletrans import Translator
    GOOGLETRANS_AVAILABLE = True
except ImportError:
    GOOGLETRANS_AVAILABLE = False
    print("AVISO: googletrans não disponível. Só será possível usar Google Translate API oficial.")

class AudioProcessor:
    def __init__(self):
        self.upload_folder = os.environ.get('UPLOAD_FOLDER', '/app/uploads')
        
        # Tentar carregar API key das configurações do banco
        self.google_api_key = self._get_google_api_key()
        
        # Inicializar tradutor alternativo
        if GOOGLETRANS_AVAILABLE:
            try:
                self.translator = Translator()
            except:
                self.translator = None
        else:
            self.translator = None
        
        # Criar pasta de uploads se não existir
        os.makedirs(self.upload_folder, exist_ok=True)
    
    def _get_google_api_key(self):
        """Obtém a API key do Google Translate das configurações ou variável de ambiente"""
        try:
            # Tentar carregar das configurações do banco
            from src.utils.settings_helper import SettingsHelper
            api_key = SettingsHelper.get_google_translate_api_key()
            if api_key and len(api_key.strip()) > 0:
                print("DEBUG: Usando Google Translate API key das configurações do sistema")
                return api_key
        except Exception as e:
            print(f"DEBUG: Erro ao acessar configurações do sistema: {e}")
        
        # Fallback para variável de ambiente
        env_key = os.environ.get('GOOGLE_TRANSLATE_API_KEY', '')
        if env_key:
            print("DEBUG: Usando Google Translate API key da variável de ambiente")
            return env_key
        
        print("AVISO: Nenhuma API key do Google Translate configurada")
        return ''
    
    def _translate_text_fallback(self, text, target_language='pt'):
        """Traduz texto usando googletrans como fallback"""
        if not self.translator:
            raise Exception("Serviço de tradução alternativo não disponível")
        
        try:
            # Mapear códigos de idioma se necessário
            lang_map = {
                'pt': 'pt',
                'pt-BR': 'pt',
                'pt-PT': 'pt'
            }
            target_lang = lang_map.get(target_language, target_language)
            
            result = self.translator.translate(text, src='en', dest=target_lang)
            return result.text
        except Exception as e:
            print(f"Erro na tradução alternativa: {e}")
            raise Exception(f"Falha na tradução alternativa: {str(e)}")
    
    def _translate_text(self, text, target_language='pt'):
        """Traduz texto usando a API do Google Translate com fallback"""
        # Primeiro, tentar API oficial se a chave estiver disponível
        if self.google_api_key:
            try:
                url = f"https://translation.googleapis.com/language/translate/v2?key={self.google_api_key}"
                
                data = {
                    'q': text,
                    'source': 'en',
                    'target': target_language
                }
                
                response = requests.post(url, data=data, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                return result['data']['translations'][0]['translatedText']
                
            except Exception as e:
                print(f"Erro na API oficial do Google Translate: {e}")
                print("Tentando método alternativo...")
                
                # Usar fallback se disponível
                if self.translator:
                    try:
                        return self._translate_text_fallback(text, target_language)
                    except Exception as fallback_error:
                        print(f"Erro no método alternativo: {fallback_error}")
                        raise Exception(f"Falha em ambos os métodos de tradução. API oficial: {str(e)}. Alternativo: {str(fallback_error)}")
                else:
                    raise Exception(f"API do Google Translate falhou e método alternativo não disponível: {str(e)}")
        else:
            # Se não houver API key, usar apenas o método alternativo
            if self.translator:
                print("API key não configurada. Usando método alternativo de tradução...")
                return self._translate_text_fallback(text, target_language)
            else:
                raise Exception("Nenhum método de tradução disponível. Configure uma API key do Google Translate ou instale 'googletrans'.")
    
    def _translate_srt_file(self, input_srt_path, output_srt_path, target_language='pt'):
        """Traduz um arquivo SRT usando nossa própria implementação"""
        try:
            print(f"Traduzindo SRT para {target_language} usando implementação própria...")
            
            # Ler arquivo SRT original
            with open(input_srt_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Regex para extrair texto das legendas (ignorando números e timestamps)
            srt_pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\d+\n|\n*$)'
            matches = re.findall(srt_pattern, content, re.DOTALL)
            
            translated_content = ""
            
            for i, (number, timestamp, text) in enumerate(matches):
                # Limpar o texto (remover quebras de linha extras)
                clean_text = text.strip().replace('\n', ' ')
                
                if clean_text:
                    # Traduzir o texto
                    translated_text = self._translate_text(clean_text, target_language)
                    
                    # Reconstruir a entrada SRT
                    translated_content += f"{number}\n{timestamp}\n{translated_text}\n\n"
                    
                    print(f"Traduzido {i+1}/{len(matches)}: {clean_text[:50]}...")
                else:
                    # Manter entrada vazia
                    translated_content += f"{number}\n{timestamp}\n{clean_text}\n\n"
            
            # Salvar arquivo traduzido
            with open(output_srt_path, 'w', encoding='utf-8') as f:
                f.write(translated_content)
            
            print(f"Arquivo SRT traduzido salvo: {output_srt_path}")
            
        except Exception as e:
            print(f"Erro ao traduzir SRT: {e}")
            raise
    
    def download_audio(self, audio_url, job_id):
        """Download do arquivo de áudio"""
        try:
            # Criar pasta específica para o job
            job_folder = os.path.join(self.upload_folder, 'api_jobs', job_id)
            os.makedirs(job_folder, exist_ok=True)
            
            # Fazer o download
            print(f"Baixando áudio de: {audio_url}")
            response = requests.get(audio_url, stream=True, timeout=300)
            response.raise_for_status()
            
            # Determinar nome do arquivo
            parsed_url = urlparse(audio_url)
            filename = os.path.basename(parsed_url.path)
            
            if not filename or '.' not in filename:
                content_type = response.headers.get('Content-Type', '')
                if 'audio/mpeg' in content_type or 'audio/mp3' in content_type:
                    filename = f"{job_id}_audio.mp3"
                elif 'audio/wav' in content_type:
                    filename = f"{job_id}_audio.wav"
                elif 'audio/mp4' in content_type or 'audio/m4a' in content_type:
                    filename = f"{job_id}_audio.m4a"
                else:
                    filename = f"{job_id}_audio.mp3"  # Default
            
            # Salvar arquivo
            filepath = os.path.join(job_folder, filename)
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            print(f"Áudio baixado: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"Erro ao baixar áudio: {e}")
            raise
    
    def generate_with_transcript(self, audio_path, transcript, target_language):
        """Gera legendas usando transcript fornecido"""
        try:
            print(f"Gerando legendas com transcript fornecido para {target_language}...")
            
            base_path = os.path.splitext(audio_path)[0]
            
            # Gerar arquivo SRT simples com o transcript
            en_srt_path = f"{base_path}_en.srt"
            self._create_simple_srt(transcript, en_srt_path)
            
            # Traduzir apenas se não for inglês
            pt_srt_path = None
            if target_language != "en":
                pt_srt_path = f"{base_path}_{target_language}.srt"
                # Usar nossa própria tradução ao invés do autosub
                self._translate_srt_file(en_srt_path, pt_srt_path, target_language)
            
            return en_srt_path, pt_srt_path
            
        except Exception as e:
            print(f"Erro ao gerar legendas com transcript: {e}")
            raise
    
    def generate_auto_transcription(self, audio_path, target_language):
        """Gera legendas usando transcrição automática (autosub)"""
        try:
            print(f"Gerando legendas com transcrição automática para {target_language}...")
            
            base_path = os.path.splitext(audio_path)[0]
            
            # Gerar legendas em inglês
            en_srt_path = f"{base_path}_en.srt"
            self._generate_english_with_autosub(audio_path, en_srt_path)
            
            # Gerar legendas em português apenas se solicitado
            pt_srt_path = None
            if target_language != "en":
                pt_srt_path = f"{base_path}_{target_language}.srt"
                # Usar nossa própria tradução ao invés do autosub
                self._translate_srt_file(en_srt_path, pt_srt_path, target_language)
            
            return en_srt_path, pt_srt_path
            
        except Exception as e:
            print(f"Erro ao gerar legendas automáticas: {e}")
            raise
    
    def _create_simple_srt(self, transcript, output_path):
        """Cria arquivo SRT simples a partir do transcript"""
        words = transcript.split()
        chunks = []
        
        # Dividir em chunks de 8 palavras
        chunk_size = 8
        for i in range(0, len(words), chunk_size):
            chunk = ' '.join(words[i:i+chunk_size])
            chunks.append(chunk)
        
        # Criar SRT com timestamps (3 segundos por chunk)
        srt_content = ""
        for i, chunk in enumerate(chunks):
            start_time = i * 3
            end_time = (i + 1) * 3
            
            start_formatted = self._seconds_to_srt_time(start_time)
            end_formatted = self._seconds_to_srt_time(end_time)
            
            srt_content += f"{i + 1}\n"
            srt_content += f"{start_formatted} --> {end_formatted}\n"
            srt_content += f"{chunk}\n\n"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)
        
        print(f"SRT simples criado: {output_path}")
    
    def _generate_english_with_autosub(self, audio_path, output_path):
        """Gera legendas em inglês usando autosub"""
        try:
            command = [
                'autosub',
                audio_path,
                '-o', output_path,
                '--format', 'srt'
            ]
            
            print(f"Executando: {' '.join(command)}")
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            
            if not os.path.exists(output_path):
                raise Exception("Arquivo SRT em inglês não foi gerado")
            
            print(f"Legendas em inglês geradas: {output_path}")
            
        except subprocess.CalledProcessError as e:
            print(f"Erro no autosub (inglês): {e.stderr}")
            raise Exception(f"Falha ao gerar legendas em inglês: {e.stderr}")
    
    def _generate_portuguese_with_autosub(self, audio_path, output_path):
        """Gera legendas em português usando autosub"""
        try:
            command = [
                'autosub',
                audio_path,
                '-S', 'en',
                '-D', 'pt',
                '-o', output_path,
                '--format', 'srt'
            ]
            
            if self.google_api_key:
                command.extend(['-K', self.google_api_key])
            
            print(f"Executando: {' '.join(command)}")
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            
            if not os.path.exists(output_path):
                raise Exception("Arquivo SRT em português não foi gerado")
            
            print(f"Legendas em português geradas: {output_path}")
            
        except subprocess.CalledProcessError as e:
            print(f"Erro no autosub (português): {e.stderr}")
            raise Exception(f"Falha ao gerar legendas em português: {e.stderr}")
    
    def _seconds_to_srt_time(self, seconds):
        """Converte segundos para formato SRT (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"
    
    def process_audio(self, job_id, audio_url, transcript=None, target_language="pt", progress_callback=None):
        """Processa áudio completo - método principal chamado pelo worker"""
        try:
            print(f"Iniciando processamento do job {job_id} (target: {target_language})")
            
            if progress_callback:
                progress_callback(5)
            
            # 1. Download do áudio
            audio_path = self.download_audio(audio_url, job_id)
            
            if progress_callback:
                progress_callback(30)
            
            # 2. Gerar legendas
            if transcript:
                # Usar transcript fornecido
                en_srt_path, pt_srt_path = self.generate_with_transcript(audio_path, transcript, target_language)
            else:
                # Transcrição automática
                en_srt_path, pt_srt_path = self.generate_auto_transcription(audio_path, target_language)
            
            if progress_callback:
                progress_callback(80)
            
            # 3. Ler conteúdo dos arquivos SRT
            with open(en_srt_path, 'r', encoding='utf-8') as f:
                en_content = f.read()
            
            # 4. Preparar resultado
            result = {
                'job_id': job_id,
                'audio_url': audio_url,
                'subtitles': {
                    'en': {
                        'language': 'en',
                        'content': en_content,
                        'format': 'srt'
                    }
                },
                'processed_at': datetime.utcnow().isoformat(),
                'transcript_provided': transcript is not None
            }
            
            # Adicionar português apenas se solicitado e arquivo existe
            if target_language == "pt" and pt_srt_path and os.path.exists(pt_srt_path):
                with open(pt_srt_path, 'r', encoding='utf-8') as f:
                    pt_content = f.read()
                
                result['subtitles']['pt'] = {
                    'language': 'pt',
                    'content': pt_content,
                    'format': 'srt'
                }
            
            if progress_callback:
                progress_callback(100)
            
            print(f"Job {job_id} processado com sucesso")
            return result
            
        except Exception as e:
            print(f"Erro ao processar job {job_id}: {e}")
            raise
        finally:
            # Limpar arquivos temporários
            try:
                self.cleanup_job_files(job_id)
            except:
                pass  # Não falhar se não conseguir limpar

    def cleanup_job_files(self, job_id):
        """Remove arquivos do job"""
        try:
            job_folder = os.path.join(self.upload_folder, 'api_jobs', job_id)
            if os.path.exists(job_folder):
                import shutil
                shutil.rmtree(job_folder)
                print(f"Arquivos do job {job_id} removidos")
        except Exception as e:
            print(f"Erro ao limpar arquivos do job {job_id}: {e}") 