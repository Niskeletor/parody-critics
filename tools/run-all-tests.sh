#!/bin/bash
echo "🚀 Running all tests..."

echo "1️⃣ Code quality checks..."
npm run lint || exit 1
npm run format:check || exit 1

if command -v python &> /dev/null; then
    echo "🐍 Python code quality..."
    black --check . || exit 1
    flake8 . || exit 1
fi

echo "2️⃣ Unit tests..."
npm test || exit 1

if command -v pytest &> /dev/null; then
    echo "🐍 Python tests..."
    pytest || exit 1
fi

echo "3️⃣ Health check..."
node tools/health-check.js || exit 1

echo "4️⃣ Performance benchmark..."
node tools/benchmark.js

echo "5️⃣ E2E tests..."
node tools/comprehensive-test-suite.js || exit 1

echo "✅ All tests passed!"
