/**
 * 🔙 Test Back Button - SAL-9000 Analysis
 * Tests the "Volver a Películas" button functionality
 */

const puppeteer = require('playwright');

async function testBackButton() {
    console.log('🔙 Testing "Volver a Películas" button...');

    try {
        const { chromium } = puppeteer;
        const browser = await chromium.launch({
            headless: false,
            slowMo: 1000
        });
        const page = await browser.newPage();

        // Monitor console for reset messages
        page.on('console', msg => {
            const text = msg.text();
            if (text.includes('🔄') || text.includes('✅') || text.includes('reset') ||
                text.includes('ULTRA-NUCLEAR') || text.includes('💥')) {
                console.log(`📄 ${text}`);
            }
        });

        await page.goto('http://localhost:8877', { waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(3000);

        // Add test item to cart
        console.log('🛒 Step 1: Adding item to cart...');
        await page.evaluate(() => {
            const testItem = {
                tmdb_id: 'back-button-test',
                title: 'Back Button Test Movie',
                year: 2024,
                type: 'movie'
            };
            window.app.addToCart(testItem);
        });

        // Open cart and go to checkout
        console.log('🛒 Step 2: Going to checkout...');
        await page.click('#cart-btn');
        await page.waitForTimeout(1000);
        await page.click('#cart-checkout-btn');
        await page.waitForTimeout(3000);

        // Verify checkout is visible
        const checkoutVisible = await page.isVisible('#checkout-view');
        console.log(`✅ Checkout visible: ${checkoutVisible}`);

        if (checkoutVisible) {
            // Look for the "Volver a películas" link and click it
            console.log('🔙 Step 3: Looking for "Volver a películas" button...');

            // Check if the back button exists (it's a <button>, not <a>)
            const backButtonExists = await page.evaluate(() => {
                // Look for the button with class btn-back
                const backButton = document.querySelector('.btn-back');
                const backLinks = Array.from(document.querySelectorAll('a')).filter(link =>
                    link.textContent.includes('Volver a películas') ||
                    link.textContent.includes('Volver a seleccionar') ||
                    (link.onclick && link.onclick.toString().includes('showView'))
                );

                return {
                    buttonExists: !!backButton,
                    buttonText: backButton?.textContent,
                    buttonOnclick: backButton?.onclick?.toString(),
                    linksFound: backLinks.length,
                    linksText: backLinks.map(l => l.textContent)
                };
            });

            console.log('🔍 Back button info:', backButtonExists);

            if (backButtonExists.buttonExists || backButtonExists.linksFound > 0) {
                console.log('🔙 Step 4: Clicking "Volver a películas" button...');

                // Try to click the back button first, then fallback to links
                const clickResult = await page.evaluate(() => {
                    // Try the button first
                    const backButton = document.querySelector('.btn-back');
                    if (backButton) {
                        backButton.click();
                        return 'button clicked';
                    }

                    // Fallback to links
                    const links = Array.from(document.querySelectorAll('a'));
                    const backLink = links.find(link =>
                        link.textContent.includes('Volver a películas') ||
                        link.textContent.includes('Volver a seleccionar') ||
                        (link.onclick && link.onclick.toString().includes('showView'))
                    );
                    if (backLink) {
                        backLink.click();
                        return 'link clicked';
                    }

                    return 'nothing found to click';
                });

                console.log('🔄 Click result:', clickResult);

                await page.waitForTimeout(2000);

                // Check if we're back to media view
                const finalState = await page.evaluate(() => ({
                    currentView: window.app?.currentView,
                    mediaViewActive: document.getElementById('media-view')?.classList.contains('active'),
                    checkoutViewActive: document.getElementById('checkout-view')?.classList.contains('active'),
                    checkoutVisible: document.getElementById('checkout-view') ?
                        window.getComputedStyle(document.getElementById('checkout-view')).position : 'not found'
                }));

                console.log('📊 Final state after clicking back button:', finalState);

                if (finalState.currentView === 'media' && finalState.mediaViewActive) {
                    console.log('🎉 SUCCESS: Back button working! Returned to media view.');
                    console.log(`✅ Checkout CSS reset to: ${finalState.checkoutVisible}`);
                } else {
                    console.log('❌ FAILED: Back button not working properly');
                }

            } else {
                console.log('❌ No back button or link found in checkout view');
                console.log('❓ Available buttons:', await page.evaluate(() =>
                    Array.from(document.querySelectorAll('button')).map(b => ({
                        class: b.className,
                        text: b.textContent,
                        onclick: b.onclick?.toString()
                    }))
                ));
            }

        } else {
            console.log('❌ Checkout not visible - cannot test back button');
        }

        console.log('⏸️ Browser staying open for verification (30s)...');
        await page.waitForTimeout(30000);
        await browser.close();

    } catch (error) {
        console.error('❌ Back button test failed:', error);
    }
}

testBackButton().catch(console.error);