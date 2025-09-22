import google.generativeai as genai
import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
CORS(app)

# --- CONFIGURAÇÃO DAS APIS ---
try:
    gemini_api_key = os.environ.get("CHAVE_API_GEMINI")
    if not gemini_api_key:
        raise ValueError("A variável de ambiente CHAVE_API_GEMINI não foi encontrada.")
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
except Exception as e:
    print(f"ERRO CRÍTICO ao configurar a API do Gemini: {e}")

# NOMES EM PORTUGUÊS PARA CONTORNAR O BUG DA VERCEL
WHATSAPP_VERIFY_TOKEN = os.environ.get("TOKEN_DE_VERIFICACAO_DO_WHATSAPP")
WHATSAPP_ACCESS_TOKEN = os.environ.get("TOKEN_DE_ACESSO_DO_WHATSAPP")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("ID_DO_NUMERO_DE_TELEFONE_WHATSAPP")

# --- FUNÇÕES AUXILIARES ---

def read_knowledge_base():
    # ... (código existente, sem alterações)
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, 'knowledge_base.txt')
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Erro ao ler a base de conhecimento: {e}")
        return "Erro interno: não foi possível carregar a base de conhecimento."

def get_gemini_response(user_message):
    # ... (código existente, sem alterações)
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
    
    # !!! INÍCIO DOS LOGS DE DEPURAÇÃO !!!
    print("--- INICIANDO ENVIO PARA WHATSAPP ---")
    print(f"ID do Número de Telefone lido da Vercel: {WHATSAPP_PHONE_NUMBER_ID}")
    print(f"Token de Acesso Existe? {WHATSAPP_ACCESS_TOKEN is not None}")
    print(f"ID do Destinatário: {recipient_id}")
    # !!! FIM DOS LOGS DE DEPURAÇÃO !!!

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
        print(f"SUCESSO ao enviar para a API da Meta. Status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"ERRO DEFINITIVO ao enviar mensagem para o WhatsApp: {e}")
        print(f"Detalhes do erro da Meta: {e.response.text if e.response else 'Sem detalhes'}")


# --- ROTAS DA API ---

# Rota para o CHAT WEB
@app.route('/api/chat', methods=['POST'])
def chat():
    # ... (código existente, sem alterações)
    try:
        data = request.json
        user_message = data.get('message')
        if not user_message:
            return jsonify({'error': 'Nenhuma mensagem recebida'}), 400
        reply_text = get_gemini_response(user_message)
        return jsonify({'reply': reply_text})
    except Exception as e:
        print(f"Erro na rota /api/chat: {e}")
        return jsonify({'error': 'Ocorreu um erro interno.'}), 500

# Rota para o WEBHOOK DO WHATSAPP
@app.route('/api/whatsapp', methods=['GET', 'POST'])
def whatsapp_webhook():
    # ... (código existente, sem alterações)
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
            if (body.get("object") and body.get("entry") and body["entry"][0].get("changes") and body["entry"][0]["changes"][0].get("value") and body["entry"][0]["changes"][0]["value"].get("messages") and body["entry"][0]["changes"][0]["value"]["messages"][0]):
                message_info = body["entry"][0]["changes"][0]["value"]["messages"][0]
                if message_info.get("type") == "text":
                    user_message = message_info["text"]["body"]
                    sender_id = message_info["from"]
                    print(f"MENSAGEM DE TEXTO recebida de {sender_id}: {user_message}")
                    reply_text = get_gemini_response(user_message)
                    send_whatsapp_message(sender_id, reply_text)
            else:
                print("Recebida uma notificação do WhatsApp que não é uma mensagem de texto de usuário. Ignorando.")
            return "OK", 200
        except Exception as e:
            print(f"ERRO CRÍTICO ao processar webhook: {e}")
            return "OK", 200

# Rota de verificação
@app.route('/api', methods=['GET'])
def home():
    return "Servidor Python para Chatbot está rodando."