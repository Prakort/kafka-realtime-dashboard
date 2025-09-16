#!/bin/bash

# Kafka Real-time Dashboard - Restart Script
# This script restarts all services

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

# Main restart function
main() {
    log "Restarting Kafka Real-time Dashboard..."
    
    # Check if scripts exist
    if [ ! -f "stop.sh" ] || [ ! -f "start.sh" ]; then
        error "Required scripts not found. Please run from project root directory."
        exit 1
    fi
    
    # Stop services
    log "Stopping services..."
    ./stop.sh
    
    # Wait a moment
    sleep 5
    
    # Start services
    log "Starting services..."
    ./start.sh "$@"
    
    log "Restart completed successfully!"
}

# Handle script arguments
case "${1:-}" in
    --with-batch-producer)
        main --with-batch-producer
        ;;
    --help)
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --with-batch-producer  Restart with batch producer for load testing"
        echo "  --help                Show this help message"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac
