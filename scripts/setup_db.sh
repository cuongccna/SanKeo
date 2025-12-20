#!/bin/bash

# Script to setup PostgreSQL Database and User
# Usage: sudo ./scripts/setup_db.sh

DB_NAME="sankeo_db"
DB_USER="sankeo_user"
DB_PASS="Cuongnv@123" # CHANGE THIS!

echo "🐘 Setting up PostgreSQL..."

# Check if PostgreSQL is running
if ! systemctl is-active --quiet postgresql; then
    echo "PostgreSQL is not running. Attempting to start..."
    sudo systemctl start postgresql
fi

# Create User
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';" || echo "User $DB_USER might already exist."

# Create Database
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" || echo "Database $DB_NAME might already exist."

# Grant Privileges
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

# Enable UUID extension (optional but good)
sudo -u postgres psql -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"

echo "✅ Database Setup Complete!"
echo "Connection String: postgresql+asyncpg://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME"
echo "⚠️  Please update your .env file with this connection string."
