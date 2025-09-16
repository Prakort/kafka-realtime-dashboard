# Kafka Real-time Dashboard

A production-ready real-time user action tracking system built with **Kafka**, **Django**, **React**, and **TailwindCSS**. This dashboard provides live monitoring of user events with WebSocket updates and comprehensive analytics.

## 📸 Dashboard Preview

![Kafka Real-time Dashboard](Dashboard.png)

*Live dashboard showing real-time event tracking, queue monitoring, and interactive controls*

## 🚀 Features

- **Real-time Event Tracking**: Live user action monitoring with WebSocket updates
- **Kafka Integration**: Robust message streaming with confluent-kafka (with mock fallback)
- **Scalable Architecture**: Multiple producers and consumers with load balancing
- **Consumer Groups**: Automatic partition assignment and fault tolerance
- **Django Channels**: WebSocket support for real-time communication
- **React Frontend**: Modern, responsive UI with TailwindCSS
- **Interactive Event Generation**: Test buttons for different event types and delays
- **Batch Event Processing**: High-volume event generation for load testing
- **Queue Monitoring**: Real-time message processing status with timing data
- **Event Analytics**: Real-time statistics and top clicked elements
- **Docker Support**: Complete containerization for easy deployment
- **Production Ready**: PostgreSQL support, Redis caching, and proper ASGI server

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   React App     │◄──►│  Django API  │◄──►│   PostgreSQL    │
│   (Frontend)    │    │  (Backend)   │    │   (Database)    │
└─────────────────┘    └──────────────┘    └─────────────────┘
         │                       │
         │              ┌──────────────┐
         │              │   WebSocket  │
         └──────────────►│   Channels   │
                        └──────────────┘
                                 │
                        ┌──────────────┐
                        │    Redis     │
                        │  (Channels)  │
                        └──────────────┘
                                 │
                        ┌──────────────┐
                        │    Kafka     │
                        │  (Messages)  │
                        └──────────────┘
                                 ▲
                        ┌──────────────┐
                        │   Producer   │
                        │   (Events)   │
                        └──────────────┘
```

## 📋 Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL (optional, SQLite used by default)
- Redis
- Apache Kafka (optional, mock mode available)

## 🛠️ Installation

### Option 1: Docker (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd kafka-realtime-dashboard
   ```

2. **Start all services with Docker Compose**
   ```bash
   docker-compose up --build
   ```

   This will start:
   - PostgreSQL database
   - Redis for caching
   - Kafka and Zookeeper
   - Django backend
   - React frontend
   - Kafka consumer

3. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - Admin Panel: http://localhost:8000/admin

### Option 2: Manual Setup

1. **Backend Setup**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Install dependencies
   pip install -r requirements.txt

   # Run migrations
   python manage.py migrate

   # Create superuser (optional)
   python manage.py createsuperuser
   ```

2. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   ```

3. **Start Services**

   **Terminal 1 - Django Backend:**
   ```bash
   python manage.py runserver
   ```

   **Terminal 2 - Kafka Consumer:**
   ```bash
   python manage.py consume_kafka
   ```

   **Terminal 3 - React Frontend:**
   ```bash
   cd frontend
   npm start
   ```

   **Terminal 4 - Event Producer (for testing):**
   ```bash
   python producer.py
   ```

## 🎯 Usage

### Event Producers

#### Interactive Producer
The `producer.py` script generates realistic user events for testing:

```bash
# Basic usage (60 seconds, 2-second intervals)
python producer.py

# Custom duration and interval
python producer.py --duration 300 --interval 1.0

# Continuous mode
python producer.py --continuous

# Mock mode (no Kafka required)
python producer.py --mock

# Custom Kafka settings
python producer.py --bootstrap-servers localhost:9092 --topic user_events
```

#### Batch Producer (Scalable)
The `producer_batch.py` script generates high-volume events for load testing:

```bash
# Batch mode (100 events)
python producer_batch.py --mode batch --batch-size 100

# Continuous mode (50 events/second for 60 seconds)
python producer_batch.py --mode continuous --events-per-second 50 --duration 60

# Custom settings
python producer_batch.py --bootstrap-servers localhost:9092 --topic user_events
```

### Scalable Consumer Management

```bash
# Start single consumer
python manage.py consume_kafka_scalable --consumer-id consumer-1

# Start multiple consumers with load balancing
python manage.py consume_kafka_scalable --consumer-id consumer-1 --consumer-group dashboard_consumer_group
python manage.py consume_kafka_scalable --consumer-id consumer-2 --consumer-group dashboard_consumer_group
python manage.py consume_kafka_scalable --consumer-id consumer-3 --consumer-group dashboard_consumer_group
```

