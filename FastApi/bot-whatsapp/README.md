<div align="center">
  <h1>🤖 Bot WhatsApp</h1>
  <p><strong>Atendimento automatizado com IA — Baileys + FastAPI + Groq</strong></p>
  <p>
    <img src="https://img.shields.io/badge/Node.js-22.x-339933?logo=node.js&logoColor=white" alt="Node.js">
    <img src="https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white" alt="Python">
    <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white" alt="FastAPI">
    <img src="https://img.shields.io/badge/Groq_API-OpenAI%20compatível-F55036?logo=groq&logoColor=white" alt="Groq">
    <img src="https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white" alt="SQLite">
  </p>
</div>

---

## 📋 Sobre

Bot para atendimento automatizado no WhatsApp com suporte a **menu interativo**, **conversas com IA** (Groq), **agendamento de horários** e **banco de dados** para histórico de clientes.

A arquitetura separa a **conexão com o WhatsApp** (Node.js + Baileys — leve, ~100 MB RAM) da **lógica do bot** (Python + FastAPI), permitindo manutenção independente.

---

## ✨ Funcionalidades

| Funcionalidade | Detalhes |
|---|---|
| 🧭 **Menu interativo** | Informações, agendamento, conversa com IA, falar com atendente |
| 🧠 **IA (Groq)** | Respostas inteligentes usando modelos como `openai/gpt-oss-120b` |
| 📅 **Agendamento** | Fluxo guia: nome → serviço → data/hora → confirmação |
| 🗄️ **Banco de dados** | SQLite com tabelas para clientes, conversas e agendamentos |
| 🔄 **Histórico** | Todas as mensagens e respostas são armazenadas |
| 📊 **Endpoints REST** | Consulta de clientes e agendamentos via API |
| 🖥️ **Dashboard web** | Painel administrativo com senha para gerenciar tudo |

---

## 🖥️ Dashboard Administrativo

O bot inclui um **painel web** para gerenciar tudo visualmente.

```
Acesse: http://localhost:8000/admin/
Senha:  definida na primeira vez que acessar o dashboard
```

**Funcionalidades do dashboard:**

| Aba | Descrição |
|---|---|
| **Visão Geral** | Estatísticas, últimas conversas, próximos agendamentos |
| **Clientes** | Lista com busca, editar nome, ver conversa |
| **Conversas** | Histórico completo de mensagens + enviar resposta manual |
| **Agendamentos** | Gerenciar status: confirmar, cancelar, concluir |
| **Configurações** | IA (API key, modelo), whitelist de números autorizados |

O dashboard é **protegido por senha** — definida na primeira vez que acessar. Todas as credenciais ficam salvas no banco SQLite.

---

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────┐
│                    WhatsApp                          │
└──────────────────┬──────────────────────────────────┘
                   │ WebSocket (Baileys)
┌──────────────────▼──────────────────────────────────┐
│              Gateway (Node.js)                       │
│  • Conecta ao WhatsApp via Baileys                   │
│  • Gera QR code para autenticação                    │
│  • API REST para enviar mensagens                    │
│  • Envia webhooks para o bot                         │
│  • Porta 3001                                        │
└──────────────────┬──────────────────────────────────┘
                   │ HTTP (Webhook + API)
┌──────────────────▼──────────────────────────────────┐
│              Bot (Python FastAPI)                    │
│  • Processa mensagens (menu / IA)                    │
│  • Gerencia estados do cliente                       │
│  • Persiste dados no SQLite                          │
│  • Integração com Groq API                           │
│  • Porta 8000                                        │
└─────────────────────────────────────────────────────┘
```

---

## 🚀 Começando

### Pré-requisitos

- **Node.js** 18+ (recomendado 22)
- **Python** 3.11+
- Conta na [Groq](https://console.groq.com) para obter uma chave de API

### 1. Clonar e configurar

```bash
# Instalar dependências do gateway
cd gateway
npm install

# Instalar dependências do bot
cd ../bot
pip install -r requirements.txt
```

### 2. Configurar

O bot funciona com um `.env` mínimo. As demais configurações (chave da IA, modelo, whitelist) são feitas pelo **dashboard** na primeira vez que você acessar.

```env
GATEWAY_URL=http://localhost:3001
DATABASE_URL=sqlite:///./bot.db
```

> 💡 **Modelos disponíveis na Groq:** `openai/gpt-oss-120b`, `gemma2-9b-it`, `llama-3.3-70b-versatile`, `mixtral-8x7b-32768`

### 3. Iniciar o Gateway (WhatsApp)

```bash
cd gateway
npm start
```

Um **QR code** será exibido no terminal. Abra o WhatsApp no celular → Menu → Aparelhos conectados → Conectar um dispositivo. Escaneie o QR code.

O gateway está pronto quando aparecer:
```
[Gateway] HTTP server running on port 3001
[Gateway] Connected as Nome do Contato
```

### 4. Iniciar o Bot

Em outro terminal:

```bash
cd bot
python main.py
```

```
[Bot] Database initialized
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 5. Testar

Envie uma mensagem para o número conectado. O bot responderá com o menu:

```
╔══════════════════════╗
║       ATENDIMENTO     ║
╚══════════════════════╝

1️⃣ Informações
2️⃣ Agendar horário
3️⃣ Falar com o Bot 🤖
4️⃣ Falar com atendente
5️⃣ Sair
```

---

