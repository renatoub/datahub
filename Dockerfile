# Stage 1: Build
FROM python:3.12-slim AS build

WORKDIR /usr/src/app

# Instalação de dependências para compilar
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Stage 2: Final
FROM python:3.12-slim

WORKDIR /usr/src/app

# Instale APENAS libs de runtime (Removido -dev)
# Adicionado 'dos2unix' para corrigir arquivos criados no Windows
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libjpeg62-turbo \
    libpng16-16 \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# Copia venv
COPY --from=build /opt/venv /opt/venv

# Copia código
COPY . .

# Configurações de Ambiente
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# --- CORREÇÃO CRÍTICA DO ENTRYPOINT ---
# 1. Copia explicitamente para a raiz (opcional, mas mais seguro para achar)
COPY entrypoint_prod.sh /entrypoint_prod.sh
# 2. Converte quebras de linha Windows -> Linux
RUN dos2unix /entrypoint_prod.sh
# 3. Dá permissão de execução
RUN chmod +x /entrypoint_prod.sh

# Criação de usuário e diretório de mídia
RUN mkdir -p /data/media && \
    useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /usr/src/app /data

USER appuser

EXPOSE 8080

# Caminho absoluto correto
ENTRYPOINT [ "/entrypoint_prod.sh" ]

CMD ["/opt/venv/bin/gunicorn", "datahub.wsgi:application", "--bind", "0.0.0.0:8080", "--workers", "1"]