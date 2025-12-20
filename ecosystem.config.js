module.exports = {
  apps: [
    {
      name: "sankeo-bot",
      script: "src/bot/main.py",
      interpreter: "./venv/bin/python3",
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "500M",
      env: {
        PYTHONPATH: ".",
        NODE_ENV: "production"
      }
    },
    {
      name: "sankeo-worker",
      script: "src/worker/main.py",
      interpreter: "./venv/bin/python3",
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
      env: {
        PYTHONPATH: ".",
        NODE_ENV: "production"
      }
    },
    {
      name: "sankeo-ingestor",
      script: "src/ingestor/main.py",
      interpreter: "./venv/bin/python3",
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "500M",
      env: {
        PYTHONPATH: ".",
        NODE_ENV: "production"
      }
    },
    {
      name: "sankeo-payment",
      script: "./venv/bin/uvicorn",
      args: "src.bot.payment_server:app --host 0.0.0.0 --port 8000",
      interpreter: "none",
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "300M",
      env: {
        PYTHONPATH: ".",
        NODE_ENV: "production"
      }
    }
  ]
};
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "300M",
      env: {
        PYTHONPATH: ".",
        NODE_ENV: "production"
      }
    }
  ]
};
