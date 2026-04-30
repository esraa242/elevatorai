#!/bin/bash
# ElevatorAI - Quick Deploy Script
# Usage: ./deploy.sh

set -e

echo "=========================================="
echo "  ElevatorAI - Deployment Script"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Docker Compose is not installed. Please install it first.${NC}"
    exit 1
fi

echo -e "${GREEN}Prerequisites OK${NC}"
echo ""

# Check .env file
if [ ! -f .env ]; then
    echo -e "${YELLOW}.env file not found. Creating from template...${NC}"
    cp .env.example .env
    echo -e "${RED}Please edit .env and add your GEMINI_API_KEY, then run this script again.${NC}"
    exit 1
fi

# Check if GEMINI_API_KEY is set
if grep -q "your-gemini-api-key" .env; then
    echo -e "${RED}Please set your GEMINI_API_KEY in the .env file first.${NC}"
    echo "Get your key at: https://aistudio.google.com/app/apikey"
    exit 1
fi

echo -e "${GREEN}Environment configuration OK${NC}"
echo ""

# Step 1: Build and start infrastructure
echo "Step 1/5: Starting PostgreSQL and Redis..."
docker-compose up -d db redis
echo -e "${GREEN}Infrastructure started${NC}"
echo ""

# Wait for databases
sleep 5

# Step 2: Build API
echo "Step 2/5: Building API container..."
docker-compose build api
echo -e "${GREEN}API built${NC}"
echo ""

# Step 3: Seed database
echo "Step 3/5: Initializing database and seeding cabin data..."
docker-compose run --rm api python seed_data.py
echo -e "${GREEN}Database seeded${NC}"
echo ""

# Step 4: Start all services
echo "Step 4/5: Starting all services..."
docker-compose up -d
echo -e "${GREEN}All services started${NC}"
echo ""

# Step 5: Health check
echo "Step 5/5: Running health check..."
sleep 5

if curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}=========================================="
    echo "  Deployment Successful!"
    echo "==========================================${NC}"
    echo ""
    echo "Services:"
    echo "  Frontend:     http://localhost:3000"
    echo "  Backend API:  http://localhost:8000"
    echo "  Health Check: http://localhost:8000/health"
    echo ""
    echo "To view logs: docker-compose logs -f"
    echo "To stop:      docker-compose down"
else
    echo -e "${YELLOW}Health check pending. Services may still be starting...${NC}"
    echo "Check logs with: docker-compose logs -f"
fi
