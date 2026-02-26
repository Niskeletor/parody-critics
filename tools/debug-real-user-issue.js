/**
 * 🔍 Debug Real User Issue - SAL-9000 Emergency Analysis
 * Tests exactly why user can't see checkout after our fix
 */

const puppeteer = require('playwright');

async function debugRealUserIssue() {
  console.log("🚨 EMERGENCY DEBUG: Why user still can't see checkout...");

  try {
    const { chromium } = puppeteer;
    const browser = await chromium.launch({
      headless: false,
      slowMo: 1500,
    });
    const page = await browser.newPage();

    // Capture ALL console messages
    page.on('console', (msg) => {
      console.log(`📄 ${msg.type().toUpperCase()}: ${msg.text()}`);
    });

    page.on('pageerror', (error) => {
      console.error('💥 PAGE ERROR:', error.message);
    });

    await page.goto('http://localhost:8877', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    console.log('🔍 STEP 1: Check if our forceCheckoutVisible method exists...');
    const methodExists = await page.evaluate(() => {
      return typeof window.app?.forceCheckoutVisible === 'function';
    });
    console.log(`🔧 forceCheckoutVisible method exists: ${methodExists}`);

    // Add test item
    console.log('🔍 STEP 2: Adding item to cart...');
    await page.evaluate(() => {
      const testItem = {
        tmdb_id: 'debug-test',
        title: 'Debug Test Movie',
        year: 2024,
        type: 'movie',
      };
      window.app.addToCart(testItem);
    });

    // Open cart
    console.log('🔍 STEP 3: Opening cart...');
    await page.click('#cart-btn');
    await page.waitForTimeout(2000);

    // Check cart state before clicking
    const cartState = await page.evaluate(() => ({
      cartSize: window.app.cart.size,
      cartPanelVisible: document.getElementById('cart-panel')?.classList.contains('open'),
      checkoutBtnExists: !!document.getElementById('cart-checkout-btn'),
      checkoutBtnDisabled: document.getElementById('cart-checkout-btn')?.disabled,
    }));
    console.log('🛒 Cart state before checkout:', cartState);

    console.log('🚨 STEP 4: CLICKING CHECKOUT - MONITORING EVERYTHING...');

    // Click and immediately start monitoring
    await page.click('#cart-checkout-btn');

    // Check immediate state
    await page.waitForTimeout(500);
    const immediateState = await page.evaluate(() => {
      const checkout = document.getElementById('checkout-view');
      return {
        checkoutExists: !!checkout,
        hasActiveClass: checkout?.classList.contains('active'),
        currentAppView: window.app?.currentView,
        checkoutStyles: checkout
          ? {
              position: window.getComputedStyle(checkout).position,
              top: window.getComputedStyle(checkout).top,
              left: window.getComputedStyle(checkout).left,
              zIndex: window.getComputedStyle(checkout).zIndex,
              display: window.getComputedStyle(checkout).display,
              width: window.getComputedStyle(checkout).width,
              height: window.getComputedStyle(checkout).height,
            }
          : null,
      };
    });

    console.log('⚡ IMMEDIATE state (500ms after click):', JSON.stringify(immediateState, null, 2));

    // Wait longer and check again
    await page.waitForTimeout(3000);

    const finalState = await page.evaluate(() => {
      const checkout = document.getElementById('checkout-view');
      const rect = checkout?.getBoundingClientRect();

      return {
        checkoutExists: !!checkout,
        hasActiveClass: checkout?.classList.contains('active'),
        isVisible: checkout
          ? window.getComputedStyle(checkout).display !== 'none' &&
            window.getComputedStyle(checkout).visibility !== 'hidden' &&
            parseFloat(window.getComputedStyle(checkout).opacity) > 0
          : false,
        inViewport: rect
          ? rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= window.innerHeight &&
            rect.right <= window.innerWidth
          : false,
        boundingRect: rect
          ? {
              top: rect.top,
              left: rect.left,
              width: rect.width,
              height: rect.height,
            }
          : null,
        computedStyles: checkout
          ? {
              position: window.getComputedStyle(checkout).position,
              top: window.getComputedStyle(checkout).top,
              left: window.getComputedStyle(checkout).left,
              zIndex: window.getComputedStyle(checkout).zIndex,
              display: window.getComputedStyle(checkout).display,
              transform: window.getComputedStyle(checkout).transform,
              backgroundColor: window.getComputedStyle(checkout).backgroundColor,
            }
          : null,
      };
    });

    console.log('🔬 FINAL state (3.5s after click):', JSON.stringify(finalState, null, 2));

    const userCanSee = await page.isVisible('#checkout-view');
    console.log(`👁️ Can USER actually see checkout? ${userCanSee}`);

    if (!userCanSee) {
      console.log('❌ CONFIRMED: User issue reproduced - checkout not visible');

      // Let's try to manually force it visible and see what happens
      console.log('🔧 MANUALLY applying nuclear CSS...');
      const manualResult = await page.evaluate(() => {
        const checkout = document.getElementById('checkout-view');
        if (checkout) {
          checkout.style.position = 'fixed';
          checkout.style.top = '0';
          checkout.style.left = '0';
          checkout.style.width = '100vw';
          checkout.style.height = '100vh';
          checkout.style.zIndex = '999999';
          checkout.style.backgroundColor = '#121212';
          checkout.style.display = 'block';
          checkout.style.visibility = 'visible';
          checkout.style.opacity = '1';
          return 'Manual CSS applied';
        }
        return 'Checkout element not found';
      });

      console.log('🔧 Manual CSS result:', manualResult);

      await page.waitForTimeout(2000);
      const afterManual = await page.isVisible('#checkout-view');
      console.log(`👁️ Visible after manual CSS? ${afterManual}`);
    }

    console.log('⏸️ Browser staying open for your inspection (60s)...');
    console.log('💡 Compare what you see vs what the tests report');
    await page.waitForTimeout(60000);
    await browser.close();
  } catch (error) {
    console.error('❌ Debug failed:', error);
  }
}

debugRealUserIssue().catch(console.error);
