#!/bin/bash
echo "Iniciando Ollama en segundo plano..."
ollama serve &
OLLAMA_PID=$!

echo "Esperando a que el servidor Ollama esté listo..."
for i in $(seq 1 30); do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "Ollama servidor listo."
        break
    fi
    echo "Esperando... ($i/30)"
    sleep 2
done

echo "Descargando modelo $OLLAMA_MODEL (puede tardar varios minutos)..."
ollama pull ${OLLAMA_MODEL:-llama3}
echo "Modelo descargado."

echo "Dejando Ollama en primer plano..."
wait $OLLAMA_PID
