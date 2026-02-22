/**
 * 🎭 Parody Critics - Frontend Application
 * =======================================
 * JavaScript application for the Parody Critics web interface
 */

class ParodyCriticsApp {
    constructor() {
        this.apiBase = 'http://localhost:8888/api';
        this.currentView = 'home';
        this.selectedCharacter = null;
        this.selectedMedia = null;

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

    async loadMediaData() {
        const mediaGrid = document.getElementById('media-grid');
        mediaGrid.innerHTML = '<div class="loading">🎬 Cargando películas y series...</div>';

        try {
            const typeFilter = document.getElementById('type-filter').value;
            const criticsFilter = document.getElementById('critics-filter').value;

            let url = '/media?limit=50';
            if (typeFilter) url += `&type=${typeFilter}`;
            if (criticsFilter) url += `&has_critics=${criticsFilter}`;

            const media = await this.fetchAPI(url);
            this.renderMediaGrid(media);

            // Setup filters
            this.setupMediaFilters();

        } catch (error) {
            console.error('Failed to load media:', error);
            mediaGrid.innerHTML = '<div class="loading">❌ Error loading media</div>';
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
    }

    renderMediaGrid(media) {
        const mediaGrid = document.getElementById('media-grid');

        if (!media || media.length === 0) {
            mediaGrid.innerHTML = '<div class="loading">📽️ No media found</div>';
            return;
        }

        mediaGrid.innerHTML = media.map(item => `
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
            const media = await this.fetchAPI('/media?limit=100');

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
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new ParodyCriticsApp();
});