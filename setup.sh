#!/bin/bash

# AI Background Removal Tool - Setup Script
# This script automates the installation and setup process

set -e

echo "🚀 AI Background Removal Tool Setup"
echo "======================================"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"

# Create environment file if it doesn't exist
if [ ! -f backend/.env ]; then
    echo "📝 Creating environment configuration..."
    cp backend/.env.example backend/.env
    echo "✅ Environment file created at backend/.env"
    echo "📋 Please edit backend/.env with your specific settings if needed"
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p backend/uploads
mkdir -p backend/results
mkdir -p backend/logs

# Build and start services
echo "🔨 Building Docker images..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🔍 Checking service health..."

# Check backend health
BACKEND_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/api/health || echo "000")
if [ "$BACKEND_HEALTH" = "200" ]; then
    echo "✅ Backend service is healthy"
else
    echo "❌ Backend service is not responding"
    echo "🔍 Checking backend logs..."
    docker-compose logs backend
fi

# Check frontend
FRONTEND_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080 || echo "000")
if [ "$FRONTEND_HEALTH" = "200" ]; then
    echo "✅ Frontend service is healthy"
else
    echo "❌ Frontend service is not responding"
    echo "🔍 Checking frontend logs..."
    docker-compose logs frontend
fi

# Check Redis
REDIS_HEALTH=$(docker-compose exec -T redis redis-cli ping 2>/dev/null || echo "FAIL")
if [ "$REDIS_HEALTH" = "PONG" ]; then
    echo "✅ Redis service is healthy"
else
    echo "⚠️  Redis service may not be running (this is optional)"
fi

echo ""
echo "🎉 Setup Complete!"
echo "==================="
echo ""
echo "📱 Access your application:"
echo "   Frontend: http://localhost:8080"
echo "   Backend API: http://localhost:5000"
echo "   API Health: http://localhost:5000/api/health"
echo ""
echo "🛠️  Useful commands:"
echo "   View logs: docker-compose logs -f"
echo "   Stop services: docker-compose down"
echo "   Restart services: docker-compose restart"
echo "   Update services: docker-compose pull && docker-compose up -d"
echo ""
echo "📚 Documentation: See README.md for detailed usage instructions"
echo ""

# Optional: Open browser
if command -v open &> /dev/null; then
    echo "🌐 Opening browser..."
    open http://localhost:8080
elif command -v xdg-open &> /dev/null; then
    echo "🌐 Opening browser..."
    xdg-open http://localhost:8080
else
    echo "💡 Open http://localhost:8080 in your browser to start using the tool"
fi

echo "✨ Happy background removing! ✨"