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
        letter: '',
      },
    };

    // 🔍 Search state
    this._searchDebounce = null;
    this.isSearchActive = false;

    // 🛒 E-commerce Cart System properties
    this.cart = new Map(); // Map of tmdb_id -> media object
    this.isCartOpen = false;
    this.batchProcessing = {
      isProcessing: false,
      selectedCritics: new Set(),
      results: [],
      controller: null,
    };

    // 🗄️ Data Cache for performance
    this.dataCache = {
      characters: null,
      media: null,
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
    navButtons.forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const view = e.target.dataset.view;
        this.showView(view);

        // Update active nav button
        navButtons.forEach((b) => b.classList.remove('active'));
        e.target.classList.add('active');
      });
    });

    // CTA buttons
    const ctaButtons = document.querySelectorAll('[data-view]');
    ctaButtons.forEach((btn) => {
      if (!btn.classList.contains('nav-btn')) {
        btn.addEventListener('click', (e) => {
          const view = e.target.dataset.view;
          this.showView(view);

          // Update nav
          const navBtn = document.querySelector(`.nav-btn[data-view="${view}"]`);
          if (navBtn) {
            navButtons.forEach((b) => b.classList.remove('active'));
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

    // 🛒 Cart checkout button event listener
    const checkoutButton = document.getElementById('cart-checkout-btn');
    if (checkoutButton) {
      checkoutButton.addEventListener('click', async (e) => {
        e.preventDefault();
        e.stopPropagation();
        console.log('✨ Checkout button clicked');

        if (!checkoutButton.disabled) {
          try {
            // VISUAL DEBUG - Show user what's happening
            this.showMessage('🔄 Procesando checkout...', 'info');

            await this.proceedToCheckout();

            // VISUAL CONFIRMATION - Check if checkout is actually visible
            const checkoutView = document.getElementById('checkout-view');
            const isVisible = checkoutView && checkoutView.classList.contains('active');

            if (isVisible) {
              this.showMessage('✅ Checkout cargado correctamente', 'success');
              console.log('✅ VISUAL DEBUG: Checkout view is active and should be visible');
            } else {
              console.error(
                '❌ VISUAL DEBUG: Checkout view is NOT active after proceedToCheckout()'
              );
              this.showMessage('⚠️ Problema cargando checkout - activando debug', 'warning');
              this.enableDebug(); // Auto-enable debug when there's a problem
              // Don't fallback immediately, let user see debug info
              setTimeout(() => {
                this.showView('media');
              }, 5000);
            }
          } catch (error) {
            console.error('❌ Checkout failed:', error);
            this.showMessage('Error en checkout: ' + error.message, 'error');
            this.showView('media'); // Fallback to media view
          }
        } else {
          console.log('⚠️ Checkout button is disabled');
          this.showMessage('⚠️ Carrito vacío - agrega contenido primero', 'warning');
        }
      });
      console.log('✨ Checkout button event listener added');
    } else {
      console.error('❌ Checkout button not found during setup');
    }
  }

  showView(viewName) {
    // 🔄 RESET: Remove ultra-nuclear CSS from checkout when leaving it
    if (this.currentView === 'checkout' && viewName !== 'checkout') {
      this.resetCheckoutStyles();
    }

    const targetView = document.getElementById(`${viewName}-view`);
    if (!targetView) return;

    // Animate out the current active view, then animate in the new one
    const outgoing = document.querySelector('.view.active');
    if (outgoing && outgoing !== targetView) {
      outgoing.classList.add('leaving');
      setTimeout(() => outgoing.classList.remove('active', 'leaving'), 150);
    } else if (!outgoing) {
      document.querySelectorAll('.view').forEach((v) => v.classList.remove('active'));
    }

    targetView.classList.add('active');
    this.currentView = viewName;

    // 🔥 NUCLEAR CSS FIX: Force checkout view to be visible
    if (viewName === 'checkout') {
      this.forceCheckoutVisible(targetView);
    }

    // Update navigation buttons
    const navButtons = document.querySelectorAll('.nav-btn');
    navButtons.forEach((btn) => {
      if (btn.dataset.view === viewName) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    // Load view-specific data
    this.loadViewData(viewName);
  }

  // 🔥 NUCLEAR CSS FIX: Force checkout view to be visible
  // This method applies ULTRA-AGGRESSIVE CSS styling to make checkout view visible
  // Solves the positioning issue where checkout appears at top: 1753px
  forceCheckoutVisible(checkoutView) {
    console.log('🔥 Applying ULTRA-NUCLEAR CSS fix to make checkout visible...');

    // ULTRA-AGGRESSIVE CSS - Override EVERYTHING
    checkoutView.style.setProperty('position', 'fixed', 'important');
    checkoutView.style.setProperty('top', '0px', 'important');
    checkoutView.style.setProperty('left', '0px', 'important');
    checkoutView.style.setProperty('width', '100vw', 'important');
    checkoutView.style.setProperty('height', '100vh', 'important');
    checkoutView.style.setProperty('z-index', '999999', 'important');
    checkoutView.style.setProperty('background-color', '#121212', 'important');
    checkoutView.style.setProperty('overflow', 'auto', 'important');
    checkoutView.style.setProperty('display', 'block', 'important');
    checkoutView.style.setProperty('visibility', 'visible', 'important');
    checkoutView.style.setProperty('opacity', '1', 'important');
    checkoutView.style.setProperty('transform', 'none', 'important');
    checkoutView.style.setProperty('max-width', 'none', 'important');
    checkoutView.style.setProperty('max-height', 'none', 'important');
    checkoutView.style.setProperty('margin', '0', 'important');
    checkoutView.style.setProperty('padding', '20px', 'important');

    // Remove any conflicting classes
    checkoutView.classList.remove('hidden');

    // Add a timeout to ensure DOM is ready
    setTimeout(() => {
      checkoutView.scrollIntoView({ behavior: 'instant', block: 'start' });
      console.log('🚀 Scrolled checkout into view');
    }, 100);

    console.log('💥 ULTRA-NUCLEAR CSS fix applied - checkout MUST be visible now');
  }

  // 🔄 RESET: Remove ultra-nuclear CSS styles from checkout
  resetCheckoutStyles() {
    const checkoutView = document.getElementById('checkout-view');
    if (checkoutView) {
      console.log('🔄 Resetting ultra-nuclear CSS styles from checkout...');

      // Remove all the ultra-nuclear styles
      checkoutView.style.removeProperty('position');
      checkoutView.style.removeProperty('top');
      checkoutView.style.removeProperty('left');
      checkoutView.style.removeProperty('width');
      checkoutView.style.removeProperty('height');
      checkoutView.style.removeProperty('z-index');
      checkoutView.style.removeProperty('background-color');
      checkoutView.style.removeProperty('overflow');
      checkoutView.style.removeProperty('display');
      checkoutView.style.removeProperty('visibility');
      checkoutView.style.removeProperty('opacity');
      checkoutView.style.removeProperty('transform');
      checkoutView.style.removeProperty('max-width');
      checkoutView.style.removeProperty('max-height');
      checkoutView.style.removeProperty('margin');
      checkoutView.style.removeProperty('padding');

      console.log('✅ Checkout styles reset - back to normal CSS');
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
      case 'status':
        await this.loadStatusData();
        break;
      case 'checkout':
        // 🛒 Load checkout data
        await this.loadCheckoutData();
        break;
      case 'characters':
        // 🎭 Load characters management data
        await this.loadCharactersData();
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
      this.showError(t('error.load_data', { error: error.message }));
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
        statusElement.textContent = t('status.operative');
        statusElement.style.color = 'var(--success)';
      } else {
        statusElement.textContent = t('status.issues');
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
      mediaGrid.innerHTML = `<div class="loading">${t('media.loading_all')}</div>`;
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

      const page = Math.floor(this.mediaState.currentOffset / this.mediaState.limit) + 1;
      let url = `/media?page=${page}&page_size=${this.mediaState.limit}`;
      if (typeFilter) url += `&type=${typeFilter}`;
      if (criticsFilter) url += `&has_critics=${criticsFilter}`;
      if (this.mediaState.currentFilters.letter)
        url += `&start_letter=${this.mediaState.currentFilters.letter}`;

      const response = await this.fetchAPI(url);
      const newMedia = response.items ?? response; // backwards compat

      if (newMedia.length === 0) {
        this.mediaState.hasMore = false;
        if (this.mediaState.currentData.length === 0) {
          mediaGrid.innerHTML = `<div class="loading">${t('media.not_found')}</div>`;
        }
      } else {
        // Add new media to current data
        this.mediaState.currentData = [...this.mediaState.currentData, ...newMedia];
        this.mediaState.currentOffset += newMedia.length;
        this.mediaState.hasMore = response.has_next ?? newMedia.length >= this.mediaState.limit;

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
        mediaGrid.innerHTML = `<div class="loading">${t('media.error_loading')}</div>`;
      }
    } finally {
      this.mediaState.isLoading = false;
    }
  }

  setupMediaFilters() {
    const typeFilter = document.getElementById('type-filter');
    const criticsFilter = document.getElementById('critics-filter');

    [typeFilter, criticsFilter].forEach((filter) => {
      filter.addEventListener('change', () => {
        this.loadMediaData();
      });
    });

    // Generate alphabet navigation
    this.generateAlphabetNavigation();
  }

  onSearchInput(value) {
    clearTimeout(this._searchDebounce);
    const q = value.trim();

    if (q.length === 0) {
      this.isSearchActive = false;
      this._setFiltersDisabled(false);
      this.loadMediaData();
      return;
    }

    if (q.length < 2) return;

    this._searchDebounce = setTimeout(() => this._runSearch(q), 300);
  }

  async _runSearch(q) {
    this.isSearchActive = true;
    this._setFiltersDisabled(true);

    const mediaGrid = document.getElementById('media-grid');
    mediaGrid.innerHTML = `<div class="loading">🔍 Buscando "${q}"…</div>`;

    try {
      const results = await this.fetchAPI(`/media/search?query=${encodeURIComponent(q)}&limit=20`);
      if (results.length === 0) {
        mediaGrid.innerHTML = `<div class="loading">Sin resultados para <em>"${q}"</em></div>`;
      } else {
        this.renderMediaGrid(results);
      }
    } catch {
      mediaGrid.innerHTML = `<div class="loading">Error al buscar. Inténtalo de nuevo.</div>`;
    }
  }

  _setFiltersDisabled(disabled) {
    ['type-filter', 'critics-filter', 'group-toggle'].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.disabled = disabled;
    });
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

    // Load more when user is 300px from bottom (not during search)
    if (!this.isSearchActive && scrollTop + windowHeight >= documentHeight - 300) {
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
    return media
      .map((item) => {
        const posterSrc = item.jellyfin_id
          ? `/api/poster/${item.jellyfin_id}`
          : '/static/images/parody_critics_logo.png';
        return `
            <div class="media-card" data-tmdb-id="${item.tmdb_id}">
                <!-- 🛒 E-commerce Selection Checkbox -->
                <div class="media-card-select" onclick="app.toggleMediaSelection({
                    tmdb_id: '${item.tmdb_id}',
                    title: '${item.title.replace(/'/g, "\\'")}',
                    year: '${item.year || 'N/A'}',
                    type: '${item.type}',
                    poster_url: '${posterSrc}',
                    has_critics: ${item.has_critics || false}
                })">
                </div>

                <img class="media-card-poster" src="${posterSrc || '/static/images/parody_critics_logo.png'}" alt="${item.title.replace(/"/g, '&quot;')}" onerror="this.src='/static/images/parody_critics_logo.png'">

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
                        ${(item.genres || []).map((genre) => `<span class="genre-tag">${genre}</span>`).join('')}
                    </div>
                </div>
                <div class="media-card-footer">
                    <span class="critics-count ${item.has_critics ? 'has-critics' : ''}">
                        ${item.critics_count > 0 ? `📝 ${item.critics_count} críticas` : '📝 Sin críticas'}
                    </span>
                </div>
            </div>
          `;
      })
      .join('');
  }

  renderGroupedView(media) {
    const groups = this.groupMediaByPattern(media);

    return groups
      .map(
        (group) => `
            <div class="media-group">
                <div class="group-header">
                    <h3 class="group-title">${group.name}</h3>
                    <span class="group-count">${group.count} elementos</span>
                </div>
                <div class="group-content">
                    ${group.items
                      .map(
                        (item) => `
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
                            </div>
                        </div>
                    `
                      )
                      .join('')}
                </div>
            </div>
        `
      )
      .join('');
  }

  // Group media by detected patterns in titles
  groupMediaByPattern(media) {
    const groups = new Map();

    media.forEach((item) => {
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
        count: items.length,
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
    toggleButton.textContent = this.mediaState.isGroupedView
      ? t('media.btn_list')
      : t('media.btn_grouped');

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
    document.querySelectorAll('.letter-btn').forEach((btn) => btn.classList.remove('active'));
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
    html += `<button class="letter-btn active" onclick="app.filterByLetter('')" data-letter="">${t('media.alphabet_all')}</button>`;

    // Numbers button
    html += `<button class="letter-btn" onclick="app.filterByLetter('0-9')" data-letter="0-9">#</button>`;

    // Alphabet buttons
    alphabet.forEach((letter) => {
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

    return data.filter((item) => {
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
    criticsList.innerHTML = `<div class="loading">${t('critics.loading')}</div>`;

    try {
      // Get all media with critics
      const response = await this.fetchAPI('/media?has_critics=true&page_size=20');
      const media = response.items ?? response;

      if (!media || media.length === 0) {
        criticsList.innerHTML = `<div class="loading">${t('critics.none_found')}</div>`;
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
      criticsList.innerHTML = `<div class="loading">${t('critics.error_loading')}</div>`;
    }
  }

  renderCriticsList(criticsData) {
    const criticsList = document.getElementById('critics-list');

    if (!criticsData || criticsData.length === 0) {
      criticsList.innerHTML = `<div class="loading">${t('critics.none_available')}</div>`;
      return;
    }

    let html = '';

    criticsData.forEach(({ media, critics }) => {
      const bannerSrc = media.jellyfin_id
        ? `/api/banner/${media.jellyfin_id}`
        : '/static/images/parody_critics_logo.png';
      html += `<div class="media-critics-section">
                <div class="media-section-banner">
                  <img class="media-section-banner-img" src="${bannerSrc}" alt="${media.title.replace(/"/g, '&quot;')}" onerror="this.src='/static/images/parody_critics_logo.png'">
                  <div class="media-section-banner-overlay">
                    <h3 class="media-section-title">${media.title} <span class="media-section-year">(${media.year})</span></h3>
                  </div>
                </div>`;

      Object.values(critics).forEach((critic) => {
        html += this.renderCriticCard(critic, media);
      });

      html += '</div>';
    });

    criticsList.innerHTML = html;
  }

  renderCriticCard(critic, media = null, tmdbId = null) {
    const deleteBtn =
      tmdbId && critic.critic_id
        ? `
            <button class="btn-icon btn-danger" style="font-size:0.8rem; padding:0.3rem 0.6rem;"
                onclick="app.deleteSingleCritic(${critic.critic_id}, '${tmdbId}', '${critic.author}')"
                title="Eliminar esta crítica">🗑️</button>`
        : '';

    const rating = parseFloat(critic.rating) || 0;
    const ratingClass = rating >= 7 ? 'rating-high' : rating >= 4 ? 'rating-mid' : 'rating-low';

    return `
            <div class="critic-card" id="critic-card-${critic.critic_id || ''}">
                <div class="critic-header">
                    <div class="critic-character">
                        <span class="critic-character-emoji">${critic.emoji || '🎭'}</span>
                        <div class="critic-character-info">
                            <h3>${critic.author}</h3>
                            <span class="personality">${(critic.personality || '').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}</span>
                        </div>
                    </div>
                    <div style="display:flex; align-items:center; gap:0.5rem;">
                        <div class="critic-rating ${ratingClass}">${critic.rating}/10</div>
                        ${deleteBtn}
                    </div>
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

  async loadCharacters() {
    const characterSelector = document.getElementById('character-selector');

    try {
      const characters = await this.fetchAPI('/characters');

      characterSelector.innerHTML = characters
        .map(
          (char) => `
                <div class="character-card ${char.id}" onclick="app.selectCharacter('${char.id}')">
                    <span class="character-emoji">${char.emoji}</span>
                    <h3 class="character-name">${char.name}</h3>
                    <p class="character-description">${char.description}</p>
                </div>
            `
        )
        .join('');
    } catch (error) {
      console.error('Failed to load characters:', error);
      characterSelector.innerHTML = `<div class="loading">${t('characters.error_loading')}</div>`;
    }
  }

  selectCharacter(characterId) {
    // Remove previous selection
    document.querySelectorAll('.character-card').forEach((card) => {
      card.classList.remove('selected');
    });

    // Select new character
    const characterCard = document.querySelector(`.character-card.${characterId}`);
    if (characterCard) {
      characterCard.classList.add('selected');
      this.selectedCharacter = characterId;
    }
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
      healthStatus.innerHTML = `<div class="loading">${t('status.error_health')}</div>`;
      llmStatus.innerHTML = `<div class="loading">${t('status.error_llm')}</div>`;
      dbStats.innerHTML = `<div class="loading">${t('status.error_db')}</div>`;
    }
  }

  exportDatabase() {
    const status = document.getElementById('db-export-status');
    const btn = document.getElementById('db-export-btn');
    if (btn) btn.disabled = true;
    if (status) status.textContent = 'Preparando…';

    const a = document.createElement('a');
    a.href = '/api/admin/db/export';
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    // Reset feedback after a moment
    setTimeout(() => {
      if (btn) btn.disabled = false;
      if (status) status.textContent = '';
    }, 3000);
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

    const tmdbId = criticsData.tmdb_id;
    const hasAnyCritics = criticsData.critics && Object.keys(criticsData.critics).length > 0;

    let html = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
                <h2 style="margin:0;">📝 Críticas de "${criticsData.title}" (${criticsData.year})</h2>
                ${
                  hasAnyCritics
                    ? `
                <button class="btn-danger" style="font-size:0.85rem; padding:0.4rem 0.9rem;"
                    onclick="app.deleteAllMediaCritics('${tmdbId}', '${criticsData.title.replace(/'/g, "\\'")}')">
                    🗑️ Eliminar todas
                </button>`
                    : ''
                }
            </div>
            <div class="modal-critics">
        `;

    if (!hasAnyCritics) {
      html += `
                <div style="text-align: center; padding: 2rem; color: var(--text-secondary);">
                    <p>📝 No hay críticas disponibles para este medio.</p>
                    <p>¡Usa el generador para crear la primera crítica!</p>
                </div>
            `;
    } else {
      Object.values(criticsData.critics).forEach((critic) => {
        html += this.renderCriticCard(critic, null, tmdbId);
      });
    }

    html += '</div>';
    modalBody.innerHTML = html;
    modal.classList.remove('hidden');
    modal.style.display = '';
    modal.style.visibility = '';
    modal.style.opacity = '';
    modal.style.pointerEvents = '';
    modal.style.zIndex = '';

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
        minute: '2-digit',
      });
    } catch (error) {
      return 'Invalid date';
    }
  }

  showMessage(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => toast.remove(), 5000);
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
          'Content-Type': 'application/json',
        },
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
      this.showError(t('import.error_start'));
    }
  }

  async startEnrichAll() {
    const btn = document.getElementById('enrich-btn');
    const originalText = btn.innerHTML;

    try {
      const status = await this.fetchAPI('/enrich/status');
      if (status.pending === 0) {
        this.showMessage(
          `✅ Todo el catálogo ya está enriquecido (${status.enriched} items)`,
          'success'
        );
        return;
      }

      btn.disabled = true;
      btn.innerHTML = t('enrich.btn_starting');

      const result = await this.fetchAPI('/enrich/all', 'POST');

      btn.innerHTML = originalText;
      btn.disabled = false;

      if (result.success && result.session_id) {
        this.showEnrichProgress(result.session_id);
      } else if (result.success && !result.session_id) {
        this.showMessage(result.message, 'success');
      }
    } catch (error) {
      console.error('Enrich failed:', error);
      this.showError(t('enrich.error_start'));
      btn.disabled = false;
      btn.innerHTML = originalText;
    }
  }

  showEnrichProgress(sessionId) {
    let modal = document.getElementById('enrich-progress-modal');
    if (!modal) {
      modal = this.createEnrichProgressModal(sessionId);
      document.body.appendChild(modal);
    }
    modal.classList.remove('hidden');
    modal.style.display = '';
    this.connectToEnrichProgress(sessionId);
  }

  createEnrichProgressModal(sessionId) {
    this._ensureProgressModalStyles();
    const modal = document.createElement('div');
    modal.id = 'enrich-progress-modal';
    modal.className = 'import-progress-modal';
    modal.innerHTML = `
      <div class="import-progress-content">
        <div class="import-progress-header">
          <h3>🔍 Enriching Media Context</h3>
          <button class="close-import-btn" onclick="app.closeEnrichProgressModal()">&times;</button>
        </div>
        <div class="import-progress-body">
          <div class="progress-container">
            <div class="progress-bar">
              <div class="progress-fill" id="enrich-progress-fill"></div>
            </div>
            <div class="progress-text">
              <span id="enrich-percentage">0%</span>
              <span id="enrich-status">Starting...</span>
            </div>
          </div>
          <div class="import-stats">
            <div class="stat-item">
              <span class="stat-label">Total Items:</span>
              <span id="enrich-total-items">-</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Enriched:</span>
              <span id="enrich-processed-items" class="stat-success">0</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Errors:</span>
              <span id="enrich-errors" class="stat-error">0</span>
            </div>
          </div>
          <div class="current-operation">
            <strong>Current:</strong>
            <span id="enrich-current-item">Initializing...</span>
          </div>
          <div class="import-actions">
            <button id="cancel-enrich-btn" class="btn-cancel" onclick="app.cancelEnrich('${sessionId}')">
              Cancel Enrichment
            </button>
          </div>
          <div class="import-log" id="enrich-log">
            <div class="log-entry">🔍 Enrichment session started...</div>
          </div>
        </div>
      </div>
    `;
    return modal;
  }

  connectToEnrichProgress(sessionId) {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/import-progress/${sessionId}`;
    console.log(`🔌 Connecting to enrichment WebSocket: ${wsUrl}`);

    this.enrichWebSocket = new WebSocket(wsUrl);

    this.enrichWebSocket.onopen = () => {
      console.log('✅ Enrichment WebSocket connected');
      this.addEnrichLogEntry('🔌 Connected to progress stream');
    };

    this.enrichWebSocket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        switch (message.type) {
          case 'import_progress':
            this.updateEnrichProgress(message.data);
            break;
          case 'import_completed':
            this.handleEnrichCompleted(message.data);
            break;
          case 'import_error':
            this.handleEnrichError(message.data);
            break;
          case 'import_cancelled':
            this.handleEnrichCancelled(message.data);
            break;
        }
      } catch (error) {
        console.error('❌ Error parsing enrichment WebSocket message:', error);
      }
    };

    this.enrichWebSocket.onclose = () => {
      this.addEnrichLogEntry('🔌 Connection closed');
    };

    this.enrichWebSocket.onerror = () => {
      this.addEnrichLogEntry('❌ Connection error');
    };

    this.enrichPingInterval = setInterval(() => {
      if (this.enrichWebSocket && this.enrichWebSocket.readyState === WebSocket.OPEN) {
        this.enrichWebSocket.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000);
  }

  updateEnrichProgress(data) {
    const fill = document.getElementById('enrich-progress-fill');
    if (fill) fill.style.width = `${data.percentage}%`;
    const pct = document.getElementById('enrich-percentage');
    if (pct) pct.textContent = `${Math.round(data.percentage)}%`;
    const st = document.getElementById('enrich-status');
    if (st) st.textContent = data.status;
    const total = document.getElementById('enrich-total-items');
    if (total) total.textContent = data.total_items;
    const processed = document.getElementById('enrich-processed-items');
    if (processed) processed.textContent = data.processed_items;
    const errors = document.getElementById('enrich-errors');
    if (errors) errors.textContent = data.errors;
    const current = document.getElementById('enrich-current-item');
    if (current) current.textContent = data.current_item || t('import.processing');
    if (data.current_item) {
      this.addEnrichLogEntry(`📄 Enriching: ${data.current_item}`);
    }
  }

  handleEnrichCompleted(data) {
    const fill = document.getElementById('enrich-progress-fill');
    if (fill) {
      fill.style.width = '100%';
      fill.classList.add('completed');
    }
    const content = document.querySelector('#enrich-progress-modal .import-progress-content');
    if (content) content.classList.add('import-success');
    const pct = document.getElementById('enrich-percentage');
    if (pct) pct.textContent = '100%';
    const st = document.getElementById('enrich-status');
    if (st) st.textContent = t('enrich.completed');
    const current = document.getElementById('enrich-current-item');
    if (current) current.textContent = t('enrich.all_done');

    this.addEnrichLogEntry('✅ Enrichment completed successfully!');
    this.addEnrichLogEntry(`📊 Final: ${data.processed_items} enriched, ${data.errors} errors`);

    const cancelBtn = document.getElementById('cancel-enrich-btn');
    if (cancelBtn) cancelBtn.style.display = 'none';

    this.closeEnrichWebSocket();
    this.showMessage(
      `✅ Enriquecimiento completo — ${data.processed_items} items procesados`,
      'success'
    );
  }

  handleEnrichError(data) {
    const fill = document.getElementById('enrich-progress-fill');
    if (fill) fill.classList.add('import-error');
    const content = document.querySelector('#enrich-progress-modal .import-progress-content');
    if (content) content.classList.add('import-fail');
    const st = document.getElementById('enrich-status');
    if (st) st.textContent = t('enrich.failed');
    const current = document.getElementById('enrich-current-item');
    if (current) current.textContent = t('enrich.error_occurred');

    this.addEnrichLogEntry(
      `❌ Enrichment failed: ${data.error_messages?.join(', ') || 'Unknown error'}`
    );

    const cancelBtn = document.getElementById('cancel-enrich-btn');
    if (cancelBtn) cancelBtn.style.display = 'none';

    this.closeEnrichWebSocket();
    this.showError(t('enrich.error_failed'));
  }

  handleEnrichCancelled(data) {
    const st = document.getElementById('enrich-status');
    if (st) st.textContent = t('enrich.cancelled');
    const current = document.getElementById('enrich-current-item');
    if (current) current.textContent = t('enrich.was_cancelled');

    this.addEnrichLogEntry('🛑 Enrichment cancelled by user');

    const cancelBtn = document.getElementById('cancel-enrich-btn');
    if (cancelBtn) cancelBtn.style.display = 'none';

    this.closeEnrichWebSocket();
    this.showMessage('Enrichment was cancelled.', 'warning');
  }

  async cancelEnrich(sessionId) {
    try {
      const response = await fetch(`${this.apiBase}/enrich/cancel/${sessionId}`, {
        method: 'POST',
      });
      const data = await response.json();
      if (data.success) {
        this.addEnrichLogEntry('🛑 Cancellation requested...');
      } else {
        throw new Error('Failed to cancel enrichment');
      }
    } catch (error) {
      console.error('❌ Failed to cancel enrichment:', error);
      this.showError(t('enrich.error_cancel'));
    }
  }

  addEnrichLogEntry(message) {
    const logContainer = document.getElementById('enrich-log');
    if (logContainer) {
      const entry = document.createElement('div');
      entry.className = 'log-entry';
      entry.textContent = `${new Date().toLocaleTimeString()} - ${message}`;
      logContainer.appendChild(entry);
      logContainer.scrollTop = logContainer.scrollHeight;
      const entries = logContainer.children;
      if (entries.length > 100) {
        logContainer.removeChild(entries[0]);
      }
    }
  }

  closeEnrichProgressModal() {
    const modal = document.getElementById('enrich-progress-modal');
    if (modal) {
      modal.classList.add('hidden');
      modal.style.display = 'none';
    }
    this.closeEnrichWebSocket();
  }

  closeEnrichWebSocket() {
    if (this.enrichWebSocket) {
      this.enrichWebSocket.close();
      this.enrichWebSocket = null;
    }
    if (this.enrichPingInterval) {
      clearInterval(this.enrichPingInterval);
      this.enrichPingInterval = null;
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
                    <button class="close-import-btn" onclick="app.closeImportProgressModal()">&times;</button>
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

    this._ensureProgressModalStyles();
    return modal;
  }

  _ensureProgressModalStyles() {
    if (document.getElementById('_progress-modal-styles')) return;
    const style = document.createElement('style');
    style.id = '_progress-modal-styles';
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

            .progress-fill.completed::after {
                display: none;
            }

            .progress-fill.completed {
                background: linear-gradient(90deg, #22c55e, #16a34a);
                transition: width 0.3s ease, background 0.6s ease;
            }

            .import-progress-content.import-success {
                border: 2px solid #22c55e;
                box-shadow: 0 0 30px rgba(34, 197, 94, 0.25);
                transition: box-shadow 0.5s ease, border-color 0.5s ease;
            }

            .progress-fill.import-error::after {
                display: none;
            }

            .progress-fill.import-error {
                background: linear-gradient(90deg, #ef4444, #dc2626);
            }

            .import-progress-content.import-fail {
                border: 2px solid #ef4444;
                box-shadow: 0 0 30px rgba(239, 68, 68, 0.25);
            }

            #error-items.has-errors {
                cursor: pointer;
                text-decoration: underline dotted;
                transition: opacity 0.2s;
            }

            #error-items.has-errors:hover {
                opacity: 0.75;
            }

            .error-detail-panel {
                margin-top: 1rem;
                padding: 1rem;
                background: rgba(239, 68, 68, 0.08);
                border: 1px solid rgba(239, 68, 68, 0.4);
                border-radius: 8px;
                max-height: 160px;
                overflow-y: auto;
            }

            .error-detail-panel strong {
                display: block;
                color: #ef4444;
                margin-bottom: 0.5rem;
                font-size: 0.85rem;
            }

            .error-detail-item {
                font-size: 0.8rem;
                color: #fca5a5;
                padding: 0.2rem 0;
                border-bottom: 1px solid rgba(239, 68, 68, 0.15);
                font-family: 'Courier New', monospace;
            }

            .error-detail-item:last-child {
                border-bottom: none;
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
    document.getElementById('current-item').textContent =
      data.current_item || t('import.processing');

    // Add log entry for progress
    if (data.current_item) {
      this.addLogEntry(`📄 Processing: ${data.current_item}`);
    }
  }

  handleImportCompleted(data) {
    const fill = document.getElementById('import-progress-fill');
    fill.style.width = '100%';
    fill.classList.add('completed');
    document.querySelector('.import-progress-content').classList.add('import-success');
    document.getElementById('import-percentage').textContent = '100%';
    document.getElementById('import-status').textContent = t('import.completed');
    document.getElementById('current-item').textContent = t('import.all_done');

    this.addLogEntry('✅ Import completed successfully!');
    this.addLogEntry(`📊 Final stats: ${data.processed_items} items processed`);

    // Make error count clickable if there are errors
    if (data.errors > 0 && data.error_messages?.length > 0) {
      const errorEl = document.getElementById('error-items');
      errorEl.classList.add('has-errors');
      errorEl.title = 'Click to see failed items';

      const panel = document.createElement('div');
      panel.className = 'error-detail-panel';
      panel.id = 'error-detail-panel';
      panel.style.display = 'none';
      panel.innerHTML =
        `<strong>Failed items (${data.errors}):</strong>` +
        data.error_messages.map((msg) => `<div class="error-detail-item">${msg}</div>`).join('');

      document.querySelector('.import-stats').after(panel);

      errorEl.addEventListener('click', () => {
        const p = document.getElementById('error-detail-panel');
        p.style.display = p.style.display === 'none' ? 'block' : 'none';
      });
    }

    // Hide cancel button
    document.getElementById('cancel-import-btn').style.display = 'none';

    // Close WebSocket
    this.closeImportWebSocket();

    // Show success message
    this.showMessage('Media import completed successfully!', 'success');
  }

  handleImportError(data) {
    const fill = document.getElementById('import-progress-fill');
    fill.classList.add('import-error');
    document.querySelector('.import-progress-content').classList.add('import-fail');
    document.getElementById('import-status').textContent = t('import.failed');
    document.getElementById('current-item').textContent = t('import.error_occurred');

    this.addLogEntry(`❌ Import failed: ${data.error_messages?.join(', ') || 'Unknown error'}`);

    // Hide cancel button
    document.getElementById('cancel-import-btn').style.display = 'none';

    // Close WebSocket
    this.closeImportWebSocket();

    // Show error message
    this.showError(t('import.error_failed'));
  }

  handleImportCancelled(data) {
    document.getElementById('import-status').textContent = t('import.cancelled');
    document.getElementById('current-item').textContent = t('import.was_cancelled');

    this.addLogEntry('🛑 Import cancelled by user');

    // Hide cancel button
    document.getElementById('cancel-import-btn').style.display = 'none';

    // Close WebSocket
    this.closeImportWebSocket();

    // Show info message
    this.showMessage('Media import was cancelled.', 'warning');
  }

  // ========================================
  // 🗑️ Critics Delete Actions
  // ========================================

  async deleteSingleCritic(criticId, tmdbId, authorName) {
    if (!confirm(t('critics.confirm_delete', { author: authorName }))) return;

    try {
      const result = await this.fetchAPI(`/critics/${criticId}`, 'DELETE');
      if (result.success) {
        // Remove card from DOM instantly
        const card = document.getElementById(`critic-card-${criticId}`);
        if (card) card.remove();
        // If no more critics, refresh modal
        const remaining = document.querySelectorAll('.critic-card').length;
        if (remaining === 0) {
          this.showMediaDetails(tmdbId);
        }
        // Update count on media card
        this._updateCardCriticCount(tmdbId, -1);
        this.showMessage(`Crítica de "${authorName}" eliminada`, 'success');
      }
    } catch (error) {
      this.showError(t('critics.error_delete', { error: error.message }));
    }
  }

  async deleteAllMediaCritics(tmdbId, title) {
    if (!confirm(t('critics.confirm_delete_all', { title }))) return;

    try {
      const result = await this.fetchAPI(`/media/${tmdbId}/critics`, 'DELETE');
      if (result.success) {
        this.showMessage(`${result.deleted_count} críticas de "${title}" eliminadas`, 'success');
        this.hideModal();
        this._updateCardCriticCount(tmdbId, 0);
      }
    } catch (error) {
      this.showError(t('critics.error_delete_all', { error: error.message }));
    }
  }

  _updateCardCriticCount(tmdbId, delta) {
    const card = document.querySelector(`.media-card[data-tmdb-id="${tmdbId}"]`);
    if (!card) return;
    const countEl = card.querySelector('.critics-count');
    if (!countEl) return;
    if (delta === 0) {
      countEl.textContent = t('critics.none_for_media');
      countEl.className = 'critics-count';
    } else {
      const match = countEl.textContent.match(/(\d+)/);
      const current = match ? parseInt(match[1]) : 0;
      const newCount = Math.max(0, current + delta);
      if (newCount === 0) {
        countEl.textContent = t('critics.none_for_media');
        countEl.className = 'critics-count';
      } else {
        countEl.textContent = `📝 ${newCount} críticas`;
        countEl.className = 'critics-count has-critics';
      }
    }
  }

  async cancelImport(sessionId) {
    try {
      const response = await fetch(`${this.apiBase}/media/import/cancel/${sessionId}`, {
        method: 'POST',
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

  closeImportProgressModal() {
    console.log('🚪 Closing import progress modal');

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
        addedAt: Date.now(),
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
                         src="${item.poster_url || '/static/images/parody_critics_logo.png'}"
                         alt="${item.title}"
                         onerror="this.src='/static/images/parody_critics_logo.png'">
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

    mediaCards.forEach((card) => {
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

    console.log(
      `🛒 Updated ${updatedCount} selected cards out of ${mediaCards.length} total cards`
    );
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
  async proceedToCheckout() {
    if (this.cart.size === 0) {
      this.showMessage('Carrito vacío. Selecciona contenido primero.', 'warning');
      return;
    }

    // Close cart and show checkout view
    this.closeCart();
    this.showView('checkout');

    // Await the checkout view rendering with error handling
    try {
      await this.renderCheckoutView();
      console.log('✅ Checkout view rendered successfully');
    } catch (error) {
      console.error('❌ Failed to render checkout view:', error);
      this.showMessage('Error cargando vista de checkout', 'error');
      // Fallback: go back to media view
      this.showView('media');
      return;
    }

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
    console.log('🎬 Rendering checkout media list...');
    const mediaList = document.getElementById('checkout-media-list');
    if (!mediaList) {
      console.error('❌ Checkout media list element not found!');
      return;
    }

    if (this.cart.size === 0) {
      console.log('🛒 Cart is empty, showing empty message');
      mediaList.innerHTML = `
                <div class="empty-cart">
                    <p>🎬 No hay contenido seleccionado</p>
                    <p><a href="#" onclick="app.showView('media')">← Volver a seleccionar</a></p>
                </div>
            `;
      return;
    }

    console.log(`🎬 Rendering ${this.cart.size} items in checkout`);

    try {
      let html = '';
      this.cart.forEach((item, tmdbId) => {
        html += `
                <div class="checkout-media-item" data-tmdb-id="${tmdbId}">
                    <img class="checkout-media-poster"
                         src="${item.poster_url || '/static/images/parody_critics_logo.png'}"
                         alt="${item.title}"
                         onerror="this.src='/static/images/parody_critics_logo.png'">
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
      console.log('✅ Checkout media list rendered successfully');
    } catch (error) {
      console.error('❌ Error rendering checkout media list:', error);
      mediaList.innerHTML = `
                <div class="error-message">
                    <p>❌ Error cargando contenido del carrito</p>
                    <p><a href="#" onclick="app.showView('media')">← Volver a películas</a></p>
                </div>
            `;
      throw error; // Re-throw to be caught by parent
    }
  }

  // Remove from cart in checkout view
  removeFromCartCheckout(tmdbId) {
    this.removeFromCart(tmdbId);
    this.renderCheckoutMediaList();
    this.updateProcessingControls();
  }

  // Render critics selection
  async renderCriticsSelection() {
    console.log('🎭 Rendering critics selection...');
    const criticsSelection = document.getElementById('critics-selection');
    if (!criticsSelection) {
      console.error('❌ Critics selection element not found!');
      return;
    }

    try {
      console.log('🌐 Fetching characters from API...');
      const characters = await this.fetchAPI('/characters');
      console.log(`✅ Received ${characters.length} characters from API`);

      let html = '';
      characters.forEach((character) => {
        const isSelected = this.batchProcessing.selectedCritics.has(character.id);
        const desc = character.description || 'Crítico experto';
        const truncatedDesc = desc.length > 90 ? desc.slice(0, 90) + '…' : desc;
        const personality = (character.personality || '')
          .replace(/_/g, ' ')
          .replace(/\b\w/g, (c) => c.toUpperCase());
        html += `
                    <div class="critic-checkbox-item ${isSelected ? 'selected' : ''}"
                         onclick="app.toggleCriticSelection('${character.id}')">
                        <input type="checkbox"
                               class="critic-checkbox"
                               id="critic-${character.id}"
                               ${isSelected ? 'checked' : ''}
                               onchange="app.toggleCriticSelection('${character.id}')">
                        <span class="critic-emoji">${character.emoji || '🎭'}</span>
                        <div class="critic-info">
                            <div class="critic-header">
                                <span class="critic-name">${character.name}</span>
                                ${personality ? `<span class="critic-personality-tag">${personality}</span>` : ''}
                            </div>
                            <div class="critic-description">${truncatedDesc}</div>
                        </div>
                    </div>
                `;
      });

      criticsSelection.innerHTML = html;
      console.log('✅ Critics selection rendered successfully');
    } catch (error) {
      console.error('❌ Error loading critics:', error);
      criticsSelection.innerHTML = `
                <div class="error-message">
                    <p>❌ Error cargando críticos</p>
                    <p>Por favor recarga la página</p>
                </div>
            `;
      throw error; // Re-throw to be caught by parent
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
      const canStart =
        this.cart.size > 0 &&
        this.batchProcessing.selectedCritics.size > 0 &&
        !this.batchProcessing.isProcessing;
      startBtn.disabled = !canStart;
    }
  }

  // Get critic name by ID
  async getCriticName(criticId) {
    try {
      // First check if we have characters data cached
      if (this.dataCache.characters) {
        const critic = this.dataCache.characters.find((c) => c.id === criticId);
        if (critic) return critic.name;
      }

      // Fetch characters if not cached
      const response = await fetch('/api/characters');
      if (!response.ok) throw new Error('Failed to fetch characters');

      const characters = await response.json();
      this.dataCache.characters = characters; // Cache for future use

      const critic = characters.find((c) => c.id === criticId);
      return critic ? critic.name : criticId;
    } catch (error) {
      console.error('❌ Error getting critic name:', error);
      return criticId; // Fallback to ID
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

    console.log(
      `🚀 Starting batch processing: ${mediaItems.length} media × ${critics.length} critics = ${totalOperations} operations`
    );

    // Prepare the request payload
    const requestPayload = {
      media_items: mediaItems,
      selected_critics: critics,
    };

    try {
      // Update initial progress
      this.updateProgressDisplay(0, totalOperations, 0, 'Iniciando procesamiento...', null);

      let completed = 0;
      let errors = 0;
      let currentOperation = 0;

      // Process each combination individually for real-time progress
      for (const mediaItem of mediaItems) {
        for (const criticId of critics) {
          if (this.batchProcessing.controller.signal.aborted) {
            throw new Error('Procesamiento cancelado por el usuario');
          }

          currentOperation++;

          // Update progress with current operation
          const currentCritic = await this.getCriticName(criticId);
          this.updateProgressDisplay(
            completed,
            totalOperations,
            errors,
            'Procesando...',
            `${mediaItem.title} + ${currentCritic}`
          );

          try {
            // Process single critic for single media
            const singlePayload = {
              media_items: [mediaItem],
              selected_critics: [criticId],
            };

            console.log(
              `🎭 Processing ${currentOperation}/${totalOperations}: ${mediaItem.title} + ${currentCritic}`
            );

            const response = await fetch('/api/generate/cart-batch', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify(singlePayload),
              signal: this.batchProcessing.controller.signal,
            });

            if (!response.ok) {
              throw new Error(`Error HTTP ${response.status}`);
            }

            const result = await response.json();
            const item = result.results[0]; // Single result

            if (item.status === 'success') {
              completed++;
              console.log(`✅ Success: ${item.title} + ${item.critic}`);
            } else {
              errors++;
              console.log(
                `⚠️ ${item.status}: ${item.title} + ${item.critic} - ${item.error || item.reason}`
              );
            }

            // Store result
            this.batchProcessing.results.push({
              media: {
                title: item.title || mediaItem.title,
                tmdb_id: item.tmdb_id || mediaItem.tmdb_id,
              },
              critic: item.critic || currentCritic,
              status: item.status,
              result: item.status === 'success' ? { rating: item.rating } : null,
              error: item.error || item.reason,
            });

            // Update progress after each completion
            this.updateProgressDisplay(
              completed,
              totalOperations,
              errors,
              currentOperation === totalOperations ? 'Procesamiento completado' : 'Procesando...',
              currentOperation === totalOperations
                ? null
                : `Completado: ${item.title} + ${item.critic}`
            );

            // Small delay to make progress visible
            await new Promise((resolve) => setTimeout(resolve, 100));
          } catch (itemError) {
            errors++;
            console.error(`❌ Error processing ${mediaItem.title} + ${currentCritic}:`, itemError);

            this.batchProcessing.results.push({
              media: { title: mediaItem.title, tmdb_id: mediaItem.tmdb_id },
              critic: currentCritic,
              status: 'error',
              result: null,
              error: itemError.message,
            });

            // Update progress with error
            this.updateProgressDisplay(
              completed,
              totalOperations,
              errors,
              'Procesando...',
              `Error: ${mediaItem.title} + ${currentCritic}`
            );
          }
        }
      }

      console.log(`🎉 Batch processing completed: ${completed} success, ${errors} errors`);

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

    const response = await fetch(
      `${this.apiBase}/generate/critic/${tmdbId}?character=${encodeURIComponent(criticId)}&language=${i18n.current}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: signal,
      }
    );

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
  updateProgressDisplay(completed, total, errors, status, currentItem) {
    const percentage = total > 0 ? ((completed + errors) / total) * 100 : 0;
    const remaining = total - completed - errors;

    // Update progress bar
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    if (progressFill && progressText) {
      progressFill.style.width = `${percentage}%`;
      progressText.textContent = `${Math.round(percentage)}%`;
    }

    // Update status with more detailed information
    const statusElement = document.getElementById('processing-status');
    if (statusElement) {
      if (status) {
        statusElement.textContent = `${status} (${completed + errors}/${total})`;
      } else {
        statusElement.textContent = `Procesando... ${completed}/${total} completadas`;
      }
    }

    // Update current item
    const currentElement = document.getElementById('processing-current');
    if (currentElement) {
      if (currentItem) {
        currentElement.textContent = `🎬 ${currentItem}`;
      } else {
        currentElement.textContent =
          percentage === 100 ? 'Completado' : 'Preparando siguiente elemento...';
      }
    }

    // Update statistics
    const completedElement = document.getElementById('completed-count');
    const errorElement = document.getElementById('error-count');
    const remainingElement = document.getElementById('remaining-count');

    if (completedElement) completedElement.textContent = completed;
    if (errorElement) errorElement.textContent = errors;
    if (remainingElement) remainingElement.textContent = remaining;
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

    console.log(
      `🎉 Batch processing completed: ${completed} success, ${errors} errors of ${total} total`
    );

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
    this.showMessage(
      `🎉 Procesamiento completado: ${completed} críticas generadas${errors > 0 ? `, ${errors} errores` : ''}`,
      'success'
    );
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

    const successful = this.batchProcessing.results.filter((r) => r.status === 'success').length;
    const failed = this.batchProcessing.results.filter((r) => r.status === 'error').length;
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
    this.batchProcessing.results.forEach((result) => {
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

  // ========================================
  // 🎭 Characters Management System
  // ========================================

  async loadCharactersData() {
    console.log('🎭 Loading characters management data...');

    try {
      // Setup character action buttons
      this.setupCharacterActions();

      // Load and display characters
      await this.renderCharactersGrid();

      console.log('✅ Characters data loaded successfully');
    } catch (error) {
      console.error('❌ Failed to load characters data:', error);
      this.showError('Error cargando datos de personajes: ' + error.message);
    }
  }

  setupCharacterActions() {
    // Add character button
    const addBtn = document.getElementById('add-character-btn');
    if (addBtn) {
      addBtn.addEventListener('click', () => this.openAddCharacterModal());
    }

    // Import characters button
    const importBtn = document.getElementById('import-characters-btn');
    if (importBtn) {
      importBtn.addEventListener('click', () => this.openImportCharactersModal());
    }

    // Export characters button
    const exportBtn = document.getElementById('export-characters-btn');
    if (exportBtn) {
      exportBtn.addEventListener('click', () => this.exportCharacters());
    }

    // Setup modal close buttons
    this.setupCharacterModalEvents();

    console.log('🎭 Character action buttons configured');
  }

  setupCharacterModalEvents() {
    // Character modal events
    const characterModal = document.getElementById('character-modal');
    const characterModalClose = document.getElementById('character-modal-close');
    const characterForm = document.getElementById('character-form');

    if (characterModalClose) {
      characterModalClose.addEventListener('click', () => this.closeCharacterModal());
    }

    if (characterModal) {
      characterModal.addEventListener('click', (e) => {
        if (e.target === characterModal) {
          this.closeCharacterModal();
        }
      });
    }

    if (characterForm) {
      characterForm.addEventListener('submit', (e) => this.handleCharacterFormSubmit(e));
    }

    // Import modal events
    const importModal = document.getElementById('import-modal');
    const importModalClose = document.getElementById('import-modal-close');
    const importForm = document.getElementById('import-form');
    const importCancelBtn = document.getElementById('import-cancel-btn');

    if (importModalClose) {
      importModalClose.addEventListener('click', () => this.closeImportModal());
    }

    if (importCancelBtn) {
      importCancelBtn.addEventListener('click', () => this.closeImportModal());
    }

    if (importModal) {
      importModal.addEventListener('click', (e) => {
        if (e.target === importModal) {
          this.closeImportModal();
        }
      });
    }

    if (importForm) {
      importForm.addEventListener('submit', (e) => this.handleImportFormSubmit(e));
    }
  }

  async renderCharactersGrid() {
    const charactersGrid = document.getElementById('characters-grid');
    if (!charactersGrid) return;

    try {
      charactersGrid.innerHTML = `<div class="loading">${t('characters.loading')}</div>`;

      const characters = await this.fetchAPI('/characters');

      if (!characters || characters.length === 0) {
        charactersGrid.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">🎭</div>
                        <h3>${t('characters.none_available')}</h3>
                        <p>${t('characters.none_action')}</p>
                        <button class="btn-primary" onclick="app.openAddCharacterModal()">
                            ${t('characters.btn_create')}
                        </button>
                    </div>
                `;
        return;
      }

      let html = '';
      characters.forEach((character) => {
        const criticsCount = character.total_reviews || 0;
        const avgRating = character.avg_rating ? character.avg_rating.toFixed(1) : '—';

        html += `
                    <div class="character-card" data-character-id="${character.id}">
                        <div class="character-card-header">
                            <div class="character-emoji">${character.emoji || '🎭'}</div>
                            <div class="character-actions">
                                <button class="btn-icon" onclick="app.editCharacter('${character.id}')" title="${t('characters.btn_edit_title')}">
                                    ✏️
                                </button>
                                <button class="btn-icon btn-danger" onclick="app.deleteCharacter('${character.id}', '${character.name}')" title="${t('characters.btn_delete_title')}">
                                    🗑️
                                </button>
                            </div>
                        </div>

                        <div class="character-card-body">
                            <h3 class="character-name">${character.name}</h3>
                            <p class="character-personality">${(character.personality || 'Personalidad única').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}</p>
                            <p class="character-description">${character.description || 'Sin descripción'}</p>
                        </div>

                        <div class="character-card-stats">
                            <div class="character-stat">
                                <span class="stat-label">Críticas</span>
                                <span class="stat-value">${criticsCount}</span>
                            </div>
                            <div class="character-stat">
                                <span class="stat-label">Rating Promedio</span>
                                <span class="stat-value">⭐ ${avgRating}</span>
                            </div>
                        </div>

                        <div class="character-card-footer">
                            <button class="btn-secondary btn-sm" onclick="app.viewCharacterCritics('${character.id}')">
                                📝 Ver Críticas
                            </button>
                            <button class="btn-danger btn-sm" onclick="app.deleteAllCharacterCritics('${character.id}', '${character.name}')">
                                🗑️ Eliminar Críticas
                            </button>
                        </div>
                    </div>
                `;
      });

      charactersGrid.innerHTML = html;
    } catch (error) {
      console.error('❌ Error rendering characters:', error);
      charactersGrid.innerHTML = `
                <div class="error-state">
                    <div class="error-state-icon">❌</div>
                    <h3>Error cargando personajes</h3>
                    <p>${error.message}</p>
                    <button class="btn-primary" onclick="app.renderCharactersGrid()">
                        🔄 Reintentar
                    </button>
                </div>
            `;
    }
  }

  // Open add character modal → routes to Soul Wizard
  openAddCharacterModal() {
    this.openSoulWizard();
  }

  // ── Soul Wizard ────────────────────────────────────────────────

  openSoulWizard() {
    this._soulRealName = '';
    this._soulData = null;

    // Reset Step 1
    const realNameInput = document.getElementById('soul-real-name');
    const archetypeSelect = document.getElementById('soul-archetype');
    if (realNameInput) realNameInput.value = '';
    if (archetypeSelect) archetypeSelect.value = '';

    // Show Step 1, hide Step 2
    const step1 = document.getElementById('soul-step-1');
    const step2 = document.getElementById('soul-step-2');
    if (step1) step1.classList.remove('hidden');
    if (step2) step2.classList.add('hidden');

    // Always re-enable generate button (may be disabled from previous session)
    const generateBtn = document.getElementById('soul-generate-btn');
    if (generateBtn) generateBtn.disabled = false;

    const modal = document.getElementById('soul-wizard-modal');
    if (modal) {
      modal.classList.remove('hidden');
      if (realNameInput) setTimeout(() => realNameInput.focus(), 80);
    }

    this._setupSoulWizardEvents();
  }

  closeSoulWizard() {
    const modal = document.getElementById('soul-wizard-modal');
    if (modal) modal.classList.add('hidden');
  }

  _setupSoulWizardEvents() {
    // Only wire once
    if (this._soulEventsWired) return;
    this._soulEventsWired = true;

    // Close buttons & backdrop
    const modal = document.getElementById('soul-wizard-modal');
    modal.addEventListener('click', (e) => {
      if (e.target === modal) this.closeSoulWizard();
    });
    document.getElementById('soul-close-1').addEventListener('click', () => this.closeSoulWizard());
    document.getElementById('soul-close-2').addEventListener('click', () => this.closeSoulWizard());
    document
      .getElementById('soul-cancel-1')
      .addEventListener('click', () => this.closeSoulWizard());
    document
      .getElementById('soul-cancel-2')
      .addEventListener('click', () => this.closeSoulWizard());

    // Back button
    document.getElementById('soul-back-btn').addEventListener('click', () => {
      document.getElementById('soul-step-2').classList.add('hidden');
      document.getElementById('soul-step-1').classList.remove('hidden');
      const generateBtn = document.getElementById('soul-generate-btn');
      if (generateBtn) generateBtn.disabled = false;
      document.getElementById('soul-progress-section').classList.add('hidden');
      document.getElementById('soul-fields-section').classList.add('hidden');
    });

    // Generate button
    document
      .getElementById('soul-generate-btn')
      .addEventListener('click', () => this._generateSoul());

    // Save button
    document
      .getElementById('soul-save-btn')
      .addEventListener('click', () => this._saveSoulCharacter());

    // Regen buttons (delegated on fields section)
    document.getElementById('soul-fields-section').addEventListener('click', (e) => {
      const btn = e.target.closest('.btn-regen');
      if (btn && !btn.disabled) {
        const field = btn.dataset.field;
        if (field) this._regenField(field, btn);
      }
    });

    // Archetype change in step 2 — confirm + full regeneration
    document.getElementById('sf-personality').addEventListener('change', (e) => {
      if (!this._soulData) return;
      const newValue = e.target.value;
      const oldValue = this._soulData.personality || '';
      if (!confirm('Cambiar el arquetipo regenerará el alma completa. ¿Continuar?')) {
        e.target.value = oldValue;
        return;
      }
      const archetypeStep1 = document.getElementById('soul-archetype');
      if (archetypeStep1) archetypeStep1.value = newValue;
      this._generateSoul();
    });

    // Enter key on real name input
    document.getElementById('soul-real-name').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') this._generateSoul();
    });
  }

  async _generateSoul() {
    const realName = (document.getElementById('soul-real-name').value || '').trim();
    if (!realName) {
      this.showError('Introduce el nombre de la persona a parodiar');
      return;
    }
    const archetype = document.getElementById('soul-archetype').value || null;

    this._soulRealName = realName;

    // Switch to Step 2 showing progress
    document.getElementById('soul-step-1').classList.add('hidden');
    document.getElementById('soul-step-2').classList.remove('hidden');
    document.getElementById('soul-step2-title').textContent = `🎭 ${realName}`;
    document.getElementById('soul-fields-section').classList.add('hidden');
    document.getElementById('soul-progress-section').classList.remove('hidden');

    this._setSoulProgress(5, 'Iniciando búsqueda...');
    const generateBtn = document.getElementById('soul-generate-btn');
    if (generateBtn) generateBtn.disabled = true;

    // Simulate gradual progress while waiting for API
    const progressSteps = [
      [1000, 15, 'Buscando contexto (DuckDuckGo)...'],
      [3000, 30, 'Contexto obtenido, generando alma...'],
      [6000, 45, 'Generando personalidad...'],
      [9000, 60, 'Generando loves y hates...'],
      [12000, 72, 'Generando motivos y frases...'],
      [15000, 82, 'Finalizando...'],
    ];
    const timers = progressSteps.map(([delay, pct, msg]) =>
      setTimeout(() => this._setSoulProgress(pct, msg), delay)
    );

    try {
      const result = await this.fetchAPI('/characters/generate-soul', 'POST', {
        real_name: realName,
        archetype,
        language: i18n.current,
      });
      timers.forEach(clearTimeout);

      if (!result.success) throw new Error(result.detail || 'Generation failed');

      this._soulData = result.soul;
      this._setSoulProgress(95, 'Procesando...');
      this._populateSoulFields(result.soul);

      setTimeout(() => {
        this._setSoulProgress(100, '¡Alma generada!');
        setTimeout(() => {
          document.getElementById('soul-progress-section').classList.add('hidden');
          document.getElementById('soul-fields-section').classList.remove('hidden');
        }, 400);
      }, 300);
    } catch (err) {
      timers.forEach(clearTimeout);
      this.showError('Error generando alma: ' + err.message);
      // Go back to Step 1
      document.getElementById('soul-step-2').classList.add('hidden');
      document.getElementById('soul-step-1').classList.remove('hidden');
      if (generateBtn) generateBtn.disabled = false;
    }
  }

  _setSoulProgress(pct, label) {
    const fill = document.getElementById('soul-progress-fill');
    const lbl = document.getElementById('soul-progress-label');
    if (fill) fill.style.width = pct + '%';
    if (lbl) lbl.textContent = label;
  }

  _populateSoulFields(soul) {
    const listToText = (arr) => (Array.isArray(arr) ? arr.join('\n') : arr || '');

    document.getElementById('sf-caricature_name').value = soul.caricature_name || '';
    document.getElementById('sf-emoji').value = soul.emoji || '🎭';
    document.getElementById('sf-color').value = soul.color || '#6366f1';
    const personalityEl = document.getElementById('sf-personality');
    if (personalityEl) personalityEl.value = soul.personality || '';
    document.getElementById('sf-description').value = soul.description || '';
    document.getElementById('sf-loves').value = listToText(soul.loves);
    document.getElementById('sf-hates').value = listToText(soul.hates);
    document.getElementById('sf-motifs').value = listToText(soul.motifs);
    document.getElementById('sf-catchphrases').value = listToText(soul.catchphrases);
    document.getElementById('sf-avoid').value = listToText(soul.avoid);
    document.getElementById('sf-red_flags').value = listToText(soul.red_flags);
  }

  _collectSoulFields() {
    const textToList = (id) =>
      document
        .getElementById(id)
        .value.split('\n')
        .map((s) => s.trim())
        .filter(Boolean);

    return {
      caricature_name: document.getElementById('sf-caricature_name').value.trim(),
      emoji: document.getElementById('sf-emoji').value.trim() || '🎭',
      color: document.getElementById('sf-color').value,
      personality: document.getElementById('sf-personality').value,
      description: document.getElementById('sf-description').value.trim(),
      loves: textToList('sf-loves'),
      hates: textToList('sf-hates'),
      motifs: textToList('sf-motifs'),
      catchphrases: textToList('sf-catchphrases'),
      avoid: textToList('sf-avoid'),
      red_flags: textToList('sf-red_flags'),
    };
  }

  async _regenField(field, btn) {
    if (!this._soulRealName) return;
    btn.disabled = true;
    btn.textContent = '⏳';

    const currentSoul = this._collectSoulFields();

    try {
      const result = await this.fetchAPI('/characters/regen-field', 'POST', {
        field,
        current_soul: currentSoul,
        real_name: this._soulRealName,
      });

      if (!result.success) throw new Error(result.detail || 'Regen failed');

      const value = result.value;
      const listFields = ['loves', 'hates', 'motifs', 'catchphrases', 'avoid', 'red_flags'];
      const el = document.getElementById(`sf-${field}`);
      if (el) {
        if (listFields.includes(field)) {
          el.value = Array.isArray(value) ? value.join('\n') : value;
        } else {
          el.value = value;
        }
      }
    } catch (err) {
      this.showError(`Error regenerando ${field}: ` + err.message);
    } finally {
      btn.disabled = false;
      btn.textContent = '🎲';
    }
  }

  async _saveSoulCharacter() {
    const soul = this._collectSoulFields();
    const name = soul.caricature_name;

    if (!name) {
      this.showError('El apodo del personaje es obligatorio');
      return;
    }

    const saveBtn = document.getElementById('soul-save-btn');
    saveBtn.disabled = true;
    saveBtn.textContent = '⏳ Guardando...';

    const characterData = {
      name,
      emoji: soul.emoji,
      personality: soul.personality,
      description: soul.description,
      color: soul.color,
      border_color: soul.color,
      accent_color: soul.color + '33',
      loves: soul.loves,
      hates: soul.hates,
      motifs: soul.motifs,
      catchphrases: soul.catchphrases,
      avoid: soul.avoid,
      red_flags: soul.red_flags,
    };

    try {
      const result = await this.fetchAPI('/characters', 'POST', characterData);
      if (!result.success) throw new Error(result.detail || 'Save failed');
      this.closeSoulWizard();
      this.showMessage(`Personaje "${name}" creado con éxito`, 'success');
      await this.renderCharactersGrid();
    } catch (err) {
      this.showError('Error guardando personaje: ' + err.message);
      saveBtn.disabled = false;
      saveBtn.textContent = '💾 Guardar Personaje';
    }
  }

  // Open edit character modal
  async editCharacter(characterId) {
    try {
      console.log('🎭 Loading character for editing:', characterId);

      const characters = await this.fetchAPI('/characters');
      const character = characters.find((c) => c.id === characterId);

      if (!character) {
        this.showError('Personaje no encontrado');
        return;
      }

      this.currentEditingCharacter = character;
      this.showCharacterModal(t('modal.character.title_edit'), character);
    } catch (error) {
      console.error('❌ Error loading character for edit:', error);
      this.showError('Error cargando personaje: ' + error.message);
    }
  }

  // Show character modal
  showCharacterModal(title, character = null) {
    const modal = document.getElementById('character-modal');
    const modalTitle = document.getElementById('character-modal-title');
    const form = document.getElementById('character-form');

    if (!modal || !modalTitle || !form) {
      console.error('❌ Character modal elements not found');
      return;
    }

    // Set modal title
    modalTitle.textContent = title;

    // Populate form if editing
    if (character) {
      document.getElementById('character-id').value = character.id || '';
      document.getElementById('character-name').value = character.name || '';
      document.getElementById('character-emoji').value = character.emoji || '🎭';
      document.getElementById('character-personality').value = character.personality || '';
      document.getElementById('character-description').value = character.description || '';
      document.getElementById('char-loves').value = (character.loves || []).join(', ');
      document.getElementById('char-hates').value = (character.hates || []).join(', ');
    } else {
      form.reset();
      document.getElementById('character-emoji').value = '🎭';
      document.getElementById('char-loves').value = '';
      document.getElementById('char-hates').value = '';
    }

    // Show modal
    modal.classList.remove('hidden');

    // Focus first input
    setTimeout(() => {
      document.getElementById('character-name').focus();
    }, 100);
  }

  // Close character modal
  closeCharacterModal() {
    const modal = document.getElementById('character-modal');
    if (modal) {
      modal.classList.add('hidden');
      this.currentEditingCharacter = null;
    }
    console.log('🚪 Character modal closed');
  }

  // Handle character form submit
  async handleCharacterFormSubmit(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);

    const lovesRaw = document.getElementById('char-loves').value;
    const hatesRaw = document.getElementById('char-hates').value;

    const characterData = {
      name: formData.get('name').trim(),
      emoji: formData.get('emoji').trim() || '🎭',
      personality: formData.get('personality').trim(),
      description: formData.get('description').trim(),
      loves: lovesRaw
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean),
      hates: hatesRaw
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean),
    };

    // Basic validation
    if (!characterData.name) {
      this.showError('El nombre del personaje es obligatorio');
      return;
    }

    try {
      const submitBtn = form.querySelector('button[type="submit"]');
      const originalText = submitBtn.textContent;
      submitBtn.textContent = '⏳ Guardando...';
      submitBtn.disabled = true;

      let result;
      if (this.currentEditingCharacter) {
        // Update existing character
        characterData.id = this.currentEditingCharacter.id;
        console.log('🔄 Updating character:', characterData);
        result = await this.fetchAPI(
          `/characters/${this.currentEditingCharacter.id}`,
          'PUT',
          characterData
        );
      } else {
        // Create new character
        console.log('➕ Creating new character:', characterData);
        result = await this.fetchAPI('/characters', 'POST', characterData);
      }

      if (result.success || result.id) {
        this.showMessage(
          this.currentEditingCharacter
            ? 'Personaje actualizado correctamente'
            : 'Personaje creado correctamente',
          'success'
        );
        this.closeCharacterModal();
        await this.renderCharactersGrid(); // Refresh the grid
      } else {
        throw new Error(result.error || 'Error guardando personaje');
      }
    } catch (error) {
      console.error('❌ Error saving character:', error);
      this.showError('Error guardando personaje: ' + error.message);
    } finally {
      const submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn) {
        submitBtn.textContent = this.currentEditingCharacter ? '💾 Actualizar' : '➕ Crear';
        submitBtn.disabled = false;
      }
    }
  }

  // Delete character
  async deleteCharacter(characterId, characterName) {
    const confirmed = confirm(
      `¿Estás seguro de que quieres eliminar el personaje "${characterName}"?\n\n` +
        `⚠️ Esta acción también eliminará todas las críticas escritas por este personaje.\n\n` +
        `Esta acción no se puede deshacer.`
    );

    if (!confirmed) return;

    try {
      console.log('🗑️ Deleting character:', characterId);

      const result = await this.fetchAPI(`/characters/${characterId}`, 'DELETE');

      if (result.success) {
        this.showMessage(`Personaje "${characterName}" eliminado correctamente`, 'success');
        await this.renderCharactersGrid(); // Refresh the grid
      } else {
        throw new Error(result.error || 'Error eliminando personaje');
      }
    } catch (error) {
      console.error('❌ Error deleting character:', error);
      this.showError('Error eliminando personaje: ' + error.message);
    }
  }

  // Delete all character critics
  async deleteAllCharacterCritics(characterId, characterName) {
    const confirmed = confirm(
      `¿Estás seguro de que quieres eliminar TODAS las críticas de "${characterName}"?\n\n` +
        `Esta acción eliminará permanentemente todas las críticas escritas por este personaje.\n\n` +
        `Esta acción no se puede deshacer.`
    );

    if (!confirmed) return;

    try {
      console.log('🗑️ Deleting all critics for character:', characterId);

      const result = await this.fetchAPI(`/characters/${characterId}/critics`, 'DELETE');

      if (result.success) {
        this.showMessage(`Todas las críticas de "${characterName}" han sido eliminadas`, 'success');
        await this.renderCharactersGrid(); // Refresh to update stats
      } else {
        throw new Error(result.error || 'Error eliminando críticas');
      }
    } catch (error) {
      console.error('❌ Error deleting character critics:', error);
      this.showError(t('critics.error_delete_all', { error: error.message }));
    }
  }

  // View character critics
  async viewCharacterCritics(characterId) {
    try {
      const data = await this.fetchAPI(`/characters/${characterId}/critics`);
      this._showCharacterCriticsModal(data);
    } catch (error) {
      this.showError('Error cargando críticas: ' + error.message);
    }
  }

  _showCharacterCriticsModal(data) {
    const existing = document.getElementById('character-critics-modal');
    if (existing) existing.remove();

    const modal = document.createElement('div');
    modal.id = 'character-critics-modal';
    modal.className = 'modal';
    modal.innerHTML = `
      <div class="modal-content" style="max-width:860px;">
        <button class="modal-close" id="char-modal-close">&times;</button>
        <div style="padding:1.5rem;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1.2rem; flex-wrap:gap;">
            <h2 style="margin:0;">${data.character_emoji} Críticas de ${data.character_name} <span style="font-size:0.85rem; color:var(--text-secondary);">(${data.total})</span></h2>
            <button id="char-delete-selected" class="btn-danger" style="font-size:0.85rem; padding:0.4rem 0.9rem; display:none;">
              🗑️ Eliminar seleccionadas (<span id="char-selected-count">0</span>)
            </button>
          </div>

          ${
            data.total === 0
              ? `
            <div style="text-align:center; padding:2rem; color:var(--text-secondary);">
              <p>📝 Este personaje aún no tiene críticas generadas.</p>
            </div>
          `
              : `
            <div style="margin-bottom:1rem; display:flex; align-items:center; gap:0.6rem;">
              <input type="checkbox" id="char-select-all" style="width:16px; height:16px; cursor:pointer;">
              <label for="char-select-all" style="cursor:pointer; color:var(--text-secondary); font-size:0.9rem;">Seleccionar todas</label>
            </div>
            <div id="char-critics-list">
              ${data.critics.map((c) => this._renderCharacterCriticCard(c, data.character_name)).join('')}
            </div>
          `
          }
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    // Clear inline styles so CSS takes over
    modal.style.display = '';

    // Close button
    modal.querySelector('#char-modal-close').addEventListener('click', () => modal.remove());
    modal.addEventListener('click', (e) => {
      if (e.target === modal) modal.remove();
    });

    // Select all
    const selectAll = modal.querySelector('#char-select-all');
    if (selectAll) {
      selectAll.addEventListener('change', () => {
        modal
          .querySelectorAll('.char-critic-check')
          .forEach((cb) => (cb.checked = selectAll.checked));
        this._updateCharacterModalSelection(modal);
      });
    }

    // Checkbox delegation
    const list = modal.querySelector('#char-critics-list');
    if (list) {
      list.addEventListener('change', (e) => {
        if (e.target.classList.contains('char-critic-check')) {
          this._updateCharacterModalSelection(modal);
        }
      });
    }

    // Delete selected
    modal.querySelector('#char-delete-selected').addEventListener('click', () => {
      this._deleteSelectedCharacterCritics(modal, data.character_name);
    });
  }

  _renderCharacterCriticCard(critic, characterName) {
    const date = critic.generated_at
      ? new Date(critic.generated_at).toLocaleDateString('es-ES', {
          day: 'numeric',
          month: 'short',
          year: 'numeric',
        })
      : '';
    const preview =
      critic.content.length > 280 ? critic.content.slice(0, 280) + '…' : critic.content;
    return `
      <div class="critic-card" id="char-critic-card-${critic.critic_id}" style="margin-bottom:0.8rem; position:relative;">
        <div style="display:flex; align-items:flex-start; gap:0.8rem;">
          <input type="checkbox" class="char-critic-check" data-id="${critic.critic_id}"
            style="width:16px; height:16px; margin-top:0.3rem; cursor:pointer; flex-shrink:0;">
          <div style="flex:1; min-width:0;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
              <span style="font-weight:600; font-size:0.95rem;">🎬 ${critic.media_title} <span style="color:var(--text-secondary); font-weight:400;">(${critic.media_year || '?'})</span></span>
              <div style="display:flex; align-items:center; gap:0.5rem; flex-shrink:0;">
                <span style="color:var(--accent-gold); font-weight:700;">${critic.rating}/10</span>
                <button class="btn-icon btn-danger" style="font-size:0.8rem; padding:0.3rem 0.5rem;"
                  onclick="app.deleteSingleCritic(${critic.critic_id}, '${critic.tmdb_id}', '${characterName.replace(/'/g, "\\'")}')">🗑️</button>
              </div>
            </div>
            <p style="margin:0 0 0.4rem; font-size:0.85rem; line-height:1.5; color:var(--text-secondary);">${preview}</p>
            <span style="font-size:0.75rem; color:var(--text-muted);">Generado: ${date}</span>
          </div>
        </div>
      </div>
    `;
  }

  _updateCharacterModalSelection(modal) {
    const checked = modal.querySelectorAll('.char-critic-check:checked');
    const deleteBtn = modal.querySelector('#char-delete-selected');
    const countEl = modal.querySelector('#char-selected-count');
    countEl.textContent = checked.length;
    deleteBtn.style.display = checked.length > 0 ? 'inline-flex' : 'none';

    const all = modal.querySelectorAll('.char-critic-check');
    const selectAll = modal.querySelector('#char-select-all');
    if (selectAll) selectAll.checked = all.length > 0 && checked.length === all.length;
  }

  async _deleteSelectedCharacterCritics(modal, characterName) {
    const checked = [...modal.querySelectorAll('.char-critic-check:checked')];
    const ids = checked.map((cb) => parseInt(cb.dataset.id));
    if (ids.length === 0) return;

    if (
      !confirm(`¿Eliminar ${ids.length} crítica${ids.length > 1 ? 's' : ''} de "${characterName}"?`)
    )
      return;

    try {
      const result = await this.fetchAPI('/critics/batch', 'DELETE', { critic_ids: ids });
      if (result.success) {
        ids.forEach((id) => {
          const card = document.getElementById(`char-critic-card-${id}`);
          if (card) card.remove();
        });
        this._updateCharacterModalSelection(modal);

        // Update total count in header
        const remaining = modal.querySelectorAll('.char-critic-check').length;
        const header = modal.querySelector('h2 span');
        if (header) header.textContent = `(${remaining})`;

        // Update character card stats
        this.loadCharactersData();

        this.showMessage(
          `${ids.length} crítica${ids.length > 1 ? 's' : ''} eliminada${ids.length > 1 ? 's' : ''}`,
          'success'
        );
      }
    } catch (error) {
      this.showError(t('critics.error_delete_all', { error: error.message }));
    }
  }

  // Open import characters modal
  openImportCharactersModal() {
    const modal = document.getElementById('import-modal');
    if (modal) {
      modal.classList.remove('hidden');

      // Focus file input
      setTimeout(() => {
        const fileInput = document.getElementById('import-file');
        if (fileInput) fileInput.focus();
      }, 100);
    }
    console.log('📁 Opening import characters modal');
  }

  // Close import modal
  closeImportModal() {
    const modal = document.getElementById('import-modal');
    if (modal) {
      modal.classList.add('hidden');
      const form = document.getElementById('import-form');
      if (form) form.reset();
      const msg = document.getElementById('import-validation-msg');
      if (msg) msg.classList.add('hidden');
    }
  }

  // Handle import form submit
  async handleImportFormSubmit(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);
    const file = formData.get('file');
    const overwrite = formData.get('overwrite') === 'on';
    const validationMsg = document.getElementById('import-validation-msg');

    const showValidationError = (msg) => {
      if (validationMsg) {
        validationMsg.textContent = msg;
        validationMsg.style.background = '#fee2e2';
        validationMsg.style.color = '#dc2626';
        validationMsg.classList.remove('hidden');
      }
    };

    const hideValidation = () => {
      if (validationMsg) validationMsg.classList.add('hidden');
    };

    hideValidation();

    if (!file || file.size === 0) {
      showValidationError('Por favor selecciona un archivo.');
      return;
    }

    // Only .json allowed
    if (!file.name.endsWith('.json')) {
      showValidationError('Solo se admiten archivos .json');
      return;
    }

    // Max 1MB sanity check
    if (file.size > 1024 * 1024) {
      showValidationError('El archivo es demasiado grande (máx. 1MB).');
      return;
    }

    let fileContent;
    try {
      fileContent = await this.readFileAsText(file);
    } catch {
      showValidationError('No se pudo leer el archivo.');
      return;
    }

    // Validate JSON structure before sending
    let parsed;
    try {
      parsed = JSON.parse(fileContent);
    } catch {
      showValidationError('El archivo no es JSON válido.');
      return;
    }

    const characters = Array.isArray(parsed) ? parsed : [parsed];
    if (characters.length === 0) {
      showValidationError('El archivo no contiene personajes.');
      return;
    }
    const missing = characters.filter((c) => !c.name);
    if (missing.length > 0) {
      showValidationError(
        `${missing.length} personaje(s) sin campo "name" — todos los personajes deben tener nombre.`
      );
      return;
    }

    try {
      const submitBtn = form.querySelector('button[type="submit"]');
      submitBtn.textContent = `⏳ Importando ${characters.length} personaje(s)...`;
      submitBtn.disabled = true;

      console.log(`📁 Importing ${characters.length} character(s) from ${file.name}`);

      const result = await this.fetchAPI('/characters/import', 'POST', {
        filename: file.name,
        content: fileContent,
        overwrite: overwrite,
      });

      if (result.success) {
        let msg = `Importación exitosa: ${result.imported || 0} personaje(s) importado(s)`;
        if (result.errors && result.errors.length > 0) {
          msg += ` (${result.errors.length} omitido(s))`;
        }
        this.showMessage(msg, 'success');
        this.closeImportModal();
        await this.renderCharactersGrid();
      } else {
        throw new Error(result.error || 'Error en la importación');
      }
    } catch (error) {
      console.error('❌ Error importing characters:', error);
      showValidationError('Error importando personajes: ' + error.message);
    } finally {
      const submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn) {
        submitBtn.textContent = '📁 Importar';
        submitBtn.disabled = false;
      }
    }
  }

  // Read file as text
  readFileAsText(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => resolve(e.target.result);
      reader.onerror = () => reject(new Error('Error leyendo el archivo'));
      reader.readAsText(file, 'UTF-8');
    });
  }

  // Export characters
  async exportCharacters() {
    try {
      console.log('💾 Exporting all characters...');

      const result = await this.fetchAPI('/characters/export');

      if (result.success && result.data) {
        // Create and download file
        const blob = new Blob([result.data], { type: 'application/json' });
        const url = URL.createObjectURL(blob);

        const a = document.createElement('a');
        a.href = url;
        a.download = result.filename || 'personajes.md';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        this.showMessage(
          `Personajes exportados a ${result.filename || 'personajes.md'}`,
          'success'
        );
      } else {
        throw new Error(result.error || 'Error en la exportación');
      }
    } catch (error) {
      console.error('❌ Error exporting characters:', error);
      this.showError('Error exportando personajes: ' + error.message);
    }
  }

  // ========================================
  // 🔍 Debug Functions for Visual Troubleshooting
  // ========================================

  enableDebug() {
    const debugInfo = document.getElementById('debug-info');
    if (debugInfo) {
      debugInfo.style.display = 'block';
      this.debugEnabled = true;
      this.updateDebugInfo();
      console.log('🔍 Debug mode enabled - check top-right corner');

      // Auto-update debug info every second
      setInterval(() => {
        if (this.debugEnabled) {
          this.updateDebugInfo();
        }
      }, 1000);
    }
  }

  updateDebugInfo() {
    if (!this.debugEnabled) return;

    const currentViewEl = document.getElementById('debug-current-view');
    const cartSizeEl = document.getElementById('debug-cart-size');
    const checkoutActiveEl = document.getElementById('debug-checkout-active');
    const cartOpenEl = document.getElementById('debug-cart-open');

    if (currentViewEl) currentViewEl.textContent = this.currentView || 'undefined';
    if (cartSizeEl) cartSizeEl.textContent = this.cart.size;

    if (checkoutActiveEl) {
      const checkoutView = document.getElementById('checkout-view');
      const isActive = checkoutView && checkoutView.classList.contains('active');
      checkoutActiveEl.textContent = isActive;
      checkoutActiveEl.style.color = isActive ? 'lime' : 'red';
    }

    if (cartOpenEl) {
      const cartPanel = document.getElementById('cart-panel');
      const isOpen = cartPanel && cartPanel.classList.contains('open');
      cartOpenEl.textContent = isOpen;
      cartOpenEl.style.color = isOpen ? 'lime' : 'red';
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
