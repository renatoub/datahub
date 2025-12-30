# DataHub - Gestão de Demandas

Sistema Django para gestão de demandas, atividades, pendências e Kanban, com dashboard administrativo customizado.

## Funcionalidades
- Cadastro e hierarquia de demandas (iniciativa, épico, história, atividade)
- Kanban visual (front e admin)
- Controle de situação (padrão, pendente, execução, finalizado)
- Cadastro de contatos e solicitantes
- Pendências vinculadas às demandas, com histórico e controle de resolução
- Dashboard admin com tabela de demandas e Kanban
- Histórico de alterações (simple_history)
- Integração com tema Jazzmin para admin

## Instalação
1. Clone o repositório:
   ```sh
   git clone https://github.com/renatoub/datahub.git
   cd DataHub
   ```
2. Baixe o uv:
   ```sh
   pip install uv
   ```
3. Execute as migrações:
   ```sh
   uv run python datahub/manage.py migrate
   ```
4. Crie um superusuário:
   ```sh
   uv run python datahub/manage.py createsuperuser
   ```
5. Inicie o servidor:
   ```sh
   uv run python datahub/manage.py runserver
   ```

## Uso
- Acesse o admin: [http://localhost:8000/admin/](http://localhost:8000/admin/)
- O dashboard customizado aparece na página inicial do admin, com Kanban e tabela de demandas.
- Para o dashboard público, acesse [http://localhost:8000/](http://localhost:8000/)

## Estrutura
```
pyproject.toml
README.md
requirements.txt
manage.py
core/
    models.py
    admin.py
    views.py
    migrations/
    templates/
        core/
        admin/core/
```

## Principais Tecnologias
- Django 6.x
- SQLite
- Jazzmin (tema admin)
- django-simple-history
- Bootstrap 5, FontAwesome, Chart.js

## Licença
MIT
