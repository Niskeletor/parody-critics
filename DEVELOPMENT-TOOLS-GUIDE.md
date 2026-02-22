# 🛠️ SAL-9000 Development Tools Arsenal
*Comprehensive guide for debugging, testing, and development tools*

**Never do blind debugging again!** 🎯

## 🚀 Quick Start Commands

```bash
# Full test suite
node test-suite.js

# Python code quality
black . && flake8 . && mypy .

# JavaScript linting
npx eslint . && npx prettier --write .

# End-to-end testing
npx playwright test

# Performance profiling
py-spy top --pid $(pgrep python)
```

---

## 📋 Installed Tools Inventory

### 🎭 **Browser Testing & Automation**
| Tool | Purpose | Usage | Why Essential |
|------|---------|-------|---------------|
| **Puppeteer** | Headless Chrome automation | `node test-script.js` | ✅ Already proven effective for UI testing |
| **Playwright** | Multi-browser testing (Chrome, Firefox, Safari) | `npx playwright test` | 🎯 More robust than Puppeteer, cross-browser |
| **Cypress** | E2E testing with UI | `npx cypress open` | 👁️ Visual debugging, great for complex flows |

### 🧪 **Testing Frameworks**
| Tool | Purpose | Usage | Why Essential |
|------|---------|-------|---------------|
| **Jest** | JavaScript unit testing | `npm test` | ⚡ Fast unit tests for functions |
| **PyTest** | Python testing | `pytest tests/` | 🐍 Python testing with fixtures |
| **@testing-library/jest-dom** | DOM testing utilities | Import in tests | 🎯 Better DOM assertions |

### 🔍 **Code Quality & Linting**
| Tool | Purpose | Usage | Why Essential |
|------|---------|-------|---------------|
| **ESLint** | JavaScript linting | `npx eslint .` | 🚨 Catch JS errors before runtime |
| **Prettier** | Code formatting | `npx prettier --write .` | 💅 Consistent code style |
| **Black** | Python code formatting | `black .` | 🎯 Python code consistency |
| **Flake8** | Python linting | `flake8 .` | 🔍 Python code quality |
| **MyPy** | Python type checking | `mypy .` | 🛡️ Prevent type errors |

### 📊 **Profiling & Performance**
| Tool | Purpose | Usage | Why Essential |
|------|---------|-------|---------------|
| **py-spy** | Python profiling | `py-spy top --pid <PID>` | 🔥 Find Python performance bottlenecks |
| **memory-profiler** | Memory usage | `@profile` decorator | 💾 Track memory leaks |
| **Lighthouse** | Web performance | `npx lighthouse http://localhost` | ⚡ Web performance metrics |
| **webpack-bundle-analyzer** | Bundle analysis | `npx webpack-bundle-analyzer` | 📦 Optimize bundle size |

### 🔧 **Development Server Tools**
| Tool | Purpose | Usage | Why Essential |
|------|---------|-------|---------------|
| **Nodemon** | Auto-restart server | `nodemon server.js` | 🔄 No manual restarts |
| **Browser-sync** | Live reload | `browser-sync start` | 🌐 Instant browser refresh |

### 🎯 **API Testing & Mocking**
| Tool | Purpose | Usage | Why Essential |
|------|---------|-------|---------------|
| **json-server** | Mock REST API | `json-server db.json` | 🎭 Test without real API |
| **MSW** | Mock service worker | Import in tests | 🛡️ Intercept HTTP requests |
| **httpx[test]** | Python HTTP testing | `httpx.get(...)` | 🐍 Test Python APIs |

---

## 🎯 **Most Useful Tool Combinations**

### 1. **Full Stack Testing Pipeline**
```bash
# 1. Code quality check
black . && flake8 . && mypy .
npx eslint . && npx prettier --write .

# 2. Unit tests
pytest tests/
npm test

# 3. E2E tests
node test-suite.js
npx playwright test

# 4. Performance check
py-spy top --duration 30
npx lighthouse http://localhost:8877
```

### 2. **Quick Bug Investigation**
```bash
# 1. Profile running Python process
py-spy top --pid $(pgrep python)

# 2. Check memory usage
memory_profiler

# 3. Browser automation debugging
node debug-script.js

# 4. API testing
curl -X POST http://localhost:8877/api/test | jq
```

### 3. **Pre-commit Quality Gate**
```bash
# Run before any git commit
black . && flake8 . && mypy . && \
npx eslint . && npx prettier --write . && \
pytest tests/ && npm test && \
node test-suite.js
```

---

## 🏗️ **Recommended Project Structure**

```
project/
├── tests/
│   ├── unit/           # Jest/PyTest unit tests
│   ├── e2e/            # Playwright/Cypress E2E tests
│   ├── api/            # API testing
│   └── fixtures/       # Test data
├── tools/
│   ├── test-suite.js   # Comprehensive test runner
│   ├── debug-tools.js  # Debugging utilities
│   ├── performance.js  # Performance testing
│   └── setup.sh        # Tool setup script
├── .eslintrc.js        # ESLint config
├── .prettierrc         # Prettier config
├── pytest.ini         # PyTest config
└── playwright.config.js # Playwright config
```

