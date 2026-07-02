<div align="center">
  <h1>Bot WhatsApp</h1>
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

## Sobre

Bot para atendimento automatizado no WhatsApp com suporte a **menu interativo**, **conversas com IA** (Groq), **reconhecimento de imagens** (Groq Vision), **transcrição de áudio** (faster-whisper), **agendamento de horários** e **banco de dados** para histórico de clientes.

A arquitetura separa a **conexão com o WhatsApp** (Node.js + Baileys — leve, ~100 MB RAM) da **lógica do bot** (Python + FastAPI), permitindo manutenção independente e hot-reload do bot sem perder a conexão com o WhatsApp.

---

## Funcionalidades

| Funcionalidade | Detalhes |
|---|---|
| **Menu interativo** | Informações, agendamento, conversa com IA, falar com atendente |
| **IA (Groq)** | Respostas inteligentes com fallback automático entre modelos |
| **Visão computacional** | Análise de imagens com Groq Vision (`llama-3.2-11b-vision`) |
| **Transcrição de áudio** | Áudios do WhatsApp transcritos com faster-whisper (local, gratuito) |
| **Agendamento** | Fluxo guia: nome → serviço → data/hora → confirmação |
| **Banco de dados** | SQLite com tabelas para clientes, conversas, agendamentos e cache |
| **Cache de respostas** | Evita chamadas repetidas à API para perguntas frequentes |
| **Histórico** | Todas as mensagens e respostas armazenadas |
| **Endpoints REST** | Consulta de clientes, conversas e agendamentos via API |
| **Dashboard web** | Painel administrativo protegido por senha |
| **Senha hasheada** | Admin password armazenada com bcrypt |
| **API key criptografada** | Chave da Groq criptografada em repouso (Fernet/AES) |
| **Validação de entrada** | Schemas Pydantic + validação de JID no gateway |
| **Logging estruturado** | structlog (Python) + pino (Node.js) |
| **Testes automatizados** | pytest com 13 testes |
| **Migrações (Alembic)** | Versionamento do schema do banco |
| **Rate limiting** | slowapi (Python) + express-rate-limit (Node.js) |
| **Webhook assíncrono** | FastAPI BackgroundTasks + retry exponencial (3 tentativas) |
| **CSRF** | Verificação de Origin/Referer no dashboard |
| **Grupos** | Suporte opcional a grupos WhatsApp (@g.us, configurável) |
| **Whitelist** | Controle de quais números podem interagir com o bot — fora da lista são ignorados |

---

## Whitelist (Lista de Autorizados)

A whitelist controla **quem pode falar com o bot**. Quando ativada, apenas números cadastrados são processados — os demais recebem `blocked: true` e são ignorados.

### Como funciona

- A whitelist armazena apenas o **número** (sem `@s.whatsapp.net` ou `@lid`), ex: `5511999998888`
- Para contas **normais** (WhatsApp no celular), o número antes do `@s.whatsapp.net` **é** o telefone — a whitelist funciona direto
- Para **dispositivos vinculados** (Lid), o identificador `@lid` é opaco e **não** corresponde ao número real. Nesse caso, é necessário adicionar o Lid ID (número antes do `@lid`) na whitelist

### Formato correto

```
5511999998888         # numero internacional sem + e sem @
126186290155742       # Lid ID (para dispositivos vinculados)
```

### Gerenciamento

- **Dashboard**: Aba Configurações → campo Whitelist (um número por linha ou separado por vírgula)
- **Desativar**: Marque "Whitelist Ativada" como off no dashboard, ou no banco: `UPDATE admin_config SET value='0' WHERE key='whitelist_enabled'`

---

## Dashboard Administrativo

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
| **Configurações** | IA (API key, modelo, base URL), whitelist de números autorizados |

O dashboard é **protegido por senha** — definida na primeira vez que acessar. A senha é armazenada com **bcrypt** e a chave da API **criptografada** (Fernet).

---

## Arquitetura

