const { chromium } = require('playwright');

(async () => {
  console.log('🔍 SAL-9000: Testing cart overlay closing functionality...');

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  // Listen for console messages
  page.on('console', (msg) => console.log('🌐 [LOG]:', msg.text()));
  page.on('pageerror', (err) => console.log('🔴 [ERROR]:', err.message));

  try {
    console.log('📍 1. Loading page...');
    await page.goto('http://localhost:8877');
    await page.waitForLoadState('networkidle');

    console.log('📍 2. Waiting for app to initialize...');
    await page.waitForTimeout(2000);

    console.log('📍 3. Going to media tab to add items...');
    await page.click('button[data-view="media"]');
    await page.waitForTimeout(1000);

    console.log('📍 4. Adding items to cart...');
    const checkboxes = await page.$$('input[type="checkbox"]');
    if (checkboxes.length >= 2) {
      await checkboxes[0].click();
      await checkboxes[1].click();
      await page.waitForTimeout(500);
    }

    console.log('📍 5. Opening cart...');
    await page.click('#cart-btn');
    await page.waitForTimeout(1000);

    // Check if cart is open
    const isCartVisible = await page.isVisible('#cart-panel.show');
    console.log(`Cart panel visible: ${isCartVisible}`);

    const isOverlayVisible = await page.isVisible('#cart-overlay.show');
    console.log(`Overlay visible: ${isOverlayVisible}`);

    if (isCartVisible && isOverlayVisible) {
      console.log('✅ SUCCESS: Both cart and overlay are visible!');

      console.log('📍 6. Testing overlay click to close...');
      await page.click('#cart-overlay');
      await page.waitForTimeout(1000);

      const isCartClosed = await page.isHidden('#cart-panel.show');
      const isOverlayClosed = await page.isHidden('#cart-overlay.show');

      if (isCartClosed && isOverlayClosed) {
        console.log('✅ SUCCESS: Overlay click successfully closes cart!');
      } else {
        console.log('❌ FAILED: Overlay click did not close cart properly');
        console.log(`Cart closed: ${isCartClosed}, Overlay closed: ${isOverlayClosed}`);
      }
    } else {
      console.log('❌ FAILED: Cart or overlay not visible');
    }

    console.log('🏁 Test completed');
  } catch (error) {
    console.log('❌ Test failed:', error.message);
  } finally {
    await browser.close();
  }
})();
