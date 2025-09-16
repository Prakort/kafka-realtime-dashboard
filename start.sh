#!/bin/bash

# Kafka Real-time Dashboard - Start Script
# This script starts all services in the correct order

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

# Check if Docker is running
check_docker() {
    log "Checking Docker status..."
    
    if ! docker info >/dev/null 2>&1; then
        error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    
    log "Docker is running"
}

# Check if required files exist
check_files() {
    log "Checking required files..."
    
    required_files=("docker-compose.yml" "requirements.txt" "frontend/package.json")
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            error "Required file not found: $file"
            exit 1
        fi
    done
    
    log "All required files found"
}

# Create necessary directories
create_directories() {
    log "Creating necessary directories..."
    
    mkdir -p volumes/{postgres,kafka,redis,logs}
    mkdir -p logs
    
    log "Directories created"
}

# Start infrastructure services first
start_infrastructure() {
    log "Starting infrastructure services..."
    
    # Start PostgreSQL and Redis
    docker-compose up -d postgres redis
    log "PostgreSQL and Redis started"
    
    # Wait for services to be ready
    log "Waiting for infrastructure services to be ready..."
    sleep 15
    
    # Check if services are healthy
    if ! docker-compose ps postgres | grep -q "healthy"; then
        warn "PostgreSQL is not healthy yet, waiting..."
        sleep 10
    fi
    
    if ! docker-compose ps redis | grep -q "healthy"; then
        warn "Redis is not healthy yet, waiting..."
        sleep 5
    fi
    
    log "Infrastructure services are ready"
}

# Start Kafka services
start_kafka() {
    log "Starting Kafka services..."
    
    # Start Zookeeper and Kafka
    docker-compose up -d zookeeper kafka
    log "Zookeeper and Kafka started"
    
    # Wait for Kafka to be ready
    log "Waiting for Kafka to be ready..."
    sleep 30
    
    # Check Kafka health
    if ! docker-compose ps kafka | grep -q "healthy"; then
        warn "Kafka is not healthy yet, waiting..."
        sleep 15
    fi
    
    # Create Kafka topic if it doesn't exist
    log "Ensuring Kafka topic exists..."
    docker-compose exec kafka kafka-topics --create --if-not-exists --topic user_events --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1 || true
    
    log "Kafka services are ready"
}

# Start backend services
start_backend() {
    log "Starting backend services..."
    
    # Activate Python virtual environment
    if [ -d "venv" ]; then
        source venv/bin/activate
        log "Python virtual environment activated"
    fi
    
    # Run migrations
    log "Running database migrations..."
    docker-compose up -d backend
    sleep 10
    
    # Check if backend is ready
    log "Waiting for backend to be ready..."
    sleep 15
    
    # Test backend health
    if curl -f http://localhost:8000/api/health/ >/dev/null 2>&1; then
        log "Backend is healthy"
    else
        warn "Backend health check failed, but continuing..."
    fi
}

# Start Kafka consumers
start_consumers() {
    log "Starting Kafka consumers..."
    
    # Start all consumers
    docker-compose up -d kafka-consumer-1 kafka-consumer-2 kafka-consumer-3
    log "Kafka consumers started"
    
    # Wait for consumers to initialize
    sleep 10
    log "Kafka consumers are initializing"
}

# Start batch producer (optional)
start_batch_producer() {
    if [ "$1" == "--with-batch-producer" ]; then
        log "Starting batch producer..."
        docker-compose up -d batch-producer
        log "Batch producer started"
    else
        info "Skipping batch producer (use --with-batch-producer to include)"
    fi
}

# Start frontend
start_frontend() {
    log "Starting frontend..."
    
    # Check if Node.js dependencies are installed
    if [ ! -d "frontend/node_modules" ]; then
        warn "Frontend dependencies not found. Installing..."
        cd frontend
        npm install
        cd ..
    fi
    
    # Start frontend
    docker-compose up -d frontend
    log "Frontend started"
    
    # Wait for frontend to be ready
    sleep 10
    log "Frontend is ready"
}

# Display service status
show_status() {
    log "Service Status:"
    echo ""
    
    # Docker services status
    docker-compose ps
    
    echo ""
    log "Service URLs:"
    info "Frontend Dashboard: http://localhost:3000"
    info "Backend API: http://localhost:8000"
    info "API Health Check: http://localhost:8000/api/health/"
    info "API Metrics: http://localhost:8000/api/metrics/"
    info "Django Admin: http://localhost:8000/admin/ (admin/admin123)"
    
    echo ""
    log "Useful Commands:"
    info "View logs: docker-compose logs -f [service-name]"
    info "Stop services: ./stop.sh"
    info "Check status: ./status.sh"
    info "Restart services: ./restart.sh"
}

# Wait for all services to be ready
wait_for_services() {
    log "Waiting for all services to be ready..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:8000/api/health/ >/dev/null 2>&1 && curl -f http://localhost:3000 >/dev/null 2>&1; then
            log "All services are ready!"
            return 0
        fi
        
        info "Attempt $attempt/$max_attempts: Services not ready yet, waiting..."
        sleep 10
        ((attempt++))
    done
    
    warn "Some services may not be fully ready. Check status with './status.sh'"
}

# Main start function
main() {
    log "Starting Kafka Real-time Dashboard..."
    
    check_docker
    check_files
    create_directories
    
    start_infrastructure
    start_kafka
    start_backend
    start_consumers
    start_batch_producer "$@"
    start_frontend
    
    wait_for_services
    show_status
    
    log "Kafka Real-time Dashboard started successfully!"
    
    info "Dashboard is available at: http://localhost:3000"
    info "Press Ctrl+C to view logs, or run './status.sh' to check service status"
}

# Handle script arguments
case "${1:-}" in
    --with-batch-producer)
        main --with-batch-producer
        ;;
    --help)
        echo "Usage: $0 [--with-batch-producer]"
        echo ""
        echo "Options:"
        echo "  --with-batch-producer  Start with batch producer for load testing"
        echo "  --help                Show this help message"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac
