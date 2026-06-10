#!/bin/bash

echo "Starting Database..."
docker-compose up -d

echo "Starting Backend API..."
uvicorn api.main:app --reload --port 8000 &
BACKEND_PID=$!

echo "Starting Frontend..."
cd frontend
npm install
npm run dev &
FRONTEND_PID=$!

echo "====================================="
echo "App is running!"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "Press Ctrl+C to stop all processes."
echo "====================================="

# Trap Ctrl+C (SIGINT) to clean up background processes
trap "echo 'Stopping processes...'; kill $BACKEND_PID $FRONTEND_PID; docker-compose stop; exit" SIGINT SIGTERM

# Wait for background processes to finish
wait
