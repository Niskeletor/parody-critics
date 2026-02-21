/**
 * Críticos de Parodia - Versión API Híbrida
 * Diseño original + Conectividad backend real
 * Marco Aurelio (Estoico) y Rosario Costras (Woke)
 */

(function() {
    'use strict';

    const logPrefix = '🎭 Parody Critics:';

    // Sistema de temas por personaje (TU DISEÑO ORIGINAL)
    const CHARACTER_THEMES = {
        'marco_aurelio': {
            color: '#8B4513',      // Marrón emperador/estoico
            emoji: '🏛️',
            name: 'Marco Aurelio',
            borderColor: '#8B4513',
            accentColor: 'rgba(139, 69, 19, 0.2)'
        },
        'rosario_costras': {
            color: '#FF69B4',      // Rosa woke/progre
            emoji: '🏳️‍⚧️',
            name: 'Rosario Costras',
            borderColor: '#FF69B4',
            accentColor: 'rgba(255, 105, 180, 0.2)'
        }
    };

    // Configuración API (NUEVA - conecta al backend real)
    const API_CONFIG = {
        BASE_URL: 'http://192.168.45.181:8002/api',
        RETRY_ATTEMPTS: 2,
        TIMEOUT: 5000
    };

    // Fallback data (si API falla)
    const PARODY_CRITICS_FALLBACK = {
        "338969": {
            "marco_aurelio": {
                author: "Marco Aurelio",
                rating: 8,
                content: `Como emperador y filósofo, he contemplado muchas transformaciones. Esta obra cinematográfica presenta una metamorfosis singular: un hombre común que abraza su destino adverso para convertirse en instrumento de justicia.

La **virtud surge del sufrimiento**, principio fundamental del estoicismo que aquí se manifiesta de forma... particular. El protagonista no lamenta su deformidad; la acepta y la utiliza. *"Acepta lo que no puedes cambiar, cambia lo que puedes, y ten sabiduría para distinguir la diferencia".*

**Reflexión filosófica**: ¿No somos todos, en cierto sentido, vengadores tóxicos de nuestras propias circunstancias?

> "La felicidad de tu vida depende de la calidad de tus pensamientos."

Y estos pensamientos, aunque grotescos, poseen cierta pureza de propósito.`,
                personality: "stoic",
                created_at: "2024-01-15T10:30:00Z",
                author_details: { rating: 8 }
            },
            "rosario_costras": {
                author: "Rosario Costras",
                rating: 2,
                content: `Como **persona racializada, de género fluido y neurodivergente**, me siento profundamente **triggereada** por esta película que perpetúa múltiples violencias sistémicas.

❌ **Problemas identificados**:
- Glorificación de la **masculinidad tóxica** a través de la venganza
- **Capacitismo** al presentar la discapacidad como superpoder
- **Clasismo** al retratar a la clase trabajadora como víctimas pasivas
- **Violencia patriarcal** normalizada contra mujeres
- **Apropiación cultural** del concepto de justicia vigilante

La transformación del protagonista es una **metáfora del capitalismo tardío** que consume y deforma los cuerpos de la clase obrera. Su "heroísmo" no es más que **fascismo encubierto**.

🏳️‍⚧️ **Representación**: CERO diversidad, CERO inclusión, CERO conciencia social.

Esta película debería venir con **avisos de contenido** por sus múltiples violencias. Es **hora de deconstruir** estos productos culturales problemáticos.

*#DecolonizeHollywood #RepresentationMatters #ToxicMasculinityKills*`,
                personality: "woke",
                created_at: "2024-01-16T14:45:00Z",
                author_details: { rating: 2 }
            }
        }
    };

    // NUEVA: Función para obtener críticas desde API
    async function fetchCriticsFromAPI(tmdbId) {
        try {
            console.log(`${logPrefix} Fetching from API: ${tmdbId}`);

            const response = await fetch(`${API_CONFIG.BASE_URL}/critics/${tmdbId}`, {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' },
                signal: AbortSignal.timeout(API_CONFIG.TIMEOUT)
            });

            if (response.ok) {
                const data = await response.json();
                console.log(`${logPrefix} ✅ API Success - ${data.total_critics} critics`);

                // Convertir formato API a formato interno
                const convertedCritics = {};
                Object.entries(data.critics).forEach(([key, critic]) => {
                    convertedCritics[key] = {
                        author: critic.author,
                        rating: critic.rating,
                        content: critic.content,
                        personality: critic.personality,
                        created_at: critic.generated_at,
                        author_details: { rating: critic.rating }
                    };
                });

                return convertedCritics;
            } else {
                throw new Error(`API responded with ${response.status}`);
            }
        } catch (error) {
            console.warn(`${logPrefix} API failed: ${error.message}`);
            return null;
        }
    }

    // Función para obtener TMDB ID actual (TU CÓDIGO ORIGINAL)
    function getCurrentTmdbId() {
        try {
            const video = document.querySelector('video');
            if (!video) return null;

            const posterUrl = video.getAttribute('poster');
            if (!posterUrl) return null;

            const itemIdMatch = posterUrl.match(/\/Items\/([a-f0-9]+)\//);
            return itemIdMatch ? itemIdMatch[1] : null;
        } catch (error) {
            console.error(`${logPrefix} Error getting TMDB ID:`, error);
            return null;
        }
    }

    // Función para obtener TMDB ID desde URL de página de detalles (TU CÓDIGO ORIGINAL)
    function getTmdbIdFromDetailsPage() {
        try {
            const urlParams = new URLSearchParams(window.location.hash.split('?')[1]);
            return urlParams.get('id');
        } catch (error) {
            console.error(`${logPrefix} Error getting ID from URL:`, error);
            return null;
        }
    }

    // Escape HTML (TU CÓDIGO ORIGINAL)
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Parser Markdown simplificado (TU CÓDIGO ORIGINAL)
    function parseMarkdown(text) {
        if (!text) return '';

        let html = escapeHtml(text);
        html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
        html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');
        html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
        html = html.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>');
        html = '<p>' + html + '</p>';

        return html;
    }

    // Crear elemento de crítica parodia con temas personalizados (TU CÓDIGO ORIGINAL)
    function createParodyCriticCard(critic, criticId) {
        const criticCard = document.createElement('div');
        const theme = CHARACTER_THEMES[criticId] || CHARACTER_THEMES['marco_aurelio'];

        criticCard.className = 'parody-critic-card';
        criticCard.setAttribute('data-character', criticId);

        const content = critic.content || 'Sin contenido disponible';
        const PREVIEW_LENGTH = 300;
        const isLongReview = content.length > PREVIEW_LENGTH;
        const previewContent = isLongReview ? content.substring(0, PREVIEW_LENGTH) : content;

        const reviewDate = critic.created_at ?
            new Date(critic.created_at).toLocaleDateString('es-ES', {
                year: 'numeric', month: 'short', day: 'numeric'
            }) : '';

        const rating = critic.author_details?.rating;
        const ratingDisplay = rating ?
            `<span class="parody-critic-rating" style="color: ${theme.color}; background: ${theme.accentColor};">⭐ ${rating}/10</span>` : '';

        criticCard.innerHTML = `
            <div class="parody-critic-header">
                <div class="parody-critic-author-info">
                    <strong class="parody-critic-author" style="color: ${theme.color};">
                        ${theme.emoji} ${escapeHtml(critic.author)}
                    </strong>
                    <span class="parody-critic-date">${reviewDate}</span>
                </div>
                ${ratingDisplay}
            </div>
            <div class="parody-critic-content">
                <div class="parody-critic-text"></div>
            </div>
        `;

        criticCard.style.borderLeft = `4px solid ${theme.borderColor}`;

        const textElement = criticCard.querySelector('.parody-critic-text');
        textElement.innerHTML = parseMarkdown(previewContent) +
            (isLongReview ? `<span class="parody-critic-toggle" style="color: ${theme.color};"> ...leer más</span>` : '');

        if (isLongReview) {
            textElement.addEventListener('click', function(e) {
                if (e.target.classList.contains('parody-critic-toggle')) {
                    const isExpanded = textElement.classList.contains('expanded');

                    if (!isExpanded) {
                        textElement.innerHTML = parseMarkdown(content) +
                            `<span class="parody-critic-toggle" style="color: ${theme.color};"> ...leer menos</span>`;
                        textElement.classList.add('expanded');
                    } else {
                        textElement.innerHTML = parseMarkdown(previewContent) +
                            `<span class="parody-critic-toggle" style="color: ${theme.color};"> ...leer más</span>`;
                        textElement.classList.remove('expanded');
                    }
                }
            });
        }

        return criticCard;
    }

    // Crear sección completa de críticos parodia (TU CÓDIGO ORIGINAL)
    function createParodyCriticsSection(critics, dataSource = 'unknown') {
        const section = document.createElement('details');
        section.className = 'detailSection parody-critics-section';
        section.setAttribute('open', '');

        const summary = document.createElement('summary');
        summary.className = 'sectionTitle';

        // Mostrar badge de estado de conexión
        const statusBadge = dataSource === 'api' ? '🌐' : '📦';
        const statusText = dataSource === 'api' ? 'API' : 'Demo';

        summary.innerHTML = `🎭 Críticos de la Casa (${Object.keys(critics).length}) ${statusBadge} ${statusText} <i class="material-icons expand-icon">expand_more</i>`;
        section.appendChild(summary);

        const container = document.createElement('div');
        container.className = 'parody-critics-container';

        Object.entries(critics).forEach(([criticId, critic]) => {
            container.appendChild(createParodyCriticCard(critic, criticId));
        });

        section.appendChild(container);
        return section;
    }

    // Inyectar CSS personalizado (TU DISEÑO ORIGINAL HERMOSO)
    function injectParodyCss() {
        const styleId = 'parody-critics-styles';
        if (document.getElementById(styleId)) return;

        const style = document.createElement('style');
        style.id = styleId;
        style.textContent = `
            .parody-critics-section {
                margin: 2em 0 1em 0;
                display: flex !important;
                flex-direction: column;
            }
            .parody-critics-section summary {
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: space-between;
                user-select: none;
                color: rgba(255, 255, 255, 0.8);
                padding-bottom: 0.5em;
            }
            .parody-critics-section summary .expand-icon {
                color: rgba(255, 255, 255, 0.8);
                transition: transform 0.2s ease-in-out;
                font-size: 1.2em;
            }
            .parody-critics-section[open] summary .expand-icon {
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
            .parody-critic-card[data-character="marco_aurelio"]:hover {
                box-shadow: 0 4px 12px rgba(139, 69, 19, 0.2);
            }
            .parody-critic-card[data-character="rosario_costras"]:hover {
                box-shadow: 0 4px 12px rgba(255, 105, 180, 0.2);
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
                margin: 1em 0;
                color: #ccc;
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
                color: #ffd700;
                font-weight: bold;
                cursor: pointer;
                text-decoration: underline;
                margin-left: 0.5em;
            }
            .parody-critic-toggle:hover {
                color: #ffed4e;
            }
        `;
        document.head.appendChild(style);
    }

    // Procesar e inyectar críticos (HÍBRIDO: API + Fallback)
    async function processCritics(critics, dataSource = 'unknown') {
        if (!critics) {
            console.log(`${logPrefix} No parody critics found`);
            return;
        }

        const existingSection = document.querySelector('.parody-critics-section');
        if (existingSection) {
            console.log(`${logPrefix} Section already exists, skipping injection`);
            return;
        }

        const parodySection = createParodyCriticsSection(critics, dataSource);

        const enhancedReviews = document.querySelector('.tmdb-reviews-section');
        const insertionPoint = enhancedReviews ||
                             document.querySelector('.streaming-lookup-container') ||
                             document.querySelector('.itemExternalLinks') ||
                             document.querySelector('.tagline');

        if (insertionPoint && insertionPoint.parentNode) {
            if (!document.querySelector('.parody-critics-section')) {
                if (enhancedReviews) {
                    enhancedReviews.after(parodySection);
                } else {
                    insertionPoint.parentNode.insertBefore(parodySection, insertionPoint.nextSibling);
                }
                console.log(`${logPrefix} Parody critics section injected successfully! 🎭`);
            }
        } else {
            console.warn(`${logPrefix} Could not find insertion point`);
        }
    }

    // Inyectar críticos en la página (NUEVA VERSIÓN HÍBRIDA)
    async function injectParodyCritics() {
        if (document.querySelector('.parody-critics-section')) {
            console.log(`${logPrefix} Section already exists`);
            return;
        }

        const itemId = getTmdbIdFromDetailsPage() || getCurrentTmdbId();
        if (!itemId) {
            console.log(`${logPrefix} No item ID found`);
            return;
        }

        console.log(`${logPrefix} Processing item ID: ${itemId}`);

        let critics = null;
        let dataSource = 'fallback';

        // Intentar obtener TMDB ID y buscar en API
        if (window.ApiClient) {
            try {
                const userId = window.ApiClient.getCurrentUserId();
                const item = await window.ApiClient.getItem(userId, itemId);
                const tmdbId = item?.ProviderIds?.Tmdb;

                if (tmdbId) {
                    console.log(`${logPrefix} Found TMDB ID: ${tmdbId}`);

                    // Intentar API primero
                    critics = await fetchCriticsFromAPI(tmdbId);
                    if (critics) {
                        dataSource = 'api';
                    } else {
                        // Fallback a datos locales
                        critics = PARODY_CRITICS_FALLBACK[tmdbId];
                        dataSource = 'fallback';
                        console.log(`${logPrefix} Using fallback data for ${tmdbId}`);
                    }
                }
            } catch (error) {
                console.warn(`${logPrefix} Error getting TMDB ID: ${error}`);
            }
        }

        // Si no encontramos nada, usar datos de prueba
        if (!critics) {
            critics = PARODY_CRITICS_FALLBACK["338969"];
            dataSource = 'fallback';
        }

        await processCritics(critics, dataSource);
    }

    // Monitor de páginas (TU CÓDIGO ORIGINAL)
    function startMonitoring() {
        injectParodyCss();

        let processedPages = new Set();
        let isProcessing = false;

        const processPageSafely = () => {
            if (isProcessing) return;

            const currentUrl = window.location.hash;
            const isDetailsPage = currentUrl.includes('details') || currentUrl.includes('id=');

            if (!isDetailsPage) return;
            if (processedPages.has(currentUrl)) return;

            isProcessing = true;
            processedPages.add(currentUrl);

            setTimeout(async () => {
                await injectParodyCritics();
                isProcessing = false;
            }, 1500);
        };

        let currentHash = window.location.hash;
        setInterval(() => {
            if (window.location.hash !== currentHash) {
                currentHash = window.location.hash;
                processedPages.clear();
                processPageSafely();
            }
        }, 500);

        processPageSafely();
        console.log(`${logPrefix} Monitoring started (API + Fallback hybrid) 🎭`);
    }

    // Inicialización
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', startMonitoring);
    } else {
        startMonitoring();
    }

    console.log(`${logPrefix} Hybrid Parody Critics script loaded! 🎭`);
})();