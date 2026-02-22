const puppeteer = require('puppeteer');

async function testGenerateCriticButton() {
    console.log('🤖 SAL-9000: Starting automated testing...');

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
            console.log(`🌐 [${type.toUpperCase()}]: ${text}`);
        });

        // Enable error logging
        page.on('pageerror', error => {
            console.error('❌ Page Error:', error.message);
        });

        console.log('📍 Navigating to http://localhost:8877...');
        await page.goto('http://localhost:8877', { waitUntil: 'networkidle0' });

        console.log('🎬 Clicking on "Películas & Series" tab...');
        await page.click('button[data-view="media"]');

        console.log('⏱️ Waiting for media to load...');
        await new Promise(resolve => setTimeout(resolve, 2000));

        console.log('🔍 Looking for generate critic buttons...');
        const buttons = await page.$$('.generate-critic-btn, .compact-generate-btn');
        console.log(`📊 Found ${buttons.length} generate critic buttons`);

        if (buttons.length > 0) {
            console.log('🎯 Testing first button click...');
            const button = buttons[0];

            // Get button details
            const buttonInfo = await page.evaluate(btn => {
                return {
                    tmdbId: btn.dataset.tmdbId,
                    title: btn.dataset.title,
                    classes: Array.from(btn.classList),
                    text: btn.textContent.trim()
                };
            }, button);

            console.log('🔍 Button info:', buttonInfo);

            // Click the button
            await button.click();

            console.log('⏱️ Waiting for modal/navigation response...');
            await new Promise(resolve => setTimeout(resolve, 1000));

            // Check if we navigated to generate tab
            const activeTab = await page.$eval('.nav-btn.active', btn => btn.dataset.view);
            console.log('📍 Current active tab:', activeTab);

            // Check if we can see the generate view
            const generateView = await page.$('#generate-view');
            const hasActiveClass = await page.evaluate(view => view.classList.contains('active'), generateView);
            console.log('🔍 Generate view active:', hasActiveClass);

        } else {
            console.log('❌ No generate critic buttons found!');

            // Debug: Check what's actually in the media grid
            const mediaGridContent = await page.$eval('#media-grid', grid => grid.innerHTML);
            console.log('🔍 Media grid content preview:', mediaGridContent.substring(0, 500));
        }

    } catch (error) {
        console.error('❌ Test failed:', error);
    } finally {
        await browser.close();
        console.log('🏁 Test completed');
    }
}

testGenerateCriticButton();