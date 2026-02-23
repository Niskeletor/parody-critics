const { chromium } = require('playwright');

/**
 * 🛒 SAL-9000 Checkout Test
 * Test complete checkout flow
 */
async function testCheckout() {
    console.log('🛒 SAL-9000: Testing complete checkout flow...');

    const browser = await chromium.launch({
        headless: false, // Visible for debugging
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    try {
        const page = await browser.newPage();

        // Enable console logging
        page.on('console', msg => {
            console.log(`🌐 [${msg.type().toUpperCase()}]: ${msg.text()}`);
        });

        page.on('pageerror', error => {
            console.error('❌ Page Error:', error.message);
        });

        console.log('📍 1. Loading page...');
        await page.goto('http://localhost:8877', { waitUntil: 'networkidle' });

        console.log('📍 2. Going to media section...');
        await page.click('button[data-view="media"]');
        await page.waitForTimeout(3000); // Wait for media to load

        console.log('📍 3. Adding items to cart...');
        const selectCheckboxes = await page.$$('.media-card-select');
        console.log(`Found ${selectCheckboxes.length} selection checkboxes`);

        // Add first two items
        if (selectCheckboxes.length >= 2) {
            await selectCheckboxes[0].click();
            await page.waitForTimeout(500);
            await selectCheckboxes[1].click();
            await page.waitForTimeout(500);
        } else {
            throw new Error('Need at least 2 media items for checkout test');
        }

        console.log('📍 4. Opening cart...');
        await page.click('#cart-btn');
        await page.waitForTimeout(1000);

        console.log('📍 5. Checking cart contents...');
        const cartItems = await page.$$('.cart-item');
        console.log(`Cart has ${cartItems.length} items`);

        console.log('📍 6. Proceeding to checkout...');
        await page.click('#cart-checkout-btn');
        await page.waitForTimeout(3000);

        console.log('📍 7. Checking if checkout view is visible...');
        const checkoutView = await page.$('#checkout-view.active');
        if (checkoutView) {
            console.log('✅ SUCCESS: Checkout view is visible!');

            // Check if media items are displayed
            const checkoutMediaItems = await page.$$('.checkout-media-item');
            console.log(`Checkout shows ${checkoutMediaItems.length} media items`);

            // Check if critics are loaded
            const criticItems = await page.$$('.critic-checkbox-item');
            console.log(`Found ${criticItems.length} critic options`);

        } else {
            console.log('❌ FAILURE: Checkout view is not visible');

            // Check what view is currently active
            const activeView = await page.evaluate(() => {
                const active = document.querySelector('.view.active');
                return active ? active.id : 'no active view';
            });
            console.log(`Current active view: ${activeView}`);
        }

    } catch (error) {
        console.error('❌ Test failed:', error.message);
    } finally {
        await browser.close();
        console.log('🏁 Test completed');
    }
}

testCheckout();