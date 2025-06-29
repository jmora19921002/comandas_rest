#!/bin/bash

# Script de inicio para la aplicación Flask
echo "Iniciando Sistema de Comandas REST..."

# Verificar si estamos en desarrollo o producción
if [ "$FLASK_ENV" = "development" ]; then
    echo "Modo desarrollo"
    python app.py
else
    echo "Modo producción"
    gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --access-logfile - --error-logfile -
fi 