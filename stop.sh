#!/bin/bash

# Kafka Real-time Dashboard - Stop Script
# This script gracefully stops all services

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

# Graceful shutdown function
graceful_shutdown() {
    local service_name=$1
    local timeout=${2:-30}
    
    log "Gracefully stopping $service_name..."
    
    if docker-compose ps | grep -q "$service_name.*running"; then
        docker-compose stop -t $timeout "$service_name"
        log "$service_name stopped gracefully"
    else
        info "$service_name is not running"
    fi
}

# Stop frontend services first
stop_frontend() {
    log "Stopping frontend services..."
    
    graceful_shutdown "frontend" 10
    graceful_shutdown "batch-producer" 10
    
    log "Frontend services stopped"
}

# Stop backend services
stop_backend() {
    log "Stopping backend services..."
    
    graceful_shutdown "backend" 15
    graceful_shutdown "kafka-consumer-1" 10
    graceful_shutdown "kafka-consumer-2" 10
    graceful_shutdown "kafka-consumer-3" 10
    
    log "Backend services stopped"
}

# Stop Kafka services
stop_kafka() {
    log "Stopping Kafka services..."
    
    graceful_shutdown "kafka" 30
    graceful_shutdown "zookeeper" 15
    
    log "Kafka services stopped"
}

# Stop infrastructure services
stop_infrastructure() {
    log "Stopping infrastructure services..."
    
    graceful_shutdown "postgres" 30
    graceful_shutdown "redis" 15
    
    log "Infrastructure services stopped"
}

# Clean up containers (optional)
cleanup_containers() {
    if [ "$1" == "--cleanup" ]; then
        log "Cleaning up containers..."
        
        # Stop all services
        docker-compose down --remove-orphans
        
        # Remove stopped containers
        docker-compose rm -f
        
        log "Containers cleaned up"
    fi
}

# Clean up volumes (optional)
cleanup_volumes() {
    if [ "$1" == "--cleanup-volumes" ]; then
        warn "This will remove all data including database and Kafka topics!"
        read -p "Are you sure? (yes/no): " confirm
        
        if [ "$confirm" = "yes" ]; then
            log "Removing volumes..."
            docker-compose down -v --remove-orphans
            log "Volumes removed"
        else
            info "Volume cleanup cancelled"
        fi
    fi
}

# Show final status
show_final_status() {
    log "Final Service Status:"
    echo ""
    
    if docker-compose ps 2>/dev/null | grep -q "Up"; then
        docker-compose ps
        warn "Some services are still running"
    else
        info "All services have been stopped"
    fi
    
    echo ""
    log "Cleanup Commands:"
    info "Remove containers: ./stop.sh --cleanup"
    info "Remove containers and data: ./stop.sh --cleanup-volumes"
    info "Start services again: ./start.sh"
}

# Main stop function
main() {
    log "Stopping Kafka Real-time Dashboard..."
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        error "Docker is not running"
        exit 1
    fi
    
    # Check if services are running
    if ! docker-compose ps | grep -q "Up"; then
        info "No services are currently running"
        exit 0
    fi
    
    # Stop services in reverse order
    stop_frontend
    stop_backend
    stop_kafka
    stop_infrastructure
    
    # Optional cleanup
    cleanup_containers "$@"
    cleanup_volumes "$@"
    
    show_final_status
    
    log "Kafka Real-time Dashboard stopped successfully!"
}

# Handle script arguments
case "${1:-}" in
    --cleanup)
        main --cleanup
        ;;
    --cleanup-volumes)
        main --cleanup-volumes
        ;;
    --help)
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --cleanup           Stop and remove containers"
        echo "  --cleanup-volumes   Stop and remove containers and volumes (WARNING: removes all data)"
        echo "  --help              Show this help message"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac
