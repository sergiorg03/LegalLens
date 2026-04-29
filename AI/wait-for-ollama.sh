#!/bin/bash
echo "Esperando a que Ollama esté listo..."
while ! curl -s http://ollama:11434/api/tags > /dev/null 2>&1; do
    echo "Ollama no está listo, reintentando en 5 segundos..."
    sleep 5
done
echo "Ollama está listo, iniciando AI service..."
exec "$@"
