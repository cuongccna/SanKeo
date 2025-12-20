module.exports = {
  apps: [
    {
      name: "sankeo-bot",
      script: "src.bot.main",
      interpreter: "python3",
      interpreter_args: "-m",
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
      script: "src.worker.main",
      interpreter: "python3",
      interpreter_args: "-m",
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
      script: "src.ingestor.main",
      interpreter: "python3",
      interpreter_args: "-m",
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
      script: "uvicorn",
      args: "src.bot.payment_server:app --host 0.0.0.0 --port 8000",
      interpreter: "python3",
      interpreter_args: "-m",
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
