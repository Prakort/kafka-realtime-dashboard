#!/bin/bash

# Kafka Real-time Dashboard - Installation Script
# This script installs all dependencies and sets up the project for development and production

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

# Check if running on supported OS
check_os() {
    log "Checking operating system..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        DISTRO=$(lsb_release -si 2>/dev/null || echo "Unknown")
        log "Detected Linux: $DISTRO"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        log "Detected macOS"
    else
        error "Unsupported operating system: $OSTYPE"
        exit 1
    fi
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install Docker and Docker Compose
install_docker() {
    log "Checking Docker installation..."
    
    if command_exists docker && command_exists docker-compose; then
        log "Docker and Docker Compose are already installed"
        return 0
    fi
    
    warn "Docker not found. Installing Docker..."
    
    if [[ "$OS" == "macos" ]]; then
        info "Please install Docker Desktop for Mac from: https://www.docker.com/products/docker-desktop"
        info "After installation, restart your terminal and run this script again"
        exit 1
    elif [[ "$OS" == "linux" ]]; then
        # Install Docker on Linux
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
        rm get-docker.sh
        
        # Install Docker Compose
        sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
        
        log "Docker installed successfully"
        warn "Please log out and log back in for Docker group changes to take effect"
        exit 1
    fi
}

# Install Python dependencies
install_python() {
    log "Checking Python installation..."
    
    if ! command_exists python3; then
        error "Python 3 is required but not installed"
        if [[ "$OS" == "macos" ]]; then
            info "Install Python 3 using: brew install python3"
        elif [[ "$OS" == "linux" ]]; then
            info "Install Python 3 using your package manager"
        fi
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    if [[ $(echo "$PYTHON_VERSION < 3.9" | bc -l) -eq 1 ]]; then
        error "Python 3.9+ is required. Current version: $PYTHON_VERSION"
        exit 1
    fi
    
    log "Python $PYTHON_VERSION found"
    
    # Install pip if not present
    if ! command_exists pip3; then
        log "Installing pip..."
        python3 -m ensurepip --upgrade
    fi
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        log "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    log "Upgrading pip..."
    pip install --upgrade pip
    
    # Install Python dependencies
    log "Installing Python dependencies..."
    pip install -r requirements.txt
    
    log "Python dependencies installed successfully"
}

# Install Node.js dependencies
install_nodejs() {
    log "Checking Node.js installation..."
    
    if ! command_exists node; then
        error "Node.js is required but not installed"
        if [[ "$OS" == "macos" ]]; then
            info "Install Node.js using: brew install node"
        elif [[ "$OS" == "linux" ]]; then
            info "Install Node.js using your package manager or from https://nodejs.org/"
        fi
        exit 1
    fi
    
    NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
    if [[ $NODE_VERSION -lt 16 ]]; then
        error "Node.js 16+ is required. Current version: $(node --version)"
        exit 1
    fi
    
    log "Node.js $(node --version) found"
    
    # Install npm if not present
    if ! command_exists npm; then
        error "npm is required but not installed"
        exit 1
    fi
    
    # Install frontend dependencies
    log "Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
    
    log "Node.js dependencies installed successfully"
}

# Create environment file
setup_environment() {
    log "Setting up environment configuration..."
    
    if [ ! -f ".env" ]; then
        log "Creating .env file..."
        cat > .env << EOF
# Django Settings
DEBUG=True
SECRET_KEY=your-secret-key-change-this-in-production

# Database Settings
DB_HOST=postgres
DB_NAME=kafka_dashboard
DB_USER=postgres
DB_PASSWORD=postgres
DB_PORT=5432

# Redis Settings
REDIS_URL=redis://redis:6379

# Kafka Settings
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_TOPIC_USER_EVENTS=user_events
MOCK_KAFKA=False

# Celery Settings
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
EOF
        log ".env file created with default values"
        warn "Please review and update .env file for production use"
    else
        log ".env file already exists"
    fi
}

# Create Docker volumes and networks
setup_docker() {
    log "Setting up Docker volumes and networks..."
    
    # Create Docker network if it doesn't exist
    docker network create kafka-dashboard-network 2>/dev/null || true
    
    # Create volume directories
    mkdir -p volumes/{postgres,kafka,redis,logs}
    
    log "Docker setup completed"
}

# Run Django migrations
run_migrations() {
    log "Running Django migrations..."
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Wait for database to be ready
    log "Waiting for database to be ready..."
    docker-compose up -d postgres redis
    sleep 10
    
    # Run migrations
    docker-compose exec -T backend python manage.py migrate || {
        warn "Running migrations locally..."
        python manage.py migrate
    }
    
    log "Migrations completed successfully"
}

# Create superuser
create_superuser() {
    log "Creating Django superuser..."
    
    source venv/bin/activate
    
    # Check if superuser already exists
    if python manage.py shell -c "from django.contrib.auth.models import User; print('Superuser exists:', User.objects.filter(is_superuser=True).exists())" | grep -q "True"; then
        log "Superuser already exists"
        return 0
    fi
    
    # Create superuser
    echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'admin123')" | python manage.py shell
    log "Superuser created (username: admin, password: admin123)"
}

# Main installation function
main() {
    log "Starting Kafka Real-time Dashboard installation..."
    
    check_os
    install_docker
    install_python
    install_nodejs
    setup_environment
    setup_docker
    
    log "Installation completed successfully!"
    
    info "Next steps:"
    info "1. Run './start.sh' to start all services"
    info "2. Open http://localhost:3000 to view the dashboard"
    info "3. Use './stop.sh' to stop all services"
    info "4. Use './status.sh' to check service status"
    
    log "Installation script completed!"
}

# Run main function
main "$@"
