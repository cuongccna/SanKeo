#!/bin/bash

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3-pip python3-venv python3-full redis-server postgresql postgresql-contrib

# Create Virtual Environment
# Try to create venv, if fails, try installing specific version
if ! python3 -m venv venv; then
    echo "⚠️ Standard venv creation failed. Attempting to install python3.12-venv..."
    sudo apt install -y python3.12-venv
    python3 -m venv venv
fi

source venv/bin/activate

# Install Python packages
pip install -r requirements.txt

# Setup Database (Interactive)
echo "Please setup PostgreSQL database manually or use a script."
echo "sudo -u postgres psql"
echo "CREATE DATABASE sankeo_db;"
echo "CREATE USER myuser WITH PASSWORD 'mypassword';"
echo "GRANT ALL PRIVILEGES ON DATABASE sankeo_db TO myuser;"

echo "Installation complete. Don't forget to configure .env!"
