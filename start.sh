#!/bin/bash

echo "🚀 Starting Backend Server..."
# Backend ko background me chalane ke liye '&' lagate hain
uvicorn backend:app --host 0.0.0.0 --port 8000 &

echo "⏳ Waiting for Backend to be fully ready..."
# Ye loop tab tak check karega jab tak backend port 8000 par properly live na ho jaye
while ! curl -s http://0.0.0.0:8000/ > /dev/null; do
  sleep 2
done

echo "✅ Backend is UP! Now starting Frontend..."
# Jab backend 100% ready hoga, tabhi ye frontend chalayega aur buttons ko freeze hone se rokega
streamlit run crmDashboard.py --server.port $PORT --server.address 0.0.0.0 --server.enableCORS false --server.enableXsrfProtection false --server.headless true