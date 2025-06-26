#!/bin/bash

echo "🔍 Verificando estrutura do banco de dados..."

# Verificar se o container do banco está rodando
if ! docker-compose ps db | grep -q "Up"; then
    echo "❌ Container do banco não está rodando!"
    exit 1
fi

echo "✅ Container do banco está rodando"

# Verificar conexão com o banco
if ! docker-compose exec db psql -U postgres -d videoai -c "\q" 2>/dev/null; then
    echo "❌ Não foi possível conectar ao banco de dados!"
    exit 1
fi

echo "✅ Conexão com o banco estabelecida"

# Verificar tabelas essenciais
echo "📊 Verificando tabelas..."

TABLES=("users" "videos" "subtitles" "sessions" "api_keys" "settings")

for table in "${TABLES[@]}"; do
    if docker-compose exec db psql -U postgres -d videoai -c "SELECT COUNT(*) FROM $table;" >/dev/null 2>&1; then
        count=$(docker-compose exec db psql -U postgres -d videoai -t -c "SELECT COUNT(*) FROM $table;" | tr -d ' ')
        echo "✅ Tabela '$table' existe ($count registros)"
    else
        echo "❌ Tabela '$table' NÃO existe!"
    fi
done

# Verificar configurações na tabela settings
echo "⚙️ Verificando configurações..."
if docker-compose exec db psql -U postgres -d videoai -c "SELECT COUNT(*) FROM settings;" >/dev/null 2>&1; then
    count=$(docker-compose exec db psql -U postgres -d videoai -t -c "SELECT COUNT(*) FROM settings;" | tr -d ' ')
    echo "✅ Configurações na tabela settings: $count"

    # Listar categorias
    echo "📂 Categorias de configurações:"
    docker-compose exec db psql -U postgres -d videoai -t -c "SELECT DISTINCT category FROM settings ORDER BY category;" | sed 's/^[ \t]*/  - /'
else
    echo "❌ Tabela settings não existe ou está inacessível!"
fi

echo "🔍 Verificação concluída!" 