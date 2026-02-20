/**
 * Parody Critics - API Client Version
 * Integrates with FastAPI backend for dynamic critic reviews
 */

(function() {
    'use strict';

    const logPrefix = '🎭 Parody Critics API:';

    // Configuration
    const CONFIG = {
        API_BASE_URL: 'http://localhost:8000/api',
        RETRY_ATTEMPTS: 3,
        RETRY_DELAY: 1000,
        CACHE_DURATION: 300000, // 5 minutes
        BUTTON_ID: 'parody-critics-api-btn',
        SECTION_CLASS: 'parody-critics-section'
    };

    // Simple in-memory cache
    const cache = new Map();

    // Fetch critics from API
    async function fetchCritics(tmdbId) {
        const cacheKey = `critics_${tmdbId}`;

        // Check cache first
        if (cache.has(cacheKey)) {
            const cached = cache.get(cacheKey);
            if (Date.now() - cached.timestamp < CONFIG.CACHE_DURATION) {
                console.log(`${logPrefix} Using cached data for ${tmdbId}`);
                return cached.data;
            }
        }

        console.log(`${logPrefix} Fetching critics for TMDB ID: ${tmdbId}`);

        for (let attempt = 1; attempt <= CONFIG.RETRY_ATTEMPTS; attempt++) {
            try {
                const response = await fetch(`${CONFIG.API_BASE_URL}/critics/${tmdbId}`, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });

                if (response.ok) {
                    const data = await response.json();

                    // Cache the result
                    cache.set(cacheKey, {
                        data: data,
                        timestamp: Date.now()
                    });

                    console.log(`${logPrefix} Successfully fetched ${data.total_critics} critics`);
                    return data;
                } else if (response.status === 404) {
                    console.log(`${logPrefix} No critics found for TMDB ID: ${tmdbId}`);
                    return null;
                } else {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

            } catch (error) {
                console.warn(`${logPrefix} Attempt ${attempt} failed:`, error);

                if (attempt === CONFIG.RETRY_ATTEMPTS) {
                    console.error(`${logPrefix} All retry attempts failed for ${tmdbId}`);
                    return null;
                }

                // Wait before retry
                await new Promise(resolve => setTimeout(resolve, CONFIG.RETRY_DELAY * attempt));
            }
        }

        return null;
    }

    // Get TMDB ID from current media
    function getCurrentTmdbId() {
        try {
            // Method 1: From URL (details page)
            const urlParams = new URLSearchParams(window.location.hash.split('?')[1]);
            const itemId = urlParams.get('id');

            if (itemId && window.ApiClient) {
                return window.ApiClient.getItem(window.ApiClient.getCurrentUserId(), itemId)
                    .then(item => item?.ProviderIds?.Tmdb)
                    .catch(() => null);
            }

            // Method 2: From video poster (player page)
            const video = document.querySelector('video');
            if (video) {
                const posterUrl = video.getAttribute('poster');
                if (posterUrl) {
                    const itemIdMatch = posterUrl.match(/\/Items\/([a-f0-9]+)\//);
                    if (itemIdMatch && window.ApiClient) {
                        return window.ApiClient.getItem(window.ApiClient.getCurrentUserId(), itemIdMatch[1])
                            .then(item => item?.ProviderIds?.Tmdb)
                            .catch(() => null);
                    }
                }
            }

            return Promise.resolve(null);
        } catch (error) {
            console.error(`${logPrefix} Error getting TMDB ID:`, error);
            return Promise.resolve(null);
        }
    }

    // Escape HTML (security)
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Simple Markdown parser
    function parseMarkdown(text) {
        if (!text) return '';

        let html = escapeHtml(text);

        // Basic markdown parsing
        html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
        html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');
        html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
        html = html.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>');
        html = '<p>' + html + '</p>';

        return html;
    }

    // Create critic card element
    function createCriticCard(criticData) {
        const card = document.createElement('div');
        card.className = 'parody-critic-card';
        card.setAttribute('data-character', criticData.character_id);

        const content = criticData.content || 'Sin contenido disponible';
        const PREVIEW_LENGTH = 300;
        const isLongReview = content.length > PREVIEW_LENGTH;
        const previewContent = isLongReview ? content.substring(0, PREVIEW_LENGTH) : content;

        const reviewDate = criticData.generated_at ?
            new Date(criticData.generated_at).toLocaleDateString('es-ES', {
                year: 'numeric', month: 'short', day: 'numeric'
            }) : '';

        const ratingDisplay = criticData.rating ?
            `<span class="parody-critic-rating" style="color: ${criticData.color}; background: ${criticData.accent_color};">⭐ ${criticData.rating}/10</span>` : '';

        card.innerHTML = `
            <div class="parody-critic-header">
                <div class="parody-critic-author-info">
                    <strong class="parody-critic-author" style="color: ${criticData.color};">
                        ${criticData.emoji} ${escapeHtml(criticData.author)}
                    </strong>
                    <span class="parody-critic-date">${reviewDate}</span>
                </div>
                ${ratingDisplay}
            </div>
            <div class="parody-critic-content">
                <div class="parody-critic-text"></div>
            </div>
        `;

        // Apply border color
        card.style.borderLeft = `4px solid ${criticData.border_color}`;

        const textElement = card.querySelector('.parody-critic-text');
        textElement.innerHTML = parseMarkdown(previewContent) +
            (isLongReview ? `<span class="parody-critic-toggle" style="color: ${criticData.color};"> ...leer más</span>` : '');

        // Toggle expand/collapse
        if (isLongReview) {
            textElement.addEventListener('click', function(e) {
                if (e.target.classList.contains('parody-critic-toggle')) {
                    const isExpanded = textElement.classList.contains('expanded');

                    if (!isExpanded) {
                        textElement.innerHTML = parseMarkdown(content) +
                            `<span class="parody-critic-toggle" style="color: ${criticData.color};"> ...leer menos</span>`;
                        textElement.classList.add('expanded');
                    } else {
                        textElement.innerHTML = parseMarkdown(previewContent) +
                            `<span class="parody-critic-toggle" style="color: ${criticData.color};"> ...leer más</span>`;
                        textElement.classList.remove('expanded');
                    }
                }
            });
        }

        return card;
    }

    // Create critics section
    function createCriticsSection(criticsData) {
        const section = document.createElement('details');
        section.className = `detailSection ${CONFIG.SECTION_CLASS}`;
        section.setAttribute('open', '');

        const summary = document.createElement('summary');
        summary.className = 'sectionTitle';
        summary.innerHTML = `🎭 Críticos de la Casa (${criticsData.total_critics}) <i class="material-icons expand-icon">expand_more</i>`;
        section.appendChild(summary);

        const container = document.createElement('div');
        container.className = 'parody-critics-container';

        // Create cards for each critic
        Object.values(criticsData.critics).forEach(critic => {
            container.appendChild(createCriticCard(critic));
        });

        section.appendChild(container);
        return section;
    }

    // Inject CSS styles
    function injectStyles() {
        const styleId = 'parody-critics-api-styles';
        if (document.getElementById(styleId)) return;

        const style = document.createElement('style');
        style.id = styleId;
        style.textContent = `
            .${CONFIG.SECTION_CLASS} {
                margin: 2em 0 1em 0;
                display: flex !important;
                flex-direction: column;
            }
            .${CONFIG.SECTION_CLASS} summary {
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: space-between;
                user-select: none;
                color: rgba(255, 255, 255, 0.8);
                padding-bottom: 0.5em;
            }
            .${CONFIG.SECTION_CLASS} summary .expand-icon {
                color: rgba(255, 255, 255, 0.8);
                transition: transform 0.2s ease-in-out;
            }
            .${CONFIG.SECTION_CLASS}[open] summary .expand-icon {
                transform: rotate(180deg);
            }
            .parody-critics-container {
                display: flex;
                flex-direction: column;
                gap: 1.2em;
                padding: 1em 0.5em;
                max-width: 100%;
            }
            .parody-critic-card {
                background: rgba(0, 0, 0, 0.3);
                border-radius: 8px;
                padding: 1.5em;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                transition: transform 0.2s ease, box-shadow 0.2s ease;
                display: flex;
                flex-direction: column;
                max-width: 100%;
            }
            .parody-critic-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
            }
            .parody-critic-header {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-bottom: 1em;
            }
            .parody-critic-author-info {
                display: flex;
                flex-direction: column;
                gap: 0.3em;
            }
            .parody-critic-author {
                font-size: 1.1em;
                font-weight: 600;
            }
            .parody-critic-date {
                color: #aaa;
                font-size: 0.9em;
            }
            .parody-critic-rating {
                padding: 0.2em 0.5em;
                border-radius: 4px;
                font-weight: bold;
            }
            .parody-critic-content {
                flex-grow: 1;
                line-height: 1.7;
                color: #ddd;
                font-size: 0.95em;
            }
            .parody-critic-text strong {
                color: #fff;
                font-weight: 600;
            }
            .parody-critic-text em {
                font-style: italic;
                color: #e0e0e0;
            }
            .parody-critic-text blockquote {
                border-left: 3px solid #ffd700;
                padding-left: 1em;
                margin: 0.8em 0;
                color: #aaa;
                font-style: italic;
            }
            .parody-critic-text a {
                color: #ffd700;
                text-decoration: underline;
            }
            .parody-critic-text a:hover {
                color: #ffed4e;
            }
            .parody-critic-toggle {
                font-weight: bold;
                cursor: pointer;
                text-decoration: underline;
                margin-left: 0.5em;
            }
            .parody-critic-toggle:hover {
                opacity: 0.8;
            }
        `;
        document.head.appendChild(style);
    }

    // Process and inject critics
    async function processCritics() {
        // Check if already exists
        if (document.querySelector(`.${CONFIG.SECTION_CLASS}`)) {
            console.log(`${logPrefix} Section already exists, skipping`);
            return;
        }

        try {
            // Get TMDB ID
            const tmdbId = await getCurrentTmdbId();

            if (!tmdbId) {
                console.log(`${logPrefix} No TMDB ID found, skipping`);
                return;
            }

            console.log(`${logPrefix} Processing TMDB ID: ${tmdbId}`);

            // Fetch critics from API
            const criticsData = await fetchCritics(tmdbId);

            if (!criticsData || !criticsData.critics || Object.keys(criticsData.critics).length === 0) {
                console.log(`${logPrefix} No critics found for TMDB ID: ${tmdbId}`);
                return;
            }

            // Create and inject section
            const criticsSection = createCriticsSection(criticsData);

            // Find insertion point
            const enhancedReviews = document.querySelector('.tmdb-reviews-section');
            const insertionPoint = enhancedReviews ||
                                 document.querySelector('.streaming-lookup-container') ||
                                 document.querySelector('.itemExternalLinks') ||
                                 document.querySelector('.tagline');

            if (insertionPoint && insertionPoint.parentNode) {
                // Double check before inserting
                if (!document.querySelector(`.${CONFIG.SECTION_CLASS}`)) {
                    if (enhancedReviews) {
                        enhancedReviews.after(criticsSection);
                    } else {
                        insertionPoint.parentNode.insertBefore(criticsSection, insertionPoint.nextSibling);
                    }
                    console.log(`${logPrefix} Critics section injected successfully! 🎭`);
                }
            } else {
                console.warn(`${logPrefix} Could not find insertion point`);
            }

        } catch (error) {
            console.error(`${logPrefix} Error processing critics:`, error);
        }
    }

    // Page monitoring system
    function startMonitoring() {
        injectStyles();

        let processedPages = new Set();
        let isProcessing = false;

        const processPageSafely = async () => {
            if (isProcessing) return;

            const currentUrl = window.location.hash;
            const isDetailsPage = currentUrl.includes('details') || currentUrl.includes('id=');

            if (!isDetailsPage) return;
            if (processedPages.has(currentUrl)) return;

            isProcessing = true;
            processedPages.add(currentUrl);

            // Wait for page to load
            setTimeout(async () => {
                await processCritics();
                isProcessing = false;
            }, 1500);
        };

        // Monitor URL changes
        let currentHash = window.location.hash;
        setInterval(() => {
            if (window.location.hash !== currentHash) {
                currentHash = window.location.hash;
                processedPages.clear();
                processPageSafely();
            }
        }, 500);

        // Initial processing
        processPageSafely();

        console.log(`${logPrefix} Monitoring started (API version) 🎭`);
    }

    // Check API health on startup
    async function checkAPIHealth() {
        try {
            const response = await fetch(`${CONFIG.API_BASE_URL}/health`);
            if (response.ok) {
                console.log(`${logPrefix} API health check passed ✅`);
                return true;
            } else {
                console.warn(`${logPrefix} API health check failed: ${response.status}`);
                return false;
            }
        } catch (error) {
            console.warn(`${logPrefix} API not available:`, error);
            return false;
        }
    }

    // Initialize
    async function initialize() {
        console.log(`${logPrefix} Initializing API client...`);

        const apiHealthy = await checkAPIHealth();
        if (!apiHealthy) {
            console.warn(`${logPrefix} API not available, critics will not be loaded`);
            return;
        }

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', startMonitoring);
        } else {
            setTimeout(startMonitoring, 1000);
        }

        console.log(`${logPrefix} API client loaded successfully! 🎭`);
    }

    // Start the show!
    initialize();
})();