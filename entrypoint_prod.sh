#!/bin/sh

# Encerra o script se qualquer comando falhar
set -e

# REMOVIDO: python manage.py makemigrations (NUNCA FAÇA ISSO EM PROD)

echo "Rodando Migrations..."
python manage.py migrate --noinput

echo "Coletando Estáticos..."
# --clear limpa estáticos velhos para economizar espaço
python manage.py collectstatic --noinput --clear

echo "Iniciando Gunicorn..."
exec "$@"