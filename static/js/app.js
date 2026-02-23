/**
 * 🎭 Parody Critics - Frontend Application
 * =======================================
 * JavaScript application for the Parody Critics web interface
 */

class ParodyCriticsApp {
    constructor() {
        this.apiBase = `${window.location.protocol}//${window.location.host}/api`;
        this.currentView = 'home';
        this.selectedCharacter = null;
        this.selectedMedia = null;

        // Media pagination state
        this.mediaState = {
            currentData: [],
            isLoading: false,
            hasMore: true,
            currentOffset: 0,
            limit: 200,
            isGroupedView: false,
            currentFilters: {
                type: '',
                critics: '',
                letter: ''
            }
        };

        // 🛒 E-commerce Cart System properties
        this.cart = new Map(); // Map of tmdb_id -> media object
        this.isCartOpen = false;
        this.batchProcessing = {
            isProcessing: false,
            selectedCritics: new Set(),
            results: [],
            controller: null
        };

        this.init();
    }

    async init() {
        console.log('🎭 Initializing Parody Critics App');

        // Setup event listeners
        this.setupNavigation();
        this.setupModals();

        // Ensure modal is hidden on init
        this.ensureModalHidden();

        // Load initial data
        await this.loadInitialData();

        // Show home view
        this.showView('home');

        console.log('✅ App initialized successfully');
    }

    // ========================================
    // Navigation
    // ========================================

