#!/bin/bash

# Kafka Real-time Dashboard - Status Script
# This script checks the status of all services and displays comprehensive information

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

fail() {
    echo -e "${RED}❌ $1${NC}"
}

# Check Docker status
check_docker() {
    log "Checking Docker status..."
    
    if docker info >/dev/null 2>&1; then
        success "Docker is running"
        echo "Docker Version: $(docker --version | cut -d' ' -f3 | cut -d',' -f1)"
        echo "Docker Compose Version: $(docker-compose --version | cut -d' ' -f3 | cut -d',' -f1)"
    else
        fail "Docker is not running"
        return 1
    fi
    echo ""
}

# Check service status
check_services() {
    log "Checking service status..."
    
    if [ ! -f "docker-compose.yml" ]; then
        error "docker-compose.yml not found"
        return 1
    fi
    
    echo "Service Status:"
    echo "==============="
    
    # Get service status
    local services=("postgres" "redis" "zookeeper" "kafka" "backend" "kafka-consumer-1" "kafka-consumer-2" "kafka-consumer-3" "batch-producer" "frontend")
    
    for service in "${services[@]}"; do
        local status=$(docker-compose ps "$service" --format "table {{.Name}}\t{{.Status}}" 2>/dev/null | tail -n +2)
        if [ -n "$status" ]; then
            if echo "$status" | grep -q "Up"; then
                success "$status"
            else
                fail "$status"
            fi
        fi
    done
    echo ""
}

# Check health endpoints
check_health() {
    log "Checking health endpoints..."
    
    local endpoints=(
        "Backend Health:http://localhost:8000/api/health/"
        "Frontend:http://localhost:3000"
        "Metrics:http://localhost:8000/api/metrics/"
    )
    
    for endpoint_info in "${endpoints[@]}"; do
        local name=$(echo "$endpoint_info" | cut -d':' -f1)
        local url=$(echo "$endpoint_info" | cut -d':' -f2-)
        
        if curl -f -s "$url" >/dev/null 2>&1; then
            success "$name is healthy"
        else
            fail "$name is not responding"
        fi
    done
    echo ""
}

# Check Kafka status
check_kafka() {
    log "Checking Kafka status..."
    
    if docker-compose ps kafka | grep -q "Up"; then
        success "Kafka is running"
        
        # Check topics
        echo "Kafka Topics:"
        docker-compose exec -T kafka kafka-topics --bootstrap-server localhost:9092 --list 2>/dev/null | while read -r topic; do
            if [ -n "$topic" ]; then
                info "  - $topic"
            fi
        done
        
        # Check consumer groups
        echo "Consumer Groups:"
        docker-compose exec -T kafka kafka-consumer-groups --bootstrap-server localhost:9092 --list 2>/dev/null | while read -r group; do
            if [ -n "$group" ]; then
                info "  - $group"
            fi
        done
    else
        fail "Kafka is not running"
    fi
    echo ""
}

# Check database status
check_database() {
    log "Checking database status..."
    
    if docker-compose ps postgres | grep -q "Up"; then
        success "PostgreSQL is running"
        
        # Check database connection
        if docker-compose exec -T backend python manage.py shell -c "from django.db import connection; connection.ensure_connection(); print('Database connection: OK')" 2>/dev/null | grep -q "OK"; then
            success "Database connection is healthy"
        else
            fail "Database connection failed"
        fi
        
        # Get event count
        local event_count=$(docker-compose exec -T backend python manage.py shell -c "from tracking.models import UserEvent; print(UserEvent.objects.count())" 2>/dev/null | tail -1)
        if [ -n "$event_count" ] && [[ "$event_count" =~ ^[0-9]+$ ]]; then
            info "Total events in database: $event_count"
        fi
    else
        fail "PostgreSQL is not running"
    fi
    echo ""
}

# Check system resources
check_resources() {
    log "Checking system resources..."
    
    # Memory usage
    local memory_usage=$(free -h | awk '/^Mem:/ {print $3 "/" $2}')
    info "Memory usage: $memory_usage"
    
    # Disk usage
    local disk_usage=$(df -h . | awk 'NR==2 {print $3 "/" $2 " (" $5 ")"}')
    info "Disk usage: $disk_usage"
    
    # Docker stats
    if docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null | grep -q "kafka-realtime-dashboard"; then
        echo "Docker Container Resource Usage:"
        docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep "kafka-realtime-dashboard"
    fi
    echo ""
}

# Show service URLs
show_urls() {
    log "Service URLs:"
    
    echo "🌐 Frontend Dashboard: http://localhost:3000"
    echo "🔧 Backend API: http://localhost:8000"
    echo "❤️  Health Check: http://localhost:8000/api/health/"
    echo "📊 Metrics: http://localhost:8000/api/metrics/"
    echo "👤 Django Admin: http://localhost:8000/admin/ (admin/admin123)"
    echo "📝 API Documentation: http://localhost:8000/api/"
    echo ""
}

# Show useful commands
show_commands() {
    log "Useful Commands:"
    
    echo "📋 View logs:"
    echo "  docker-compose logs -f [service-name]"
    echo "  docker-compose logs -f backend"
    echo "  docker-compose logs -f kafka-consumer-1"
    echo ""
    echo "🔧 Management:"
    echo "  ./start.sh                    # Start all services"
    echo "  ./stop.sh                     # Stop all services"
    echo "  ./stop.sh --cleanup           # Stop and remove containers"
    echo "  ./restart.sh                  # Restart all services"
    echo ""
    echo "📊 Monitoring:"
    echo "  curl http://localhost:8000/api/health/"
    echo "  curl http://localhost:8000/api/metrics/"
    echo "  docker-compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list"
    echo ""
}

# Main status function
main() {
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║           Kafka Real-time Dashboard - Status Report         ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    check_docker
    check_services
    check_health
    check_kafka
    check_database
    check_resources
    show_urls
    show_commands
    
    log "Status check completed!"
}

# Handle script arguments
case "${1:-}" in
    --health)
        check_health
        ;;
    --services)
        check_services
        ;;
    --kafka)
        check_kafka
        ;;
    --database)
        check_database
        ;;
    --resources)
        check_resources
        ;;
    --help)
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --health       Check health endpoints only"
        echo "  --services     Check service status only"
        echo "  --kafka        Check Kafka status only"
        echo "  --database     Check database status only"
        echo "  --resources    Check system resources only"
        echo "  --help         Show this help message"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac
