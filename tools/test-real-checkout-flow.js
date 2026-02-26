/**
 * 🎬 Real Checkout Flow Test - SAL-9000 Analysis
 * Tests checkout with actual media data to reproduce the user's issue
 */

const puppeteer = require('playwright');

async function testRealCheckoutFlow() {
  console.log('🎬 Starting real checkout flow test...');

  try {
    const { chromium } = puppeteer;
    const browser = await chromium.launch({
      headless: false,
      slowMo: 500,
      devtools: true,
    });
    const page = await browser.newPage();

    // Enable all logging
    page.on('console', (msg) => {
      const type = msg.type();
      const text = msg.text();
      if (type === 'error') {
        console.error(`❌ ${type.toUpperCase()}: ${text}`);
      } else if (text.includes('❌') || text.includes('Error')) {
        console.error(`🔍 ${type.toUpperCase()}: ${text}`);
      } else {
        console.log(`📄 ${type.toUpperCase()}: ${text}`);
      }
    });

    page.on('pageerror', (error) => {
      console.error('❌ Page Error:', error.message);
    });

    // Navigate to the app
    console.log('🌐 Loading Parody Critics app...');
    await page.goto('http://localhost:8877', { waitUntil: 'domcontentloaded' });

    // Wait for app to be fully loaded
    await page.waitForSelector('.header', { timeout: 10000 });
    await page.waitForTimeout(2000); // Give time for JS to initialize

    console.log('✅ App loaded, proceeding with real workflow...');

    // Step 1: Go to media view
    console.log('🎬 Step 1: Navigating to media view...');
    await page.click('.nav-btn[data-view="media"]');
    await page.waitForTimeout(1000);

    // Step 2: Search for actual content
    console.log('🔍 Step 2: Searching for Matrix...');
    await page.fill('#search-input', 'matrix');
    await page.press('#search-input', 'Enter');
    await page.waitForTimeout(2000); // Wait for search results

    // Check if results loaded
    const resultsExist = await page.isVisible('.media-grid');
    console.log(`🎬 Search results visible: ${resultsExist}`);

    if (resultsExist) {
      // Step 3: Add first item to cart
      console.log('🛒 Step 3: Adding first item to cart...');
      const firstAddBtn = await page.waitForSelector('.btn-add-to-cart', { timeout: 5000 });

      // Get the movie title for logging
      const movieTitle = await page.evaluate(() => {
        const firstCard = document.querySelector('.media-card');
        return firstCard ? firstCard.querySelector('.media-title')?.textContent : 'Unknown';
      });
      console.log(`🎬 Adding "${movieTitle}" to cart...`);

      await firstAddBtn.click();
      await page.waitForTimeout(1000);

      // Verify cart count updated
      const cartCount = await page.textContent('#cart-count');
      console.log(`🛒 Cart count after add: ${cartCount}`);

      if (cartCount && cartCount !== '0') {
        // Step 4: Open cart
        console.log('🛒 Step 4: Opening cart panel...');
        await page.click('#cart-btn');
        await page.waitForTimeout(1000);

        // Verify cart panel opened
        const cartPanelOpen = await page.isVisible('#cart-panel');
        console.log(`🛒 Cart panel open: ${cartPanelOpen}`);

        if (cartPanelOpen) {
          // Check cart contents
          const cartItems = await page.evaluate(() => {
            const items = document.querySelectorAll('.cart-item');
            return Array.from(items).map((item) => {
              return {
                title: item.querySelector('.cart-item-title')?.textContent,
                year: item.querySelector('.cart-item-year')?.textContent,
              };
            });
          });
          console.log('🛒 Cart items:', cartItems);

          // Step 5: Proceed to checkout (THE CRITICAL STEP)
          console.log('✅ Step 5: CRITICAL - Proceeding to checkout...');

          // Log app state before checkout
          const beforeState = await page.evaluate(() => {
            return {
              currentView: window.app?.currentView,
              cartSize: window.app?.cart.size,
              activeViews: Array.from(document.querySelectorAll('.view.active')).map((v) => v.id),
            };
          });
          console.log('🔍 State before checkout:', beforeState);

          const checkoutBtn = await page.waitForSelector('#proceed-checkout-btn', {
            timeout: 5000,
          });
          await checkoutBtn.click();

          // Wait a moment and check what happened
          await page.waitForTimeout(2000);

          // Log app state after checkout
          const afterState = await page.evaluate(() => {
            return {
              currentView: window.app?.currentView,
              cartSize: window.app?.cart.size,
              activeViews: Array.from(document.querySelectorAll('.view.active')).map((v) => v.id),
              cartPanelVisible:
                document.getElementById('cart-panel')?.style.display !== 'none' &&
                document.getElementById('cart-panel')?.classList.contains('open'),
              checkoutViewVisible: document
                .getElementById('checkout-view')
                ?.classList.contains('active'),
            };
          });
          console.log('🔍 State after checkout:', afterState);

          // Check if checkout view is actually visible
          const checkoutVisible = await page.isVisible('#checkout-view');
          console.log(`👁️ Checkout view visible to user: ${checkoutVisible}`);

          if (checkoutVisible) {
            console.log('✅ SUCCESS: Real checkout flow working!');

            // Check for checkout content
            const hasMediaList = await page.isVisible('#checkout-media-list');
            const hasCriticsSelection = await page.isVisible('#critics-selection');
            console.log(`📽️ Checkout media list visible: ${hasMediaList}`);
            console.log(`🎭 Critics selection visible: ${hasCriticsSelection}`);
          } else {
            console.error('❌ PROBLEM REPRODUCED: Checkout view not visible after real checkout!');

            // Try to diagnose the issue
            const diagnosis = await page.evaluate(() => {
              const checkoutView = document.getElementById('checkout-view');
              const cartPanel = document.getElementById('cart-panel');

              return {
                checkoutExists: !!checkoutView,
                checkoutClasses: checkoutView?.className,
                checkoutStyle: checkoutView?.style.cssText,
                cartPanelExists: !!cartPanel,
                cartPanelClasses: cartPanel?.className,
                cartPanelStyle: cartPanel?.style.cssText,
                allActiveViews: Array.from(document.querySelectorAll('.view')).map((v) => ({
                  id: v.id,
                  active: v.classList.contains('active'),
                  display: v.style.display,
                })),
              };
            });

            console.log('🔬 Detailed diagnosis:', JSON.stringify(diagnosis, null, 2));
          }
        } else {
          console.error('❌ Cart panel did not open');
        }
      } else {
        console.error('❌ Item was not added to cart');
      }
    } else {
      console.error('❌ No search results found');
    }

    // Keep browser open for manual inspection
    console.log('⏸️ Keeping browser open for manual inspection...');
    await page.waitForTimeout(60000);

    await browser.close();
  } catch (error) {
    console.error('❌ Real flow test failed:', error);
  }
}

// Run the test
testRealCheckoutFlow().catch(console.error);
