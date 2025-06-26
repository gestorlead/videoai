#!/bin/bash

echo "🚀 Iniciando o AutoSub..."

# Aguardar PostgreSQL estar pronto
echo "⏳ Aguardando conexão com o banco de dados..."
while ! nc -z db 5432; do
    sleep 2
done
echo "✅ Conexão com o banco de dados estabelecida!"

# Configurar variáveis de ambiente do PostgreSQL
export PGPASSWORD=postgres

# Verificar se o banco de dados existe, se não, criá-lo
echo "🔧 Verificando se o banco de dados 'autosub' existe..."
if ! psql -h db -U postgres -lqt | cut -d \| -f 1 | grep -qw autosub; then
    echo "📦 Criando banco de dados 'autosub'..."
    psql -h db -U postgres -c "CREATE DATABASE autosub;"
else
    echo "✅ Banco de dados 'autosub' já existe."
fi

# Executar todas as migrações
echo "🔄 Executando todas as migrações do banco de dados..."
python -m src.migrations.run_all_migrations

# Executar o comando passado como parâmetro
echo "▶️ Iniciando aplicação..."
exec "$@" 