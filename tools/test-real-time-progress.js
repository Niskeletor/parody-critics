const { chromium } = require('playwright');

(async () => {
    console.log('🔄 SAL-9000: Testing real-time progress tracking system...');

    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();

    // Listen for console messages
    page.on('console', msg => console.log('🌐 [LOG]:', msg.text()));
    page.on('pageerror', err => console.log('🔴 [ERROR]:', err.message));

    try {
        console.log('📍 1. Loading page...');
        await page.goto('http://localhost:8877');
        await page.waitForLoadState('networkidle');

        console.log('📍 2. Waiting for app to initialize...');
        await page.waitForTimeout(2000);

        console.log('📍 3. Going to media tab and adding items...');
        await page.click('button[data-view="media"]');
        await page.waitForTimeout(1500);

        // Add 2 media items to cart using the selection boxes
        const selectionBoxes = await page.$$('.media-card-select');
        console.log(`📍 Found ${selectionBoxes.length} selection boxes`);

        if (selectionBoxes.length >= 2) {
            await selectionBoxes[0].click();
            await selectionBoxes[1].click();
            await page.waitForTimeout(500);
            console.log('✅ Added 2 items to cart');
        } else {
            console.log('❌ Not enough selection boxes found, trying alternative method...');

            // Fallback: try to click media cards directly
            const mediaCards = await page.$$('.media-card');
            if (mediaCards.length >= 2) {
                await mediaCards[0].click();
                await page.waitForTimeout(200);
                await mediaCards[1].click();
                await page.waitForTimeout(500);
                console.log('✅ Added items using fallback method');
            } else {
                console.log('❌ No media cards found');
                return;
            }
        }

        console.log('📍 4. Opening cart and proceeding to checkout...');
        await page.click('#cart-btn');
        await page.waitForTimeout(1000);
        await page.click('#cart-checkout-btn');
        await page.waitForTimeout(2000);

        console.log('📍 5. Selecting 2 critics for variety...');
        const criticCheckboxes = await page.$$('.critic-checkbox');
        if (criticCheckboxes.length >= 2) {
            await criticCheckboxes[0].click();
            await criticCheckboxes[1].click();
            await page.waitForTimeout(500);
            console.log('✅ Selected 2 critics');
        } else {
            console.log('❌ Not enough critic options found');
        }

        console.log('📍 6. Starting batch processing...');
        await page.click('#start-processing-btn');
        await page.waitForTimeout(1000);

        console.log('📍 7. Monitoring progress updates...');
        const progressUpdates = [];
        let lastProgress = -1;

        // Monitor progress for up to 60 seconds
        const monitoringStart = Date.now();
        const maxMonitoringTime = 60000; // 60 seconds

        while (Date.now() - monitoringStart < maxMonitoringTime) {
            try {
                const progressText = await page.$eval('#progress-text', el => el.textContent);
                const currentProgress = parseInt(progressText);

                if (currentProgress !== lastProgress) {
                    const statusText = await page.$eval('#processing-status', el => el.textContent);
                    const currentItem = await page.$eval('#processing-current', el => el.textContent);

                    progressUpdates.push({
                        time: Date.now() - monitoringStart,
                        progress: currentProgress,
                        status: statusText,
                        currentItem: currentItem
                    });

                    console.log(`📊 Progress Update: ${currentProgress}% - ${statusText} - ${currentItem}`);
                    lastProgress = currentProgress;

                    // If we reached 100%, break
                    if (currentProgress >= 100) {
                        console.log('✅ Progress reached 100%');
                        break;
                    }
                }

                await page.waitForTimeout(500); // Check every 500ms
            } catch (error) {
                // Elements might not be visible yet
                await page.waitForTimeout(500);
            }
        }

        console.log('📍 8. Analyzing progress updates...');

        if (progressUpdates.length >= 2) {
            console.log(`✅ SUCCESS: Real-time progress tracking working! Captured ${progressUpdates.length} updates`);

            // Check if progress increased incrementally
            let progressIncreased = true;
            for (let i = 1; i < progressUpdates.length; i++) {
                if (progressUpdates[i].progress < progressUpdates[i-1].progress) {
                    progressIncreased = false;
                    break;
                }
            }

            if (progressIncreased) {
                console.log('✅ SUCCESS: Progress increased incrementally');
            } else {
                console.log('⚠️  WARNING: Progress did not increase incrementally');
            }

            // Show first and last updates
            console.log('📈 Progress Timeline:');
            console.log(`   Start: ${progressUpdates[0].progress}% at ${progressUpdates[0].time}ms`);
            console.log(`   End:   ${progressUpdates[progressUpdates.length-1].progress}% at ${progressUpdates[progressUpdates.length-1].time}ms`);

            // Check if we had intermediate progress (not just 0% -> 100%)
            const intermediateUpdates = progressUpdates.filter(u => u.progress > 0 && u.progress < 100);
            if (intermediateUpdates.length > 0) {
                console.log('✅ SUCCESS: Intermediate progress updates detected');
            } else {
                console.log('⚠️  WARNING: No intermediate progress detected (might still be 0% -> 100% jump)');
            }

        } else {
            console.log('❌ FAILED: Not enough progress updates captured');
        }

        // Wait for completion
        console.log('📍 9. Waiting for completion...');
        await page.waitForTimeout(3000);

        // Check if results are shown
        const resultsVisible = await page.isVisible('#results-section:not(.hidden)');
        if (resultsVisible) {
            console.log('✅ SUCCESS: Results section is visible after completion');
        } else {
            console.log('❌ FAILED: Results section not visible');
        }

        console.log('🏁 Real-time progress test completed');

    } catch (error) {
        console.log('❌ Test failed:', error.message);
    } finally {
        await browser.close();
    }
})();