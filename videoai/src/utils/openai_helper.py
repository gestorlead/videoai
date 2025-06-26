import os
import requests
import json
import sys
import dotenv

# Carregar variáveis de ambiente dos arquivos .env ou .env.dev se existirem
dotenv.load_dotenv('.env', override=True)
if os.path.exists('.env.dev'):
    dotenv.load_dotenv('.env.dev', override=True)

# Tentar importar o helper de configurações
try:
    from src.utils.settings_helper import SettingsHelper
    USE_SETTINGS_DB = True
except ImportError:
    USE_SETTINGS_DB = False

# URLs das APIs
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

def get_api_configuration():
    """Obtém a configuração da API baseada nas configurações do sistema ou variáveis de ambiente"""
    
    # Priorizar configurações do banco de dados se disponível
    if USE_SETTINGS_DB:
        try:
            openai_key = SettingsHelper.get_openai_api_key()
            model = SettingsHelper.get_openai_model_text()
            
            if openai_key and len(openai_key.strip()) > 0:
                print(f"DEBUG: Usando chave OpenAI das configurações do sistema", file=sys.stderr)
                return {
                    'api_key': openai_key,
                    'api_url': OPENAI_API_URL,
                    'model': model,
                    'provider': 'openai'
                }
        except Exception as e:
            print(f"DEBUG: Erro ao acessar configurações do sistema: {e}", file=sys.stderr)
    
    # Fallback para variáveis de ambiente
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

# Usar Groq por padrão se a chave estiver disponível
    if GROQ_API_KEY and len(GROQ_API_KEY.strip()) > 0:
        print(f"DEBUG: Usando API do Groq (variável de ambiente)", file=sys.stderr)
        return {
            'api_key': GROQ_API_KEY,
            'api_url': GROQ_API_URL,
            'model': "llama3-70b-8192",
            'provider': 'groq'
        }
    elif OPENAI_API_KEY and len(OPENAI_API_KEY.strip()) > 0:
        print(f"DEBUG: Usando API da OpenAI (variável de ambiente)", file=sys.stderr)
        return {
            'api_key': OPENAI_API_KEY,
            'api_url': OPENAI_API_URL,
            'model': "gpt-4o-mini",
            'provider': 'openai'
        }
    else:
        print("AVISO: Nenhuma chave de API configurada. A geração de texto não funcionará.", file=sys.stderr)
        return {
            'api_key': "",
            'api_url': OPENAI_API_URL,
            'model': "gpt-4o-mini",
            'provider': 'openai'
                 }

def get_default_prompt(transcript, platform):
    """Retorna o prompt padrão para a plataforma especificada"""
    if platform.lower() == "tiktok":
        return f"""
        Crie uma legenda atraente para um vídeo do TikTok sobre aprendizagem de inglês com base na seguinte transcrição:
        
        Transcrição: {transcript}
        
        A legenda deve:
        - Destacar dicas de aprendizagem de inglês presentes na transcrição
        - Ter entre 150-300 caracteres
        - Incluir 3-5 hashtags relevantes para aprendizagem de idiomas (#aprendendoingles #dicasdeingles #englishfluency)
        - Ser envolvente e educativa
        - Enfatizar a importância de aprender a expressão ou tema do vídeo
        - Ter um tom incentivador para quem está aprendendo inglês
        """
    else:  # Instagram por padrão
        return f"""
        Crie uma legenda atraente para um post do Instagram sobre ensino de inglês com base na seguinte transcrição:
        
        Transcrição: {transcript}
        
        A legenda deve:
        - Começar com uma dica valiosa de inglês relacionada ao conteúdo da transcrição
        - Destacar a importância da expressão ou tema abordado no uso cotidiano do inglês
        - Explicar brevemente como e quando usar a expressão ou construção gramatical mencionada
        - Ter aproximadamente 300-500 caracteres
        - Incluir 5-8 hashtags relevantes para aprendizagem de inglês (#englishlessons #dicasdeingles #aprenderingles)
        - Incluir um call-to-action convidando os seguidores a praticar ou comentar
        - Ter um tom profissional, mas amigável e encorajador para estudantes de inglês
        """