```
                         WhatsApp
                            │ WebSocket (Baileys)
                    ┌───────▼──────────────────────────┐
                    │     Gateway (Node.js — 3001)       │
                    │  • Conexão WhatsApp via Baileys    │
                    │  • Geração de QR code              │
                    │  • Download de mídia (imagem/áudio)│
                    │  • Envio de mensagens (texto/imagem)│
                    │  • Enfileiramento + retry de webhook│
                    │  • Logging: pino                   │
                    └───────────────┬────────────────────┘
                                    │ HTTP POST (webhook)
                    ┌───────────────▼────────────────────┐
                    │      Bot (Python FastAPI — 8000)    │
                    │  • Processamento de mensagens       │
                    │  • Máquina de estados do menu       │
                    │  • Integração Groq (chat + vision)  │
                    │  • Transcrição de áudio (faster-w)  │
                    │  • SQLite via SQLAlchemy            │
                    │  • Cache de respostas (SHA256)      │
                    │  • Dashboard admin (vanilla JS)     │
                    │  • Autenticação (bcrypt + token)    │
                    │  • Logging: structlog               │
                    └────────────────────────────────────┘
```

### Fluxo de mensagens

```
Usuário envia "Olá"
       │
       ▼
Gateway recebe → valida JID → enfileira → POST /webhook
       │                                          │ retry 3x (1s/5s/15s)
       ▼                                          ▼
Bot valida (Pydantic) → whitelist? → 202 (BackgroundTasks)
       │
       ▼
   ┌───┴──────────────────────────────────────────┐
   │              processar_webhook_async()         │
   ├───────────────────────────────────────────────┤
   │  Imagem?  → ask_ai_with_image(text, base64)   │
   │  Áudio?   → transcribe_audio() → ask_ai()     │
   │  Texto:                                       │
   │    ├─ "1".."5" / "menu" → processar_menu()   │
   │    ├─ estado "falando_bot" → ask_ai()         │
   │    └─ outro → ask_ai() + reset estado         │
   └───────────────────────────┬───────────────────┘
                               │
                               ▼
                   Bot → POST /send (gateway)
                               │
                               ▼
                   Gateway → sock.sendMessage()
                               │
                               ▼
                   Usuário recebe resposta no WhatsApp
```

---

## Começando

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

```env
# bot/.env
GATEWAY_URL=http://localhost:3001
DATABASE_URL=sqlite:///./bot.db
# ENCRYPTION_KEY=     # Opcional. Se não definida, é gerada automaticamente na 1ª execução.
```

> A chave Fernet é **auto-gerada e persistida no banco** (tabela `admin_config`, chave `encryption_key`) na primeira execução. Você só precisa definir `ENCRYPTION_KEY` no `.env` se quiser usar uma chave fixa (ex: para compartilhar entre múltiplas instâncias).

```env
# gateway/.env
PORT=3001
WEBHOOK_URL=http://localhost:8000/webhook
LOG_LEVEL=info
```

### 3. Iniciar o Gateway (WhatsApp)

```bash
cd gateway
npm start
```

Um **QR code** será exibido no terminal. Abra o WhatsApp no celular → Menu → Aparelhos conectados → Conectar um dispositivo. Escaneie o QR code.

O gateway está pronto quando aparecer:

```
[10:30:00] INFO: gateway_http_started
[10:30:02] INFO: whatsapp_connected
```

### 4. Iniciar o Bot

Em outro terminal:

```bash
cd bot
python main.py
```

```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

> Na primeira execução, o faster-whisper baixa automaticamente o modelo de transcrição (~150 MB para o modelo `base`) para `~/.cache/faster_whisper/`.

### 5. Migrações do banco de dados

As tabelas são criadas automaticamente na primeira execução via **Alembic**. Para gerenciar mudanças futuras no schema:

```bash
cd bot
# Gerar uma nova migration (após alterar os modelos em database.py)
alembic revision --autogenerate -m "descricao"

