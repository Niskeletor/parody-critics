const { chromium } = require('playwright');

/**
 * 🛒 SAL-9000 E-commerce Cart System Test Suite
 * Testing the complete e-commerce functionality
 */
class EcommerceCartTestSuite {
  constructor() {
    this.baseUrl = 'http://localhost:8877';
    this.results = {
      passed: 0,
      failed: 0,
      tests: [],
    };
    this.browser = null;
    this.page = null;
  }

  async init() {
    console.log('🛒 SAL-9000: Initializing E-commerce Cart Test Suite...');
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
    console.log(`🧪 Testing: ${testName}`);
    const testStart = Date.now();

    try {
      await testFn();
      const duration = Date.now() - testStart;
      this.results.passed++;
      this.results.tests.push({
        name: testName,
        status: 'PASSED',
        duration: `${duration}ms`,
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
          path: `/tmp/ecommerce-failure-${Date.now()}.png`,
          fullPage: true,
        });
        console.log(`📸 Screenshot saved for debugging`);
      } catch (screenshotError) {
        console.log(`📸 Could not take screenshot: ${screenshotError.message}`);
      }
    }
  }

  // Test cart button visibility and initialization
  async testCartButtonInitialization() {
    await this.page.goto(this.baseUrl);

    // Check if cart button exists
    const cartButton = await this.page.$('#cart-btn');
    if (!cartButton) {
      throw new Error('Cart button not found in header');
    }

    // Check initial cart count
    const cartCount = await this.page.$eval('#cart-count', (el) => el.textContent);
    if (cartCount !== '0') {
      throw new Error(`Expected cart count to be 0, got: ${cartCount}`);
    }

    console.log('✅ Cart button initialized with count 0');
  }

  // Test adding items to cart
  async testAddItemsToCart() {
    await this.page.goto(this.baseUrl);

    // Navigate to media view
    await this.page.click('button[data-view="media"]');
    await this.page.waitForSelector('.media-card', { timeout: 10000 });

    // Find and click first selection checkbox
    const selectCheckbox = await this.page.$('.media-card-select');
    if (!selectCheckbox) {
      throw new Error('No selection checkboxes found on media cards');
    }

    await selectCheckbox.click();
    await this.page.waitForTimeout(1000);

    // Check cart count updated
    const cartCount = await this.page.$eval('#cart-count', (el) => el.textContent);
    if (cartCount !== '1') {
      throw new Error(`Expected cart count to be 1 after adding item, got: ${cartCount}`);
    }

    console.log('✅ Successfully added item to cart');
  }

  // Test cart panel functionality
  async testCartPanelFunctionality() {
    // Assuming we already have items in cart from previous test

    // Open cart panel
    await this.page.click('#cart-btn');
    await this.page.waitForTimeout(500);

    // Check if cart panel is visible
    const cartPanel = await this.page.$('.cart-panel.show');
    if (!cartPanel) {
      throw new Error('Cart panel did not open');
    }

    // Check if cart items are displayed
    const cartItems = await this.page.$$('.cart-item');
    if (cartItems.length === 0) {
      throw new Error('No cart items found in cart panel');
    }

    // Check if checkout button is enabled
    const checkoutBtn = await this.page.$('#cart-checkout-btn');
    const isDisabled = await this.page.evaluate((btn) => btn.disabled, checkoutBtn);
    if (isDisabled) {
      throw new Error('Checkout button should be enabled when cart has items');
    }

    console.log('✅ Cart panel functionality working correctly');
  }

  // Test removing items from cart
  async testRemoveItemsFromCart() {
    // Cart should be open from previous test

    // Find and click remove button
    const removeBtn = await this.page.$('.cart-item-remove');
    if (!removeBtn) {
      throw new Error('Remove button not found in cart item');
    }

    await removeBtn.click();
    await this.page.waitForTimeout(1000);

    // Check cart count decreased
    const cartCount = await this.page.$eval('#cart-count', (el) => el.textContent);
    if (cartCount !== '0') {
      throw new Error(`Expected cart count to be 0 after removing item, got: ${cartCount}`);
    }

    console.log('✅ Successfully removed item from cart');
  }

  // Test checkout flow
  async testCheckoutFlow() {
    // First add items back to cart
    await this.page.goto(this.baseUrl);
    await this.page.click('button[data-view="media"]');
    await this.page.waitForSelector('.media-card-select', { timeout: 10000 });

    // Add multiple items to cart
    const selectCheckboxes = await this.page.$$('.media-card-select');
    if (selectCheckboxes.length < 2) {
      throw new Error('Need at least 2 media items for checkout test');
    }

    // Add first two items
    await selectCheckboxes[0].click();
    await this.page.waitForTimeout(500);
    await selectCheckboxes[1].click();
    await this.page.waitForTimeout(500);

    // Open cart and proceed to checkout
    await this.page.click('#cart-btn');
    await this.page.waitForTimeout(500);

    const checkoutBtn = await this.page.$('#cart-checkout-btn');
    await checkoutBtn.click();
    await this.page.waitForTimeout(1000);

    // Check if we're in checkout view
    const checkoutView = await this.page.$('#checkout-view.active');
    if (!checkoutView) {
      throw new Error('Checkout view did not activate');
    }

    // Check if selected media is displayed
    const mediaItems = await this.page.$$('.checkout-media-item');
    if (mediaItems.length !== 2) {
      throw new Error(`Expected 2 media items in checkout, found: ${mediaItems.length}`);
    }

    console.log('✅ Checkout flow navigation working correctly');
  }

  // Test critic selection in checkout
  async testCriticSelectionInCheckout() {
    // Should be in checkout view from previous test

    // Wait for critics to load
    await this.page.waitForSelector('.critic-checkbox-item', { timeout: 10000 });

    // Select first critic
    const criticItems = await this.page.$$('.critic-checkbox-item');
    if (criticItems.length === 0) {
      throw new Error('No critics found in checkout');
    }

    await criticItems[0].click();
    await this.page.waitForTimeout(500);

    // Check if critic is selected
    const selectedCritic = await this.page.$('.critic-checkbox-item.selected');
    if (!selectedCritic) {
      throw new Error('Critic selection did not work');
    }

    // Check if processing button is enabled
    const processingBtn = await this.page.$('#start-processing-btn');
    const isDisabled = await this.page.evaluate((btn) => btn.disabled, processingBtn);
    if (isDisabled) {
      throw new Error('Processing button should be enabled when media and critics are selected');
    }

    console.log('✅ Critic selection functionality working correctly');
  }

  // Test batch processing initiation (without actually processing)
  async testBatchProcessingInitiation() {
    // Should have media and critics selected from previous tests

    // Click start processing
    const processingBtn = await this.page.$('#start-processing-btn');
    await processingBtn.click();
    await this.page.waitForTimeout(2000);

    // Check if progress section is visible
    const progressSection = await this.page.$('#progress-section:not(.hidden)');
    if (!progressSection) {
      throw new Error('Progress section did not become visible');
    }

    // Check if cancel button is visible
    const cancelBtn = await this.page.$('#cancel-processing-btn:not(.hidden)');
    if (!cancelBtn) {
      throw new Error('Cancel button did not become visible');
    }

    // Cancel the processing to avoid actual API calls
    await cancelBtn.click();
    await this.page.waitForTimeout(1000);

    console.log('✅ Batch processing initiation working correctly');
  }

  // Test cart persistence across navigation
  async testCartPersistenceAcrossNavigation() {
    // Clear cart first
    await this.page.evaluate(() => {
      if (window.app) {
        window.app.clearCart();
      }
    });

    // Add items to cart
    await this.page.goto(this.baseUrl);
    await this.page.click('button[data-view="media"]');
    await this.page.waitForSelector('.media-card-select', { timeout: 10000 });

    const selectCheckbox = await this.page.$('.media-card-select');
    await selectCheckbox.click();
    await this.page.waitForTimeout(500);

    // Navigate to different views and back
    await this.page.click('button[data-view="critics"]');
    await this.page.waitForTimeout(500);
    await this.page.click('button[data-view="status"]');
    await this.page.waitForTimeout(500);
    await this.page.click('button[data-view="media"]');
    await this.page.waitForTimeout(500);

    // Check cart count is still 1
    const cartCount = await this.page.$eval('#cart-count', (el) => el.textContent);
    if (cartCount !== '1') {
      throw new Error(`Cart did not persist across navigation. Expected 1, got: ${cartCount}`);
    }

    console.log('✅ Cart persistence working correctly');
  }

  // Test selection state visual feedback
  async testSelectionStateVisualFeedback() {
    await this.page.goto(this.baseUrl);
    await this.page.click('button[data-view="media"]');
    await this.page.waitForSelector('.media-card', { timeout: 10000 });

    // Get first media card
    const mediaCard = await this.page.$('.media-card');

    // Check initial state (not selected)
    let hasSelectedClass = await this.page.evaluate(
      (card) => card.classList.contains('selected'),
      mediaCard
    );
    if (hasSelectedClass) {
      throw new Error('Media card should not have selected class initially');
    }

    // Click to select
    const selectCheckbox = await mediaCard.$('.media-card-select');
    await selectCheckbox.click();
    await this.page.waitForTimeout(500);

    // Check selected state
    hasSelectedClass = await this.page.evaluate(
      (card) => card.classList.contains('selected'),
      mediaCard
    );
    if (!hasSelectedClass) {
      throw new Error('Media card should have selected class after clicking');
    }

    console.log('✅ Selection state visual feedback working correctly');
  }

  // Run all tests
  async runAllTests() {
    console.log('🛒 SAL-9000: Starting E-commerce Cart System Tests...\n');

    console.log('🛒 === CART INITIALIZATION TESTS ===');
    await this.runTest('Cart Button Initialization', () => this.testCartButtonInitialization());

    console.log('\n🛒 === CART MANIPULATION TESTS ===');
    await this.runTest('Add Items to Cart', () => this.testAddItemsToCart());
    await this.runTest('Cart Panel Functionality', () => this.testCartPanelFunctionality());
    await this.runTest('Remove Items from Cart', () => this.testRemoveItemsFromCart());

    console.log('\n🛒 === CHECKOUT FLOW TESTS ===');
    await this.runTest('Checkout Flow Navigation', () => this.testCheckoutFlow());
    await this.runTest('Critic Selection in Checkout', () => this.testCriticSelectionInCheckout());
    await this.runTest('Batch Processing Initiation', () => this.testBatchProcessingInitiation());

    console.log('\n🛒 === ADVANCED CART FEATURES ===');
    await this.runTest('Cart Persistence Across Navigation', () =>
      this.testCartPersistenceAcrossNavigation()
    );
    await this.runTest('Selection State Visual Feedback', () =>
      this.testSelectionStateVisualFeedback()
    );

    // Generate Report
    this.generateReport();
  }

  generateReport() {
    const total = this.results.passed + this.results.failed;

    console.log('\n' + '='.repeat(60));
    console.log('🛒 SAL-9000 E-COMMERCE CART TEST REPORT');
    console.log('='.repeat(60));
    console.log(`📊 Total Tests: ${total}`);
    console.log(`✅ Passed: ${this.results.passed}`);
    console.log(`❌ Failed: ${this.results.failed}`);
    console.log(`🎯 Success Rate: ${((this.results.passed / total) * 100).toFixed(1)}%`);

    if (this.results.failed > 0) {
      console.log('\n❌ FAILED TESTS:');
      this.results.tests
        .filter((t) => t.status === 'FAILED')
        .forEach((test) => {
          console.log(`   • ${test.name}: ${test.error}`);
        });
    }

    console.log('='.repeat(60));

    if (this.results.failed === 0) {
      console.log('🎉 ALL E-COMMERCE CART TESTS PASSED! System is ready for production! 🚀');
    } else {
      console.log('🚨 SOME E-COMMERCE TESTS FAILED! Review and fix issues! 🔍');
    }

    return this.results.failed === 0;
  }
}

// Run the test suite
(async () => {
  const testSuite = new EcommerceCartTestSuite();

  try {
    await testSuite.init();
    const success = await testSuite.runAllTests();
    process.exit(success ? 0 : 1);
  } catch (error) {
    console.error('❌ E-commerce test suite failed to initialize:', error);
    process.exit(1);
  } finally {
    await testSuite.cleanup();
  }
})();
