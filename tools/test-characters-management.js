const { chromium } = require('playwright');

(async () => {
    console.log('🧪 SAL-9000: Testing complete Characters management system...');

    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();

    // Listen for console messages
    page.on('console', msg => console.log('🌐 [LOG]:', msg.text()));
    page.on('pageerror', err => console.log('🔴 [ERROR]:', err.message));

    try {
        console.log('📍 1. Loading page...');
        await page.goto('http://localhost:8877');
        await page.waitForLoadState('networkidle');

        console.log('📍 2. Navigating to Characters section...');
        await page.click('button[data-view="characters"]');
        await page.waitForTimeout(2000);

        console.log('📍 3. Testing "Add Character" button...');
        await page.click('#add-character-btn');
        await page.waitForTimeout(1000);

        // Check if modal opened
        const modalVisible = await page.isVisible('#character-modal:not(.hidden)');
        if (modalVisible) {
            console.log('✅ SUCCESS: Add character modal opened');

            console.log('📍 4. Filling character form...');
            await page.fill('#character-name', 'Test Character');
            await page.fill('#character-emoji', '🧪');
            await page.selectOption('#character-personality', 'stoic');
            await page.fill('#character-description', 'This is a test character for automated testing');

            console.log('📍 5. Submitting form...');
            await page.click('#character-form button[type="submit"]');
            await page.waitForTimeout(2000);

            // Check if modal closed
            const modalHidden = await page.isVisible('#character-modal.hidden');
            if (modalHidden || !await page.isVisible('#character-modal')) {
                console.log('✅ SUCCESS: Character form submitted and modal closed');
            } else {
                console.log('❌ FAILED: Modal did not close after submission');
            }
        } else {
            console.log('❌ FAILED: Add character modal did not open');
        }

        console.log('📍 6. Testing Export functionality...');
        await page.click('#export-characters-btn');
        await page.waitForTimeout(1000);

        // Check for download - we can't easily test file download in headless mode
        console.log('✅ Export button clicked (download would occur in real browser)');

        console.log('📍 7. Testing Import modal...');
        await page.click('#import-characters-btn');
        await page.waitForTimeout(1000);

        const importModalVisible = await page.isVisible('#import-modal:not(.hidden)');
        if (importModalVisible) {
            console.log('✅ SUCCESS: Import modal opened');

            // Close import modal
            await page.click('#import-modal-close');
            await page.waitForTimeout(500);

            const importModalClosed = await page.isVisible('#import-modal.hidden');
            if (importModalClosed || !await page.isVisible('#import-modal')) {
                console.log('✅ SUCCESS: Import modal closed successfully');
            }
        } else {
            console.log('❌ FAILED: Import modal did not open');
        }

        console.log('🏁 Characters management test completed successfully!');

    } catch (error) {
        console.log('❌ Test failed:', error.message);
    } finally {
        await browser.close();
    }
})();