# Learning Log

Projeto Django para registrar topicos de estudo e entradas relacionadas a cada topico. Ele usa SQLite em desenvolvimento e esta organizado com o projeto principal `learning_log` e o app `learning_logs`.

## Estrutura

- `manage.py`: utilitario de linha de comando do Django.
- `learning_log/`: configuracoes do projeto, rotas principais, ASGI e WSGI.
- `learning_logs/`: app com modelos, views, rotas, templates e admin.
- `learning_logs/models.py`: modelos `Topic` e `Entry`.
- `learning_logs/templates/learning_logs/`: templates da pagina inicial e base.
- `db.sqlite3`: banco local de desenvolvimento.

## Requisitos

- Python 3.13.3
- Django 6.0.4

O ambiente virtual local fica em `venv/`.

## Como rodar no Windows PowerShell

Ative o ambiente virtual:

```powershell
.\venv\Scripts\Activate.ps1
```

Se estiver configurando em uma maquina nova, instale o Django:

```powershell
python -m pip install Django
```

Aplique as migracoes:

```powershell
python manage.py migrate
```

Inicie o servidor de desenvolvimento:

```powershell
python manage.py runserver
```

Acesse:

```text
http://127.0.0.1:8000/
```

## Admin

Os modelos `Topic` e `Entry` ja estao registrados no admin do Django.

Para criar um usuario administrador:

```powershell
python manage.py createsuperuser
```

Depois acesse:

```text
http://127.0.0.1:8000/admin/
```

## Comandos uteis do Django

Criar migracoes depois de alterar modelos:

```powershell
python manage.py makemigrations
```

Aplicar migracoes no banco:

```powershell
python manage.py migrate
```

Abrir o shell do Django:

```powershell
python manage.py shell
```

Rodar testes:

```powershell
python manage.py test
```

Verificar a configuracao do projeto:

```powershell
python manage.py check
```

Criar um novo app:

```powershell
python manage.py startapp nome_do_app
```

## Rotas atuais

- `/`: pagina inicial do app `learning_logs`.
- `/admin/`: painel administrativo do Django.

## Observacoes

- `venv/`, `__pycache__/` e `db.sqlite3` devem estar no `.gitignore`.
- O banco usado em desenvolvimento e o SQLite.
- Antes de mexer nos modelos, confira `learning_logs/models.py`.
- Depois de mexer nos modelos, rode `makemigrations` e `migrate`.