# Aplicar migrations pendentes
alembic upgrade head
```

> O `init_db()` no startup já executa `alembic upgrade head` automaticamente, com fallback para `create_all`.

### 6. Executar testes

```bash
cd bot
python -m pytest tests/ -v
```

### 7. Testar

Pegue **outro celular** (ou peça para um amigo) e envie um WhatsApp para o **número que você usou para escanear o QR code**. O bot responderá automaticamente com o menu:

```
╔══════════════════════╗
║       ATENDIMENTO     ║
╚══════════════════════╝

1 Informações
2 Agendar horário
3 Falar com o Bot 🤖
4 Falar com atendente
5 Sair
```

---

## Endpoints da API

### Gateway (porta 3001)

| Método | Rota | Descrição | Corpo (JSON) |
|---|---|---|---|
| `GET` | `/health` | Status da conexão | — |
| `POST` | `/send` | Enviar mensagem de texto | `{ "to": "5511999998888@s.whatsapp.net", "text": "Olá" }` |
| `POST` | `/send-buttons` | Enviar botões interativos | `{ "to": "...", "text": "...", "buttons": [...] }` |
| `POST` | `/send-image` | Enviar imagem | `{ "to": "...", "imageUrl": "...", "text": "opcional" }` |

### Bot (porta 8000)

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/webhook` | Webhook recebido do gateway |
| `GET` | `/clientes` | Listar todos os clientes |
| `GET` | `/agendamentos` | Listar todos os agendamentos |
| `POST` | `/admin/login` | Login no dashboard |
| `GET` | `/admin/` | Dashboard web |
| `GET` | `/api/setup-status` | Status da configuração |
| `POST` | `/api/setup` | Configuração inicial |
| `GET` | `/api/stats` | Estatísticas do sistema |
| `GET` | `/api/conversas/{telefone}` | Conversas de um cliente |
| `PUT` | `/api/agendamentos/{id}` | Atualizar status do agendamento |
| `PUT` | `/api/clientes/{telefone}/nome` | Editar nome do cliente |
| `GET` | `/api/whitelist` | Listar whitelist |
| `PUT` | `/api/whitelist` | Atualizar whitelist |
| `GET` | `/api/settings` | Listar configurações |
| `PUT` | `/api/settings` | Atualizar configurações |
| `POST` | `/api/send` | Enviar mensagem manualmente |

---

## Modelos de IA

### Chat (texto)

| Modelo | Contexto | Observação |
|---|---|---|
| `grok-2-1212` | — | Padrão (configurável) |
| `openai/gpt-oss-120b` | 32K | Primeiro fallback |
| `gemma2-9b-it` | 8K | Segundo fallback |
| `llama-3.3-70b-versatile` | 128K | Terceiro fallback |
| `mixtral-8x7b-32768` | 32K | Quarto fallback |

O modelo primário é configurável no dashboard ou via API. Em caso de falha (exceto 401), o bot tenta automaticamente os modelos de fallback em ordem.

### Visão (imagem)

| Modelo | Uso |
|---|---|
| `llama-3.2-11b-vision-preview` | Tentativa principal |
| `llava-v1.5-7b` | Fallback |

### Transcrição (áudio)

| Modelo | Tamanho | RAM | Qualidade |
|---|---|---|---|
| `tiny` | 75 MB | ~1 GB | Básica |
| `base` | 150 MB | ~1.5 GB | Padrão (recomendado) |
| `small` | 500 MB | ~2 GB | Boa |
| `medium` | 1.5 GB | ~5 GB | Muito boa |
| `large-v3` | 3 GB | ~10 GB | Excelente |

> Configure com a chave `whisper_model` no banco ou via dashboard (em breve). Padrão: `base`. A transcrição roda em CPU com `int8` e não bloqueia o event loop (executa em thread separada).

---

## Banco de Dados

O SQLite é criado automaticamente em `bot/bot.db` com 5 tabelas gerenciadas por **Alembic** (migrations em `bot/alembic/versions/`):

