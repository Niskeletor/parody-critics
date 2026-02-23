const { chromium } = require('playwright');

/**
 * 🛒 SAL-9000 Cart Button Test
 * Specific test for cart button functionality
 */
async function testCartButton() {
    console.log('🔍 SAL-9000: Testing cart button specifically...');

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

        console.log('📍 2. Waiting for app to initialize...');
        await page.waitForTimeout(2000);

        console.log('📍 3. Checking cart button exists...');
        const cartButton = await page.$('#cart-btn');
        if (!cartButton) {
            throw new Error('Cart button not found');
        }

        console.log('📍 4. Checking if cart panel exists...');
        const cartPanel = await page.$('#cart-panel');
        if (!cartPanel) {
            throw new Error('Cart panel not found');
        }

        console.log('📍 5. Checking initial state...');
        const isInitiallyVisible = await page.evaluate(() => {
            const panel = document.getElementById('cart-panel');
            return panel && panel.classList.contains('show');
        });
        console.log(`Initial cart panel visibility: ${isInitiallyVisible}`);

        console.log('📍 6. Clicking cart button...');
        await cartButton.click();

        console.log('📍 7. Waiting for animation...');
        await page.waitForTimeout(1000);

        console.log('📍 8. Checking if panel opened...');
        const isVisible = await page.evaluate(() => {
            const panel = document.getElementById('cart-panel');
            return panel && panel.classList.contains('show');
        });

        console.log(`Cart panel visibility after click: ${isVisible}`);

        if (isVisible) {
            console.log('✅ SUCCESS: Cart button is working!');
        } else {
            console.log('❌ FAILURE: Cart button is not working');

            // Additional debugging
            const panelClasses = await page.evaluate(() => {
                const panel = document.getElementById('cart-panel');
                return panel ? Array.from(panel.classList) : 'Panel not found';
            });
            console.log(`Panel classes: ${JSON.stringify(panelClasses)}`);
        }

        console.log('📍 9. Testing second click (should close)...');
        await cartButton.click();
        await page.waitForTimeout(1000);

        const isClosedAfterSecondClick = await page.evaluate(() => {
            const panel = document.getElementById('cart-panel');
            return panel && !panel.classList.contains('show');
        });

        console.log(`Panel closed after second click: ${isClosedAfterSecondClick}`);

    } catch (error) {
        console.error('❌ Test failed:', error.message);
    } finally {
        await browser.close();
        console.log('🏁 Test completed');
    }
}

testCartButton();