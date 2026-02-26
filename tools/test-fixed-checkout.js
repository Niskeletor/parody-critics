/**
 * 🔧 Fixed Checkout Test - SAL-9000 Analysis
 * Tests the improved checkout flow with better error handling
 */

const puppeteer = require('playwright');

async function testFixedCheckout() {
  console.log('🔧 Testing improved checkout flow...');

  try {
    const { chromium } = puppeteer;
    const browser = await chromium.launch({
      headless: false,
      slowMo: 800,
    });
    const page = await browser.newPage();

    // Comprehensive logging
    page.on('console', (msg) => {
      const type = msg.type();
      const text = msg.text();
      const prefix =
        type === 'error'
          ? '❌'
          : type === 'warning'
            ? '⚠️'
            : text.includes('✅')
              ? '✅'
              : text.includes('❌')
                ? '❌'
                : text.includes('🎬') || text.includes('🎭') || text.includes('🛒')
                  ? '📍'
                  : '📄';
      console.log(`${prefix} ${type.toUpperCase()}: ${text}`);
    });

    page.on('pageerror', (error) => {
      console.error('💥 PAGE ERROR:', error.message);
    });

    // Load app
    console.log('🌐 Loading app with improved error handling...');
    await page.goto('http://localhost:8877', { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('.header', { timeout: 10000 });
    await page.waitForTimeout(2000);

    // Go to media
    console.log('🎬 Navigating to media view...');
    await page.click('.nav-btn[data-view="media"]');
    await page.waitForTimeout(2000);

    // Wait for media to load
    await page.waitForSelector('.media-grid', { timeout: 10000 });

    // Add a test item directly via console (to avoid navigation complexity)
    console.log('🧪 Adding test item to cart via console...');
    const addResult = await page.evaluate(() => {
      if (window.app) {
        const testItem = {
          tmdb_id: 'test-fixed-checkout',
          title: 'Test Movie for Fixed Checkout',
          year: 2024,
          type: 'movie',
          poster_url: null,
          has_critics: false,
        };
        window.app.addToCart(testItem);
        return { success: true, cartSize: window.app.cart.size };
      }
      return { success: false, error: 'App not found' };
    });

    console.log('🛒 Add to cart result:', addResult);

    if (addResult.success && addResult.cartSize > 0) {
      // Open cart
      console.log('🛒 Opening cart...');
      await page.click('#cart-btn');
      await page.waitForTimeout(1000);

      // Verify cart is open
      const cartOpen = await page.isVisible('#cart-panel');
      console.log(`🛒 Cart panel open: ${cartOpen}`);

      if (cartOpen) {
        console.log('🔧 TESTING IMPROVED CHECKOUT - Clicking proceed...');

        // Click checkout with our improved error handling
        await page.click('#proceed-checkout-btn');

        // Give it more time and watch the console
        console.log('⏳ Waiting for checkout to complete...');
        await page.waitForTimeout(5000);

        // Check final state
        const finalState = await page.evaluate(() => ({
          currentView: window.app?.currentView,
          checkoutVisible: document.getElementById('checkout-view')?.classList.contains('active'),
          cartPanelVisible:
            window.getComputedStyle(document.getElementById('cart-panel')).display !== 'none',
        }));

        console.log('🔍 Final state after improved checkout:', finalState);

        const userVisibleCheckout = await page.isVisible('#checkout-view');
        console.log(`👁️ Checkout visible to user: ${userVisibleCheckout}`);

        if (userVisibleCheckout) {
          console.log('✅ SUCCESS: Improved checkout flow working!');

          // Test checkout content loading
          const contentLoaded = await page.evaluate(() => {
            const mediaList = document.getElementById('checkout-media-list');
            const criticsSection = document.getElementById('critics-selection');

            return {
              mediaListHasContent: mediaList?.children.length > 0,
              criticsHasContent: criticsSection?.children.length > 0,
              mediaListHTML: mediaList?.innerHTML.substring(0, 100) + '...',
              criticsHTML: criticsSection?.innerHTML.substring(0, 100) + '...',
            };
          });

          console.log('📋 Checkout content loaded:', contentLoaded);

          if (contentLoaded.mediaListHasContent && contentLoaded.criticsHasContent) {
            console.log('🎉 PERFECT: All checkout content loaded successfully!');
          } else {
            console.log('⚠️  Warning: Some content might not have loaded completely');
          }
        } else {
          console.log('❌ Issue still exists: Checkout not visible after improvements');

          // Get any error messages that might have appeared
          const errorMessages = await page.evaluate(() => {
            const errors = document.querySelectorAll('.error-message');
            return Array.from(errors).map((e) => e.textContent);
          });

          if (errorMessages.length > 0) {
            console.log('🔍 Error messages found:', errorMessages);
          }
        }
      }
    }

    // Keep browser open for inspection
    console.log('⏸️ Keeping browser open for inspection (30s)...');
    await page.waitForTimeout(30000);
    await browser.close();
  } catch (error) {
    console.error('❌ Fixed checkout test failed:', error);
  }
}

testFixedCheckout().catch(console.error);
