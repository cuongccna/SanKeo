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
      script: "./venv/bin/python3",
      args: "-m uvicorn src.bot.payment_server:app --host 0.0.0.0 --port 8000",
      interpreter: "none",
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "300M",
      env: {
        PYTHONPATH: ".",
        NODE_ENV: "production"
      }
    },
    {
      name: "sankeo-sniper",
      script: "src/sniper/main.py",
      interpreter: "./venv/bin/python3",
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "300M",
      env: {
        PYTHONPATH: ".",
        NODE_ENV: "production"
      }
    },
    {
      name: "sankeo-analyzer",
      script: "src/worker/news_analyzer.py",
      interpreter: "./venv/bin/python3",
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "800M",
      env: {
        PYTHONPATH: ".",
        NODE_ENV: "production"
      },
      error_file: "logs/analyzer-error.log",
      out_file: "logs/analyzer-out.log",
      log_date_format: "YYYY-MM-DD HH:mm:ss Z"
    }
    // Scanner is now integrated into Sniper to avoid DB locks
    // {
    //   name: "sankeo-scanner",
    //   script: "scripts/scanner_joiner.py",
    //   interpreter: "./venv/bin/python3",
    //   instances: 1,
    //   autorestart: false,
    //   cron_restart: "0 */4 * * *", // Run every 4 hours
    //   watch: false,
    //   max_memory_restart: "500M",
    //   env: {
    //     PYTHONPATH: ".",
    //     NODE_ENV: "production"
    //   }
    // }
  ]
};
