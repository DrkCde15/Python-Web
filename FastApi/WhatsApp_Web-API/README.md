# WhatsApp Web API

API FastAPI para gerar respostas automaticas, enviar mensagens pelo WhatsApp Web
e controlar o bot leitor de conversas. Este projeto roda somente como API HTTP.

## Como preparar

No PowerShell, dentro da pasta `WhatsApp_Web-API`:

```powershell
.\.venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
copy .env.example .env
```

## Como iniciar a API

```powershell
python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

Depois acesse:

- documentacao interativa: `http://127.0.0.1:8000/docs`
- status simples: `http://127.0.0.1:8000/health`

## Endpoints principais

### Gerar resposta

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/messages/reply `
  -ContentType "application/json" `
  -Body '{"message":"oi"}'
```

### Enviar mensagem

Use `print_only=true` para testar sem abrir/enviar pelo WhatsApp.

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/messages/send `
  -ContentType "application/json" `
  -Body '{
    "phone_number":"+5511999999999",
    "message":"Ola! Tudo bem?",
    "print_only":true
  }'
```

Tambem e possivel enviar `incoming_message` no lugar de `message`; nesse caso a
API usa `build_reply()` para gerar a resposta.

### Testar planilha de contatos

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/contacts/preview `
  -ContentType "application/json" `
  -Body '{
    "contacts_path":"contatos.example.csv",
    "message_template":"Ola {nome}, tudo bem?",
    "limit":5
  }'
```

### Enviar planilha de contatos

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/contacts/send `
  -ContentType "application/json" `
  -Body '{
    "contacts_path":"contatos.example.csv",
    "message_template":"Ola {nome}, tudo bem?",
    "contact_delay":5
  }'
```

### Iniciar leitor do WhatsApp Web

Na primeira execucao, o navegador abre o WhatsApp Web. Escaneie o QR Code com o
celular. A sessao fica salva em `whatsapp_session`.

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/web-bot/start `
  -ContentType "application/json" `
  -Body '{
    "session_dir":"whatsapp_session",
    "poll_interval":2,
    "fixed_reply":"",
    "print_only":false
  }'
```

Controle do bot:

- `GET /web-bot/status`
- `GET /web-bot/logs`
- `POST /web-bot/stop`

## Planilha de contatos

A planilha pode ser `.csv`, `.xlsx` ou `.xlsm`. A primeira linha deve ter
cabecalhos. O bot tenta encontrar automaticamente estas colunas:

- telefone: `telefone`, `celular`, `whatsapp`, `numero`, `phone` ou `number`
- nome: `nome`, `contato`, `cliente` ou `name`
- mensagem: `mensagem`, `message`, `texto` ou `recado`

Exemplo `contatos.csv`:

```csv
telefone,nome,mensagem
+5511999999999,Ana,"Ola {nome}, tudo bem?"
11988887777,Joao,"Ola {nome}, tudo bem?"
```

## Configuracao

As opcoes ficam no arquivo `.env`:

```env
BOT_NAME=Bot do WhatsApp
BOT_TIMEZONE=America/Sao_Paulo
PYWHATKIT_WAIT_TIME=15
PYWHATKIT_CLOSE_TAB=false
PYWHATKIT_CLOSE_TIME=3
WHATSAPP_WEB_SESSION_DIR=whatsapp_session
DEFAULT_COUNTRY_CODE=+55
CONTACT_SEND_DELAY=5
```
