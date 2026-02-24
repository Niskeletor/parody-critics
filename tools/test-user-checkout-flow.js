/**
 * 🎭 User Checkout Flow Test - SAL-9000 Analysis
 * Simulates the exact user flow: click letter → add to cart → checkout
 */

const puppeteer = require('playwright');

async function testUserCheckoutFlow() {
    console.log('🎭 Starting user checkout flow simulation...');

    try {
        const { chromium } = puppeteer;
        const browser = await chromium.launch({
            headless: false,
            slowMo: 1000,
            devtools: true
        });
        const page = await browser.newPage();

        // Console logging
        page.on('console', msg => {
            const type = msg.type();
            const text = msg.text();
            console.log(`📄 ${type.toUpperCase()}: ${text}`);
        });

        page.on('pageerror', error => {
            console.error('❌ Page Error:', error.message);
        });

        // Load app
        console.log('🌐 Loading app...');
        await page.goto('http://localhost:8877', { waitUntil: 'domcontentloaded' });
        await page.waitForSelector('.header', { timeout: 10000 });
        await page.waitForTimeout(3000);

        // Navigate to media
        console.log('🎬 Going to media view...');
        await page.click('.nav-btn[data-view="media"]');
        await page.waitForTimeout(3000);

        // Click on a letter to load movies (simulating user navigation)
        console.log('🔤 Clicking on letter M to find Matrix movies...');
        const letterM = await page.waitForSelector('[data-letter="M"]', { timeout: 10000 });
        await letterM.click();
        await page.waitForTimeout(3000);

        // Look for any available "Add to Cart" button
        const addButtons = await page.$$('.btn-add-to-cart');
        console.log(`🛒 Found ${addButtons.length} "Add to Cart" buttons`);

        if (addButtons.length > 0) {
            // Get movie title before adding
            const movieTitle = await page.evaluate(() => {
                const firstCard = document.querySelector('.media-card');
                return firstCard ? firstCard.querySelector('.media-title')?.textContent?.trim() : 'Unknown Movie';
            });

            console.log(`🎬 Adding "${movieTitle}" to cart...`);
            await addButtons[0].click();
            await page.waitForTimeout(1000);

            // Check cart count
            const cartCount = await page.textContent('#cart-count');
            console.log(`🛒 Cart count: ${cartCount}`);

            if (cartCount && parseInt(cartCount) > 0) {
                console.log('🛒 Opening cart...');
                await page.click('#cart-btn');
                await page.waitForTimeout(2000);

                // Check if cart is open
                const cartOpen = await page.isVisible('#cart-panel');
                console.log(`🛒 Cart panel open: ${cartOpen}`);

                if (cartOpen) {
                    console.log('✅ CRITICAL STEP: Clicking "Proceder al Checkout"...');

                    // Log state before checkout
                    const beforeState = await page.evaluate(() => ({
                        currentView: window.app?.currentView,
                        cartSize: window.app?.cart.size,
                        activeViews: Array.from(document.querySelectorAll('.view.active')).map(v => v.id)
                    }));
                    console.log('🔍 Before checkout:', beforeState);

                    // Click checkout button
                    await page.click('#proceed-checkout-btn');
                    await page.waitForTimeout(3000);

                    // Log state after checkout
                    const afterState = await page.evaluate(() => ({
                        currentView: window.app?.currentView,
                        cartSize: window.app?.cart.size,
                        activeViews: Array.from(document.querySelectorAll('.view.active')).map(v => v.id),
                        checkoutViewActive: document.getElementById('checkout-view')?.classList.contains('active'),
                        cartPanelVisible: window.getComputedStyle(document.getElementById('cart-panel')).display !== 'none'
                    }));
                    console.log('🔍 After checkout:', afterState);

                    // Final visibility check
                    const checkoutVisible = await page.isVisible('#checkout-view');
                    console.log(`👁️ Checkout view visible to user: ${checkoutVisible}`);

                    if (checkoutVisible) {
                        console.log('✅ SUCCESS: Checkout flow worked perfectly!');

                        // Check checkout content
                        const hasContent = await page.evaluate(() => {
                            const mediaList = document.getElementById('checkout-media-list');
                            const criticsSection = document.getElementById('critics-selection');
                            return {
                                mediaListExists: !!mediaList,
                                mediaListHasContent: mediaList?.children.length > 0,
                                criticsExists: !!criticsSection,
                                criticsHasContent: criticsSection?.children.length > 0
                            };
                        });
                        console.log('📋 Checkout content:', hasContent);

                    } else {
                        console.error('❌ PROBLEM CONFIRMED: Checkout view disappeared!');
                        console.log('🔬 This matches the user\'s reported issue');

                        // Detailed diagnosis
                        const diagnosis = await page.evaluate(() => {
                            const checkout = document.getElementById('checkout-view');
                            const cart = document.getElementById('cart-panel');

                            return {
                                checkout: {
                                    exists: !!checkout,
                                    classes: checkout?.className,
                                    style: checkout?.style.cssText,
                                    computedDisplay: checkout ? window.getComputedStyle(checkout).display : 'N/A',
                                    computedVisibility: checkout ? window.getComputedStyle(checkout).visibility : 'N/A'
                                },
                                cart: {
                                    exists: !!cart,
                                    classes: cart?.className,
                                    style: cart?.style.cssText
                                },
                                allViews: Array.from(document.querySelectorAll('.view')).map(v => ({
                                    id: v.id,
                                    hasActiveClass: v.classList.contains('active'),
                                    computedDisplay: window.getComputedStyle(v).display
                                }))
                            };
                        });

                        console.log('🔬 Detailed diagnosis:', JSON.stringify(diagnosis, null, 2));
                    }

                    // Test manual fix - try to show checkout again
                    console.log('🔧 Testing manual fix...');
                    await page.evaluate(() => {
                        if (window.app) {
                            window.app.showView('checkout');
                        }
                    });
                    await page.waitForTimeout(1000);

                    const fixedVisible = await page.isVisible('#checkout-view');
                    console.log(`🔧 After manual fix, checkout visible: ${fixedVisible}`);
                }
            }
        }

        console.log('⏸️ Keeping browser open for manual inspection (60s)...');
        await page.waitForTimeout(60000);
        await browser.close();

    } catch (error) {
        console.error('❌ User flow test failed:', error);
    }
}

testUserCheckoutFlow().catch(console.error);