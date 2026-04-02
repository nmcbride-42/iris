#!/bin/bash
# Start the Iris Mycelial Dashboard
cd "$(dirname "$0")/dashboard"
echo "Iris Mycelial Dashboard — http://localhost:8051"
python app.py
