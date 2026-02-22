#!/bin/bash

echo "🧪 AI Stress Level Analyzer - System Test Script"
echo "=================================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0

# Test function
test_endpoint() {
    local name="$1"
    local url="$2"
    local expected="$3"
    
    echo -n "Testing: $name... "
    
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
    
    if [ "$response" = "$expected" ]; then
        echo -e "${GREEN}✓ PASSED${NC} (HTTP $response)"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAILED${NC} (Expected: $expected, Got: $response)"
        ((FAILED++))
    fi
}

echo "📋 Pre-flight Checks"
echo "──────────────────────────────────────"
echo ""

# Check MongoDB
echo -n "MongoDB Connection... "
if mongosh --eval "db.runCommand({ ping: 1 })" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Connected${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ Not Connected${NC}"
    echo "Please start MongoDB first"
    ((FAILED++))
    exit 1
fi

# Check if backend is running
echo -n "Backend Server (Port 8000)... "
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠ Not Running${NC}"
    echo "Please start backend with: cd backend && python -m app.main"
    ((FAILED++))
fi

# Check if frontend is running
echo -n "Frontend Server (Port 3000)... "
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠ Not Running${NC}"
    echo "Please start frontend with: cd frontend && npm run dev"
    ((FAILED++))
fi

# Check ML model
echo -n "ML Model File... "
if [ -f "backend/ml_model/stress_model.pkl" ]; then
    echo -e "${GREEN}✓ Exists${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ Not Found${NC}"
    echo "Please train model with: cd backend && python -m ml_model.train_model"
    ((FAILED++))
fi

echo ""
echo "🔧 Backend API Tests"
echo "──────────────────────────────────────"
echo ""

# Test health endpoint
test_endpoint "Health Check" "http://localhost:8000/health" "200"

# Test root endpoint
test_endpoint "Root Endpoint" "http://localhost:8000/" "200"

# Test API docs
test_endpoint "API Documentation" "http://localhost:8000/docs" "200"

# Test questionnaire (requires auth, should return 401 or 200)
echo -n "Testing: Questionnaire Endpoint... "
response=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/user/questionnaire" 2>/dev/null)
if [ "$response" = "200" ] || [ "$response" = "401" ] || [ "$response" = "403" ]; then
    echo -e "${GREEN}✓ PASSED${NC} (HTTP $response)"
    ((PASSED++))
else
    echo -e "${RED}✗ FAILED${NC} (Got: $response)"
    ((FAILED++))
fi

echo ""
echo "🌐 Frontend Tests"
echo "──────────────────────────────────────"
echo ""

# Test frontend pages
test_endpoint "Home Page" "http://localhost:3000/" "200"
test_endpoint "Login Page" "http://localhost:3000/login" "200"
test_endpoint "Register Page" "http://localhost:3000/register" "200"

echo ""
echo "📁 File Structure Tests"
echo "──────────────────────────────────────"
echo ""

# Check critical files
check_file() {
    local file="$1"
    local name="$2"
    
    echo -n "Checking: $name... "
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓ Exists${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ Missing${NC}"
        ((FAILED++))
    fi
}

check_file "backend/app/main.py" "Backend Main"
check_file "backend/app/database.py" "Database Config"
check_file "backend/ml_model/predictor.py" "ML Predictor"
check_file "frontend/src/App.tsx" "Frontend App"
check_file "frontend/src/services/api.ts" "API Service"
check_file "README.md" "Documentation"

echo ""
echo "📊 Database Tests"
echo "──────────────────────────────────────"
echo ""

# Check database collections
echo "Checking MongoDB collections..."
collections=$(mongosh --quiet --eval "db.getSiblingDB('ai stress detector').getCollectionNames()" 2>/dev/null)

if echo "$collections" | grep -q "users"; then
    echo -e "Users collection: ${GREEN}✓ Exists${NC}"
    ((PASSED++))
else
    echo -e "Users collection: ${YELLOW}⚠ Will be created on first use${NC}"
fi

if echo "$collections" | grep -q "admin"; then
    echo -e "Admin collection: ${GREEN}✓ Exists${NC}"
    ((PASSED++))
else
    echo -e "Admin collection: ${YELLOW}⚠ Will be created on startup${NC}"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 TEST SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED!${NC}"
    echo ""
    echo "🎉 System is ready to use!"
    echo ""
    echo "Access the application:"
    echo "  Frontend: http://localhost:3000"
    echo "  Backend:  http://localhost:8000"
    echo "  API Docs: http://localhost:8000/docs"
    echo ""
    echo "Default credentials:"
    echo "  Admin: admin@stressanalyzer.com / admin123"
    exit 0
else
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo ""
    echo "Please fix the issues above and try again."
    echo "See SETUP.md for detailed instructions."
    exit 1
fi