### Kafka Topic Management

```bash
# Create topic with partitions
python manage_kafka.py --action create --topic user_events --partitions 3

# List topics
python manage_kafka.py --action list

# Delete topic
python manage_kafka.py --action delete --topic user_events
```

### API Endpoints

- `GET /api/events/latest/` - Get the latest 50 events with statistics
- `POST /api/events/create/` - Create new events from frontend actions
- `GET /api/queue/messages/` - Get message queue status
- `GET /api/queue/stats/` - Get queue statistics
- `WS /ws/events/` - WebSocket endpoint for real-time updates

### Event Types

The system tracks various types of user events:

1. **page_view** - User visits a page
2. **button_click** - User clicks a button (Button 1, 2, 3, 4, 5)
3. **form_submit** - User submits a form (Send Message)
4. **Custom events** - With configurable delays and failure simulation

### Event Format

```json
{
  "user_id": "user_001",
  "event_type": "button_click",
  "element_id": "btn_submit",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## 🔧 Configuration

### Environment Variables

Copy `env.example` to `.env` and configure:

```bash
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (for production)
DB_NAME=kafka_dashboard
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC_USER_EVENTS=user_events

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Database Configuration

By default, the system uses SQLite for development. For production, uncomment the PostgreSQL configuration in `settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='kafka_dashboard'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}
```

## 🧪 Testing

### Manual Testing

1. Start all services
2. Run the event producer: `python producer.py`
3. Open the dashboard at http://localhost:3000
4. Watch events appear in real-time

### API Testing

```bash
# Get latest events
curl http://localhost:8000/api/events/latest/

# Test WebSocket connection
wscat -c ws://localhost:8000/ws/events/
```

## 📊 Dashboard Features

### Real-time Event Feed
- Live stream of user events
- Color-coded event types
- Timestamp display
- Auto-scrolling feed

### Statistics Panel
- Total event count
- Event type breakdown
- Top clicked elements
- Real-time updates

### Connection Status
- WebSocket connection indicator
- Error handling and reconnection
- Connection status display

## 🚀 Production Deployment

### Using Docker

1. **Build and deploy**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

2. **Set up reverse proxy (nginx)**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://localhost:3000;
       }

       location /api/ {
           proxy_pass http://localhost:8000;
       }

       location /ws/ {
           proxy_pass http://localhost:8000;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
       }
   }
   ```

### Manual Production Setup

1. **Configure production settings**
   - Set `DEBUG=False`
   - Configure PostgreSQL
   - Set up Redis
   - Configure Kafka cluster

2. **Use a process manager (PM2, systemd)**
   ```bash
   # Start Django with Gunicorn
   gunicorn dashboard_backend.wsgi:application --bind 0.0.0.0:8000

   # Start Celery worker
   celery -A dashboard_backend worker --loglevel=info

   # Start Kafka consumer
   python manage.py consume_kafka
   ```

## 🔍 Monitoring

### Health Checks

- **Backend**: `GET /api/health/`
- **Database**: Django admin panel
- **Redis**: `redis-cli ping`
- **Kafka**: `kafka-topics --bootstrap-server localhost:9092 --list`

### Logs

- Django logs: `python manage.py runserver --verbosity=2`
- Kafka consumer logs: Check console output
- Docker logs: `docker-compose logs -f [service-name]`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Add tests if applicable
5. Commit your changes: `git commit -am 'Add feature'`
6. Push to the branch: `git push origin feature-name`
7. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Troubleshooting

### Common Issues

1. **WebSocket connection failed**
   - Check if Django Channels is running
   - Verify Redis is accessible
   - Check CORS settings

2. **Kafka consumer not receiving messages**
   - Verify Kafka is running
   - Check topic exists: `kafka-topics --bootstrap-server localhost:9092 --list`
   - Check consumer group: `kafka-consumer-groups --bootstrap-server localhost:9092 --list`

3. **Database connection issues**
   - Check PostgreSQL is running
   - Verify database credentials
   - Run migrations: `python manage.py migrate`

4. **Frontend not loading**
   - Check if React dev server is running
   - Verify API URL configuration
   - Check browser console for errors

### Getting Help

- Check the logs for error messages
- Verify all services are running
- Test individual components separately
- Check network connectivity between services

## 🎉 Success!

If everything is working correctly, you should see:

1. ✅ Django backend running on port 8000
2. ✅ React frontend running on port 3000
3. ✅ WebSocket connection established
4. ✅ Events appearing in real-time on the dashboard
5. ✅ Statistics updating automatically

Enjoy your real-time user action tracking dashboard! 🚀
