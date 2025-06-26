import json
from datetime import datetime
from src.utils.database import execute_query

class Settings:
    def __init__(self, id=None, key=None, value=None, category=None, description=None, 
                 created_at=None, updated_at=None):
        self.id = id
        self.key = key
        self.value = value
        self.category = category
        self.description = description
        self.created_at = created_at
        self.updated_at = updated_at

    @staticmethod
    def create_table():
        """Cria a tabela de configurações se não existir"""
        query = """
        CREATE TABLE IF NOT EXISTS settings (
            id SERIAL PRIMARY KEY,
            key VARCHAR(100) UNIQUE NOT NULL,
            value TEXT,
            category VARCHAR(50) NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(key);
        CREATE INDEX IF NOT EXISTS idx_settings_category ON settings(category);
        """
        execute_query(query)

    @staticmethod
    def get_by_key(key):
        """Busca uma configuração pela chave"""
        query = "SELECT * FROM settings WHERE key = %s;"
        result = execute_query(query, (key,), fetchone=True)
        
        if result:
            return Settings(
                id=result['id'],
                key=result['key'],
                value=result['value'],
                category=result['category'],
                description=result['description'],
                created_at=result['created_at'],
                updated_at=result['updated_at']
            )
        return None

    @staticmethod
    def get_by_category(category):
        """Busca todas as configurações de uma categoria"""
        query = "SELECT * FROM settings WHERE category = %s ORDER BY key;"
        results = execute_query(query, (category,), fetchall=True)
        
        settings = []
        for result in results:
            settings.append(Settings(
                id=result['id'],
                key=result['key'],
                value=result['value'],
                category=result['category'],
                description=result['description'],
                created_at=result['created_at'],
                updated_at=result['updated_at']
            ))
        return settings

    @staticmethod
    def get_all():
        """Busca todas as configurações agrupadas por categoria"""
        query = "SELECT * FROM settings ORDER BY category, key;"
        results = execute_query(query, fetchall=True)
        
        settings_by_category = {}
        for result in results:
            category = result['category']
            if category not in settings_by_category:
                settings_by_category[category] = []
            
            settings_by_category[category].append(Settings(
                id=result['id'],
                key=result['key'],
                value=result['value'],
                category=result['category'],
                description=result['description'],
                created_at=result['created_at'],
                updated_at=result['updated_at']
            ))
        return settings_by_category

    @staticmethod
    def set(key, value, category, description=None):
        """Define ou atualiza uma configuração"""
        existing = Settings.get_by_key(key)
        
        if existing:
            # Atualizar existente
            query = """
            UPDATE settings 
            SET value = %s, category = %s, description = %s, updated_at = CURRENT_TIMESTAMP 
            WHERE key = %s;
            """
            execute_query(query, (value, category, description, key))
        else:
            # Criar nova
            query = """
            INSERT INTO settings (key, value, category, description) 
            VALUES (%s, %s, %s, %s);
            """
            execute_query(query, (key, value, category, description))

    @staticmethod
    def get_value(key, default=None):
        """Obtém apenas o valor de uma configuração"""
        setting = Settings.get_by_key(key)
        return setting.value if setting else default

    @staticmethod
    def delete(key):
        """Remove uma configuração"""
        query = "DELETE FROM settings WHERE key = %s;"
        execute_query(query, (key,))

    @staticmethod
    def initialize_defaults():
        """Inicializa configurações padrão"""
        defaults = [
            # Configurações Gerais
            ('transcription_service', 'autosub', 'general', 'Serviço de transcrição (autosub ou openai_whisper)'),
            
            # Serviços de API
            ('google_translate_api_key', '', 'api_service', 'Chave da API do Google Translate'),
            ('openai_api_key', '', 'api_service', 'Chave da API da OpenAI'),
            
            # Prompts
            ('instagram_prompt', 'Crie uma legenda envolvente para Instagram baseada nesta transcrição. Use hashtags relevantes e mantenha um tom casual e atrativo.', 'prompts', 'Prompt para gerar legendas do Instagram'),
            ('tiktok_prompt', 'Crie uma legenda viral para TikTok baseada nesta transcrição. Use linguagem jovem, emojis e hashtags trending.', 'prompts', 'Prompt para gerar legendas do TikTok'),
            
            # Modelos OpenAI
            ('openai_model_transcription', 'whisper-1', 'models', 'Modelo OpenAI para transcrição'),
            ('openai_model_text', 'gpt-4o-mini', 'models', 'Modelo OpenAI para geração de texto (opções: gpt-4o-mini, gpt-4o, gpt-4.1, gpt-4.1-mini, o3, gpt-3.5-turbo)'),
            
            # Configurações de Vídeo
            ('logo_path', '', 'video', 'Caminho do arquivo de logo'),
            ('logo_filename', '', 'video', 'Nome do arquivo de logo'),
            ('logo_position', 'top-right', 'video', 'Posição do logo no vídeo (top-left, top-right, bottom-left, bottom-right, center)'),
            ('logo_size', '25', 'video', 'Tamanho do logo em porcentagem da largura do vídeo (1-100)'),
            ('logo_opacity', '80', 'video', 'Opacidade do logo em porcentagem (10-100)'),
            
            # Configurações de Legendas
            ('subtitle_font_size', '20', 'subtitles', 'Tamanho da fonte das legendas (10-40)'),
            ('subtitle_font_family', 'Arial', 'subtitles', 'Família da fonte das legendas (Arial, Helvetica, Times, Verdana, Impact)'),
            ('subtitle_font_color', '#FFFFFF', 'subtitles', 'Cor da fonte das legendas (formato hexadecimal)'),
            ('subtitle_background_color', '#000000', 'subtitles', 'Cor de fundo das legendas (formato hexadecimal)'),
            ('subtitle_background_opacity', '70', 'subtitles', 'Opacidade do fundo das legendas (0-100, 0=transparente)'),
            ('subtitle_position', 'bottom-center', 'subtitles', 'Posição das legendas (top-left, top-center, top-right, bottom-left, bottom-center, bottom-right)'),
            ('subtitle_height_offset', '80', 'subtitles', 'Distância da borda em pixels para posição da legenda'),
            ('subtitle_outline_color', '#000000', 'subtitles', 'Cor do contorno das legendas (formato hexadecimal)'),
            ('subtitle_outline_width', '1', 'subtitles', 'Largura do contorno das legendas (0-3)'),
        ]
        
        for key, value, category, description in defaults:
            if not Settings.get_by_key(key):
                Settings.set(key, value, category, description)

    def to_dict(self):
        """Converte para dicionário"""
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'category': self.category,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 