def generate_social_media_post(transcript, platform="instagram"):
    """
    Gera um texto para publicação no Instagram/TikTok baseado na transcrição do vídeo.
    
    Args:
        transcript (str): Transcrição do vídeo.
        platform (str): Plataforma para a qual o texto será criado ('instagram' ou 'tiktok').
        
    Returns:
        str: Texto formatado para publicação.
    """
    # Obter configuração da API
    config = get_api_configuration()
    if not config['api_key']:
        return "Erro: Chave da API não configurada."
    
    # Obter prompts das configurações se disponível
    if USE_SETTINGS_DB:
        try:
            if platform.lower() == "tiktok":
                prompt_template = SettingsHelper.get_tiktok_prompt()
            else:
                prompt_template = SettingsHelper.get_instagram_prompt()
            
            prompt = f"{prompt_template}\n\nTranscrição: {transcript}"
        except Exception as e:
            print(f"DEBUG: Erro ao obter prompt das configurações: {e}", file=sys.stderr)
            prompt = get_default_prompt(transcript, platform)
    else:
        prompt = get_default_prompt(transcript, platform)
    
    # Configuração da requisição para a API
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config['api_key']}"
    }
    
    data = {
        "model": config['model'],
        "messages": [
            {"role": "system", "content": "Você é um professor de inglês especialista em marketing digital que cria conteúdo educativo para redes sociais focado no ensino de inglês."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }
    
    try:
        print(f"DEBUG: Enviando requisição para API... ({config['api_url']})", file=sys.stderr)
        response = requests.post(config['api_url'], headers=headers, data=json.dumps(data), timeout=30)
        print(f"DEBUG: Resposta recebida! Status: {response.status_code}", file=sys.stderr)
        
        if response.status_code != 200:
            print(f"DEBUG: Erro na resposta: {response.text}", file=sys.stderr)
            error_text = response.json().get('error', {}).get('message', 'Erro desconhecido na API')
            return f"Erro ao gerar texto (Status {response.status_code}): {error_text}"
        
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    except requests.exceptions.Timeout:
        print("DEBUG: Timeout na requisição à API", file=sys.stderr)
        return "Erro: Tempo esgotado ao tentar conectar com a API. Tente novamente mais tarde."
    except requests.exceptions.ConnectionError:
        print("DEBUG: Erro de conexão com a API", file=sys.stderr)
        return "Erro: Não foi possível conectar-se à API. Verifique sua conexão de internet."
    except Exception as e:
        print(f"DEBUG: Erro na chamada à API: {str(e)}", file=sys.stderr)
        return f"Erro ao gerar texto: {str(e)}"

def correct_subtitles(autosub_transcript, manual_transcript):
    """
    Envia para a API a transcrição do autosub e a transcrição manual para corrigir inconsistências.
    
    Args:
        autosub_transcript (str): Transcrição gerada pelo autosub.
        manual_transcript (str): Transcrição manual fornecida pelo usuário.
        
    Returns:
        str: Transcrição corrigida no formato SRT.
    """
    # Obter configuração da API
    config = get_api_configuration()
    if not config['api_key']:
        return "Erro: Chave da API não configurada."
    
    prompt = f"""
    Compare a transcrição gerada automaticamente com a transcrição manual fornecida e corrija o arquivo SRT mantendo seu formato.
    
    Transcrição gerada automaticamente (formato SRT):
    {autosub_transcript}
    
    Transcrição manual correta:
    {manual_transcript}
    
    Instruções importantes:
    1. REMOVA COMPLETAMENTE os nomes de personagens (como "GRIFFIN:" ou "JET:") das legendas corrigidas
    2. Mantenha o formato exato do SRT com números de sequência e timestamps originais
    3. Substitua apenas o texto das falas para corresponder à transcrição manual correta
    4. Preserve as quebras de linha e a formatação das legendas
    5. Se a transcrição manual tiver diálogos com nomes de personagens, use apenas o texto da fala, removendo os nomes dos personagens
    6. Não adicione texto explicativo, apenas retorne o SRT corrigido
    
    Lembre-se que estamos trabalhando com conteúdo educativo para ensino de inglês, então a precisão das falas e expressões é essencial.
    """
    
    # Configuração da requisição para a API
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config['api_key']}"
    }
    
    data = {
        "model": config['model'],
        "messages": [
            {"role": "system", "content": "Você é um especialista em legendagem de vídeos educativos para ensino de inglês, com ampla experiência em transcrição de diálogos com múltiplos personagens."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 1500
    }
    
    try:
        print(f"DEBUG: Enviando requisição para corrigir legendas... ({config['api_url']})", file=sys.stderr)
        response = requests.post(config['api_url'], headers=headers, data=json.dumps(data), timeout=45)
        print(f"DEBUG: Resposta recebida para correção! Status: {response.status_code}", file=sys.stderr)
        
        if response.status_code != 200:
            print(f"DEBUG: Erro na resposta de correção: {response.text}", file=sys.stderr)
            error_text = response.json().get('error', {}).get('message', 'Erro desconhecido na API')
            return f"Erro ao corrigir legendas (Status {response.status_code}): {error_text}"
        
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    except requests.exceptions.Timeout:
        print("DEBUG: Timeout na requisição à API para correção", file=sys.stderr)
        return "Erro: Tempo esgotado ao tentar conectar com a API. Tente novamente mais tarde."
    except requests.exceptions.ConnectionError:
        print("DEBUG: Erro de conexão com a API para correção", file=sys.stderr)
        return "Erro: Não foi possível conectar-se à API. Verifique sua conexão de internet."
    except Exception as e:
        print(f"DEBUG: Erro na chamada à API para correção: {str(e)}", file=sys.stderr)
        return f"Erro ao corrigir legendas: {str(e)}" 