    setupNavigation() {
        const navButtons = document.querySelectorAll('.nav-btn');
        navButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const view = e.target.dataset.view;
                this.showView(view);

                // Update active nav button
                navButtons.forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
            });
        });

        // CTA buttons
        const ctaButtons = document.querySelectorAll('[data-view]');
        ctaButtons.forEach(btn => {
            if (!btn.classList.contains('nav-btn')) {
                btn.addEventListener('click', (e) => {
                    const view = e.target.dataset.view;
                    this.showView(view);

                    // Update nav
                    const navBtn = document.querySelector(`.nav-btn[data-view="${view}"]`);
                    if (navBtn) {
                        navButtons.forEach(b => b.classList.remove('active'));
                        navBtn.classList.add('active');
                    }
                });
            }
        });

        // 🛒 Cart button event listener
        const cartButton = document.getElementById('cart-btn');
        if (cartButton) {
            cartButton.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('🛒 Cart button clicked');
                this.toggleCart();
            });
            console.log('🛒 Cart button event listener added');
        } else {
            console.error('❌ Cart button not found during setup');
        }
    }

    showView(viewName) {
        // Hide all views
        const views = document.querySelectorAll('.view');
        views.forEach(view => view.classList.remove('active'));

        // Show selected view
        const targetView = document.getElementById(`${viewName}-view`);
        if (targetView) {
            targetView.classList.add('active');
            this.currentView = viewName;

            // Update navigation buttons
            const navButtons = document.querySelectorAll('.nav-btn');
            navButtons.forEach(btn => {
                if (btn.dataset.view === viewName) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            });

            // Load view-specific data
            this.loadViewData(viewName);
        }
    }

    async loadViewData(viewName) {
        switch (viewName) {
            case 'home':
                await this.loadHomeData();
                break;
            case 'media':
                await this.loadMediaData();
                break;
            case 'critics':
                await this.loadCriticsData();
                break;
            case 'generate':
                await this.loadGenerateData();
                break;
            case 'status':
                await this.loadStatusData();
                break;
            case 'checkout':
                // 🛒 Load checkout data
                await this.loadCheckoutData();
                break;
        }
    }

    // ========================================
    // Data Loading
    // ========================================

    async loadInitialData() {
        try {
            console.log('🔄 Loading initial data...');
            await this.loadHomeData();
            console.log('✅ Initial data loaded successfully');
        } catch (error) {
            console.error('❌ Failed to load initial data:', error);
            this.showError('Failed to load initial data: ' + error.message);
        }
    }

    async loadHomeData() {
        try {
            // Load stats
            const stats = await this.fetchAPI('/stats');

            document.getElementById('total-media').textContent = stats.total_media || 0;
            document.getElementById('total-critics').textContent = stats.total_critics || 0;

            // Check system status
            const health = await this.fetchAPI('/health');
            const statusElement = document.getElementById('system-status');
            if (health.status === 'healthy') {
                statusElement.textContent = '✅ Operativo';
                statusElement.style.color = 'var(--success)';
            } else {
                statusElement.textContent = '⚠️ Issues';
                statusElement.style.color = 'var(--warning)';
            }

        } catch (error) {
            console.error('Failed to load home data:', error);
        }
    }

    async loadMediaData(reset = true) {
        const mediaGrid = document.getElementById('media-grid');

        if (reset) {
            // Reset state for new search
            this.mediaState.currentData = [];
            this.mediaState.currentOffset = 0;
            this.mediaState.hasMore = true;
            mediaGrid.innerHTML = '<div class="loading">🎬 Cargando películas y series...</div>';
        } else if (this.mediaState.isLoading || !this.mediaState.hasMore) {
            return; // Already loading or no more data
        }

        this.mediaState.isLoading = true;

        try {
            const typeFilter = document.getElementById('type-filter').value;
            const criticsFilter = document.getElementById('critics-filter').value;

            // Update current filters
            this.mediaState.currentFilters.type = typeFilter;
            this.mediaState.currentFilters.critics = criticsFilter;

            let url = `/media?limit=${this.mediaState.limit}&offset=${this.mediaState.currentOffset}`;
            if (typeFilter) url += `&type=${typeFilter}`;
            if (criticsFilter) url += `&has_critics=${criticsFilter}`;
            if (this.mediaState.currentFilters.letter) url += `&start_letter=${this.mediaState.currentFilters.letter}`;

            const newMedia = await this.fetchAPI(url);

            if (newMedia.length === 0) {
                this.mediaState.hasMore = false;
                if (this.mediaState.currentData.length === 0) {
                    mediaGrid.innerHTML = '<div class="loading">📭 No se encontraron películas</div>';
                }
            } else {
                // Add new media to current data
                this.mediaState.currentData = [...this.mediaState.currentData, ...newMedia];
                this.mediaState.currentOffset += newMedia.length;

                // If we got less than the limit, we've reached the end
                if (newMedia.length < this.mediaState.limit) {
                    this.mediaState.hasMore = false;
                }

                this.renderMediaGrid(this.mediaState.currentData);

                // 🛒 Update cart selection states after rendering
                // Use requestAnimationFrame for better timing
                requestAnimationFrame(() => {
                    setTimeout(() => {
                        this.updateMediaCardSelectionStates();
                        console.log('🛒 Updated selection states after render');
                    }, 200);
                });
            }

            // Setup filters and infinite scroll on first load
            if (reset) {
                this.setupMediaFilters();
                this.setupInfiniteScroll();
            }

        } catch (error) {
            console.error('Failed to load media:', error);
            if (reset) {
                mediaGrid.innerHTML = '<div class="loading">❌ Error loading media</div>';
            }
        } finally {
            this.mediaState.isLoading = false;
        }
    }

    setupMediaFilters() {
        const typeFilter = document.getElementById('type-filter');
        const criticsFilter = document.getElementById('critics-filter');

        [typeFilter, criticsFilter].forEach(filter => {
            filter.addEventListener('change', () => {
                this.loadMediaData();
            });
        });

        // Setup event delegation for generate critic buttons
        const mediaGrid = document.getElementById('media-grid');
        mediaGrid.addEventListener('click', (e) => {
            if (e.target.classList.contains('generate-critic-btn') ||
                e.target.classList.contains('compact-generate-btn')) {
                e.stopPropagation();
                const tmdbId = e.target.dataset.tmdbId;
                const title = e.target.dataset.title;

                if (tmdbId && title) {
                    this.openGenerateCriticModal(tmdbId, title);
                } else {
                    console.error('❌ Missing tmdbId or title in button data');
                }
            }
        });

        // Generate alphabet navigation
        this.generateAlphabetNavigation();
    }

    setupInfiniteScroll() {
        // Remove any existing scroll listeners to avoid duplicates
        window.removeEventListener('scroll', this.handleScroll);

        // Bind the scroll handler to preserve 'this' context
        this.handleScroll = this.handleScroll.bind(this);
        window.addEventListener('scroll', this.handleScroll);
    }

    handleScroll() {
        // Check if we're near the bottom of the page
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        const windowHeight = window.innerHeight || document.documentElement.clientHeight;
        const documentHeight = document.documentElement.scrollHeight;

        // Load more when user is 300px from bottom
        if (scrollTop + windowHeight >= documentHeight - 300) {
            console.log('📜 Scroll detected near bottom, loading more media...');
            this.loadMediaData(false); // false = don't reset, append more data
        }
    }

    renderMediaGrid(media) {
        const mediaGrid = document.getElementById('media-grid');

        if (!media || media.length === 0) {
            mediaGrid.innerHTML = '<div class="loading">📽️ No media found</div>';
            return;
        }

        let mediaHTML;

        if (this.mediaState.isGroupedView) {
            // Grouped view
            mediaHTML = this.renderGroupedView(media);
        } else {
            // List view
            mediaHTML = this.renderListView(media);
        }

        // Add loading indicator if more content is available
        if (this.mediaState.isLoading && this.mediaState.hasMore) {
            mediaHTML += `
                <div class="media-loading" id="media-loading">
                    <div class="loading">📽️ Cargando más películas...</div>
                </div>
            `;
        } else if (!this.mediaState.hasMore && media.length > 0) {
            mediaHTML += `
                <div class="media-end" id="media-end">
                    <div class="loading">🎬 Has visto todas las ${media.length} películas y series disponibles</div>
                </div>
            `;
        }

        mediaGrid.innerHTML = mediaHTML;
    }

    renderListView(media) {
        return media.map(item => `
            <div class="media-card" data-tmdb-id="${item.tmdb_id}">
                <!-- 🛒 E-commerce Selection Checkbox -->
                <div class="media-card-select" onclick="app.toggleMediaSelection({
                    tmdb_id: '${item.tmdb_id}',
                    title: '${item.title.replace(/'/g, "\\'")}',
                    year: '${item.year || 'N/A'}',
                    type: '${item.type}',
                    poster_url: '${item.poster_url || ''}',
                    has_critics: ${item.has_critics || false}
                })">
                </div>

                <div class="media-card-header" onclick="app.showMediaDetails('${item.tmdb_id}')">
                    <h3 class="media-title">${item.title}</h3>
                    <div class="media-meta">
                        <span class="media-type ${item.type}">${item.type}</span>
                        <span>${item.year || 'Unknown'}</span>
                        ${item.vote_average ? `<div class="rating-badge">⭐ ${item.vote_average}</div>` : ''}
                    </div>
                </div>
                <div class="media-card-body" onclick="app.showMediaDetails('${item.tmdb_id}')">
                    <p class="media-description">${item.overview || 'No description available'}</p>
                    <div class="media-genres">
                        ${(item.genres || []).map(genre => `<span class="genre-tag">${genre}</span>`).join('')}
                    </div>
                </div>
                <div class="media-card-footer">
                    <span class="critics-count ${item.has_critics ? 'has-critics' : ''}">
                        ${item.critics_count > 0 ? `📝 ${item.critics_count} críticas` : '📝 Sin críticas'}
                    </span>
                    <button class="btn btn-primary btn-sm generate-critic-btn"
                            data-tmdb-id="${item.tmdb_id}" data-title="${item.title}">
                        🎭 Generar Crítica
                    </button>
                </div>
            </div>
        `).join('');
    }

    renderGroupedView(media) {
        const groups = this.groupMediaByPattern(media);

        return groups.map(group => `
            <div class="media-group">
                <div class="group-header">
                    <h3 class="group-title">${group.name}</h3>
                    <span class="group-count">${group.count} elementos</span>
                </div>
                <div class="group-content">
                    ${group.items.map(item => `
                        <div class="media-card-compact media-card" data-tmdb-id="${item.tmdb_id}">
                            <!-- 🛒 E-commerce Selection Checkbox -->
                            <div class="media-card-select" onclick="app.toggleMediaSelection({
                                tmdb_id: '${item.tmdb_id}',
                                title: '${item.title.replace(/'/g, "\\'")}',
                                year: '${item.year || 'N/A'}',
                                type: '${item.type}',
                                poster_url: '${item.poster_url || ''}',
                                has_critics: ${item.has_critics || false}
                            })">
                            </div>

                            <div class="compact-header" onclick="app.showMediaDetails('${item.tmdb_id}')">
                                <h4 class="compact-title">${item.title}</h4>
                                <span class="compact-meta">${item.year || 'N/A'} • ${item.type}</span>
                            </div>
                            <div class="compact-footer">
                                ${item.vote_average ? `<span class="compact-rating">⭐ ${item.vote_average}</span>` : ''}
                                <span class="compact-critics ${item.has_critics ? 'has-critics' : ''}">
                                    ${item.critics_count > 0 ? `📝 ${item.critics_count}` : '📝 0'}
                                </span>
                                <button class="btn btn-primary btn-xs compact-generate-btn"
                                        data-tmdb-id="${item.tmdb_id}" data-title="${item.title}">
                                    🎭
                                </button>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `).join('');
    }

    // Group media by detected patterns in titles
    groupMediaByPattern(media) {
        const groups = new Map();

        media.forEach(item => {
            const group = this.detectMediaGroup(item.title);
            if (!groups.has(group)) {
                groups.set(group, []);
            }
            groups.get(group).push(item);
        });

        // Sort groups by name and convert to array
        return Array.from(groups.entries())
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([groupName, items]) => ({
                name: groupName,
                items: items.sort((a, b) => a.title.localeCompare(b.title)),
                count: items.length
            }));
    }

    // Detect group for a media title
    detectMediaGroup(title) {
        // Collection tags [TAG]
        const collectionMatch = title.match(/^\[([^\]]+)\]/);
        if (collectionMatch) {
            const tag = collectionMatch[1];
            if (tag === 'GAL') return '🌍 Colección Galega';
            if (tag.match(/^\d{4}$/)) return `🗓️ Colección ${tag}`;
            return `📚 ${tag}`;
        }

        // Series patterns (numbers + similar titles)
        const seriesPatterns = [
            { pattern: /^(\d+)\s+(ninjas?|pequeños ninjas?)/, name: '🥷 Serie Ninjas' },
            { pattern: /^(Fast|Rapido|A todo gas|2 Fast)/i, name: '🏎️ Fast & Furious' },
            { pattern: /Matrix/i, name: '💊 Matrix Series' },
            { pattern: /Terminator/i, name: '🤖 Terminator Series' },
            { pattern: /Star Wars/i, name: '⭐ Star Wars' },
            { pattern: /Marvel|Avengers|Spider|Iron Man|Thor|Hulk/i, name: '🦸 Marvel Universe' },
            { pattern: /DC|Batman|Superman|Wonder Woman/i, name: '🦇 DC Universe' },
        ];

        for (const serie of seriesPatterns) {
            if (serie.pattern.test(title)) {
                return serie.name;
            }
        }

        // Alphabetical grouping for remaining items
        const firstLetter = title.charAt(0).toUpperCase();
        if (firstLetter >= 'A' && firstLetter <= 'D') return '🔤 A - D';
        if (firstLetter >= 'E' && firstLetter <= 'H') return '🔤 E - H';
        if (firstLetter >= 'I' && firstLetter <= 'L') return '🔤 I - L';
        if (firstLetter >= 'M' && firstLetter <= 'P') return '🔤 M - P';
        if (firstLetter >= 'Q' && firstLetter <= 'T') return '🔤 Q - T';
        if (firstLetter >= 'U' && firstLetter <= 'Z') return '🔤 U - Z';

        // Numbers and symbols
        if (/^[0-9]/.test(firstLetter)) return '🔢 Números';
        return '❓ Otros';
    }

    // Toggle between grouped and list view
    toggleGroupView() {
        this.mediaState.isGroupedView = !this.mediaState.isGroupedView;

        // Update button text
        const toggleButton = document.getElementById('group-toggle');
        toggleButton.textContent = this.mediaState.isGroupedView ? '📄 Vista Lista' : '📚 Vista Agrupada';

        // Re-render with current data
        if (this.mediaState.currentData.length > 0) {
            this.renderMediaGrid(this.mediaState.currentData);
        }

        console.log(`🔄 Switched to ${this.mediaState.isGroupedView ? 'grouped' : 'list'} view`);
    }

    // Filter by alphabet letter
    filterByLetter(letter) {
        // Update the letter filter
        this.mediaState.currentFilters.letter = letter;

        // Update active letter button
        document.querySelectorAll('.letter-btn').forEach(btn => btn.classList.remove('active'));
        if (letter) {
            const activeBtn = document.querySelector(`[data-letter="${letter}"]`);
            if (activeBtn) activeBtn.classList.add('active');
        } else {
            // If no letter (show all), activate the "TODOS" button
            const todosBtn = document.querySelector('[data-letter=""]');
            if (todosBtn) todosBtn.classList.add('active');
        }

        console.log(`🔤 Filtering by letter: ${letter || 'ALL'}`);

        // Reset pagination and reload media
        this.resetMediaPagination();
        this.loadMediaData();
    }

    // Generate alphabet navigation
    generateAlphabetNavigation() {
        const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
        const container = document.getElementById('alphabet-navigation');
        if (!container) return;

        let html = '<div class="alphabet-nav">';

        // "Todos" button
        html += `<button class="letter-btn active" onclick="app.filterByLetter('')" data-letter="">TODOS</button>`;

        // Numbers button
        html += `<button class="letter-btn" onclick="app.filterByLetter('0-9')" data-letter="0-9">#</button>`;

        // Alphabet buttons
        alphabet.forEach(letter => {
            html += `<button class="letter-btn" onclick="app.filterByLetter('${letter}')" data-letter="${letter}">${letter}</button>`;
        });

        html += '</div>';
        container.innerHTML = html;

        console.log('🔤 Alphabet navigation generated');
    }

    // Reset media pagination state
    resetMediaPagination() {
        this.mediaState.currentData = [];
        this.mediaState.currentOffset = 0;
        this.mediaState.hasMore = true;
        this.mediaState.isLoading = false;
    }

    // Filter media data by letter
    filterDataByLetter(data, letter) {
        if (!letter) return data;

        return data.filter(item => {
            const title = item.title || '';
            const firstChar = title.charAt(0).toUpperCase();

            if (letter === '0-9') {
                // Filter for numbers and special characters
                return /^[0-9]/.test(firstChar);
            } else {
                // Filter for specific letter
                return firstChar === letter;
            }
        });
    }

    async showMediaDetails(tmdbId) {
        console.log('🎬 Loading details for media:', tmdbId);

        try {
            const critics = await this.fetchAPI(`/critics/${tmdbId}`);
            console.log('📝 Critics loaded:', critics);
            this.showCriticModal(critics);
        } catch (error) {
            console.error('❌ Error loading critics for', tmdbId, ':', error);

            if (error.message.includes('404')) {
                this.showMessage('No hay críticas para este medio aún. ¡Genera una!', 'info');
            } else {
                this.showMessage('Error loading critics: ' + error.message, 'error');
            }
        }
    }

    async loadCriticsData() {
        const criticsList = document.getElementById('critics-list');
        criticsList.innerHTML = '<div class="loading">📝 Cargando críticas...</div>';

        try {
            // Get all media with critics
            const media = await this.fetchAPI('/media?has_critics=true&limit=20');

            if (!media || media.length === 0) {
                criticsList.innerHTML = '<div class="loading">📝 No critics found yet</div>';
                return;
            }

            // Load critics for each media
            const criticsPromises = media.map(async (item) => {
                try {
                    const critics = await this.fetchAPI(`/critics/${item.tmdb_id}`);
                    return { media: item, critics: critics.critics };
                } catch (error) {
                    return null;
                }
            });

            const criticsData = await Promise.all(criticsPromises);
            const validCritics = criticsData.filter(Boolean);

            this.renderCriticsList(validCritics);

        } catch (error) {
            console.error('Failed to load critics:', error);
            criticsList.innerHTML = '<div class="loading">❌ Error loading critics</div>';
        }
    }

    renderCriticsList(criticsData) {
        const criticsList = document.getElementById('critics-list');

        if (!criticsData || criticsData.length === 0) {
            criticsList.innerHTML = '<div class="loading">📝 No critics available</div>';
            return;
        }

        let html = '';

        criticsData.forEach(({ media, critics }) => {
            html += `<div class="media-critics-section">
                <h3 class="media-section-title">${media.title} (${media.year})</h3>`;

            Object.values(critics).forEach(critic => {
                html += this.renderCriticCard(critic, media);
            });

            html += '</div>';
        });

        criticsList.innerHTML = html;
    }

    renderCriticCard(critic, media = null) {
        return `
            <div class="critic-card">
                <div class="critic-header">
                    <div class="critic-character">
                        <span class="critic-character-emoji">${critic.emoji || '🎭'}</span>
                        <div class="critic-character-info">
                            <h3>${critic.author}</h3>
                            <span class="personality">${critic.personality}</span>
                        </div>
                    </div>
                    <div class="critic-rating">${critic.rating}/10</div>
                </div>
                <div class="critic-body">
                    <div class="critic-content">${critic.content}</div>
                </div>
                <div class="critic-meta">
                    <span>Generado: ${this.formatDate(critic.generated_at)}</span>
                    ${media ? `<span>${media.title}</span>` : ''}
                </div>
            </div>
        `;
    }

    async loadGenerateData() {
        // Load characters
        await this.loadCharacters();

        // Setup media search
        this.setupMediaSearch();

        // Setup form handlers
        this.setupGenerateForm();
    }

    async loadCharacters() {
        const characterSelector = document.getElementById('character-selector');

        try {
            const characters = await this.fetchAPI('/characters');

            characterSelector.innerHTML = characters.map(char => `
                <div class="character-card ${char.id}" onclick="app.selectCharacter('${char.id}')">
                    <span class="character-emoji">${char.emoji}</span>
                    <h3 class="character-name">${char.name}</h3>
                    <p class="character-description">${char.description}</p>
                </div>
            `).join('');

        } catch (error) {
            console.error('Failed to load characters:', error);
            characterSelector.innerHTML = '<div class="loading">❌ Error loading characters</div>';
        }
    }

    setupMediaSearch() {
        const searchInput = document.getElementById('media-search');
        const searchResults = document.getElementById('search-results');
        const selectedDisplay = document.getElementById('selected-media-display');

        let searchTimeout;
        let currentResults = [];
        let selectedIndex = -1;

        // Initialize search state
        this.currentSearchResults = [];

        // Search input handler
        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.trim();

            if (query.length < 2) {
                this.hideSearchResults();
                return;
            }

            // Debounce search requests
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                this.performMediaSearch(query);
            }, 300);
        });

        // Keyboard navigation
        searchInput.addEventListener('keydown', (e) => {
            if (!searchResults.classList.contains('show')) return;

            switch (e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    selectedIndex = Math.min(selectedIndex + 1, currentResults.length - 1);
                    this.highlightSearchResult(selectedIndex);
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    selectedIndex = Math.max(selectedIndex - 1, -1);
                    this.highlightSearchResult(selectedIndex);
                    break;
                case 'Enter':
                    e.preventDefault();
                    if (selectedIndex >= 0 && currentResults[selectedIndex]) {
                        this.selectMediaFromSearch(currentResults[selectedIndex]);
                    }
                    break;
                case 'Escape':
                    e.preventDefault();
                    this.hideSearchResults();
                    break;
            }
        });

        // Click outside to close
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.media-search-container')) {
                this.hideSearchResults();
            }
        });
    }

    async performMediaSearch(query) {
        const searchResults = document.getElementById('search-results');

        try {
            // Double-check query length to prevent API errors
            if (query.length < 2) {
                searchResults.innerHTML = '<div class="search-no-results">⚠️ Escribe al menos 2 caracteres</div>';
                searchResults.classList.add('show');
                return;
            }

            // Show loading state
            searchResults.innerHTML = '<div class="search-loading">🔍 Buscando...</div>';
            searchResults.classList.add('show');

            // Perform search
            const results = await this.fetchAPI(`/media/search?query=${encodeURIComponent(query)}&limit=20`);

            if (results.length === 0) {
                searchResults.innerHTML = '<div class="search-no-results">No se encontraron resultados</div>';
                currentResults = [];
                selectedIndex = -1;
                return;
            }

            // Display results
            currentResults = results;
            this.currentSearchResults = results;
            selectedIndex = -1;

            searchResults.innerHTML = results.map((item, index) => `
                <div class="search-result-item" data-index="${index}" onclick="app.selectMediaFromSearch(app.currentSearchResults[${index}])">
                    <div>
                        <div class="search-result-title">${item.title}</div>
                        <div class="search-result-meta">
                            <span class="search-result-type">${item.type}</span>
                            <span>${item.year}</span>
                            ${item.has_critics ? '<span>✅ Con críticas</span>' : '<span>➕ Sin críticas</span>'}
                        </div>
                    </div>
                </div>
            `).join('');

        } catch (error) {
            console.error('Search failed:', error);

            let errorMessage = '❌ Error en la búsqueda';

            // Check for specific error types
            if (error.message.includes('400')) {
                errorMessage = '⚠️ Escribe al menos 2 caracteres';
            } else if (error.message.includes('500')) {
                errorMessage = '❌ Error del servidor';
            } else if (error.message.includes('404')) {
                errorMessage = '❌ Servicio no encontrado';
            }

            searchResults.innerHTML = `<div class="search-no-results">${errorMessage}</div>`;
            currentResults = [];
            selectedIndex = -1;
        }
    }

    highlightSearchResult(index) {
        const items = document.querySelectorAll('.search-result-item');
        items.forEach((item, i) => {
            item.classList.toggle('selected', i === index);
        });
    }

    selectMediaFromSearch(media) {
        if (!media) return;

        // Store selected media
        this.selectedMedia = media.tmdb_id;
        this.selectedMediaData = media;

        // Update search input
        document.getElementById('media-search').value = media.title;

        // Show selected media info
        const selectedDisplay = document.getElementById('selected-media-display');
        const titleElement = document.getElementById('selected-media-title');
        const metaElement = document.getElementById('selected-media-meta');

        titleElement.textContent = media.title;
        metaElement.innerHTML = `
            <span class="search-result-type">${media.type}</span>
            <span>${media.year}</span>
            ${media.has_critics ? '<span>✅ Ya tiene críticas</span>' : '<span>➕ Sin críticas aún</span>'}
        `;

        selectedDisplay.classList.add('show');

        // Hide search results
        this.hideSearchResults();

        // Update generate button
        this.updateGenerateButton();
    }

    hideSearchResults() {
        document.getElementById('search-results').classList.remove('show');
    }

    selectCharacter(characterId) {
        // Remove previous selection
        document.querySelectorAll('.character-card').forEach(card => {
            card.classList.remove('selected');
        });

        // Select new character
        const characterCard = document.querySelector(`.character-card.${characterId}`);
        if (characterCard) {
            characterCard.classList.add('selected');
            this.selectedCharacter = characterId;
            this.updateGenerateButton();
        }
    }

    setupGenerateForm() {
        const generateBtn = document.getElementById('generate-btn');

        generateBtn.addEventListener('click', () => {
            this.generateCritic();
        });
    }

    updateGenerateButton() {
        const generateBtn = document.getElementById('generate-btn');
        const canGenerate = this.selectedCharacter && this.selectedMedia;

        generateBtn.disabled = !canGenerate;
    }

    async generateCritic() {
        if (!this.selectedCharacter || !this.selectedMedia) {
            this.showMessage('Please select both a character and media', 'warning');
            return;
        }

        const generateBtn = document.getElementById('generate-btn');
        const btnText = generateBtn.querySelector('.btn-text');
        const btnLoading = generateBtn.querySelector('.btn-loading');

        // Show loading state
        generateBtn.disabled = true;
        btnText.classList.add('hidden');
        btnLoading.classList.remove('hidden');

        try {
            // Get character name
            const characterName = this.getCharacterName(this.selectedCharacter);

            // Generate critic
            const result = await this.fetchAPI(
                `/generate/critic/${this.selectedMedia.tmdb_id}?character=${encodeURIComponent(characterName)}`,
                'POST'
            );

            if (result.success) {
                this.showGenerationResult(result);
                this.showMessage('¡Crítica generada exitosamente!', 'success');
            } else {
                throw new Error(result.error || 'Generation failed');
            }

        } catch (error) {
            console.error('Generation failed:', error);
            this.showMessage('Error generating critic: ' + error.message, 'error');
        } finally {
            // Reset button
            generateBtn.disabled = false;
            btnText.classList.remove('hidden');
            btnLoading.classList.add('hidden');
        }
    }

    getCharacterName(characterId) {
        const mapping = {
            'marco_aurelio': 'Marco Aurelio',
            'rosario_costras': 'Rosario Costras'
        };
        return mapping[characterId] || characterId;
    }

    showGenerationResult(result) {
        const resultSection = document.getElementById('generation-result');
        const criticCard = document.getElementById('generated-critic');

        // Create mock critic object for rendering
        const critic = {
            author: result.character,
            emoji: this.selectedCharacter === 'marco_aurelio' ? '👑' : '✊',
            rating: result.rating,
            content: result.content,
            personality: this.selectedCharacter === 'marco_aurelio' ? 'stoic' : 'woke',
            generated_at: new Date().toISOString()
        };

        criticCard.innerHTML = this.renderCriticCard(critic);
        resultSection.classList.remove('hidden');

        // Scroll to result
        resultSection.scrollIntoView({ behavior: 'smooth' });
    }

    async loadStatusData() {
        const healthStatus = document.getElementById('health-status');
        const llmStatus = document.getElementById('llm-status');
        const dbStats = document.getElementById('db-stats');

        try {
            // Load health status
            const health = await this.fetchAPI('/health');
            healthStatus.innerHTML = `
                <div class="status-item">
                    <span class="status-label">Database</span>
                    <span class="status-badge ${health.database === 'connected' ? 'healthy' : 'unhealthy'}">
                        ${health.database}
                    </span>
                </div>
                <div class="status-item">
                    <span class="status-label">Sync Manager</span>
                    <span class="status-badge ${health.sync_manager === 'initialized' ? 'healthy' : 'unhealthy'}">
                        ${health.sync_manager}
                    </span>
                </div>
                <div class="status-item">
                    <span class="status-label">Last Check</span>
                    <span class="status-value">${this.formatDate(health.timestamp)}</span>
                </div>
            `;

            // Load LLM status
            const llm = await this.fetchAPI('/llm/status');
            let llmHtml = `
                <div class="status-item">
                    <span class="status-label">System Status</span>
                    <span class="status-badge ${llm.system_status === 'operational' ? 'operational' : 'unhealthy'}">
                        ${llm.system_status}
                    </span>
                </div>
                <div class="status-item">
                    <span class="status-label">Healthy Endpoints</span>
                    <span class="status-value">${llm.healthy_endpoints}/${llm.total_endpoints}</span>
                </div>
            `;

            Object.entries(llm.endpoints).forEach(([name, endpoint]) => {
                llmHtml += `
                    <div class="status-item">
                        <span class="status-label">${name}</span>
                        <span class="status-badge ${endpoint.status === 'healthy' ? 'healthy' : 'unhealthy'}">
                            ${endpoint.model} - ${endpoint.status}
                        </span>
                    </div>
                `;
            });

            llmStatus.innerHTML = llmHtml;

            // Load database stats
            const stats = await this.fetchAPI('/stats');
            dbStats.innerHTML = `
                <div class="status-item">
                    <span class="status-label">Total Media</span>
                    <span class="status-value">${stats.total_media || 0}</span>
                </div>
                <div class="status-item">
                    <span class="status-label">Movies</span>
                    <span class="status-value">${stats.total_movies || 0}</span>
                </div>
                <div class="status-item">
                    <span class="status-label">Series</span>
                    <span class="status-value">${stats.total_series || 0}</span>
                </div>
                <div class="status-item">
                    <span class="status-label">Total Critics</span>
                    <span class="status-value">${stats.total_critics || 0}</span>
                </div>
                <div class="status-item">
                    <span class="status-label">Active Characters</span>
                    <span class="status-value">${stats.active_characters || 0}</span>
                </div>
                <div class="status-item">
                    <span class="status-label">Media Without Critics</span>
                    <span class="status-value">${stats.media_without_critics || 0}</span>
                </div>
            `;

        } catch (error) {
            console.error('Failed to load status data:', error);
            healthStatus.innerHTML = '<div class="loading">❌ Error loading health status</div>';
            llmStatus.innerHTML = '<div class="loading">❌ Error loading LLM status</div>';
            dbStats.innerHTML = '<div class="loading">❌ Error loading database stats</div>';
        }
    }

    async loadCheckoutData() {
        console.log('🛒 Loading checkout data...');

        // This function is called when showing the checkout view
        // The actual data loading is handled by renderCheckoutView()
        // which is called from proceedToCheckout()

        try {
            await this.renderCheckoutView();
            console.log('✅ Checkout data loaded successfully');
        } catch (error) {
            console.error('❌ Failed to load checkout data:', error);
            this.showMessage('Error cargando datos del checkout', 'error');
        }
    }

    // ========================================
    // Modal Handling
    // ========================================

    setupModals() {
        const modal = document.getElementById('critic-modal');
        const closeBtn = document.getElementById('modal-close');

        closeBtn.addEventListener('click', () => {
            this.hideModal();
        });

        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.hideModal();
            }
        });
    }

    showCriticModal(criticsData) {
        console.log('🎭 Showing modal with data:', criticsData);

        const modal = document.getElementById('critic-modal');
        const modalBody = document.getElementById('modal-body');

        if (!modal || !modalBody) {
            console.error('❌ Modal elements not found!');
            this.showMessage('Error: Modal not found', 'error');
            return;
        }

        let html = `
            <h2>📝 Críticas de "${criticsData.title}" (${criticsData.year})</h2>
            <div class="modal-critics">
        `;

        if (!criticsData.critics || Object.keys(criticsData.critics).length === 0) {
            html += `
                <div style="text-align: center; padding: 2rem; color: var(--text-secondary);">
                    <p>📝 No hay críticas disponibles para este medio.</p>
                    <p>¡Usa el generador para crear la primera crítica!</p>
                </div>
            `;
        } else {
            Object.values(criticsData.critics).forEach(critic => {
                html += this.renderCriticCard(critic);
            });
        }

        html += '</div>';
        modalBody.innerHTML = html;
        modal.classList.remove('hidden');

        console.log('✅ Modal displayed successfully');
    }

    hideModal() {
        console.log('🚪 Hiding modal');
        const modal = document.getElementById('critic-modal');
        if (modal) {
            modal.classList.add('hidden');
            console.log('✅ Modal hidden successfully');
        } else {
            console.error('❌ Modal element not found for hiding');
        }
    }

    ensureModalHidden() {
        console.log('🔒 Ensuring modal is hidden');
        const modal = document.getElementById('critic-modal');
        if (modal) {
            modal.classList.add('hidden');
            // Force inline styles to ensure hiding
            modal.style.display = 'none';
            modal.style.visibility = 'hidden';
            modal.style.opacity = '0';
            modal.style.pointerEvents = 'none';
            modal.style.zIndex = '-1';
            console.log('✅ Modal ensured hidden');
        }
    }

    openGenerateCriticModal(tmdbId, title) {
        console.log(`🎭 Opening generate critic modal for: ${title} (${tmdbId})`);

        // Set the selected media for the generator
        this.selectedMedia = {
            tmdb_id: tmdbId,
            title: title
        };

        // Update the media display in the generator
        this.updateSelectedDisplay();

        // Switch to the generator tab
        this.showView('generate');

        // Show success message
        this.showMessage(`🎬 Listo para generar crítica de "${title}"`, 'success');

        console.log('✅ Generator ready for media:', this.selectedMedia);
    }

    updateSelectedDisplay() {
        if (!this.selectedMedia) {
            console.log('❌ No selected media to display');
            return;
        }

        console.log('📋 Updating selected media display for:', this.selectedMedia);

        // Show selected media info
        const selectedDisplay = document.getElementById('selected-media-display');
        const titleElement = document.getElementById('selected-media-title');
        const metaElement = document.getElementById('selected-media-meta');

        if (!selectedDisplay || !titleElement || !metaElement) {
            console.error('❌ Selected display elements not found');
            return;
        }

        titleElement.textContent = this.selectedMedia.title;
        metaElement.innerHTML = `
            <span class="search-result-type">movie</span>
            <span>Seleccionado desde lista</span>
            <span>✅ Listo para generar</span>
        `;

        selectedDisplay.classList.add('show');

        // Hide search results
        this.hideSearchResults();

        // Update generate button
        this.updateGenerateButton();

        console.log('✅ Selected media display updated');
    }

    // ========================================
    // Utility Functions
    // ========================================

    async fetchAPI(endpoint, method = 'GET', data = null) {
        const url = this.apiBase + endpoint;
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
            },
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        const response = await fetch(url, options);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    }

    formatDate(dateString) {
        if (!dateString) return 'Unknown';

        try {
            const date = new Date(dateString);
            return date.toLocaleString('es-ES', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch (error) {
            return 'Invalid date';
        }
    }

    showMessage(message, type = 'info') {
        // Simple message display (could be enhanced with a toast system)
        const colors = {
            success: '#4ade80',
            error: '#ef4444',
            warning: '#fbbf24',
            info: '#3b82f6'
        };

        const messageDiv = document.createElement('div');
        messageDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${colors[type]};
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            z-index: 1000;
            max-width: 400px;
            font-weight: 500;
        `;
        messageDiv.textContent = message;

        document.body.appendChild(messageDiv);

        setTimeout(() => {
            messageDiv.remove();
        }, 5000);
    }

    showError(message) {
        this.showMessage(message, 'error');
    }

    // ========================================
    // 🎬 Media Import with Real-time Progress
    // ========================================

    async startMediaImport() {
        try {
            console.log('🎬 Starting media import...');

            const response = await fetch(`${this.apiBase}/media/import/start`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();

            if (data.success) {
                console.log('✅ Import started successfully:', data.session_id);

                // Show progress modal
                this.showImportProgress(data.session_id);

                this.showMessage('Import started! Check the progress panel.', 'success');
            } else {
                throw new Error('Failed to start import');
            }

        } catch (error) {
            console.error('❌ Failed to start import:', error);
            this.showError('Failed to start media import. Please try again.');
        }
    }

    showImportProgress(sessionId) {
        // Create or show import progress modal/panel
        let progressModal = document.getElementById('import-progress-modal');

        if (!progressModal) {
            progressModal = this.createImportProgressModal(sessionId);
            document.body.appendChild(progressModal);
        }

        progressModal.classList.remove('hidden');

        // Connect to WebSocket for real-time updates
        this.connectToImportProgress(sessionId);
    }

    createImportProgressModal(sessionId) {
        const modal = document.createElement('div');
        modal.id = 'import-progress-modal';
        modal.className = 'import-progress-modal';
        modal.innerHTML = `
            <div class="import-progress-content">
                <div class="import-progress-header">
                    <h3>🎬 Importing Media Library</h3>
                    <button class="close-import-btn" onclick="app.closeImportModal()">&times;</button>
                </div>

                <div class="import-progress-body">
                    <div class="progress-container">
                        <div class="progress-bar">
                            <div class="progress-fill" id="import-progress-fill"></div>
                        </div>
                        <div class="progress-text">
                            <span id="import-percentage">0%</span>
                            <span id="import-status">Starting...</span>
                        </div>
                    </div>

                    <div class="import-stats">
                        <div class="stat-item">
                            <span class="stat-label">Total Items:</span>
                            <span id="total-items">-</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Processed:</span>
                            <span id="processed-items">0</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">New:</span>
                            <span id="new-items" class="stat-success">0</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Updated:</span>
                            <span id="updated-items" class="stat-warning">0</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Unchanged:</span>
                            <span id="unchanged-items" class="stat-info">0</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Errors:</span>
                            <span id="error-items" class="stat-error">0</span>
                        </div>
                    </div>

                    <div class="current-operation">
                        <strong>Current:</strong>
                        <span id="current-item">Initializing...</span>
                    </div>

                    <div class="import-actions">
                        <button id="cancel-import-btn" class="btn-cancel" onclick="app.cancelImport('${sessionId}')">
                            Cancel Import
                        </button>
                    </div>

                    <div class="import-log" id="import-log">
                        <div class="log-entry">🎬 Import session started...</div>
                    </div>
                </div>
            </div>
        `;

        // Add CSS styles
        const style = document.createElement('style');
        style.textContent = `
            .import-progress-modal {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.8);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 1000;
            }

            .import-progress-content {
                background: var(--surface-color);
                border-radius: 16px;
                padding: 2rem;
                max-width: 600px;
                width: 90vw;
                max-height: 80vh;
                overflow-y: auto;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            }

            .import-progress-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 2rem;
                padding-bottom: 1rem;
                border-bottom: 2px solid var(--border-color);
            }

            .import-progress-header h3 {
                color: var(--accent-color);
                font-size: 1.5rem;
                margin: 0;
            }

            .close-import-btn {
                background: none;
                border: none;
                font-size: 2rem;
                color: var(--text-secondary);
                cursor: pointer;
                padding: 0;
                width: 40px;
                height: 40px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
                transition: all 0.3s ease;
            }

            .close-import-btn:hover {
                background: var(--error-color);
                color: white;
            }

            .progress-container {
                margin-bottom: 2rem;
            }

            .progress-bar {
                width: 100%;
                height: 20px;
                background: var(--background-color);
                border-radius: 10px;
                overflow: hidden;
                margin-bottom: 1rem;
                border: 2px solid var(--border-color);
            }

            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, var(--accent-color), var(--accent-dark));
                width: 0%;
                transition: width 0.3s ease;
                position: relative;
            }

            .progress-fill::after {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
                animation: shimmer 2s infinite;
            }

            @keyframes shimmer {
                0% { transform: translateX(-100%); }
                100% { transform: translateX(100%); }
            }

            .progress-text {
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-weight: 600;
            }

            #import-percentage {
                font-size: 1.2rem;
                color: var(--accent-color);
            }

            .import-stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
                gap: 1rem;
                margin-bottom: 2rem;
                padding: 1.5rem;
                background: var(--background-color);
                border-radius: 12px;
                border: 2px solid var(--border-color);
            }

            .stat-item {
                display: flex;
                flex-direction: column;
                text-align: center;
            }

            .stat-label {
                font-size: 0.85rem;
                color: var(--text-secondary);
                margin-bottom: 0.5rem;
            }

            .stat-item span:last-child {
                font-weight: 600;
                font-size: 1.1rem;
            }

            .stat-success { color: var(--success-color); }
            .stat-warning { color: var(--warning-color); }
            .stat-info { color: var(--accent-color); }
            .stat-error { color: var(--error-color); }

            .current-operation {
                padding: 1rem;
                background: var(--background-color);
                border-radius: 8px;
                margin-bottom: 1.5rem;
                border-left: 4px solid var(--accent-color);
            }

            .current-operation strong {
                color: var(--text-primary);
            }

            #current-item {
                color: var(--accent-color);
                font-weight: 500;
                margin-left: 0.5rem;
            }

            .import-actions {
                margin-bottom: 1.5rem;
                text-align: center;
            }

            .btn-cancel {
                background: var(--error-color);
                color: white;
                border: none;
                padding: 0.75rem 2rem;
                border-radius: 8px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.3s ease;
            }

            .btn-cancel:hover {
                background: #dc2626;
                transform: translateY(-2px);
            }

            .import-log {
                max-height: 200px;
                overflow-y: auto;
                background: #1f1f1f;
                color: #e5e5e5;
                padding: 1rem;
                border-radius: 8px;
                font-family: 'Courier New', monospace;
                font-size: 0.85rem;
                line-height: 1.4;
            }

            .log-entry {
                margin-bottom: 0.5rem;
                padding: 0.25rem 0;
                border-bottom: 1px solid #333;
            }

            .log-entry:last-child {
                border-bottom: none;
            }
        `;

        document.head.appendChild(style);
        return modal;
    }

    connectToImportProgress(sessionId) {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/ws/import-progress/${sessionId}`;
        console.log(`🔌 Connecting to WebSocket: ${wsUrl}`);

        this.importWebSocket = new WebSocket(wsUrl);

        this.importWebSocket.onopen = () => {
            console.log('✅ WebSocket connected');
            this.addLogEntry('🔌 Connected to progress stream');
        };

        this.importWebSocket.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                console.log('📨 WebSocket message:', message);

                switch (message.type) {
                    case 'import_progress':
                        this.updateImportProgress(message.data);
                        break;
                    case 'import_completed':
                        this.handleImportCompleted(message.data);
                        break;
                    case 'import_error':
                        this.handleImportError(message.data);
                        break;
                    case 'import_cancelled':
                        this.handleImportCancelled(message.data);
                        break;
                    case 'pong':
                        console.log('🏓 Pong received');
                        break;
                }
            } catch (error) {
                console.error('❌ Error parsing WebSocket message:', error);
            }
        };

        this.importWebSocket.onclose = () => {
            console.log('🔌 WebSocket connection closed');
            this.addLogEntry('🔌 Connection closed');
        };

        this.importWebSocket.onerror = (error) => {
            console.error('❌ WebSocket error:', error);
            this.addLogEntry('❌ Connection error');
        };

        // Send periodic ping
        this.importPingInterval = setInterval(() => {
            if (this.importWebSocket.readyState === WebSocket.OPEN) {
                this.importWebSocket.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000);
    }

    updateImportProgress(data) {
        // Update progress bar
        document.getElementById('import-progress-fill').style.width = `${data.percentage}%`;
        document.getElementById('import-percentage').textContent = `${Math.round(data.percentage)}%`;
        document.getElementById('import-status').textContent = data.status;

        // Update statistics
        document.getElementById('total-items').textContent = data.total_items;
        document.getElementById('processed-items').textContent = data.processed_items;
        document.getElementById('new-items').textContent = data.new_items;
        document.getElementById('updated-items').textContent = data.updated_items;
        document.getElementById('unchanged-items').textContent = data.unchanged_items;
        document.getElementById('error-items').textContent = data.errors;

        // Update current item
        document.getElementById('current-item').textContent = data.current_item || 'Processing...';

        // Add log entry for progress
        if (data.current_item) {
            this.addLogEntry(`📄 Processing: ${data.current_item}`);
        }
    }

    handleImportCompleted(data) {
        document.getElementById('import-status').textContent = 'Import Completed!';
        document.getElementById('current-item').textContent = 'All items processed successfully';

        this.addLogEntry('✅ Import completed successfully!');
        this.addLogEntry(`📊 Final stats: ${data.processed_items} items processed`);

        // Hide cancel button
        document.getElementById('cancel-import-btn').style.display = 'none';

        // Close WebSocket
        this.closeImportWebSocket();

        // Show success message
        this.showMessage('Media import completed successfully!', 'success');
    }

    handleImportError(data) {
        document.getElementById('import-status').textContent = 'Import Failed';
        document.getElementById('current-item').textContent = 'Error occurred during import';

        this.addLogEntry(`❌ Import failed: ${data.error_messages?.join(', ') || 'Unknown error'}`);

        // Hide cancel button
        document.getElementById('cancel-import-btn').style.display = 'none';

        // Close WebSocket
        this.closeImportWebSocket();

        // Show error message
        this.showError('Media import failed. Check the log for details.');
    }

    handleImportCancelled(data) {
        document.getElementById('import-status').textContent = 'Import Cancelled';
        document.getElementById('current-item').textContent = 'Import was cancelled by user';

        this.addLogEntry('🛑 Import cancelled by user');

        // Hide cancel button
        document.getElementById('cancel-import-btn').style.display = 'none';

        // Close WebSocket
        this.closeImportWebSocket();

        // Show info message
        this.showMessage('Media import was cancelled.', 'warning');
    }

    async cancelImport(sessionId) {
        try {
            const response = await fetch(`${this.apiBase}/media/import/cancel/${sessionId}`, {
                method: 'POST'
            });

            const data = await response.json();

            if (data.success) {
                this.addLogEntry('🛑 Cancellation requested...');
            } else {
                throw new Error('Failed to cancel import');
            }
        } catch (error) {
            console.error('❌ Failed to cancel import:', error);
            this.showError('Failed to cancel import');
        }
    }

    addLogEntry(message) {
        const logContainer = document.getElementById('import-log');
        if (logContainer) {
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            entry.textContent = `${new Date().toLocaleTimeString()} - ${message}`;
            logContainer.appendChild(entry);

            // Scroll to bottom
            logContainer.scrollTop = logContainer.scrollHeight;

            // Limit log entries to prevent memory issues
            const entries = logContainer.children;
            if (entries.length > 100) {
                logContainer.removeChild(entries[0]);
            }
        }
    }

    closeImportModal() {
        console.log('🚪 Closing import modal');

        // Hide the modal
        const modal = document.getElementById('import-progress-modal');
        if (modal) {
            modal.classList.add('hidden');
            modal.style.display = 'none'; // Force hide with CSS
        }

        // Close WebSocket connection
        this.closeImportWebSocket();
    }

    closeImportWebSocket() {
        if (this.importWebSocket) {
            this.importWebSocket.close();
            this.importWebSocket = null;
        }

        if (this.importPingInterval) {
            clearInterval(this.importPingInterval);
            this.importPingInterval = null;
        }
    }

    // ========================================
    // 🛒 E-commerce Cart System
    // ========================================

    // Add media to cart
    addToCart(mediaItem) {
        const key = mediaItem.tmdb_id;

        if (!this.cart.has(key)) {
            this.cart.set(key, {
                ...mediaItem,
                addedAt: Date.now()
            });

            this.updateCartUI();
            this.showMessage(`🛒 "${mediaItem.title}" agregado al carrito`, 'success');
            console.log(`🛒 Added to cart:`, mediaItem);
        } else {
            this.showMessage(`"${mediaItem.title}" ya está en el carrito`, 'warning');
        }
    }

    // Remove media from cart
    removeFromCart(tmdbId) {
        const item = this.cart.get(tmdbId);
        if (item) {
            this.cart.delete(tmdbId);
            this.updateCartUI();
            this.showMessage(`🗑️ "${item.title}" eliminado del carrito`, 'info');
            console.log(`🗑️ Removed from cart:`, tmdbId);
        }
    }

    // Clear entire cart
    clearCart() {
        this.cart.clear();
        this.updateCartUI();
        this.showMessage('🛒 Carrito vaciado', 'info');
        console.log('🛒 Cart cleared');
    }

    // Toggle cart panel
    toggleCart() {
        const cartPanel = document.getElementById('cart-panel');

        if (this.isCartOpen) {
            this.closeCart();
        } else {
            this.openCart();
        }
    }

    // Open cart panel
    openCart() {
        const cartPanel = document.getElementById('cart-panel');
        const cartOverlay = document.getElementById('cart-overlay');
        if (cartPanel && cartOverlay) {
            // Show overlay first
            cartOverlay.classList.remove('hidden');
            cartOverlay.classList.add('show');
            // Show panel
            cartPanel.classList.remove('hidden');
            cartPanel.classList.add('show');
            this.isCartOpen = true;
            this.renderCartItems();
            console.log('🛒 Cart opened');
        }
    }

    // Close cart panel
    closeCart() {
        const cartPanel = document.getElementById('cart-panel');
        const cartOverlay = document.getElementById('cart-overlay');
        if (cartPanel && cartOverlay) {
            // Hide panel first
            cartPanel.classList.remove('show');
            cartPanel.classList.add('hidden');
            // Hide overlay
            cartOverlay.classList.remove('show');
            cartOverlay.classList.add('hidden');
            this.isCartOpen = false;
            console.log('🛒 Cart closed');
        }
    }

    // Update cart UI elements
    updateCartUI() {
        // Update cart count
        const cartCount = document.getElementById('cart-count');
        if (cartCount) {
            cartCount.textContent = this.cart.size;
        }

        // Update total count
        const totalCount = document.getElementById('cart-total-count');
        if (totalCount) {
            totalCount.textContent = this.cart.size;
        }

        // Update checkout button
        const checkoutBtn = document.getElementById('cart-checkout-btn');
        if (checkoutBtn) {
            checkoutBtn.disabled = this.cart.size === 0;
        }

        // Update cart items if panel is open
        if (this.isCartOpen) {
            this.renderCartItems();
        }

        // Update media card selection states
        this.updateMediaCardSelectionStates();
    }

    // Render cart items
    renderCartItems() {
        const cartItems = document.getElementById('cart-items');
        if (!cartItems) return;

        if (this.cart.size === 0) {
            cartItems.innerHTML = `
                <div class="empty-cart">
                    <p>🎬 Tu carrito está vacío</p>
                    <p>Selecciona películas y series para generar críticas</p>
                </div>
            `;
            return;
        }

        let html = '';
        this.cart.forEach((item, tmdbId) => {
            html += `
                <div class="cart-item" data-tmdb-id="${tmdbId}">
                    <img class="cart-item-poster"
                         src="${item.poster_url || '/static/images/no-poster.png'}"
                         alt="${item.title}"
                         onerror="this.src='/static/images/no-poster.png'">
                    <div class="cart-item-info">
                        <div class="cart-item-title">${item.title}</div>
                        <div class="cart-item-meta">
                            ${item.year || 'N/A'} • ${item.type === 'movie' ? 'Película' : 'Serie'}
                            ${item.has_critics ? ' • 📝 Con críticas' : ''}
                        </div>
                    </div>
                    <button class="cart-item-remove" onclick="app.removeFromCart('${tmdbId}')">
                        ✕
                    </button>
                </div>
            `;
        });

        cartItems.innerHTML = html;
    }

    // Update media card selection states
    updateMediaCardSelectionStates() {
        console.log(`🛒 Updating selection states. Cart has ${this.cart.size} items`);

        // Update all media cards to show selection state
        const mediaCards = document.querySelectorAll('.media-card');
        let updatedCount = 0;

        mediaCards.forEach(card => {
            const tmdbId = card.dataset.tmdbId;
            const isSelected = this.cart.has(tmdbId);

            // Toggle selected class
            card.classList.toggle('selected', isSelected);

            // Update selection checkbox
            const selectCheckbox = card.querySelector('.media-card-select');
            if (selectCheckbox) {
                selectCheckbox.classList.toggle('selected', isSelected);
                if (isSelected) {
                    updatedCount++;
                }
            }
        });

        console.log(`🛒 Updated ${updatedCount} selected cards out of ${mediaCards.length} total cards`);
    }

    // Handle media card selection
    toggleMediaSelection(mediaItem) {
        const tmdbId = mediaItem.tmdb_id;

        if (this.cart.has(tmdbId)) {
            this.removeFromCart(tmdbId);
        } else {
            this.addToCart(mediaItem);
        }
    }

    // Proceed to checkout
    proceedToCheckout() {
        if (this.cart.size === 0) {
            this.showMessage('Carrito vacío. Selecciona contenido primero.', 'warning');
            return;
        }

        // Close cart and show checkout view
        this.closeCart();
        this.showView('checkout');
        this.renderCheckoutView();

        console.log('🎭 Proceeding to checkout with items:', Array.from(this.cart.values()));
    }

    // Render checkout view
    async renderCheckoutView() {
        await this.renderCheckoutMediaList();
        await this.renderCriticsSelection();
        this.updateProcessingControls();
    }

    // Render selected media in checkout
    renderCheckoutMediaList() {
        const mediaList = document.getElementById('checkout-media-list');
        if (!mediaList) return;

        if (this.cart.size === 0) {
            mediaList.innerHTML = `
                <div class="empty-cart">
                    <p>🎬 No hay contenido seleccionado</p>
                    <p><a href="#" onclick="app.showView('media')">← Volver a seleccionar</a></p>
                </div>
            `;
            return;
        }

        let html = '';
        this.cart.forEach((item, tmdbId) => {
            html += `
                <div class="checkout-media-item" data-tmdb-id="${tmdbId}">
                    <img class="checkout-media-poster"
                         src="${item.poster_url || '/static/images/no-poster.png'}"
                         alt="${item.title}"
                         onerror="this.src='/static/images/no-poster.png'">
                    <div class="checkout-media-info">
                        <div class="checkout-media-title">${item.title}</div>
                        <div class="checkout-media-meta">
                            ${item.year || 'N/A'} • ${item.type === 'movie' ? 'Película' : 'Serie'}
                            ${item.has_critics ? ' • 📝 Ya tiene críticas' : ' • ✨ Sin críticas'}
                        </div>
                    </div>
                    <button class="checkout-media-remove" onclick="app.removeFromCartCheckout('${tmdbId}')">
                        Eliminar
                    </button>
                </div>
            `;
        });

        mediaList.innerHTML = html;
    }

    // Remove from cart in checkout view
    removeFromCartCheckout(tmdbId) {
        this.removeFromCart(tmdbId);
        this.renderCheckoutMediaList();
        this.updateProcessingControls();
    }

    // Render critics selection
    async renderCriticsSelection() {
        const criticsSelection = document.getElementById('critics-selection');
        if (!criticsSelection) return;

        try {
            const characters = await this.fetchAPI('/characters');

            let html = '';
            characters.forEach(character => {
                const isSelected = this.batchProcessing.selectedCritics.has(character.id);
                html += `
                    <div class="critic-checkbox-item ${isSelected ? 'selected' : ''}"
                         onclick="app.toggleCriticSelection('${character.id}')">
                        <input type="checkbox"
                               class="critic-checkbox"
                               id="critic-${character.id}"
                               ${isSelected ? 'checked' : ''}
                               onchange="app.toggleCriticSelection('${character.id}')">
                        <div class="critic-info">
                            <div class="critic-name">${character.name}</div>
                            <div class="critic-description">${character.description || 'Crítico experto'}</div>
                        </div>
                    </div>
                `;
            });

            criticsSelection.innerHTML = html;

        } catch (error) {
            console.error('Error loading critics:', error);
            criticsSelection.innerHTML = `
                <div class="error-message">
                    <p>❌ Error cargando críticos</p>
                    <p>Por favor recarga la página</p>
                </div>
            `;
        }
    }

    // Toggle critic selection
    toggleCriticSelection(criticId) {
        if (this.batchProcessing.selectedCritics.has(criticId)) {
            this.batchProcessing.selectedCritics.delete(criticId);
        } else {
            this.batchProcessing.selectedCritics.add(criticId);
        }

        // Update UI
        const checkboxItem = document.querySelector(`.critic-checkbox-item[onclick*="${criticId}"]`);
        const checkbox = document.getElementById(`critic-${criticId}`);

        if (checkboxItem && checkbox) {
            const isSelected = this.batchProcessing.selectedCritics.has(criticId);
            checkboxItem.classList.toggle('selected', isSelected);
            checkbox.checked = isSelected;
        }

        this.updateProcessingControls();
        console.log('👥 Selected critics:', Array.from(this.batchProcessing.selectedCritics));
    }

    // Update processing controls
    updateProcessingControls() {
        const startBtn = document.getElementById('start-processing-btn');
        if (startBtn) {
            const canStart = this.cart.size > 0 &&
                           this.batchProcessing.selectedCritics.size > 0 &&
                           !this.batchProcessing.isProcessing;
            startBtn.disabled = !canStart;
        }
    }

    // Start batch processing
    async startBatchProcessing() {
        if (this.cart.size === 0 || this.batchProcessing.selectedCritics.size === 0) {
            this.showMessage('Selecciona contenido y críticos antes de procesar', 'warning');
            return;
        }

        this.batchProcessing.isProcessing = true;
        this.batchProcessing.results = [];
        this.batchProcessing.controller = new AbortController();

        // Update UI
        this.showProgressSection();
        this.hideResultsSection();
        this.updateProcessingControlsForStart();

        const mediaItems = Array.from(this.cart.values());
        const critics = Array.from(this.batchProcessing.selectedCritics);
        const totalOperations = mediaItems.length * critics.length;

        console.log(`🚀 Starting batch processing: ${mediaItems.length} media × ${critics.length} critics = ${totalOperations} operations`);

        // Prepare the request payload
        const requestPayload = {
            media_items: mediaItems,
            selected_critics: critics
        };

        try {
            // Update initial progress
            this.updateProgressDisplay(0, totalOperations, 0, 'Iniciando procesamiento...', null);

            // Call the new batch processing endpoint
            const response = await fetch('/api/generate/cart-batch', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestPayload),
                signal: this.batchProcessing.controller.signal
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Error en el procesamiento');
            }

            const result = await response.json();

            console.log('🎉 Batch processing completed:', result);

            // Process the results
            let completed = 0;
            let errors = 0;

            result.results.forEach(item => {
                if (item.status === 'success') {
                    completed++;
                } else {
                    errors++;
                }

                this.batchProcessing.results.push({
                    media: { title: item.title, tmdb_id: item.tmdb_id },
                    critic: item.critic,
                    status: item.status,
                    result: item.status === 'success' ? { rating: item.rating } : null,
                    error: item.error || item.reason
                });
            });

            // Update final progress
            this.updateProgressDisplay(completed, totalOperations, errors, 'Procesamiento completado', null);

            // Show completion
            this.handleBatchProcessingComplete(completed, errors, totalOperations);

        } catch (error) {
            console.error('❌ Batch processing failed:', error);

            if (error.name === 'AbortError') {
                this.handleBatchProcessingError('Procesamiento cancelado por el usuario');
            } else {
                this.handleBatchProcessingError(error.message);
            }
        }
    }

    // Generate critic for batch processing
    async generateCriticForBatch(tmdbId, criticId) {
        const signal = this.batchProcessing.controller.signal;

        const response = await fetch(`${this.apiBase}/generate/critic/${tmdbId}?character=${encodeURIComponent(criticId)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            signal: signal
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();

        if (!result.success) {
            throw new Error(result.error || 'Generation failed');
        }

        return result;
    }

    // Show progress section
    showProgressSection() {
        const progressSection = document.getElementById('progress-section');
        if (progressSection) {
            progressSection.classList.remove('hidden');
        }
    }

    // Hide progress section
    hideProgressSection() {
        const progressSection = document.getElementById('progress-section');
        if (progressSection) {
            progressSection.classList.add('hidden');
        }
    }

    // Show results section
    showResultsSection() {
        const resultsSection = document.getElementById('results-section');
        if (resultsSection) {
            resultsSection.classList.remove('hidden');
        }
    }

    // Hide results section
    hideResultsSection() {
        const resultsSection = document.getElementById('results-section');
        if (resultsSection) {
            resultsSection.classList.add('hidden');
        }
    }

    // Update processing controls for start
    updateProcessingControlsForStart() {
        const startBtn = document.getElementById('start-processing-btn');
        const cancelBtn = document.getElementById('cancel-processing-btn');

        if (startBtn) {
            startBtn.disabled = true;
            startBtn.style.display = 'none';
        }

        if (cancelBtn) {
            cancelBtn.classList.remove('hidden');
            cancelBtn.disabled = false;
        }
    }

    // Update processing controls for completion
    updateProcessingControlsForCompletion() {
        const startBtn = document.getElementById('start-processing-btn');
        const cancelBtn = document.getElementById('cancel-processing-btn');

        if (startBtn) {
            startBtn.disabled = false;
            startBtn.style.display = 'block';
        }

        if (cancelBtn) {
            cancelBtn.classList.add('hidden');
        }
    }

    // Update progress display
    updateProgressDisplay(completed, total, errors, currentMedia, currentCritic) {
        const percentage = total > 0 ? (completed / total) * 100 : 0;
        const remaining = total - completed;

        // Update progress bar
        const progressFill = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');
        if (progressFill && progressText) {
            progressFill.style.width = `${percentage}%`;
            progressText.textContent = `${Math.round(percentage)}%`;
        }

        // Update status
        const statusElement = document.getElementById('processing-status');
        if (statusElement) {
            if (currentMedia && currentCritic) {
                statusElement.textContent = `Procesando: ${currentMedia} con ${currentCritic}`;
            } else {
                statusElement.textContent = `Procesando... ${completed}/${total} completadas`;
            }
        }

        // Update current item
        const currentElement = document.getElementById('processing-current');
        if (currentElement) {
            if (currentMedia && currentCritic) {
                currentElement.textContent = `🎬 "${currentMedia}" por ${currentCritic}`;
            } else {
                currentElement.textContent = 'Preparando siguiente elemento...';
            }
        }

        // Update statistics
        document.getElementById('completed-count').textContent = completed;
        document.getElementById('error-count').textContent = errors;
        document.getElementById('remaining-count').textContent = remaining;
    }

    // Cancel batch processing
    cancelBatchProcessing() {
        if (this.batchProcessing.controller) {
            this.batchProcessing.controller.abort();
        }

        this.batchProcessing.isProcessing = false;

        // Update UI
        const statusElement = document.getElementById('processing-status');
        if (statusElement) {
            statusElement.textContent = '❌ Procesamiento cancelado por el usuario';
        }

        const currentElement = document.getElementById('processing-current');
        if (currentElement) {
            currentElement.textContent = 'Operación cancelada';
        }

        this.updateProcessingControlsForCompletion();
        this.showMessage('Procesamiento cancelado', 'warning');

        console.log('🛑 Batch processing cancelled by user');
    }

    // Handle batch processing completion
    handleBatchProcessingComplete(completed, errors, total) {
        this.batchProcessing.isProcessing = false;

        console.log(`🎉 Batch processing completed: ${completed} success, ${errors} errors of ${total} total`);

        // Update final progress
        const statusElement = document.getElementById('processing-status');
        if (statusElement) {
            statusElement.textContent = `✅ Procesamiento completado: ${completed}/${total} exitosas`;
        }

        const currentElement = document.getElementById('processing-current');
        if (currentElement) {
            currentElement.textContent = `¡Todas las operaciones han terminado!`;
        }

        // Show results
        this.renderBatchResults();
        this.showResultsSection();
        this.updateProcessingControlsForCompletion();

        // Show success message
        this.showMessage(`🎉 Procesamiento completado: ${completed} críticas generadas${errors > 0 ? `, ${errors} errores` : ''}`, 'success');
    }

    // Handle batch processing error
    handleBatchProcessingError(errorMessage) {
        this.batchProcessing.isProcessing = false;

        console.error(`❌ Batch processing failed: ${errorMessage}`);

        // Update UI
        const statusElement = document.getElementById('processing-status');
        if (statusElement) {
            statusElement.textContent = '❌ Procesamiento fallido';
        }

        const currentElement = document.getElementById('processing-current');
        if (currentElement) {
            currentElement.textContent = `Error: ${errorMessage}`;
        }

        this.updateProcessingControlsForCompletion();
        this.showMessage(`Error en procesamiento: ${errorMessage}`, 'error');
    }

    // Render batch results
    renderBatchResults() {
        const resultsSummary = document.getElementById('results-summary');
        const resultsList = document.getElementById('results-list');

        if (!resultsSummary || !resultsList) return;

        const successful = this.batchProcessing.results.filter(r => r.status === 'success').length;
        const failed = this.batchProcessing.results.filter(r => r.status === 'error').length;
        const total = this.batchProcessing.results.length;

        // Summary
        resultsSummary.innerHTML = `
            <div class="results-stats">
                <div class="result-stat success">
                    <div class="stat-number">${successful}</div>
                    <div class="stat-label">Exitosas</div>
                </div>
                <div class="result-stat error">
                    <div class="stat-number">${failed}</div>
                    <div class="stat-label">Errores</div>
                </div>
                <div class="result-stat total">
                    <div class="stat-number">${total}</div>
                    <div class="stat-label">Total</div>
                </div>
            </div>
        `;

        // Results list
        let html = '';
        this.batchProcessing.results.forEach(result => {
            html += `
                <div class="result-item ${result.status}">
                    <div class="result-item-title">
                        ${result.media.title} - ${result.critic}
                    </div>
                    <div class="result-item-status">
                        ${result.status === 'success' ? '✅ Crítica generada exitosamente' : `❌ Error: ${result.error}`}
                    </div>
                </div>
            `;
        });

        resultsList.innerHTML = html;
    }

    // Reset checkout
    resetCheckout() {
        // Clear cart
        this.clearCart();

        // Reset batch processing state
        this.batchProcessing.selectedCritics.clear();
        this.batchProcessing.results = [];
        this.batchProcessing.isProcessing = false;

        // Hide sections
        this.hideProgressSection();
        this.hideResultsSection();

        // Go back to media view
        this.showView('media');

        this.showMessage('🔄 Nueva selección iniciada', 'info');
        console.log('🔄 Checkout reset completed');
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new ParodyCriticsApp();
    // Also assign to global scope for onclick handlers
    globalThis.app = window.app;
    console.log('🎭 Parody Critics App initialized and available globally:', window.app);
});