| Tabela | Descrição | Campos principais |
|---|---|---|
| `clientes` | Dados dos clientes | telefone, nome, estado (máq. estados), dados (JSON) |
| `conversas` | Histórico de mensagens | telefone, mensagem, resposta, tipo (texto/imagem/transcricao) |
| `agendamentos` | Agendamentos | telefone, nome, data_hora, servico, status |
| `respostas_cache` | Cache de respostas da IA | pergunta, resposta, modelo, hits (contador) |
| `admin_config` | Config. chave-valor | key, value (valores sensíveis criptografados) |

> Para alterar o schema, edite os modelos em `database.py`, gere uma migration com `alembic revision --autogenerate` e aplique com `alembic upgrade head`.

---

## Personalização

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

### Alterar o modelo de transcrição

```bash
# No banco SQLite diretamente:
sqlite3 bot.db "UPDATE admin_config SET value='small' WHERE key='whisper_model';"
```

Ou adicione a chave no código em `_get_whisper_model()` em `bot/handlers/ai.py`.

---

## Estrutura do Projeto

```
bot-whatsapp/
├── gateway/                    #  Conexão WhatsApp (Node.js)
│   ├── index.js                #    Gateway Baileys + Express + pino
│   ├── package.json            #    Dependências Node.js
│   └── .env                    #    Configurações do gateway
│
├── bot/                        #  Lógica do bot (Python)
│   ├── main.py                 #    FastAPI (webhook + endpoints + dashboard)
│   ├── config.py               #    Variáveis de ambiente + structlog
│   ├── database.py             #    Modelos SQLite + CRUD + criptografia
│   ├── security.py             #    bcrypt (senha) + Fernet (API key)
│   ├── schemas.py              #    Pydantic (validação de entrada)
│   ├── .env                    #    Chave da API + configurações
│   ├── requirements.txt        #    Dependências Python
│   ├── alembic.ini             #    Config do Alembic
│   ├── alembic/                #    Migrações do banco
│   │   ├── env.py              #    Config do ambiente Alembic
│   │   └── versions/           #    Arquivos de migração
│   ├── static/
│   │   └── dashboard.html      #    Dashboard administrativo
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── menu.py             #    Textos e estados do menu
│   │   └── ai.py               #    Groq (chat+vision) + faster-whisper
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_menu.py        #    9 testes do fluxo de menu
│       └── test_security.py    #    4 testes de hash/criptografia
│
├── .gitignore
└── README.md
```

---

## Observações

- O Baileys usa o protocolo do WhatsApp Web — o número precisa estar **ativo no WhatsApp** e o celular precisa ter **conexão com internet** para manter o pareamento.
- O gateway tem **auto-reconnect** com proteção contra reconexão paralela — em caso de queda, tenta reconectar após 5 segundos.
- Se o dispositivo for **deslogado**, delete a pasta `gateway/auth_info/` e reinicie o gateway para gerar um novo QR code.
- `ENCRYPTION_KEY` é **auto-gerada** na primeira execução e persistida no banco SQLite. Você pode sobrescrever definindo a variável no `.env`.
- O faster-whisper baixa o modelo automaticamente na primeira transcrição (~150 MB para `base`). O download acontece uma vez e fica cacheado.
- Execute os testes com `python -m pytest tests/ -v` dentro da pasta `bot/`.
- As migrações de banco são gerenciadas pelo **Alembic**. Após alterar os modelos, rode `alembic revision --autogenerate -m "descricao"` e depois `alembic upgrade head` dentro de `bot/`.
- O webhook é processado de forma **assíncrona** (BackgroundTasks). O gateway tem **retry exponencial** (3 tentativas: 1s/5s/15s) em caso de falha.
- O bot tem **hot-reload** ativado (`uvicorn --reload`) — alterações no código Python são detectadas automaticamente, sem necessidade de reiniciar o servidor.

---

## Licença

MIT
