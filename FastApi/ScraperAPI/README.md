# ScraperAPI

API de pesquisa e web scraping com organizacao local das informacoes.

## O que esta versao faz

- Coleta uma URL e extrai titulo, texto principal, links e metadados.
- Processa HTML bruto quando voce ja tem o conteudo.
- Cria uma pesquisa a partir de uma lista de URLs.
- Organiza os achados em JSON e relatorio Markdown usando regras locais.
- Salva historico em SQLite.
- Pode ser protegida por chave propria via header `X-API-Key`.

## Como rodar

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Acesse:

```txt
http://127.0.0.1:8000/docs
```

## Configuracao

Copie `.env.example` para `.env` e ajuste o que precisar.

Para gerar uma chave da propria ScraperAPI:

```bash
python scripts/generate_api_key.py
```

Depois coloque no `.env`:

```txt
SCRAPER_API_KEYS=sua-chave-aqui
```

Quando `SCRAPER_API_KEYS` estiver vazio, a autenticacao fica desativada para desenvolvimento local.

Com uma chave configurada, envie o header:

```txt
X-API-Key: sua-chave-aqui
```

## Endpoints principais

```txt
GET  /health
POST /scrape
POST /extract
POST /research
GET  /research/{research_id}
GET  /research/{research_id}/report
```

## Exemplo: coletar uma URL

```json
{
  "url": "https://example.com",
  "include_text": true,
  "include_links": true
}
```

## Exemplo: pesquisa com fontes

```json
{
  "query": "ferramentas Python para web scraping",
  "urls": ["https://example.com"],
  "language": "pt-BR",
  "max_sources": 5,
  "focus": ["vantagens", "documentacao", "casos de uso"]
}
```

## Observacoes

Esta versao ainda nao descobre fontes sozinha a partir de uma busca web. Ela ja aceita URLs como fontes e deixa o modulo de descoberta preparado para evoluir depois.

Por seguranca, URLs privadas como `localhost`, `127.0.0.1` e redes internas ficam bloqueadas por padrao. Para ambiente local controlado, ajuste `ALLOW_PRIVATE_URLS=true`.