---

## 📝 **Configuration Templates**

### **package.json scripts**
```json
{
  "scripts": {
    "test": "jest",
    "test:e2e": "playwright test",
    "test:full": "node tools/test-suite.js",
    "lint": "eslint . && flake8 .",
    "format": "prettier --write . && black .",
    "dev": "nodemon server.js",
    "debug": "node --inspect-brk debug-script.js",
    "profile": "py-spy record -o profile.svg -- python main.py"
  }
}
```

### **pytest.ini**
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
addopts = --cov=. --cov-report=html --cov-report=term
asyncio_default_fixture_loop_scope = function
```

### **.eslintrc.js**
```javascript
module.exports = {
  env: {
    browser: true,
    node: true,
    es2021: true,
  },
  extends: ['eslint:recommended'],
  parserOptions: {
    ecmaVersion: 12,
  },
  rules: {
    'no-console': 'warn',
    'no-unused-vars': 'error',
  },
};
```

---

## 🎭 **SAL-9000 Testing Philosophy**

### **The Three Pillars**
1. **🔍 Test Early** - Catch issues before they become problems
2. **🎯 Test Often** - Automate everything that can be automated
3. **🛡️ Test Smart** - Focus on critical paths and edge cases

### **Testing Pyramid**
```
        E2E Tests (Playwright/Cypress)
       /                            \
    Integration Tests (API/DB)
   /                            \
Unit Tests (Jest/PyTest)
```

### **Debugging Workflow**
1. **🚨 Issue Reported** → Run automated test suite
2. **🔍 Reproduce** → Write failing test case
3. **🛠️ Fix** → Make test pass
4. **✅ Verify** → Run full test suite
5. **🚀 Deploy** → Confidence in the fix

---

## 🚀 **Advanced Usage Examples**

### **Performance Profiling**
```bash
# Profile Python API under load
py-spy record -o profile.svg --duration 60 -- python main.py &
curl -X POST http://localhost:8877/api/generate/critic/123?character=Marco%20Aurelio
```

### **Memory Leak Detection**
```python
# Add to Python code
from memory_profiler import profile

@profile
def problematic_function():
    # Your code here
    pass
```

### **Browser Automation with Screenshots**
```javascript
// Enhanced debugging with screenshots
const test = await page.screenshot({ path: 'debug.png', fullPage: true });
console.log('Screenshot saved for debugging');
```

---

## ⚡ **Performance Benchmarks**

| Tool | Typical Runtime | Use Case |
|------|----------------|----------|
| **Jest unit tests** | < 5 seconds | Quick feedback loop |
| **Playwright E2E** | 30-60 seconds | Full user journey testing |
| **py-spy profiling** | Real-time | Production debugging |
| **ESLint + Prettier** | < 10 seconds | Pre-commit checks |

---

## 🎯 **Tool Selection Matrix**

| Scenario | Primary Tool | Backup Tool | Why |
|----------|-------------|-------------|-----|
| **UI Bug** | Playwright | Puppeteer | Cross-browser + debugging |
| **API Issue** | httpx/curl | Postman | Scriptable + automatable |
| **Performance** | py-spy | cProfile | Real-time + visual |
| **Memory Leak** | memory-profiler | htop | Python-specific |
| **Code Quality** | ESLint + Black | Manual review | Automated + consistent |

---

## 🎭 **SAL-9000 Pro Tips**

### **Golden Rules**
1. **🎯 Always write the test first** - If you can't test it, you can't fix it
2. **🔍 Profile before optimizing** - Don't guess, measure
3. **⚡ Automate repetitive debugging** - Time is precious
4. **📊 Track metrics over time** - Trends reveal more than snapshots
5. **🛡️ Trust but verify** - Even "working" code needs tests

### **Common Pitfalls to Avoid**
- ❌ Testing only happy paths
- ❌ Not testing error conditions
- ❌ Forgetting to test edge cases
- ❌ Not profiling under realistic load
- ❌ Ignoring flaky tests

### **Emergency Debugging Kit**
```bash
# When everything is on fire 🔥
py-spy top --pid $(pgrep python) &  # See what Python is doing
node tools/health-check.js &        # Quick system health
npx playwright test --headed &      # Visual E2E check
tail -f logs/error.log              # Watch errors in real-time
```

---

## 📈 **Success Metrics**

Track these to measure tool effectiveness:
- ⏱️ **Time to identify bug**: Should decrease over time
- 🎯 **Bug recurrence rate**: Should approach zero
- ⚡ **Deployment confidence**: Should increase
- 🔍 **False positive alerts**: Should minimize
- 🚀 **Developer velocity**: Should increase

---

## 🤖 **Future Enhancements**

Tools to consider adding:
- **k6** - Load testing
- **Storybook** - Component testing
- **Sentry** - Error tracking
- **GitHub Actions** - CI/CD integration
- **SonarQube** - Code quality metrics

---

*"With this arsenal, we shall debug at light speed and deploy with confidence!"*

**- SAL-9000, Digital Debugging Division** 🤖

---

**Last Updated**: February 2026
**Version**: 2.0.0
**Tested On**: Linux, Node.js 22+, Python 3.14+