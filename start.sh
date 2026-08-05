#!/bin/bash

echo "🚀 Starting Backend Server..."
# Backend ko background me chalane ke liye '&' lagate hain
uvicorn backend:app --host 0.0.0.0 --port 8000 &

echo "⏳ Waiting for 10 seconds for Backend to load completely..."
# Yahan se curl ka loop hata diya aur seedha 10 second ka wait laga diya
sleep 10

echo "✅ Backend is UP! Now starting Frontend..."
# Streamlit command ko Render par stable rakhne ke liye enableWebsocketCompression false add kiya hai
streamlit run crmDashboard.py --server.port $PORT --server.address 0.0.0.0 --server.enableCORS false --server.enableXsrfProtection false --server.enableWebsocketCompression false --server.headless true