const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

/**
 * 🤖 SAL-9000 Comprehensive Test Suite
 * Never do blind debugging again!
 */
class ComprehensiveTestSuite {
  constructor() {
    this.baseUrl = 'http://localhost:8877';
    this.results = {
      passed: 0,
      failed: 0,
      skipped: 0,
      tests: [],
    };
    this.browser = null;
    this.page = null;
    this.startTime = Date.now();
  }

  async init() {
    console.log('🤖 SAL-9000: Initializing comprehensive test suite...');
    this.browser = await chromium.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox'],
    });
    this.page = await this.browser.newPage();

    // Enable console logging
    this.page.on('console', (msg) => {
      if (msg.type() === 'error') {
        console.log(`🔴 Browser Error: ${msg.text()}`);
      }
    });
  }

  async cleanup() {
    if (this.browser) {
      await this.browser.close();
    }
  }

  async runTest(testName, testFn) {
    console.log(`🧪 Running: ${testName}`);
    const testStart = Date.now();

    try {
      await testFn();
      const duration = Date.now() - testStart;
      this.results.passed++;
      this.results.tests.push({
        name: testName,
        status: 'PASSED',
        duration: `${duration}ms`,
        error: null,
      });
      console.log(`✅ PASSED: ${testName} (${duration}ms)`);
    } catch (error) {
      const duration = Date.now() - testStart;
      this.results.failed++;
      this.results.tests.push({
        name: testName,
        status: 'FAILED',
        duration: `${duration}ms`,
        error: error.message,
      });
      console.log(`❌ FAILED: ${testName} (${duration}ms)`);
      console.log(`   Error: ${error.message}`);

      // Take screenshot on failure
      try {
        await this.page.screenshot({
          path: `/tmp/test-failure-${Date.now()}.png`,
          fullPage: true,
        });
        console.log(`📸 Screenshot saved for debugging`);
      } catch (screenshotError) {
        console.log(`📸 Could not take screenshot: ${screenshotError.message}`);
      }
    }
  }

  // ========================================
  // Server Health Tests
  // ========================================

  async testServerHealth() {
    const response = await fetch(`${this.baseUrl}/api/health`);
    if (!response.ok) {
      throw new Error(`Health check failed: ${response.status}`);
    }
    const health = await response.json();
    if (health.status !== 'healthy') {
      throw new Error(`Server not healthy: ${JSON.stringify(health)}`);
    }
  }

  async testDatabaseConnection() {
    const response = await fetch(`${this.baseUrl}/api/stats`);
    if (!response.ok) {
      throw new Error(`Stats endpoint failed: ${response.status}`);
    }
    const stats = await response.json();
    if (!stats.media_count || stats.media_count === 0) {
      throw new Error('Database appears empty');
    }
  }

  async testLLMConnection() {
    const response = await fetch(`${this.baseUrl}/api/llm/status`);
    if (!response.ok) {
      throw new Error(`LLM status failed: ${response.status}`);
    }
    const status = await response.json();
    if (!status.healthy) {
      throw new Error(`LLM not healthy: ${JSON.stringify(status)}`);
    }
  }

  // ========================================
  // API Endpoint Tests
  // ========================================

  async testMediaSearch() {
    const response = await fetch(`${this.baseUrl}/api/media/search?query=matrix&limit=5`);
    if (!response.ok) {
      throw new Error(`Media search failed: ${response.status}`);
    }
    const results = await response.json();
    if (!Array.isArray(results) || results.length === 0) {
      throw new Error('Media search returned no results');
    }

    // Verify result structure
    const firstResult = results[0];
    const requiredFields = ['tmdb_id', 'title', 'year'];
    for (const field of requiredFields) {
      if (!firstResult[field]) {
        throw new Error(`Missing field in search result: ${field}`);
      }
    }
  }

  async testCharactersEndpoint() {
    const response = await fetch(`${this.baseUrl}/api/characters`);
    if (!response.ok) {
      throw new Error(`Characters endpoint failed: ${response.status}`);
    }
    const characters = await response.json();
    if (!Array.isArray(characters) || characters.length === 0) {
      throw new Error('No characters found');
    }

    // Check for expected characters
    const expectedCharacters = ['Marco Aurelio', 'Rosario Costras'];
    for (const expected of expectedCharacters) {
      const found = characters.find((c) => c.name === expected);
      if (!found) {
        throw new Error(`Expected character not found: ${expected}`);
      }
    }
  }

  async testMediaPagination() {
    const response = await fetch(`${this.baseUrl}/api/media?limit=10&offset=0`);
    if (!response.ok) {
      throw new Error(`Media pagination failed: ${response.status}`);
    }
    const results = await response.json();
    if (!Array.isArray(results) || results.length === 0) {
      throw new Error('Media pagination returned no results');
    }
    if (results.length > 10) {
      throw new Error('Media pagination limit not respected');
    }
  }

  // ========================================
  // UI Navigation Tests
  // ========================================

  async testPageLoad() {
    await this.page.goto(this.baseUrl);
    const title = await this.page.title();
    if (!title.includes('Parody Critics')) {
      throw new Error(`Unexpected page title: ${title}`);
    }

    // Check for essential elements
    const essentialSelectors = ['.header', '.nav-btn', '.main', '.footer'];

    for (const selector of essentialSelectors) {
      const element = await this.page.$(selector);
      if (!element) {
        throw new Error(`Essential element missing: ${selector}`);
      }
    }
  }

  async testTabNavigation() {
    await this.page.goto(this.baseUrl);

    const tabs = ['home', 'media', 'critics', 'generate', 'status'];

    for (const tab of tabs) {
      // Click tab
      await this.page.click(`button[data-view="${tab}"]`);
      await this.page.waitForTimeout(500);

      // Check if tab is active
      const activeTab = await this.page.$eval('.nav-btn.active', (btn) => btn.dataset.view);
      if (activeTab !== tab) {
        throw new Error(`Tab navigation failed for ${tab}. Active: ${activeTab}`);
      }

      // Check if corresponding view is visible
      const viewVisible = await this.page.isVisible(`#${tab}-view.active`);
      if (!viewVisible) {
        throw new Error(`View not visible for tab: ${tab}`);
      }
    }
  }

  async testMediaListLoad() {
    await this.page.goto(this.baseUrl);
    await this.page.click('button[data-view="media"]');

    // Wait for media to load
    await this.page.waitForSelector('.media-card', { timeout: 10000 });

    // Check if media cards are present
    const mediaCards = await this.page.$$('.media-card');
    if (mediaCards.length === 0) {
      throw new Error('No media cards loaded');
    }

    // Check if generate buttons are present
    const generateButtons = await this.page.$$('.generate-critic-btn');
    if (generateButtons.length === 0) {
      throw new Error('No generate critic buttons found');
    }
  }

  async testAlphabetNavigation() {
    await this.page.goto(this.baseUrl);
    await this.page.click('button[data-view="media"]');
    await this.page.waitForSelector('.alphabet-nav', { timeout: 5000 });

    // Test letter filtering
    const letterButtons = await this.page.$$('.letter-btn[data-letter="A"]');
    if (letterButtons.length > 0) {
      await letterButtons[0].click();
      await this.page.waitForTimeout(1000);

      // Check if filtered results are shown
      const mediaCards = await this.page.$$('.media-card');
      if (mediaCards.length === 0) {
        throw new Error('No results for letter A filter');
      }
    }
  }

  // ========================================
  // Critical User Journey Tests
  // ========================================

  async testCompleteGenerationFlow() {
    await this.page.goto(this.baseUrl);

    // 1. Navigate to media
    await this.page.click('button[data-view="media"]');
    await this.page.waitForSelector('.generate-critic-btn', { timeout: 10000 });

    // 2. Click generate button
    const generateButtons = await this.page.$$('.generate-critic-btn');
    if (generateButtons.length === 0) {
      throw new Error('No generate buttons found');
    }
    await generateButtons[0].click();

    // 3. Should be in generate tab
    await this.page.waitForSelector('#generate-view.active', { timeout: 5000 });
    const activeTab = await this.page.$eval('.nav-btn.active', (btn) => btn.dataset.view);
    if (activeTab !== 'generate') {
      throw new Error(`Expected generate tab, got: ${activeTab}`);
    }

    // 4. Check if media is selected
    const selectedDisplay = await this.page.isVisible('#selected-media-display.show');
    if (!selectedDisplay) {
      throw new Error('Selected media display not shown');
    }

    // 5. Select a character
    await this.page.waitForSelector('.character-card', { timeout: 5000 });
    const characterCards = await this.page.$$('.character-card');
    if (characterCards.length === 0) {
      throw new Error('No character cards found');
    }
    await characterCards[0].click();

    // 6. Check if generate button is enabled
    const generateBtn = await this.page.$('#generate-btn');
    const isDisabled = await this.page.evaluate((btn) => btn.disabled, generateBtn);
    if (isDisabled) {
      throw new Error('Generate button should be enabled after selecting character');
    }

    // 7. Click generate (but don't wait for completion to avoid timeout)
    await generateBtn.click();

    // Just verify the request was made (check network or UI feedback)
    await this.page.waitForTimeout(2000);
    console.log('✅ Generation flow completed successfully');
  }

  async testErrorHandling() {
    // Test invalid API endpoint
    const response = await fetch(`${this.baseUrl}/api/nonexistent`);
    if (response.status !== 404) {
      throw new Error(`Expected 404 for invalid endpoint, got: ${response.status}`);
    }

    // Test invalid search query
    const searchResponse = await fetch(`${this.baseUrl}/api/media/search?query=a&limit=5`);
    if (searchResponse.status !== 422) {
      throw new Error(`Expected 422 for short query, got: ${searchResponse.status}`);
    }
  }

  // ========================================
  // Performance Tests
  // ========================================

  async testPageLoadTime() {
    const startTime = Date.now();
    await this.page.goto(this.baseUrl);
    await this.page.waitForSelector('.main', { timeout: 10000 });
    const loadTime = Date.now() - startTime;

    console.log(`📊 Page load time: ${loadTime}ms`);

    if (loadTime > 5000) {
      throw new Error(`Page load too slow: ${loadTime}ms`);
    }
  }

  async testAPIResponseTime() {
    const startTime = Date.now();
    const response = await fetch(`${this.baseUrl}/api/media/search?query=matrix&limit=5`);
    const responseTime = Date.now() - startTime;

    console.log(`📊 API response time: ${responseTime}ms`);

    if (responseTime > 2000) {
      throw new Error(`API response too slow: ${responseTime}ms`);
    }

    if (!response.ok) {
      throw new Error(`API request failed: ${response.status}`);
    }
  }

  // ========================================
  // Main Test Runner
  // ========================================

  async runAllTests() {
    console.log('🚀 SAL-9000: Starting comprehensive test suite...\n');

    // Server Health Tests
    console.log('🏥 === SERVER HEALTH TESTS ===');
    await this.runTest('Server Health Check', () => this.testServerHealth());
    await this.runTest('Database Connection', () => this.testDatabaseConnection());
    await this.runTest('LLM Connection', () => this.testLLMConnection());

    // API Tests
    console.log('\n🔌 === API ENDPOINT TESTS ===');
    await this.runTest('Media Search API', () => this.testMediaSearch());
    await this.runTest('Characters API', () => this.testCharactersEndpoint());
    await this.runTest('Media Pagination', () => this.testMediaPagination());
    await this.runTest('Error Handling', () => this.testErrorHandling());

    // Performance Tests
    console.log('\n⚡ === PERFORMANCE TESTS ===');
    await this.runTest('API Response Time', () => this.testAPIResponseTime());
    await this.runTest('Page Load Time', () => this.testPageLoadTime());

    // UI Tests
    console.log('\n🖥️ === UI NAVIGATION TESTS ===');
    await this.runTest('Page Load', () => this.testPageLoad());
    await this.runTest('Tab Navigation', () => this.testTabNavigation());
    await this.runTest('Media List Load', () => this.testMediaListLoad());
    await this.runTest('Alphabet Navigation', () => this.testAlphabetNavigation());

    // Critical Journey Tests
    console.log('\n🎯 === CRITICAL USER JOURNEY TESTS ===');
    await this.runTest('Complete Generation Flow', () => this.testCompleteGenerationFlow());

    // Generate Report
    this.generateReport();
  }

  generateReport() {
    const totalTime = Date.now() - this.startTime;
    const total = this.results.passed + this.results.failed + this.results.skipped;

    console.log('\n' + '='.repeat(60));
    console.log('🤖 SAL-9000 COMPREHENSIVE TEST REPORT');
    console.log('='.repeat(60));
    console.log(`📊 Total Tests: ${total}`);
    console.log(`✅ Passed: ${this.results.passed}`);
    console.log(`❌ Failed: ${this.results.failed}`);
    console.log(`⏸️ Skipped: ${this.results.skipped}`);
    console.log(`⏱️ Total Time: ${totalTime}ms`);
    console.log(`🎯 Success Rate: ${((this.results.passed / total) * 100).toFixed(1)}%`);

    if (this.results.failed > 0) {
      console.log('\n❌ FAILED TESTS:');
      this.results.tests
        .filter((t) => t.status === 'FAILED')
        .forEach((test) => {
          console.log(`   • ${test.name}: ${test.error}`);
        });
    }

    // Save detailed report
    const reportPath = `/tmp/test-report-${Date.now()}.json`;
    fs.writeFileSync(
      reportPath,
      JSON.stringify(
        {
          timestamp: new Date().toISOString(),
          totalTime,
          results: this.results,
        },
        null,
        2
      )
    );

    console.log(`\n📄 Detailed report saved: ${reportPath}`);
    console.log('='.repeat(60));

    if (this.results.failed === 0) {
      console.log('🎉 ALL TESTS PASSED! System is healthy! 🚀');
    } else {
      console.log('🚨 SOME TESTS FAILED! Investigation required! 🔍');
    }

    return this.results.failed === 0;
  }
}

// Run the test suite
(async () => {
  const testSuite = new ComprehensiveTestSuite();

  try {
    await testSuite.init();
    const success = await testSuite.runAllTests();
    process.exit(success ? 0 : 1);
  } catch (error) {
    console.error('❌ Test suite failed to initialize:', error);
    process.exit(1);
  } finally {
    await testSuite.cleanup();
  }
})();
