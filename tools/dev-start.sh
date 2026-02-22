#!/bin/bash
echo "🚀 Starting development environment..."

# Check if server is running
if curl -f http://localhost:8877/api/health &>/dev/null; then
    echo "✅ Server is already running"
else
    echo "❌ Server not running. Please start it first."
    exit 1
fi

# Run quick health check
node tools/health-check.js || exit 1

# Open browser (optional)
# xdg-open http://localhost:8877 &>/dev/null || true

echo "🎉 Development environment ready!"
echo "Available commands:"
echo "  npm run test:full    - Run comprehensive tests"
echo "  npm run test:quick   - Quick button test"
echo "  npm run lint         - Check code quality"
echo "  npm run format       - Format code"
