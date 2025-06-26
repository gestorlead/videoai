"""
Helper para facilitar o acesso às configurações do sistema
"""
from src.models.settings import Settings

class SettingsHelper:
    """Helper para acessar configurações do sistema"""
    
    @staticmethod
    def get_transcription_service():
        """Retorna o serviço de transcrição configurado"""
        return Settings.get_value('transcription_service', 'autosub')
    
    @staticmethod
    def get_google_translate_api_key():
        """Retorna a chave da API do Google Translate"""
        return Settings.get_value('google_translate_api_key', '')
    
    @staticmethod
    def get_openai_api_key():
        """Retorna a chave da API da OpenAI"""
        return Settings.get_value('openai_api_key', '')
    
    @staticmethod
    def get_instagram_prompt():
        """Retorna o prompt para Instagram"""
        default_prompt = """Crie uma legenda envolvente para Instagram baseada nesta transcrição. 
Use hashtags relevantes e mantenha um tom casual e atrativo."""
        return Settings.get_value('instagram_prompt', default_prompt)
    
    @staticmethod
    def get_tiktok_prompt():
        """Retorna o prompt para TikTok"""
        default_prompt = """Crie uma legenda viral para TikTok baseada nesta transcrição. 
Use linguagem jovem, emojis e hashtags trending."""
        return Settings.get_value('tiktok_prompt', default_prompt)
    
    @staticmethod
    def get_openai_model_transcription():
        """Retorna o modelo OpenAI para transcrição"""
        return Settings.get_value('openai_model_transcription', 'whisper-1')
    
    @staticmethod
    def get_openai_model_text():
        """Retorna o modelo OpenAI para geração de texto"""
        return Settings.get_value('openai_model_text', 'gpt-4o-mini')
    
    @staticmethod
    def has_openai_api_key():
        """Verifica se a chave da OpenAI está configurada"""
        key = SettingsHelper.get_openai_api_key()
        return key and len(key.strip()) > 0
    
    @staticmethod
    def has_google_translate_api_key():
        """Verifica se a chave do Google Translate está configurada"""
        key = SettingsHelper.get_google_translate_api_key()
        return key and len(key.strip()) > 0
    
    @staticmethod
    def should_use_openai_whisper():
        """Verifica se deve usar OpenAI Whisper para transcrição"""
        service = SettingsHelper.get_transcription_service()
        return service == 'openai_whisper' and SettingsHelper.has_openai_api_key()
    
    @staticmethod
    def get_all_settings():
        """Retorna todas as configurações organizadas por categoria"""
        return Settings.get_all()
    
    @staticmethod
    def initialize_if_needed():
        """Inicializa as configurações padrão se necessário"""
        try:
            Settings.initialize_defaults()
        except Exception as e:
            print(f"Erro ao inicializar configurações: {e}")
            return False
        return True
    
    @staticmethod
    def get_logo_path():
        """Retorna o caminho do logo"""
        return Settings.get_value('logo_path', '')
    
    @staticmethod
    def get_logo_filename():
        """Retorna o nome do arquivo de logo"""
        return Settings.get_value('logo_filename', '')
    
    @staticmethod
    def get_logo_position():
        """Retorna a posição do logo"""
        return Settings.get_value('logo_position', 'top-right')
    
    @staticmethod
    def get_logo_size():
        """Retorna o tamanho do logo"""
        return int(Settings.get_value('logo_size', '10'))
    
    @staticmethod
    def get_logo_opacity():
        """Retorna a opacidade do logo"""
        return int(Settings.get_value('logo_opacity', '80'))
    
    @staticmethod
    def has_logo():
        """Verifica se há um logo configurado"""
        logo_path = SettingsHelper.get_logo_path()
        return logo_path and len(logo_path.strip()) > 0
    
    # Configurações de Legendas
    @staticmethod
    def get_subtitle_font_size():
        """Retorna o tamanho da fonte das legendas"""
        return int(Settings.get_value('subtitle_font_size', '20'))
    
    @staticmethod
    def get_subtitle_font_family():
        """Retorna a família da fonte das legendas"""
        return Settings.get_value('subtitle_font_family', 'Arial')
    
    @staticmethod
    def get_subtitle_font_color():
        """Retorna a cor da fonte das legendas"""
        return Settings.get_value('subtitle_font_color', '#FFFFFF')
    
    @staticmethod
    def get_subtitle_background_color():
        """Retorna a cor de fundo das legendas"""
        return Settings.get_value('subtitle_background_color', '#000000')
    
    @staticmethod
    def get_subtitle_background_opacity():
        """Retorna a opacidade do fundo das legendas"""
        return int(Settings.get_value('subtitle_background_opacity', '70'))
    
    @staticmethod
    def get_subtitle_position():
        """Retorna a posição das legendas"""
        return Settings.get_value('subtitle_position', 'bottom-center')
    
    @staticmethod
    def get_subtitle_outline_color():
        """Retorna a cor do contorno das legendas"""
        return Settings.get_value('subtitle_outline_color', '#000000')
    
    @staticmethod
    def get_subtitle_outline_width():
        """Retorna a largura do contorno das legendas"""
        return int(Settings.get_value('subtitle_outline_width', '1')) 