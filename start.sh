#!/bin/bash

echo "AI Background Remover - Professional Tool"
echo "=========================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    echo "Please install Python 3.8+ from your package manager"
    exit 1
fi

echo "Starting AI Background Remover..."
python3 start.py