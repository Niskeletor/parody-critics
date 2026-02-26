/**
 * 🎯 Direct Checkout Test - SAL-9000 Analysis
 * Tests checkout functionality directly to identify the exact issue
 */

const puppeteer = require('playwright');

async function testCheckoutDirect() {
  console.log('🎯 Testing checkout directly...');

  try {
    const { chromium } = puppeteer;
    const browser = await chromium.launch({
      headless: false,
      slowMo: 1000,
    });
    const page = await browser.newPage();

    // Comprehensive logging
    page.on('console', (msg) => {
      console.log(`📄 ${msg.type().toUpperCase()}: ${msg.text()}`);
    });

    page.on('pageerror', (error) => {
      console.error('💥 PAGE ERROR:', error.message);
    });

    // Load app
    await page.goto('http://localhost:8877', { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('.header', { timeout: 10000 });
    await page.waitForTimeout(3000);

    // Test the checkout flow directly using JavaScript
    console.log('🧪 Testing checkout flow directly via console...');
    const testResult = await page.evaluate(async () => {
      try {
        if (!window.app) {
          return { success: false, error: 'App not available' };
        }

        console.log('🧪 Step 1: Adding test item to cart...');
        const testItem = {
          tmdb_id: 'direct-test-item',
          title: 'Direct Test Movie',
          year: 2024,
          type: 'movie',
          poster_url: null,
          has_critics: false,
        };

        window.app.addToCart(testItem);
        console.log('✅ Item added to cart, cart size:', window.app.cart.size);

        if (window.app.cart.size === 0) {
          return { success: false, error: 'Item not added to cart' };
        }

        console.log('🧪 Step 2: Calling proceedToCheckout()...');

        // Call proceedToCheckout (now async) and wait for it
        await window.app.proceedToCheckout();

        console.log('🧪 Step 3: Checking view state after checkout...');

        const state = {
          currentView: window.app.currentView,
          checkoutViewExists: !!document.getElementById('checkout-view'),
          checkoutViewActive: document
            .getElementById('checkout-view')
            ?.classList.contains('active'),
          checkoutViewVisible:
            window.getComputedStyle(document.getElementById('checkout-view')).display !== 'none',
          allActiveViews: Array.from(document.querySelectorAll('.view.active')).map((v) => v.id),
        };

        console.log('📊 Final state:', state);

        return {
          success: true,
          state: state,
          checkoutWorked: state.checkoutViewActive,
        };
      } catch (error) {
        console.error('❌ Direct test error:', error);
        return {
          success: false,
          error: error.message,
          stack: error.stack,
        };
      }
    });

    console.log('🎯 Direct test result:', testResult);

    if (testResult.success) {
      if (testResult.checkoutWorked) {
        console.log('✅ SUCCESS: Direct checkout test passed!');
      } else {
        console.log('❌ ISSUE CONFIRMED: Checkout view not active after proceedToCheckout()');
        console.log('📊 State details:', testResult.state);
      }
    } else {
      console.log('❌ Direct test failed:', testResult.error);
    }

    // Manual verification
    await page.waitForTimeout(2000);
    const finalVisible = await page.isVisible('#checkout-view');
    console.log(`👁️ Checkout visually visible: ${finalVisible}`);

    // Keep browser open
    console.log('⏸️ Browser staying open for inspection (30s)...');
    await page.waitForTimeout(30000);
    await browser.close();
  } catch (error) {
    console.error('❌ Direct checkout test failed:', error);
  }
}

testCheckoutDirect().catch(console.error);
