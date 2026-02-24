/**
 * 🛒 Cart Button Real Test - SAL-9000 Analysis
 * Tests the actual cart checkout button click workflow
 */

const puppeteer = require('playwright');

async function testCartCheckoutButton() {
    console.log('🛒 Testing real cart checkout button workflow...');

    try {
        const { chromium } = puppeteer;
        const browser = await chromium.launch({
            headless: false,
            slowMo: 1200
        });
        const page = await browser.newPage();

        // Full console logging
        page.on('console', msg => {
            const text = msg.text();
            const type = msg.type();

            if (text.includes('✨ Checkout button clicked') ||
                text.includes('✨ Checkout button event listener added') ||
                text.includes('🛒 Cart button clicked') ||
                text.includes('❌') || text.includes('✅')) {
                console.log(`🔥 IMPORTANT ${type.toUpperCase()}: ${text}`);
            } else {
                console.log(`📄 ${type}: ${text}`);
            }
        });

        page.on('pageerror', error => {
            console.error('💥 PAGE ERROR:', error.message);
        });

        // Load app
        console.log('🌐 Loading app...');
        await page.goto('http://localhost:8877', { waitUntil: 'domcontentloaded' });
        await page.waitForSelector('.header', { timeout: 10000 });
        await page.waitForTimeout(3000);

        // Add item to cart directly to enable checkout button
        console.log('🧪 Adding test item to cart...');
        const addResult = await page.evaluate(() => {
            if (window.app) {
                const testItem = {
                    tmdb_id: 'cart-checkout-test',
                    title: 'Cart Checkout Test Movie',
                    year: 2024,
                    type: 'movie',
                    poster_url: null,
                    has_critics: false
                };
                window.app.addToCart(testItem);
                return { success: true, cartSize: window.app.cart.size };
            }
            return { success: false, error: 'App not found' };
        });

        console.log('🛒 Add result:', addResult);

        if (addResult.success && addResult.cartSize > 0) {
            console.log('🛒 Opening cart...');
            await page.click('#cart-btn');
            await page.waitForTimeout(2000);

            // Check if cart is open
            const cartVisible = await page.isVisible('#cart-panel');
            console.log(`🛒 Cart panel visible: ${cartVisible}`);

            if (cartVisible) {
                // Check if checkout button is enabled
                const checkoutEnabled = await page.evaluate(() => {
                    const btn = document.getElementById('cart-checkout-btn');
                    return {
                        exists: !!btn,
                        disabled: btn?.disabled,
                        visible: btn ? window.getComputedStyle(btn).display !== 'none' : false,
                        text: btn?.textContent?.trim()
                    };
                });

                console.log('🔍 Checkout button state:', checkoutEnabled);

                if (checkoutEnabled.exists && !checkoutEnabled.disabled) {
                    console.log('🔥 CLICKING CHECKOUT BUTTON - THE REAL USER TEST...');

                    // This is the real test - clicking the actual button the user clicks
                    await page.click('#cart-checkout-btn');

                    console.log('⏳ Waiting for checkout response...');
                    await page.waitForTimeout(5000);

                    // Check results
                    const finalState = await page.evaluate(() => ({
                        currentView: window.app?.currentView,
                        checkoutActive: document.getElementById('checkout-view')?.classList.contains('active'),
                        cartClosed: !document.getElementById('cart-panel')?.classList.contains('open')
                    }));

                    console.log('📊 Final state after button click:', finalState);

                    const checkoutVisible = await page.isVisible('#checkout-view');
                    console.log(`👁️ Checkout view visible to user: ${checkoutVisible}`);

                    if (checkoutVisible && finalState.checkoutActive) {
                        console.log('🎉 SUCCESS: Cart checkout button workflow working!');

                        // Check content loaded
                        const hasContent = await page.evaluate(() => ({
                            mediaList: document.getElementById('checkout-media-list')?.children.length > 0,
                            criticsSection: document.getElementById('critics-selection')?.children.length > 0
                        }));
                        console.log('📋 Checkout content loaded:', hasContent);

                        if (hasContent.mediaList && hasContent.criticsSection) {
                            console.log('🎉 PERFECT: Everything working as expected!');
                        } else {
                            console.log('⚠️ Content loading issue detected');
                        }

                    } else {
                        console.log('❌ CONFIRMED BUG: Button click did not open checkout properly');
                        console.log('🔍 This confirms the user\'s reported issue');

                        // Detailed diagnosis
                        const diagnosis = await page.evaluate(() => {
                            const checkout = document.getElementById('checkout-view');
                            return {
                                checkoutExists: !!checkout,
                                checkoutClasses: checkout?.className,
                                activeViews: Array.from(document.querySelectorAll('.view.active')).map(v => v.id)
                            };
                        });
                        console.log('🔬 Diagnosis:', diagnosis);
                    }
                } else {
                    console.log(`❌ Checkout button not ready: disabled=${checkoutEnabled.disabled}, exists=${checkoutEnabled.exists}`);
                }
            } else {
                console.log('❌ Cart panel not visible');
            }
        } else {
            console.log('❌ Failed to add item to cart');
        }

        // Keep browser open for manual inspection
        console.log('⏸️ Browser staying open for manual testing (60s)...');
        console.log('💡 Try clicking the checkout button manually to compare!');
        await page.waitForTimeout(60000);
        await browser.close();

    } catch (error) {
        console.error('❌ Cart checkout button test failed:', error);
    }
}

testCartCheckoutButton().catch(console.error);