# 🚀 Quick Start Guide

Get the Kafka Real-time Dashboard running on any machine in minutes!

## 📋 Prerequisites

- **Docker & Docker Compose** (will be installed automatically)
- **Python 3.9+** (will be installed automatically)
- **Node.js 16+** (will be installed automatically)
- **Git** (to clone the repository)

## ⚡ One-Command Setup

```bash
# Clone the repository
git clone https://github.com/your-username/kafka-realtime-dashboard.git
cd kafka-realtime-dashboard

# Install everything and start services
./install.sh && ./start.sh
```

That's it! 🎉 Your dashboard will be available at http://localhost:3000

## 🔧 Manual Setup (if needed)

If you prefer to set up manually:

```bash
# 1. Install dependencies
./install.sh

# 2. Start services
./start.sh

# 3. Check status
./status.sh
```

## 📊 Access Your Dashboard

Once running, you can access:

- **🌐 Dashboard**: http://localhost:3000
- **🔧 API**: http://localhost:8000
- **❤️ Health Check**: http://localhost:8000/api/health/
- **📊 Metrics**: http://localhost:8000/api/metrics/
- **👤 Admin Panel**: http://localhost:8000/admin/ (admin/admin123)

## 🛠️ Management Commands

```bash
# Start all services
./start.sh

# Start with batch producer (for load testing)
./start.sh --with-batch-producer

# Stop all services
./stop.sh

# Stop and clean up containers
./stop.sh --cleanup

# Check service status
./status.sh

# Restart all services
./restart.sh
```

## 🔍 Troubleshooting

### Services not starting?
```bash
# Check Docker is running
docker info

# Check service status
./status.sh

# View logs
docker-compose logs -f backend
docker-compose logs -f kafka-consumer-1
```

### Database issues?
```bash
# Check database connection
docker-compose exec backend python manage.py shell -c "from django.db import connection; connection.ensure_connection()"

# Run migrations
docker-compose exec backend python manage.py migrate
```

### Kafka issues?
```bash
# Check Kafka status
docker-compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list

# Check consumer groups
docker-compose exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 --list
```

## 🧪 Testing the System

1. **Generate Events**: Click the test buttons in the dashboard
2. **Check Metrics**: Visit http://localhost:8000/api/metrics/
3. **Monitor Health**: Visit http://localhost:8000/api/health/
4. **View Logs**: Use `docker-compose logs -f [service-name]`

## 📈 Load Testing

```bash
# Start with batch producer
./start.sh --with-batch-producer

# Or run batch producer manually
python producer_batch.py --mode continuous --events-per-second 50 --duration 300
```

## 🆘 Getting Help

- Check the main [README.md](README.md) for detailed documentation
- Run `./status.sh` to diagnose issues
- Check service logs with `docker-compose logs -f [service-name]`
- Verify all services are running with `docker-compose ps`

## 🎯 Success Indicators

You'll know everything is working when:

✅ All services show "Up" status in `./status.sh`  
✅ Health check returns `"status": "healthy"`  
✅ Dashboard loads at http://localhost:3000  
✅ Events appear in real-time when clicking test buttons  
✅ Metrics show processing times < 200ms  

Happy monitoring! 🚀
