#!/bin/bash

echo "🚀 AI Stress Level Analyzer - Quick Start Script"
echo "=================================================="

# Check if MongoDB is running
echo "📊 Checking MongoDB connection..."
if mongosh --eval "db.runCommand({ ping: 1 })" > /dev/null 2>&1; then
    echo "✅ MongoDB is running"
else
    echo "❌ MongoDB is not running. Please start MongoDB first:"
    echo "   Linux: sudo systemctl start mongod"
    echo "   Mac: brew services start mongodb-community"
    exit 1
fi

# Setup Backend
echo ""
echo "🐍 Setting up Backend..."
cd backend

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing Python dependencies..."
pip install -q -r requirements.txt

# Train ML model if not exists
if [ ! -f "ml_model/stress_model.pkl" ]; then
    echo "🤖 Training ML model (first time only)..."
    python -m ml_model.train_model
else
    echo "✅ ML model already trained"
fi

echo "✅ Backend setup complete!"

# Start backend in background
echo "🚀 Starting backend server..."
python -m app.main &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 5

# Setup Frontend
echo ""
echo "⚛️  Setting up Frontend..."
cd ../frontend

if [ ! -d "node_modules" ]; then
    echo "Installing Node dependencies..."
    npm install
else
    echo "✅ Node modules already installed"
fi

echo "✅ Frontend setup complete!"

# Start frontend
echo "🚀 Starting frontend server..."
npm run dev &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

echo ""
echo "✅ =================================================="
echo "✅ Application is running!"
echo "✅ =================================================="
echo ""
echo "🌐 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "👤 Default Admin Credentials:"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo "📝 Press Ctrl+C to stop all servers"
echo ""

# Wait for user interrupt
trap "echo ''; echo '🛑 Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT

# Keep script running
wait
