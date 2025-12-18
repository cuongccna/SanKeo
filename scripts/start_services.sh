#!/bin/bash

source venv/bin/activate

# Start Ingestor
nohup python -m src.ingestor.main > logs/ingestor.log 2>&1 &
echo "Ingestor started with PID $!"

# Start Worker
nohup python -m src.worker.main > logs/worker.log 2>&1 &
echo "Worker started with PID $!"

# Start Bot
nohup python -m src.bot.main > logs/bot.log 2>&1 &
echo "Bot started with PID $!"

# Start Payment Server
nohup uvicorn src.bot.payment_server:app --host 0.0.0.0 --port 8000 > logs/payment.log 2>&1 &
echo "Payment Server started with PID $!"

echo "All services started."
