/**
 * 🔍 Quick Checkout Debug - SAL-9000 Analysis
 * Simple test to identify the checkout disappearing issue
 */

const puppeteer = require('playwright');

async function debugCheckoutIssue() {
  console.log('🔍 Starting checkout debug test...');

  try {
    const { chromium } = puppeteer;
    const browser = await chromium.launch({ headless: false, slowMo: 1000 });
    const page = await browser.newPage();

    // Enable console logging
    page.on('console', (msg) => {
      console.log(`📄 ${msg.type().toUpperCase()}: ${msg.text()}`);
    });

    // Error handling
    page.on('pageerror', (error) => {
      console.error('❌ Page Error:', error.message);
    });

    // Navigate to the app
    console.log('🌐 Loading app...');
    await page.goto('http://localhost:8877', { waitUntil: 'domcontentloaded' });

    // Wait for header to load (basic element)
    await page.waitForSelector('.header', { timeout: 10000 });
    console.log('✅ App basic structure loaded');

    // Check if views exist
    const views = await page.evaluate(() => {
      const viewElements = document.querySelectorAll('.view');
      return Array.from(viewElements).map((v) => ({
        id: v.id,
        active: v.classList.contains('active'),
      }));
    });
    console.log('🔍 Available views:', views);

    // Test direct checkout view activation
    console.log('🧪 Testing direct checkout view activation...');
    const showCheckoutResult = await page.evaluate(() => {
      try {
        if (window.app) {
          window.app.showView('checkout');
          return { success: true, currentView: window.app.currentView };
        } else {
          return { success: false, error: 'App not found' };
        }
      } catch (error) {
        return { success: false, error: error.message };
      }
    });

    console.log('🧪 Direct checkout activation result:', showCheckoutResult);

    if (showCheckoutResult.success) {
      await page.waitForTimeout(2000);

      // Check if checkout view is now visible
      const checkoutVisible = await page.isVisible('#checkout-view');
      console.log(`👁️ Checkout view visible: ${checkoutVisible}`);

      if (checkoutVisible) {
        console.log('✅ Checkout view can be activated directly!');

        // Now test the cart workflow
        console.log('🛒 Testing cart → checkout workflow...');

        // Add an item to cart manually
        const cartTestResult = await page.evaluate(() => {
          try {
            if (window.app) {
              // Add a test item
              const testItem = {
                tmdb_id: 'test-item',
                title: 'Test Movie',
                year: 2024,
                type: 'movie',
                poster_url: null,
              };
              window.app.addToCart(testItem);
              return { success: true, cartSize: window.app.cart.size };
            }
            return { success: false, error: 'App not found' };
          } catch (error) {
            return { success: false, error: error.message };
          }
        });

        console.log('🛒 Cart test result:', cartTestResult);

        if (cartTestResult.success && cartTestResult.cartSize > 0) {
          // Try proceedToCheckout
          console.log('🛒 Testing proceedToCheckout...');
          const checkoutProceedResult = await page.evaluate(() => {
            try {
              if (window.app) {
                window.app.proceedToCheckout();
                return { success: true, currentView: window.app.currentView };
              }
              return { success: false, error: 'App not found' };
            } catch (error) {
              return { success: false, error: error.message };
            }
          });

          console.log('🛒 Proceed to checkout result:', checkoutProceedResult);

          await page.waitForTimeout(2000);

          // Final check
          const finalCheckoutVisible = await page.isVisible('#checkout-view');
          console.log(`👁️ Final checkout view visible: ${finalCheckoutVisible}`);

          if (finalCheckoutVisible) {
            console.log('✅ SUCCESS: Cart → Checkout workflow is working!');
          } else {
            console.log('❌ PROBLEM: Checkout view disappears after proceedToCheckout()');
          }
        }
      }
    }

    // Keep browser open for manual inspection
    console.log('⏸️ Keeping browser open for 30 seconds for manual inspection...');
    await page.waitForTimeout(30000);

    await browser.close();
  } catch (error) {
    console.error('❌ Debug test failed:', error);
  }
}

// Run the debug
debugCheckoutIssue().catch(console.error);
