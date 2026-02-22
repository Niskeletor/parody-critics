const puppeteer = require('puppeteer');

async function testCompleteGeneration() {
    console.log('🤖 SAL-9000: Testing complete generation flow...');

    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    try {
        const page = await browser.newPage();

        // Enable console logging from the page
        page.on('console', msg => {
            const type = msg.type();
            const text = msg.text();
            if (!text.includes('🔧') && !text.includes('📜 Scroll detected')) {
                console.log(`🌐 [${type.toUpperCase()}]: ${text}`);
            }
        });

        // Enable error logging
        page.on('pageerror', error => {
            console.error('❌ Page Error:', error.message);
        });

        console.log('📍 1. Navigating to http://localhost:8877...');
        await page.goto('http://localhost:8877', { waitUntil: 'networkidle0' });

        console.log('🎬 2. Clicking on "Películas & Series" tab...');
        await page.click('button[data-view="media"]');
        await new Promise(resolve => setTimeout(resolve, 2000));

        console.log('🎯 3. Finding and clicking a generate critic button...');
        const generateButtons = await page.$$('.generate-critic-btn');
        if (generateButtons.length === 0) {
            throw new Error('No generate critic buttons found!');
        }

        // Click first button
        await generateButtons[0].click();
        await new Promise(resolve => setTimeout(resolve, 1000));

        console.log('📍 4. Verifying we are in the generate tab...');
        const activeTab = await page.$eval('.nav-btn.active', btn => btn.dataset.view);
        if (activeTab !== 'generate') {
            throw new Error(`Expected generate tab, but got: ${activeTab}`);
        }

        console.log('✅ Generate tab is active!');

        console.log('👤 5. Selecting a character...');
        const characterCards = await page.$$('.character-card');
        if (characterCards.length === 0) {
            throw new Error('No character cards found!');
        }

        // Click first character
        await characterCards[0].click();
        await new Promise(resolve => setTimeout(resolve, 500));

        console.log('🎭 6. Clicking Generate button...');
        const generateBtn = await page.$('#generate-btn');
        if (!generateBtn) {
            throw new Error('Generate button not found!');
        }

        // Check if button is enabled
        const isDisabled = await page.evaluate(btn => btn.disabled, generateBtn);
        if (isDisabled) {
            throw new Error('Generate button is disabled!');
        }

        await generateBtn.click();
        console.log('⏱️ 7. Waiting for generation to complete...');

        // Wait for either success or error message
        const result = await Promise.race([
            page.waitForSelector('.generation-result:not(.hidden)', { timeout: 30000 }),
            page.waitForSelector('.message', { timeout: 30000 })
        ]);

        if (result) {
            const messageText = await page.evaluate(() => {
                const genResult = document.querySelector('.generation-result:not(.hidden)');
                const message = document.querySelector('.message');

                if (genResult) {
                    return '✅ Generation result appeared!';
                } else if (message) {
                    return `Message: ${message.textContent.trim()}`;
                }
                return 'Unknown result';
            });

            console.log('🎉 Generation Result:', messageText);
        }

    } catch (error) {
        console.error('❌ Test failed:', error.message);

        // Get current page state for debugging
        try {
            const currentUrl = page.url();
            const title = await page.title();
            console.log('🔍 Debug info - URL:', currentUrl, 'Title:', title);
        } catch (debugError) {
            console.log('Could not get debug info');
        }
    } finally {
        await browser.close();
        console.log('🏁 Test completed');
    }
}

testCompleteGeneration();