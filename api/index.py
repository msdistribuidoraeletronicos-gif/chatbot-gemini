import google.generativeai as genai
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

app = Flask(__name__)
CORS(app)  # Habilita o CORS para permitir requisições do frontend

# Configuração da API do Gemini
try:
    api_key = os.environ.get("CHAVE_API_GEMINI")
    if not api_key:
        raise ValueError("A variável de ambiente GEMINI_API_KEY não foi encontrada.")
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-pro-latest')

except Exception as e:
    print(f"Erro ao configurar a API do Gemini: {e}")
    # Se houver erro na configuração, as rotas não funcionarão corretamente.
    # Você pode querer adicionar um tratamento de erro mais robusto aqui.

def read_knowledge_base():
    """Lê o conteúdo do arquivo da base de conhecimento de forma robusta."""
    try:
        # Constrói o caminho absoluto para o arquivo, garantindo que funcione localmente e na Vercel
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, 'knowledge_base.txt')
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "Erro: Arquivo knowledge_base.txt não encontrado."
    except Exception as e:
        return f"Erro ao ler o arquivo: {e}"

# Rota principal para o chat
@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message')

        if not user_message:
            return jsonify({'error': 'Nenhuma mensagem recebida'}), 400

        knowledge_base = read_knowledge_base()
        
        # O prompt que instrui o modelo
        prompt = f"""
        Você é um assistente de vendas e atendimento ao cliente chamado Adrian IA.
        Sua principal função é seguir estritamente as regras e informações contidas na Base de Conhecimentos abaixo.
        Não invente informações e não desvie das estratégias definidas. Seja direto, profissional e siga o fluxo de conversa estipulado.
        Se o cliente perguntar algo que não está na Base de Conhecimentos, responda que você não tem essa informação e que irá verificar.

        ---
        Base de Conhecimentos:
        {knowledge_base}
        ---

        Conversa anterior:
        (Histórico da conversa será inserido aqui, se aplicável)

        Pergunta do cliente: "{user_message}"

        Sua resposta:
        """

        # Gera a resposta usando o modelo Gemini
        response = model.generate_content(prompt)
        
        return jsonify({'reply': response.text})

    except Exception as e:
        # Log do erro no servidor para depuração
        print(f"Ocorreu um erro no servidor: {e}")
        # Resposta de erro genérica para o cliente
        return jsonify({'error': 'Ocorreu um erro interno ao processar sua solic-itação.'}), 500

# Rota de verificação (opcional, bom para testar se o servidor está no ar)
@app.route('/api', methods=['GET'])
def home():
    return "Servidor Python está rodando."

# O Vercel usa 'app' como padrão
if __name__ == '__main__':
    # Este bloco não é usado pela Vercel, mas é útil para testes locais
    app.run(debug=True)