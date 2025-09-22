import google.generativeai as genai
import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env (para teste local)
load_dotenv()

app = Flask(__name__)
CORS(app)

# --- CONFIGURAÇÃO DAS APIS ---

# Configuração da API do Gemini
try:
    # Nome da variável que a Vercel força para a chave Gemini
    gemini_api_key = os.environ.get("CHAVE_API_GEMINI")
    if not gemini_api_key:
        raise ValueError("A variável de ambiente CHAVE_API_GEMINI não foi encontrada.")
    
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')

except Exception as e:
    print(f"ERRO CRÍTICO ao configurar a API do Gemini: {e}")

# Configurações da API do WhatsApp (com nomes em PORTUGUÊS para contornar o bug da Vercel)
WHATSAPP_VERIFY_TOKEN = os.environ.get("TOKEN_DE_VERIFICACAO_DO_WHATSAPP")
WHATSAPP_ACCESS_TOKEN = os.environ.get("TOKEN_DE_ACESSO_DO_WHATSAPP")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("ID_DO_NUMERO_DE_TELEFONE_WHATSAPP")

# --- FUNÇÕES AUXILIARES ---

def read_knowledge_base():
    """Lê o conteúdo do arquivo da base de conhecimento de forma robusta."""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, 'knowledge_base.txt')
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Erro ao ler a base de conhecimento: {e}")
        return "Erro interno: não foi possível carregar a base de conhecimento."

def get_gemini_response(user_message):
    """Obtém a resposta da Gemini API."""
    knowledge_base = read_knowledge_base()
    prompt = f"""
    Você é um assistente de vendas e atendimento ao cliente chamado Adrian IA.
    Siga estritamente as regras e informações da Base de Conhecimentos abaixo.
    Não invente informações. Seja direto, profissional e siga o fluxo de conversa estipulado.
    Base de Conhecimentos:
    ---
    {knowledge_base}
    ---
    Pergunta do cliente: "{user_message}"
    Sua resposta:
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Erro ao gerar resposta da Gemini: {e}")
        return "Desculpe, não consegui processar sua pergunta no momento."

def send_whatsapp_message(recipient_id, message_text):
    """Envia a resposta de volta para o cliente no WhatsApp."""
    url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    data = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "text": {"body": message_text},
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status() 
        print(f"Mensagem enviada para {recipient_id}: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"ERRO ao enviar mensagem para o WhatsApp: {e}")

# --- ROTAS DA API (ENDPOINTS) ---

# Rota para o CHAT WEB (continua funcionando como antes)
@app.route('/api/chat', methods=['POST'])
def chat():
    # ... (código existente)

# Rota para o WEBHOOK DO WHATSAPP
@app.route('/api/whatsapp', methods=['GET', 'POST'])
def whatsapp_webhook():
    if request.method == 'GET':
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        if mode == 'subscribe' and token == WHATSAPP_VERIFY_TOKEN:
            print("Webhook verificado com sucesso!")
            return challenge, 200
        else:
            print("Falha na verificação do Webhook.")
            return 'Forbidden', 403

    if request.method == 'POST':
        body = request.get_json()
        print("Corpo da requisição POST recebida:", body)
        try:
            if body.get('object') and body.get('entry') and body['entry'][0].get('changes') and body['entry'][0]['changes'][0].get('value') and body['entry'][0]['changes'][0]['value'].get('messages'):
                message_info = body['entry'][0]['changes'][0]['value']['messages'][0]
                if message_info.get('type') == 'text':
                    user_message = message_info['text']['body']
                    sender_id = message_info['from']
                    print(f"Mensagem recebida de {sender_id}: {user_message}")
                    reply_text = get_gemini_response(user_message)
                    send_whatsapp_message(sender_id, reply_text)
            return 'OK', 200
        except Exception as e:
            print(f"ERRO ao processar mensagem do WhatsApp: {e}")
            return 'Error', 500

# Rota de verificação
@app.route('/api', methods=['GET'])
def home():
    return "Servidor Python para Chatbot está rodando."