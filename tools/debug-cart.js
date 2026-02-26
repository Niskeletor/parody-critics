const { chromium } = require('playwright');

/**
 * 🛒 SAL-9000 Cart Debugging Tool
 * Quick debugging of cart functionality
 */
async function debugCart() {
  console.log('🔍 SAL-9000: Starting cart debugging...');

  const browser = await chromium.launch({
    headless: false, // Run in visible mode for debugging
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  try {
    const page = await browser.newPage();

    // Enable console logging
    page.on('console', (msg) => {
      console.log(`🌐 [${msg.type().toUpperCase()}]: ${msg.text()}`);
    });

    // Enable error logging
    page.on('pageerror', (error) => {
      console.error('❌ Page Error:', error.message);
    });

    console.log('📍 1. Navigating to site...');
    await page.goto('http://localhost:8877', { waitUntil: 'networkidle' });

    console.log('📍 2. Checking if cart button exists...');
    const cartButton = await page.$('#cart-btn');
    if (!cartButton) {
      console.error('❌ Cart button not found!');
      return;
    }
    console.log('✅ Cart button found');

    console.log('📍 3. Checking if app is initialized...');
    const appExists = await page.evaluate(() => {
      return typeof window.app !== 'undefined';
    });
    console.log(`App exists: ${appExists}`);

    if (appExists) {
      const cartSize = await page.evaluate(() => {
        return window.app.cart ? window.app.cart.size : 'undefined';
      });
      console.log(`Cart size: ${cartSize}`);
    }

    console.log('📍 4. Testing cart button click...');
    try {
      await cartButton.click();
      console.log('✅ Cart button clicked successfully');

      // Wait a moment for any animations
      await page.waitForTimeout(1000);

      // Check if cart panel is visible
      const cartPanel = await page.$('.cart-panel.show');
      if (cartPanel) {
        console.log('✅ Cart panel opened successfully');
      } else {
        console.log('❌ Cart panel did not open');

        // Check if cart panel exists at all
        const cartPanelExists = await page.$('.cart-panel');
        console.log(`Cart panel exists in DOM: ${cartPanelExists ? 'yes' : 'no'}`);
      }
    } catch (error) {
      console.error('❌ Error clicking cart button:', error.message);
    }

    console.log('📍 5. Going to media section...');
    await page.click('button[data-view="media"]');
    await page.waitForTimeout(2000);

    console.log('📍 6. Looking for selection checkboxes...');
    const selectCheckboxes = await page.$$('.media-card-select');
    console.log(`Found ${selectCheckboxes.length} selection checkboxes`);

    if (selectCheckboxes.length > 0) {
      console.log('📍 7. Testing checkbox selection...');
      await selectCheckboxes[0].click();
      await page.waitForTimeout(1000);

      // Check cart count
      const cartCount = await page.$eval('#cart-count', (el) => el.textContent);
      console.log(`Cart count after selection: ${cartCount}`);

      // Check if card has selected class
      const firstCard = await page.$('.media-card');
      const hasSelectedClass = await page.evaluate(
        (card) => card.classList.contains('selected'),
        firstCard
      );
      console.log(`First card has selected class: ${hasSelectedClass}`);
    }

    console.log('📍 8. Testing navigation persistence...');
    await page.click('button[data-view="critics"]');
    await page.waitForTimeout(1000);
    await page.click('button[data-view="media"]');
    await page.waitForTimeout(2000);

    // Check if selections are still visible
    const selectedCards = await page.$$('.media-card.selected');
    console.log(`Selected cards after navigation: ${selectedCards.length}`);

    console.log('🎉 Debugging completed');
  } catch (error) {
    console.error('❌ Debugging failed:', error);
  } finally {
    await browser.close();
  }
}

debugCart();
