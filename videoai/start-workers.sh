#!/bin/bash

echo "🚀 Iniciando workers do AutoSub..."

# Função para parar workers em caso de interrupção
cleanup() {
    echo "🛑 Parando workers..."
    kill $AUDIO_WORKER_PID $VIDEO_WORKER_PID 2>/dev/null
    exit 0
}

# Capturar sinais para limpeza
trap cleanup SIGINT SIGTERM

# Iniciar worker de áudio
echo "🎵 Iniciando worker de áudio..."
python3 worker.py &
AUDIO_WORKER_PID=$!

# Esperar um pouco antes de iniciar o próximo worker
sleep 2

# Iniciar worker de vídeo
echo "🎥 Iniciando worker de vídeo..."
python3 video_worker.py &
VIDEO_WORKER_PID=$!

echo "✅ Workers iniciados:"
echo "   - Worker de áudio (PID: $AUDIO_WORKER_PID)"
echo "   - Worker de vídeo (PID: $VIDEO_WORKER_PID)"
echo "   - Pressione Ctrl+C para parar"

# Aguardar os workers
wait $AUDIO_WORKER_PID $VIDEO_WORKER_PID 