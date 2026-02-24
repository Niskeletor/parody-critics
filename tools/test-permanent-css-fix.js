/**
 * 🔥 Test Permanent CSS Fix - SAL-9000 Analysis
 * Tests the integrated nuclear CSS solution for checkout visibility
 */

const puppeteer = require('playwright');

async function testPermanentCSSFix() {
    console.log('🔥 Testing PERMANENT CSS fix for checkout visibility...');

    try {
        const { chromium } = puppeteer;
        const browser = await chromium.launch({
            headless: false,
            slowMo: 1000
        });
        const page = await browser.newPage();

        // Monitor console for our nuclear fix messages
        page.on('console', msg => {
            const text = msg.text();
            if (text.includes('🔥') || text.includes('✅') || text.includes('NUCLEAR')) {
                console.log(`💥 ${text}`);
            }
        });

        await page.goto('http://localhost:8877', { waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(3000);

        // Add test item to cart
        console.log('🛒 Adding test item to cart...');
        await page.evaluate(() => {
            const testItem = {
                tmdb_id: 'nuclear-test',
                title: 'Nuclear Test Movie',
                year: 2024,
                type: 'movie'
            };
            window.app.addToCart(testItem);
        });

        // Open cart
        console.log('🛒 Opening cart...');
        await page.click('#cart-btn');
        await page.waitForTimeout(2000);

        // Click checkout button (the critical test)
        console.log('🔥 Clicking checkout button to trigger nuclear CSS fix...');
        await page.click('#cart-checkout-btn');
        await page.waitForTimeout(3000);

        // Check if checkout is visible
        const checkoutVisible = await page.isVisible('#checkout-view');
        console.log(`👁️ Checkout view visible after fix: ${checkoutVisible}`);

        if (checkoutVisible) {
            console.log('🎉 SUCCESS: Permanent nuclear CSS fix is working!');

            // Check the CSS styles were applied
            const appliedStyles = await page.evaluate(() => {
                const checkout = document.getElementById('checkout-view');
                const computed = window.getComputedStyle(checkout);
                return {
                    position: computed.position,
                    top: computed.top,
                    zIndex: computed.zIndex,
                    display: computed.display,
                    backgroundColor: computed.backgroundColor
                };
            });

            console.log('🎨 Applied CSS styles:', appliedStyles);

            // Check content loaded
            const contentLoaded = await page.evaluate(() => ({
                mediaList: document.getElementById('checkout-media-list')?.children.length > 0,
                criticsSection: !!document.getElementById('critics-selection')
            }));

            console.log('📋 Content loaded:', contentLoaded);

            if (contentLoaded.mediaList && contentLoaded.criticsSection) {
                console.log('🏆 PERFECT: Complete checkout workflow working with nuclear fix!');
            }

        } else {
            console.log('❌ FAILED: Nuclear CSS fix not working properly');
        }

        console.log('⏸️ Browser staying open for manual verification (30s)...');
        await page.waitForTimeout(30000);
        await browser.close();

    } catch (error) {
        console.error('❌ Test failed:', error);
    }
}

testPermanentCSSFix().catch(console.error);