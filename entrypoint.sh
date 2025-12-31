#!/bin/sh

# Encerra o script se qualquer comando falhar
set -e

echo "Criando Migrations..."
python manage.py makemigrations

echo "Rodando Migrations..."
python manage.py migrate

echo "Coletando Estáticos..."
python manage.py collectstatic --noinput

echo "Iniciando Servidor..."
exec python manage.py runserver 0.0.0.0:8080