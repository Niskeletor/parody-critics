/**
 * 🔍 Visual Checkout Debug - SAL-9000 Analysis
 * Tests exactly what the user sees visually
 */

const puppeteer = require('playwright');

async function debugVisualCheckout() {
    console.log('🔍 Testing VISUAL checkout experience (what user actually sees)...');

    try {
        const { chromium } = puppeteer;
        const browser = await chromium.launch({
            headless: false,
            slowMo: 2000 // Very slow to see exactly what happens
        });
        const page = await browser.newPage();

        // Minimal logging to focus on visual
        page.on('console', msg => {
            if (msg.text().includes('✨') || msg.text().includes('❌') || msg.text().includes('🛒')) {
                console.log(`📄 ${msg.text()}`);
            }
        });

        await page.goto('http://localhost:8877', { waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(3000);

        console.log('👤 SIMULATING USER ACTIONS:');

        // Step 1: Add item to cart (simulating user action)
        console.log('1️⃣ User adds item to cart...');
        await page.evaluate(() => {
            const testItem = {
                tmdb_id: 'visual-test',
                title: 'Visual Test Movie',
                year: 2024,
                type: 'movie'
            };
            window.app.addToCart(testItem);
        });

        // Step 2: User opens cart
        console.log('2️⃣ User clicks cart button...');
        await page.click('#cart-btn');
        await page.waitForTimeout(2000);

        // Visual check 1
        const cartVisible = await page.isVisible('#cart-panel');
        console.log(`👁️ Cart panel visible: ${cartVisible}`);

        // Step 3: USER CLICKS CHECKOUT (the problematic step)
        console.log('3️⃣ 🔥 USER CLICKS "Procesar Críticas" BUTTON...');
        await page.click('#cart-checkout-btn');

        // Wait and check what user sees immediately
        await page.waitForTimeout(1000);

        console.log('👁️ VISUAL CHECK - What user sees 1 second after click:');

        const visualState1s = await page.evaluate(() => {
            const cart = document.getElementById('cart-panel');
            const checkout = document.getElementById('checkout-view');

            return {
                cartPanel: {
                    exists: !!cart,
                    visible: cart ? window.getComputedStyle(cart).display !== 'none' : false,
                    hasOpenClass: cart ? cart.classList.contains('open') : false,
                    zIndex: cart ? window.getComputedStyle(cart).zIndex : 'N/A'
                },
                checkoutView: {
                    exists: !!checkout,
                    visible: checkout ? window.getComputedStyle(checkout).display !== 'none' : false,
                    hasActiveClass: checkout ? checkout.classList.contains('active') : false,
                    zIndex: checkout ? window.getComputedStyle(checkout).zIndex : 'N/A'
                }
            };
        });

        console.log('📊 Visual state after 1 second:', JSON.stringify(visualState1s, null, 2));

        // Wait longer and check again
        await page.waitForTimeout(3000);

        console.log('👁️ VISUAL CHECK - What user sees 4 seconds after click:');

        const visualState4s = await page.evaluate(() => {
            const cart = document.getElementById('cart-panel');
            const checkout = document.getElementById('checkout-view');

            return {
                cartPanel: {
                    visible: cart ? window.getComputedStyle(cart).display !== 'none' : false,
                    hasOpenClass: cart ? cart.classList.contains('open') : false
                },
                checkoutView: {
                    visible: checkout ? window.getComputedStyle(checkout).display !== 'none' : false,
                    hasActiveClass: checkout ? checkout.classList.contains('active') : false
                },
                whatUserSees: {
                    anyViewActive: Array.from(document.querySelectorAll('.view.active')).map(v => v.id),
                    currentAppView: window.app?.currentView
                }
            };
        });

        console.log('📊 Final visual state:', JSON.stringify(visualState4s, null, 2));

        // Test if checkout is actually visible to user
        const userCanSeeCheckout = await page.isVisible('#checkout-view');
        console.log(`🔍 Can user actually SEE checkout view? ${userCanSeeCheckout}`);

        if (!userCanSeeCheckout) {
            console.log('❌ CONFIRMED: User cannot see checkout view!');

            // Investigate CSS issues
            const cssDebug = await page.evaluate(() => {
                const checkout = document.getElementById('checkout-view');
                if (!checkout) return 'Checkout element not found';

                const computed = window.getComputedStyle(checkout);
                return {
                    display: computed.display,
                    visibility: computed.visibility,
                    opacity: computed.opacity,
                    zIndex: computed.zIndex,
                    position: computed.position,
                    top: computed.top,
                    left: computed.left,
                    width: computed.width,
                    height: computed.height,
                    classes: Array.from(checkout.classList)
                };
            });

            console.log('🔬 CSS DEBUG - Checkout view styles:', JSON.stringify(cssDebug, null, 2));

            // Check if there's an overlay or other element blocking it
            const elementAt = await page.evaluate(() => {
                const centerX = window.innerWidth / 2;
                const centerY = window.innerHeight / 2;
                const element = document.elementFromPoint(centerX, centerY);
                return {
                    tagName: element?.tagName,
                    id: element?.id,
                    className: element?.className,
                    position: { centerX, centerY }
                };
            });

            console.log('🔍 Element at center of screen:', elementAt);

        } else {
            console.log('✅ User CAN see checkout view - issue might be elsewhere');
        }

        console.log('⏸️ Browser staying open for manual inspection (60s)...');
        console.log('💡 Try the same steps manually to compare!');
        await page.waitForTimeout(60000);
        await browser.close();

    } catch (error) {
        console.error('❌ Visual debug failed:', error);
    }
}

debugVisualCheckout().catch(console.error);