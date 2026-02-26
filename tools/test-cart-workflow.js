/**
 * 🛒 Cart Workflow Debug Script - SAL-9000 Analysis
 * Tests the complete cart workflow to identify where it's breaking
 */

const puppeteer = require('playwright');

async function testCartWorkflow() {
  console.log('🛒 Starting cart workflow test...');

  try {
    // Launch browser
    const { chromium } = puppeteer;
    const browser = await chromium.launch({ headless: false });
    const page = await browser.newPage();

    // Enable console logging
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        console.error('❌ Browser Error:', msg.text());
      } else if (msg.text().includes('❌') || msg.text().includes('Error')) {
        console.error('🔍 Browser Log:', msg.text());
      } else {
        console.log('📄 Browser Log:', msg.text());
      }
    });

    // Navigate to the app
    console.log('🌐 Loading Parody Critics app...');
    await page.goto('http://localhost:8877', { waitUntil: 'networkidle' });

    // Wait for app to load
    await page.waitForSelector('.app-container', { timeout: 5000 });
    console.log('✅ App loaded successfully');

    // Step 1: Search for content
    console.log('🔍 Step 1: Searching for Matrix...');
    await page.fill('#search-input', 'matrix');
    await page.press('#search-input', 'Enter');
    await page.waitForTimeout(1000);

    // Step 2: Add item to cart
    console.log('🛒 Step 2: Adding item to cart...');
    const addToCartBtn = await page.waitForSelector('.btn-add-to-cart', { timeout: 3000 });
    await addToCartBtn.click();
    await page.waitForTimeout(500);

    // Check if cart has items
    const cartCount = await page.textContent('#cart-count');
    console.log(`🛒 Cart count: ${cartCount}`);

    // Step 3: Open cart
    console.log('🛒 Step 3: Opening cart...');
    await page.click('#cart-btn');
    await page.waitForTimeout(1000);

    // Verify cart panel is visible
    const cartPanel = await page.isVisible('#cart-panel');
    console.log(`🛒 Cart panel visible: ${cartPanel}`);

    if (cartPanel) {
      // Step 4: Proceed to checkout
      console.log('✅ Step 4: Proceeding to checkout...');
      const checkoutBtn = await page.waitForSelector('#proceed-checkout-btn', { timeout: 3000 });

      // Log cart contents before checkout
      const cartContents = await page.evaluate(() => {
        return window.app ? window.app.cart.size : 'App not found';
      });
      console.log(`🛒 Cart contents before checkout: ${cartContents}`);

      await checkoutBtn.click();
      await page.waitForTimeout(2000);

      // Step 5: Check if checkout view is visible
      const checkoutView = await page.isVisible('#checkout-view');
      console.log(`✅ Checkout view visible: ${checkoutView}`);

      if (checkoutView) {
        console.log('✅ SUCCESS: Cart workflow working correctly!');

        // Log current view for debugging
        const currentView = await page.evaluate(() => {
          return window.app ? window.app.currentView : 'No current view';
        });
        console.log(`📍 Current view: ${currentView}`);

        // Check for any missing elements
        const mediaList = await page.isVisible('#checkout-media-list');
        const criticsSelection = await page.isVisible('#critics-selection');
        console.log(`📽️ Media list visible: ${mediaList}`);
        console.log(`🎭 Critics selection visible: ${criticsSelection}`);
      } else {
        console.error('❌ FAILURE: Checkout view not visible after clicking checkout!');

        // Debug: Check what views are active
        const activeViews = await page.evaluate(() => {
          const views = document.querySelectorAll('.view.active');
          return Array.from(views).map((v) => v.id);
        });
        console.log(`🔍 Active views: ${JSON.stringify(activeViews)}`);

        // Check if cart panel is still open
        const stillOpen = await page.isVisible('#cart-panel');
        console.log(`🛒 Cart panel still open: ${stillOpen}`);
      }
    } else {
      console.error('❌ FAILURE: Cart panel not visible after clicking cart button!');
    }

    // Wait a bit before closing
    await page.waitForTimeout(5000);
    await browser.close();
  } catch (error) {
    console.error('❌ Test failed with error:', error);
  }
}

// Run the test
testCartWorkflow().catch(console.error);