## 📡 Endpoints da API

### Gateway (porta 3001)

| Método | Rota | Descrição | Corpo (JSON) |
|---|---|---|---|
| `GET` | `/health` | Status da conexão | — |
| `POST` | `/send` | Enviar mensagem de texto | `{ "to": "5511999998888@s.whatsapp.net", "text": "Olá" }` |
| `POST` | `/send-image` | Enviar imagem | `{ "to": "...", "imageUrl": "...", "text": "opcional" }` |

### Bot (porta 8000)

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/webhook` | Webhook recebido do gateway |
| `GET` | `/clientes` | Listar todos os clientes |
| `GET` | `/agendamentos` | Listar todos os agendamentos |
| `POST` | `/admin/login` | Login no dashboard |
| `GET` | `/admin/` | Dashboard web |
| `GET` | `/api/stats` | Estatísticas do sistema |
| `GET` | `/api/conversas/{telefone}` | Conversas de um cliente |
| `PUT` | `/api/agendamentos/{id}` | Atualizar status do agendamento |
| `PUT` | `/api/clientes/{telefone}/nome` | Editar nome do cliente |
| `GET` | `/api/whitelist` | Listar whitelist |
| `PUT` | `/api/whitelist` | Atualizar whitelist |
| `POST` | `/api/send` | Enviar mensagem manualmente |

Exemplo de resposta de `/clientes`:

```json
[
  {
    "id": 1,
    "telefone": "5511999998888@s.whatsapp.net",
    "nome": "",
    "estado": "inicio",
    "created_at": "2026-06-30T13:30:00"
  }
]
```

---

## 🧠 Fluxo de mensagens

```
Usuário envia "Olá"
       │
       ▼
Gateway recebe → envia webhook POST para /webhook
       │
       ▼
Bot verifica estado do cliente no banco
       │
       ├── Se for número/menu → processa_menu()
       │     ├── 1 → exibe informações
       │     ├── 2 → inicia fluxo de agendamento
       │     ├── 3 → entra em modo conversa (IA)
       │     ├── 4 → transfere para atendente
       │     └── 5 → encerra
       │
       └── Se for texto livre →
             ├── Se modo "falando_bot" → IA (mantém estado)
             ├── Se modo "falando_atendente" → mensagem fixa
             └── Senão → IA (volta ao menu após resposta)
       │
       ▼
Bot envia resposta via POST /send do gateway
       │
       ▼
Gateway entrega a mensagem no WhatsApp
```

---

## 🗃️ Banco de Dados

O SQLite é criado automaticamente em `bot/bot.db` com 3 tabelas:

| Tabela | Descrição | Campos principais |
|---|---|---|
| `clientes` | Dados dos clientes | telefone, nome, estado, dados (JSON) |
| `conversas` | Histórico de mensagens | telefone, mensagem, resposta, tipo |
| `agendamentos` | Agendamentos | telefone, nome, data_hora, servico, status |

---

## 🔧 Personalização

### Alterar o menu

Edite as constantes em `bot/handlers/menu.py`:

```python
INFORMACOES = """📌 *Horários:* Seg-Sex 8h-18h | Sáb 8h-12h
📌 *Formas de pagamento:* Cartão, PIX, Boleto
📌 *Prazo de entrega:* Até 3 dias úteis"""
```

### Alterar o prompt da IA

Edite `SYSTEM_PROMPT` em `bot/handlers/ai.py`:

```python
SYSTEM_PROMPT = """Você é um assistente de atendimento...
Regras:
- Seja educado, profissional e objetivo
- Responda em português brasileiro"""
```

### Modelos de IA disponíveis na Groq

| Modelo | Contexto | Ideal para |
|---|---|---|
| `openai/gpt-oss-120b` | 32K | Atendimento geral |
| `llama-3.3-70b-versatile` | 128K | Respostas detalhadas |
| `gemma2-9b-it` | 8K | Respostas rápidas |
| `mixtral-8x7b-32768` | 32K | Conversas longas |

---

## 📁 Estrutura do Projeto

```
bot-whatsapp/
├── gateway/                    # 🟢 Conexão WhatsApp
│   ├── index.js                #    Gateway Baileys + Express
│   ├── package.json            #    Dependências Node.js
│   └── .env                    #    Configurações do gateway
│
├── bot/                        # 🔵 Lógica do bot
│   ├── main.py                 #    FastAPI (webhook + endpoints + dashboard)
│   ├── config.py               #    Variáveis de ambiente
│   ├── database.py             #    Modelos SQLite
│   ├── .env                    #    Chave da API + configurações
│   ├── requirements.txt        #    Dependências Python
│   ├── static/
│   │   └── dashboard.html      #    🖥️ Dashboard administrativo
│   └── handlers/
│       ├── __init__.py
│       ├── menu.py             #    Textos e estados do menu
│       └── ai.py               #    Integração com Groq
│
├── app.py                      # (reservado)
└── README.md
```

---

## ⚠️ Observações

- O Baileys usa o protocolo do WhatsApp Web — o número precisa estar **ativo no WhatsApp** e o celular precisa ter **conexão com internet** para manter o pareamento.
- Em caso de desconeção, o gateway tenta reconectar automaticamente após 5 segundos.
- Se o dispositivo for **deslogado**, delete a pasta `gateway/auth_info/` e reinicie o gateway para gerar um novo QR code.

---

## 📄 Licença

MIT
