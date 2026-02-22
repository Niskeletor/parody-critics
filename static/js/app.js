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
            <div class="media-card" onclick="app.showMediaDetails('${item.tmdb_id}')">
                <div class="media-card-header">
                    <h3 class="media-title">${item.title}</h3>
                    <div class="media-meta">
                        <span class="media-type ${item.type}">${item.type}</span>
                        <span>${item.year || 'Unknown'}</span>
                        ${item.vote_average ? `<div class="rating-badge">⭐ ${item.vote_average}</div>` : ''}
                    </div>
                </div>
                <div class="media-card-body">
                    <p class="media-description">${item.overview || 'No description available'}</p>
                    <div class="media-genres">
                        ${(item.genres || []).map(genre => `<span class="genre-tag">${genre}</span>`).join('')}
                    </div>
                </div>
                <div class="media-card-footer">
                    <span class="critics-count ${item.has_critics ? 'has-critics' : ''}">
                        ${item.critics_count > 0 ? `📝 ${item.critics_count} críticas` : '📝 Sin críticas'}
                    </span>
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
                        <div class="media-card-compact" onclick="app.showMediaDetails('${item.tmdb_id}')">
                            <div class="compact-header">
                                <h4 class="compact-title">${item.title}</h4>
                                <span class="compact-meta">${item.year || 'N/A'} • ${item.type}</span>
                            </div>
                            <div class="compact-footer">
                                ${item.vote_average ? `<span class="compact-rating">⭐ ${item.vote_average}</span>` : ''}
                                <span class="compact-critics ${item.has_critics ? 'has-critics' : ''}">
                                    ${item.critics_count > 0 ? `📝 ${item.critics_count}` : '📝 0'}
                                </span>
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

        // Load media for selection
        await this.loadMediaForGeneration();

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

    async loadMediaForGeneration() {
        const mediaSelect = document.getElementById('media-select');

        try {
            const media = await this.fetchAPI('/media?limit=200');

            mediaSelect.innerHTML = '<option value="">Selecciona una película o serie...</option>' +
                media.map(item => `
                    <option value="${item.tmdb_id}" data-title="${item.title}" data-type="${item.type}">
                        ${item.title} (${item.year}) - ${item.type}
                    </option>
                `).join('');

        } catch (error) {
            console.error('Failed to load media for generation:', error);
            mediaSelect.innerHTML = '<option value="">Error loading media</option>';
        }
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
        const mediaSelect = document.getElementById('media-select');
        const generateBtn = document.getElementById('generate-btn');

        mediaSelect.addEventListener('change', (e) => {
            this.selectedMedia = e.target.value;
            this.updateGenerateButton();
        });

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
                `/generate/critic/${this.selectedMedia}?character=${encodeURIComponent(characterName)}`,
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
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new ParodyCriticsApp();
    // Also assign to global scope for onclick handlers
    globalThis.app = window.app;
    console.log('🎭 Parody Critics App initialized and available globally:', window.app);
});