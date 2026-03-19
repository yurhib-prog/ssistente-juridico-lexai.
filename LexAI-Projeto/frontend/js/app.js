/**
 * LexAI — Assistente Jurídico com IA
 * Frontend Application Logic
 * 
 * Funciona em modo demo (standalone) e pode se conectar
 * ao backend Python quando disponível.
 */

// Auto-detect API URL: same origin when deployed, fallback to localhost for dev
const API_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? `${window.location.protocol}//${window.location.hostname}:8000/api`
    : `${window.location.origin}/api`;

// ═══════════════════════════════════════════════════
// LexAI Application
// ═══════════════════════════════════════════════════

class LexAIApp {
    constructor() {
        this.currentView = 'dashboard';
        this.stats = { queries: 0, entities: 0, corrections: 0, docs: 10 };
        this.history = [];
        this.backendAvailable = false;

        // Initialize embedded modules
        this.grammar = new GrammarModule();
        this.entities = new EntityModule();
        this.search = new SearchModule();

        this.init();
    }

    init() {
        this.bindNavigation();
        this.bindChatInput();
        this.bindEditorInput();
        this.bindSearchInput();
        this.bindMobileMenu();
        this.checkBackend();
        this.updateStats();
    }

    // ─── Navigation ───
    bindNavigation() {
        document.querySelectorAll('.nav-item').forEach(btn => {
            btn.addEventListener('click', () => {
                const view = btn.dataset.view;
                this.switchView(view);
            });
        });
    }

    switchView(viewName) {
        // Update nav
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        const navBtn = document.querySelector(`[data-view="${viewName}"]`);
        if (navBtn) navBtn.classList.add('active');

        // Update view
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        const view = document.getElementById(`view-${viewName}`);
        if (view) view.classList.add('active');

        // Update title
        const titles = {
            dashboard: 'Dashboard',
            chat: 'Chat IA',
            editor: 'Editor Jurídico',
            analysis: 'Análise de Documentos',
            search: 'Busca Legal'
        };
        document.getElementById('page-title').textContent = titles[viewName] || viewName;
        this.currentView = viewName;

        // Close mobile sidebar
        document.getElementById('sidebar').classList.remove('open');
    }

    bindMobileMenu() {
        document.getElementById('mobile-menu-btn').addEventListener('click', () => {
            document.getElementById('sidebar').classList.toggle('open');
        });
    }

    // ─── Backend Check ───
    async checkBackend() {
        try {
            const resp = await fetch(`${API_URL}/saude`, { signal: AbortSignal.timeout(3000) });
            if (resp.ok) {
                this.backendAvailable = true;
                this.showToast('Backend Python conectado!', 'success');
            }
        } catch {
            this.backendAvailable = false;
            console.log('Backend não disponível. Rodando em modo demo.');
        }
    }

    // ─── Chat ───
    bindChatInput() {
        const input = document.getElementById('chat-input');
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        input.addEventListener('input', () => {
            input.style.height = 'auto';
            input.style.height = Math.min(input.scrollHeight, 120) + 'px';
        });
    }

    sendSuggestion(text) {
        document.getElementById('chat-input').value = text;
        this.sendMessage();
    }

    async sendMessage() {
        const input = document.getElementById('chat-input');
        const query = input.value.trim();
        if (!query) return;

        // Add user message
        this.addChatMessage(query, 'user');
        input.value = '';
        input.style.height = 'auto';

        // Hide suggestions after first message
        document.getElementById('chat-suggestions').style.display = 'none';

        // Show typing indicator
        const typingId = this.addTypingIndicator();

        try {
            let response;

            if (this.backendAvailable) {
                const resp = await fetch(`${API_URL}/consultar`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query, top_k: 5 })
                });
                response = await resp.json();
            } else {
                // Demo mode - process locally
                await this.sleep(800 + Math.random() * 800);
                response = this.processQueryLocally(query);
            }

            // Remove typing indicator
            this.removeTypingIndicator(typingId);

            // Add response
            this.addChatResponse(response);

            // Update stats
            this.stats.queries++;
            this.stats.entities += (response.entidades || []).length;
            this.stats.corrections += (response.correcoes_gramaticais || []).length;
            this.updateStats();

            // Add to activity
            this.addActivity(query, 'consulta');

        } catch (err) {
            this.removeTypingIndicator(typingId);
            this.addChatMessage('Erro ao processar consulta. Tente novamente.', 'system');
            this.showToast('Erro no processamento', 'error');
        }
    }

    processQueryLocally(query) {
        const searchResults = this.search.search(query);
        const entities = this.entities.extract(query);
        const grammarResult = this.grammar.correct(query);

        // Add entities from results
        searchResults.forEach(r => {
            entities.push(...this.entities.extract(r.content));
        });

        // Deduplicate entities
        const seen = new Set();
        const uniqueEntities = entities.filter(e => {
            const key = `${e.tipo}-${e.valor}`;
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
        });

        // Generate response text
        let responseText = '📋 **Análise Jurídica**\n\n';
        responseText += 'Com base na análise dos documentos recuperados:\n\n';
        responseText += '📚 **Fundamentos Legais Encontrados:**\n\n';

        searchResults.slice(0, 3).forEach((r, i) => {
            responseText += `**${i + 1}. ${r.source}** (relevância: ${Math.round(r.score * 100)}%)\n\n`;
            responseText += `> ${r.content.substring(0, 250)}${r.content.length > 250 ? '...' : ''}\n\n`;
        });

        const themes = uniqueEntities.filter(e => e.tipo === 'tema_juridico').map(e => e.valor);
        if (themes.length > 0) {
            responseText += `📎 **Temas Jurídicos:** ${themes.join(', ')}\n\n`;
        }

        const confidence = searchResults.length > 0
            ? Math.min(0.95, searchResults.reduce((a, r) => a + r.score, 0) / searchResults.length * 2)
            : 0.2;
        const level = confidence > 0.7 ? 'alta' : confidence > 0.4 ? 'média' : 'baixa';
        responseText += `\n⚖️ **Confiança:** ${Math.round(confidence * 100)}% (${level})\n\n`;
        responseText += `⚠️ *Esta análise é gerada automaticamente e não substitui a consulta a um profissional jurídico qualificado.*`;

        return {
            query_original: query,
            query_corrigida: grammarResult.corrected,
            resposta: responseText,
            score_confianca: confidence,
            temas: themes,
            entidades: uniqueEntities.slice(0, 15).map(e => ({
                tipo: e.tipo, valor: e.valor, confianca: e.confidence
            })),
            documentos_relevantes: searchResults.slice(0, 5).map(r => ({
                id: r.id, conteudo: r.content, score_combinado: r.score,
                metadata: { fonte: r.source }
            })),
            correcoes_gramaticais: grammarResult.corrections,
            referencias_normativas: {},
            tempo_processamento: 0.5 + Math.random() * 0.5
        };
    }

    addChatMessage(text, type) {
        const container = document.getElementById('chat-messages');
        const div = document.createElement('div');
        div.className = `message ${type}`;

        if (type === 'user') {
            div.innerHTML = `
                <div class="message-avatar user-avatar">U</div>
                <div class="message-content">
                    <div class="message-header">
                        <span class="message-name">Você</span>
                        <span class="message-time">${this.formatTime()}</span>
                    </div>
                    <div class="message-text"><p>${this.escapeHtml(text)}</p></div>
                </div>`;
        } else {
            div.innerHTML = `
                <div class="message-avatar system-avatar">
                    <svg viewBox="0 0 32 32" fill="none">
                        <path d="M16 2L4 8v8c0 7.732 5.12 14.96 12 16 6.88-1.04 12-8.268 12-16V8L16 2z" fill="url(#g1)" opacity="0.3"/>
                        <path d="M12 14h8M12 18h6M16 10v2" stroke="url(#g1)" stroke-width="1.5" stroke-linecap="round"/>
                        <defs><linearGradient id="g1" x1="4" y1="2" x2="28" y2="26"><stop stop-color="#60a5fa"/><stop offset="1" stop-color="#a78bfa"/></linearGradient></defs>
                    </svg>
                </div>
                <div class="message-content">
                    <div class="message-header">
                        <span class="message-name">LexAI</span>
                        <span class="message-time">${this.formatTime()}</span>
                    </div>
                    <div class="message-text"><p>${this.escapeHtml(text)}</p></div>
                </div>`;
        }

        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    }

    addChatResponse(response) {
        const container = document.getElementById('chat-messages');
        const div = document.createElement('div');
        div.className = 'message system';

        const htmlContent = this.markdownToHtml(response.resposta || 'Sem resposta disponível.');

        let entitiesHtml = '';
        if (response.entidades && response.entidades.length > 0) {
            const tags = response.entidades.slice(0, 10).map(e => {
                const cls = this.entityClass(e.tipo);
                return `<span class="entity-tag ${cls}">${e.tipo}: ${e.valor}</span>`;
            }).join(' ');
            entitiesHtml = `<div style="margin-top:12px;display:flex;flex-wrap:wrap;gap:4px;">${tags}</div>`;
        }

        let correctionHtml = '';
        if (response.correcoes_gramaticais && response.correcoes_gramaticais.length > 0) {
            correctionHtml = `<div style="margin-top:8px;font-size:0.78rem;color:var(--accent-amber);">
                ✍️ ${response.correcoes_gramaticais.length} correção(ões) sugerida(s) na query
            </div>`;
        }

        const timeHtml = response.tempo_processamento
            ? `<div style="margin-top:8px;font-size:0.72rem;color:var(--text-tertiary);">⏱️ ${response.tempo_processamento.toFixed(3)}s</div>`
            : '';

        div.innerHTML = `
            <div class="message-avatar system-avatar">
                <svg viewBox="0 0 32 32" fill="none">
                    <path d="M16 2L4 8v8c0 7.732 5.12 14.96 12 16 6.88-1.04 12-8.268 12-16V8L16 2z" fill="url(#g2)" opacity="0.3"/>
                    <path d="M12 14h8M12 18h6M16 10v2" stroke="url(#g2)" stroke-width="1.5" stroke-linecap="round"/>
                    <defs><linearGradient id="g2" x1="4" y1="2" x2="28" y2="26"><stop stop-color="#60a5fa"/><stop offset="1" stop-color="#a78bfa"/></linearGradient></defs>
                </svg>
            </div>
            <div class="message-content">
                <div class="message-header">
                    <span class="message-name">LexAI</span>
                    <span class="message-time">${this.formatTime()}</span>
                </div>
                <div class="message-text">${htmlContent}${entitiesHtml}${correctionHtml}${timeHtml}</div>
            </div>`;

        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    }

    addTypingIndicator() {
        const container = document.getElementById('chat-messages');
        const id = 'typing-' + Date.now();
        const div = document.createElement('div');
        div.className = 'message system';
        div.id = id;
        div.innerHTML = `
            <div class="message-avatar system-avatar">
                <svg viewBox="0 0 32 32" fill="none">
                    <path d="M16 2L4 8v8c0 7.732 5.12 14.96 12 16 6.88-1.04 12-8.268 12-16V8L16 2z" fill="url(#g3)" opacity="0.3"/>
                    <defs><linearGradient id="g3" x1="4" y1="2" x2="28" y2="26"><stop stop-color="#60a5fa"/><stop offset="1" stop-color="#a78bfa"/></linearGradient></defs>
                </svg>
            </div>
            <div class="message-content">
                <div class="message-text" style="display:flex;gap:6px;padding:4px 0;">
                    <span class="typing-dot" style="animation:typingBounce 1.4s ease-in-out infinite;animation-delay:0s;">●</span>
                    <span class="typing-dot" style="animation:typingBounce 1.4s ease-in-out infinite;animation-delay:0.2s;">●</span>
                    <span class="typing-dot" style="animation:typingBounce 1.4s ease-in-out infinite;animation-delay:0.4s;">●</span>
                </div>
            </div>`;

        // Inject keyframes if not already present
        if (!document.getElementById('typing-styles')) {
            const style = document.createElement('style');
            style.id = 'typing-styles';
            style.textContent = `@keyframes typingBounce{0%,60%,100%{transform:translateY(0);opacity:0.3;}30%{transform:translateY(-6px);opacity:1;}}`;
            document.head.appendChild(style);
        }

        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
        return id;
    }

    removeTypingIndicator(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    // ─── Editor ───
    bindEditorInput() {
        const input = document.getElementById('editor-input');
        input.addEventListener('input', () => {
            document.getElementById('char-count').textContent = `${input.value.length} caracteres`;
        });
    }

    loadSampleText() {
        const sample = `Conforme o art 1 da Lei 4.504/64, o Estatuto da Terra estabelece através de seus dispositivos a reforma agrária. O mandado de seguranca foi impetrado face ao exposto, considerando o fumus boni iuris e o periculum in mora.

A grande maioria dos réus compareceu pessoalmente à audiência ,, tendo em vista que o habeas-corpus havia sido concedido há anos atrás.

De acordo com o Art. 186 da Constituição Federal, a propriedade rural deve cumprir sua função social. O IBAMA realizou fiscalização em area de preservação permanente conforme Lei 12.651/12.

O STF decidiu na ADI 3239 que o marco temporal para reconhecimento de terras quilombolas não deve se limitar à data da promulgação da CF/88. Processo nº 0001234-56.2023.8.26.0100.

Valor da indenização fixado em R$ 250.000,00, com prazo de 30 dias úteis para pagamento. CPF do requerente: 123.456.789-00.`;

        document.getElementById('editor-input').value = sample;
        document.getElementById('char-count').textContent = `${sample.length} caracteres`;
        this.showToast('Texto exemplo carregado', 'info');
    }

    async correctText() {
        const text = document.getElementById('editor-input').value.trim();
        if (!text) {
            this.showToast('Digite ou cole um texto primeiro', 'warning');
            return;
        }

        this.showLoading(true);

        try {
            let result;

            if (this.backendAvailable) {
                const resp = await fetch(`${API_URL}/corrigir`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ texto: text })
                });
                result = await resp.json();
            } else {
                await this.sleep(500);
                result = this.grammar.correct(text);
                result = {
                    texto_original: text,
                    texto_corrigido: result.corrected,
                    correcoes: result.corrections,
                    resumo: result.summary
                };
            }

            // Display result
            this.displayEditorOutput(result);
            this.stats.corrections += (result.correcoes || []).length;
            this.updateStats();
            this.addActivity('Correção gramatical', 'correção');

        } catch (err) {
            this.showToast('Erro na correção', 'error');
        }

        this.showLoading(false);
    }

    displayEditorOutput(result) {
        const output = document.getElementById('editor-output');
        const corrections = result.correcoes || [];

        // Build highlighted text
        let html = this.escapeHtml(result.texto_corrigido || result.texto_original);

        // Count by severity
        const counts = { erro: 0, aviso: 0, info: 0, critico: 0 };
        corrections.forEach(c => { counts[c.severidade] = (counts[c.severidade] || 0) + 1; });

        document.getElementById('correction-count').textContent =
            `${corrections.length} correção(ões) — ❌${counts.erro} ⚠️${counts.aviso} ℹ️${counts.info}`;

        output.innerHTML = `<div style="white-space:pre-wrap;word-wrap:break-word;">${html}</div>`;

        // Show corrections panel
        if (corrections.length > 0) {
            const panel = document.getElementById('corrections-panel');
            const list = document.getElementById('corrections-list');

            const icons = { erro: '❌', aviso: '⚠️', info: 'ℹ️', critico: '🚨' };

            list.innerHTML = corrections.map(c => `
                <div class="correction-item ${c.severidade}">
                    <span class="correction-icon">${icons[c.severidade] || '•'}</span>
                    <div class="correction-details">
                        <div class="correction-type">${c.tipo}</div>
                        <div class="correction-change">
                            <span class="old">${this.escapeHtml(c.texto_original)}</span> → 
                            <span class="new">${this.escapeHtml(c.sugestao)}</span>
                        </div>
                        <div class="correction-explanation">${this.escapeHtml(c.explicacao)}</div>
                    </div>
                </div>
            `).join('');

            panel.style.display = 'block';
        }

        this.showToast(`${corrections.length} correção(ões) encontrada(s)`, 'success');
    }

    async extractEntities() {
        const text = document.getElementById('editor-input').value.trim();
        if (!text) {
            this.showToast('Digite ou cole um texto primeiro', 'warning');
            return;
        }

        this.showLoading(true);

        try {
            let result;

            if (this.backendAvailable) {
                const resp = await fetch(`${API_URL}/entidades`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ texto: text })
                });
                result = await resp.json();
            } else {
                await this.sleep(400);
                const entities = this.entities.extract(text);
                result = { entidades: entities, total: entities.length };
            }

            this.displayEntitiesOutput(result);
            this.stats.entities += result.total || 0;
            this.updateStats();
            this.addActivity('Extração de entidades', 'entidades');

        } catch (err) {
            this.showToast('Erro na extração', 'error');
        }

        this.showLoading(false);
    }

    displayEntitiesOutput(result) {
        const output = document.getElementById('editor-output');
        const entities = result.entidades || [];

        if (entities.length === 0) {
            output.innerHTML = '<div class="empty-state small"><p>Nenhuma entidade encontrada.</p></div>';
            return;
        }

        let html = `<div style="margin-bottom:16px;font-weight:600;font-size:0.9rem;">
            🏛️ ${entities.length} entidade(s) encontrada(s)
        </div>`;
        html += '<div style="display:flex;flex-wrap:wrap;gap:6px;">';

        entities.forEach(e => {
            const cls = this.entityClass(e.tipo);
            html += `<span class="entity-tag ${cls}" title="${e.tipo}">${e.tipo}: ${e.valor}</span>`;
        });

        html += '</div>';

        // Group by type
        const grouped = {};
        entities.forEach(e => {
            if (!grouped[e.tipo]) grouped[e.tipo] = [];
            grouped[e.tipo].push(e.valor);
        });

        html += '<div style="margin-top:20px;">';
        Object.entries(grouped).forEach(([tipo, valores]) => {
            html += `<div style="margin-bottom:12px;">
                <div style="font-size:0.78rem;font-weight:600;color:var(--text-secondary);text-transform:uppercase;margin-bottom:4px;">${tipo.replace(/_/g, ' ')}</div>
                <div style="font-size:0.85rem;color:var(--text-primary);">${[...new Set(valores)].join(', ')}</div>
            </div>`;
        });
        html += '</div>';

        output.innerHTML = html;
        document.getElementById('correction-count').textContent = `${entities.length} entidade(s)`;
        this.showToast(`${entities.length} entidade(s) extraída(s)`, 'success');
    }

    clearEditor() {
        document.getElementById('editor-input').value = '';
        document.getElementById('editor-output').innerHTML = `
            <div class="empty-state small">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                <p>Cole um texto e clique em <strong>"Corrigir"</strong></p>
            </div>`;
        document.getElementById('char-count').textContent = '0 caracteres';
        document.getElementById('correction-count').textContent = '';
        document.getElementById('corrections-panel').style.display = 'none';
    }

    // ─── Analysis ───
    async analyzeDocument() {
        const text = document.getElementById('analysis-input').value.trim();
        if (!text) {
            this.showToast('Cole o texto do documento', 'warning');
            return;
        }

        this.showLoading(true);

        try {
            await this.sleep(600);

            // Local analysis
            const entities = this.entities.extract(text);
            const grammarResult = this.grammar.correct(text);
            const chunks = this.simpleChunking(text);

            // Display results
            const resultsDiv = document.getElementById('analysis-results');
            resultsDiv.style.display = 'block';

            // Structure
            document.getElementById('structure-body').innerHTML = `
                <div style="font-size:0.88rem;">
                    <div style="margin-bottom:8px;"><strong>${chunks.length}</strong> segmento(s) identificado(s)</div>
                    ${chunks.map((c, i) => `
                        <div style="padding:8px 10px;margin:4px 0;background:var(--bg-tertiary);border-radius:var(--radius-sm);border-left:3px solid var(--accent-blue);">
                            <span style="font-size:0.72rem;color:var(--text-tertiary);">${c.type}</span><br>
                            <span style="font-size:0.82rem;">${this.escapeHtml(c.content.substring(0, 120))}${c.content.length > 120 ? '...' : ''}</span>
                        </div>
                    `).join('')}
                </div>`;

            // Entities
            const grouped = {};
            entities.forEach(e => {
                if (!grouped[e.tipo]) grouped[e.tipo] = [];
                if (!grouped[e.tipo].includes(e.valor)) grouped[e.tipo].push(e.valor);
            });

            document.getElementById('entities-body').innerHTML = `
                <div style="font-size:0.88rem;">
                    <div style="margin-bottom:8px;"><strong>${entities.length}</strong> entidade(s)</div>
                    ${Object.entries(grouped).map(([tipo, vals]) => `
                        <div style="margin-bottom:10px;">
                            <span style="font-size:0.72rem;font-weight:600;color:var(--text-tertiary);text-transform:uppercase;">${tipo.replace(/_/g,' ')}</span>
                            <div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:4px;">
                                ${vals.map(v => `<span class="entity-tag ${this.entityClass(tipo)}">${v}</span>`).join('')}
                            </div>
                        </div>  
                    `).join('')}
                </div>`;

            // Corrections
            const corrections = grammarResult.corrections;
            document.getElementById('corrections-body').innerHTML = `
                <div style="font-size:0.88rem;">
                    <div style="margin-bottom:8px;"><strong>${corrections.length}</strong> correção(ões)</div>
                    ${corrections.slice(0, 10).map(c => {
                        const icons = { erro: '❌', aviso: '⚠️', info: 'ℹ️', critico: '🚨' };
                        return `<div style="padding:6px 0;border-bottom:1px solid var(--border-color);font-size:0.82rem;">
                            ${icons[c.severidade] || '•'} <span style="color:var(--accent-rose);text-decoration:line-through;">${this.escapeHtml(c.texto_original)}</span>
                            → <span style="color:var(--accent-emerald);">${this.escapeHtml(c.sugestao)}</span>
                        </div>`;
                    }).join('')}
                </div>`;

            // References
            document.getElementById('references-body').innerHTML = `
                <div style="font-size:0.88rem;">
                    ${entities.filter(e => ['lei', 'artigo', 'sumula', 'jurisprudencia'].includes(e.tipo)).length > 0
                        ? entities.filter(e => ['lei', 'artigo', 'sumula', 'jurisprudencia'].includes(e.tipo))
                            .map(e => `<div style="padding:4px 0;"><span class="entity-tag ${this.entityClass(e.tipo)}">${e.tipo}</span> ${e.valor}</div>`).join('')
                        : '<p style="color:var(--text-tertiary);">Nenhuma referência normativa encontrada.</p>'}
                </div>`;

            this.stats.entities += entities.length;
            this.stats.corrections += corrections.length;
            this.updateStats();
            this.addActivity('Análise de documento', 'análise');
            this.showToast('Análise concluída!', 'success');

        } catch (err) {
            this.showToast('Erro na análise', 'error');
        }

        this.showLoading(false);
    }

    simpleChunking(text) {
        const chunks = [];
        const artPattern = /Art\.\s*\d+/g;
        const parts = text.split(/(?=Art\.\s*\d+)/);

        parts.forEach(part => {
            part = part.trim();
            if (!part) return;
            const match = part.match(/^Art\.\s*(\d+)/);
            chunks.push({
                type: match ? `Artigo ${match[1]}` : 'Texto',
                content: part
            });
        });

        return chunks.length > 0 ? chunks : [{ type: 'Texto', content: text }];
    }

    // ─── Search ───
    bindSearchInput() {
        const input = document.getElementById('legal-search-input');
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') this.legalSearch();
        });
    }

    async legalSearch() {
        const query = document.getElementById('legal-search-input').value.trim();
        if (!query) {
            this.showToast('Digite um termo de busca', 'warning');
            return;
        }

        const method = document.querySelector('input[name="search-method"]:checked')?.value || 'hibrido';

        this.showLoading(true);

        try {
            await this.sleep(400);
            const results = this.search.search(query, method);
            this.displaySearchResults(results, method);
            this.addActivity(`Busca: "${query}"`, 'busca');
        } catch (err) {
            this.showToast('Erro na busca', 'error');
        }

        this.showLoading(false);
    }

    displaySearchResults(results, method) {
        const container = document.getElementById('search-results');

        if (results.length === 0) {
            container.innerHTML = `<div class="empty-state"><p>Nenhum resultado encontrado. Tente termos diferentes.</p></div>`;
            return;
        }

        const methodLabels = { hibrido: 'Híbrido', bm25: 'BM25', semantico: 'Semântico' };

        container.innerHTML = `
            <div style="margin-bottom:16px;display:flex;align-items:center;justify-content:space-between;">
                <span style="font-weight:600;">${results.length} resultado(s)</span>
                <span class="badge badge-blue">Método: ${methodLabels[method] || method}</span>
            </div>
            ${results.map(r => `
                <div class="search-result-item">
                    <div class="result-item-header">
                        <span class="result-item-source">📜 ${r.source}</span>
                        <div class="result-item-score">
                            <span class="score-badge badge-blue">${Math.round(r.score * 100)}%</span>
                            ${r.bm25 ? `<span class="score-badge badge-purple">BM25: ${Math.round(r.bm25 * 100)}%</span>` : ''}
                        </div>
                    </div>
                    <div class="result-item-content">${this.escapeHtml(r.content)}</div>
                    ${r.metadata?.area ? `<div style="margin-top:8px;"><span class="entity-tag tema">${r.metadata.area.replace(/_/g, ' ')}</span></div>` : ''}
                </div>
            `).join('')}
        `;
    }

    // ─── UI Utilities ───
    showLoading(show) {
        document.getElementById('loading-overlay').classList.toggle('active', show);
    }

    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `<span class="toast-icon">${icons[type]}</span><span class="toast-message">${message}</span>`;
        container.appendChild(toast);
        setTimeout(() => toast.remove(), 4000);
    }

    updateStats() {
        document.getElementById('total-queries').textContent = this.stats.queries;
        document.getElementById('total-docs').textContent = this.stats.docs;
        document.getElementById('total-entities').textContent = this.stats.entities;
        document.getElementById('total-corrections').textContent = this.stats.corrections;
    }

    addActivity(title, type) {
        const list = document.getElementById('activity-list');
        const colors = { consulta: 'var(--accent-blue)', correção: 'var(--accent-amber)', entidades: 'var(--accent-emerald)', análise: 'var(--accent-purple)', busca: 'var(--accent-rose)' };

        // Remove empty state
        const empty = list.querySelector('.empty-state');
        if (empty) empty.remove();

        const item = document.createElement('div');
        item.className = 'activity-item';
        item.innerHTML = `
            <div class="activity-dot" style="background:${colors[type] || 'var(--accent-blue)'};"></div>
            <div class="activity-info">
                <div class="activity-title">${this.escapeHtml(title)}</div>
                <div class="activity-time">${this.formatTime()}</div>
            </div>`;

        list.insertBefore(item, list.firstChild);

        // Keep max 10 items
        while (list.children.length > 10) {
            list.removeChild(list.lastChild);
        }

        this.history.push({ title, type, time: new Date().toISOString() });
    }

    formatTime() {
        return new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    }

    escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    markdownToHtml(text) {
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/^> (.*)/gm, '<blockquote>$1</blockquote>')
            .replace(/^- (.*)/gm, '<li>$1</li>')
            .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>')
            .replace(/^(.*)$/, '<p>$1</p>');
    }

    entityClass(tipo) {
        const map = {
            lei: 'lei', decreto: 'lei', medida_provisoria: 'lei', constituicao: 'lei',
            artigo: 'artigo', paragrafo: 'artigo', inciso: 'artigo', alinea: 'artigo',
            tribunal: 'tribunal', sumula: 'tribunal', jurisprudencia: 'tribunal',
            orgao: 'orgao',
            tema_juridico: 'tema',
            data: 'data', prazo: 'data',
            numero_processo: 'processo',
        };
        return map[tipo] || 'default';
    }

    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}


// ═══════════════════════════════════════════════════
// Grammar Module (Client-side)
// ═══════════════════════════════════════════════════

class GrammarModule {
    constructor() {
        this.ortografia = {
            'mandado de seguranca': 'mandado de segurança',
            'habeas-corpus': 'habeas corpus',
            'excecao': 'exceção', 'exceçao': 'exceção',
            'peticao': 'petição', 'petiçao': 'petição',
            'acordao': 'acórdão', 'acordão': 'acórdão',
            'prescriçao': 'prescrição', 'prescricao': 'prescrição',
            'constituiçao': 'constituição', 'constituicao': 'constituição',
            'jurisdiçao': 'jurisdição', 'jurisdicao': 'jurisdição',
            'usucapiao': 'usucapião',
            'indenisação': 'indenização', 'indenisacao': 'indenização',
            'desapropriaçao': 'desapropriação', 'desapropriacao': 'desapropriação',
        };

        this.redundancias = [
            ['elo de ligação', 'elo', "'Elo' já significa ligação"],
            ['há anos atrás', 'há anos', "'Há' já indica passado"],
            ['a grande maioria', 'a maioria', "'Maioria' já indica a maior parte"],
            ['comparecer pessoalmente', 'comparecer', "Já implica presença pessoal"],
        ];

        this.estilo = [
            ['através de', 'por meio de', "Prefira 'por meio de' na linguagem jurídica formal"],
            ['face ao exposto', 'ante o exposto', "A forma mais aceita é 'ante o exposto'"],
            ['tendo em vista que', 'considerando que', "Expressão mais adequada"],
        ];

        this.latinismos = {
            'fumus boni iuris': 'aparência do bom direito',
            'periculum in mora': 'perigo na demora',
            'habeas corpus': 'garantia de liberdade',
            'ad hoc': 'para este fim',
            'data venia': 'com a devida permissão',
            'ex nunc': 'a partir de agora',
            'ex tunc': 'desde então',
            'in dubio pro reo': 'na dúvida, a favor do réu',
            'sub judice': 'sob julgamento',
        };
    }

    correct(text) {
        const corrections = [];
        let corrected = text;

        // Orthography
        for (const [wrong, right] of Object.entries(this.ortografia)) {
            const regex = new RegExp(this.escapeRegex(wrong), 'gi');
            let match;
            while ((match = regex.exec(text)) !== null) {
                corrections.push({
                    tipo: 'ortografia', severidade: 'erro',
                    texto_original: match[0], sugestao: right,
                    explicacao: `Grafia correta: '${right}'`,
                    posicao_inicio: match.index, posicao_fim: match.index + match[0].length
                });
            }
            corrected = corrected.replace(regex, right);
        }

        // Redundancies
        this.redundancias.forEach(([red, sug, expl]) => {
            const regex = new RegExp(this.escapeRegex(red), 'gi');
            let match;
            while ((match = regex.exec(text)) !== null) {
                corrections.push({
                    tipo: 'redundancia', severidade: 'aviso',
                    texto_original: match[0], sugestao: sug,
                    explicacao: expl,
                    posicao_inicio: match.index, posicao_fim: match.index + match[0].length
                });
            }
        });

        // Style
        this.estilo.forEach(([term, sug, expl]) => {
            const regex = new RegExp('\\b' + this.escapeRegex(term) + '\\b', 'gi');
            let match;
            while ((match = regex.exec(text)) !== null) {
                corrections.push({
                    tipo: 'estilo', severidade: 'info',
                    texto_original: match[0], sugestao: sug,
                    explicacao: expl,
                    posicao_inicio: match.index, posicao_fim: match.index + match[0].length
                });
            }
        });

        // Double punctuation
        const dblPunct = /([.,;:!?])\1+/g;
        let m;
        while ((m = dblPunct.exec(text)) !== null) {
            corrections.push({
                tipo: 'pontuacao', severidade: 'erro',
                texto_original: m[0], sugestao: m[1],
                explicacao: 'Remover pontuação duplicada',
                posicao_inicio: m.index, posicao_fim: m.index + m[0].length
            });
            corrected = corrected.replace(m[0], m[1]);
        }

        // Space before punctuation
        const spacePunct = /\s+([.,;:!?])/g;
        while ((m = spacePunct.exec(text)) !== null) {
            corrections.push({
                tipo: 'pontuacao', severidade: 'aviso',
                texto_original: m[0], sugestao: m[1],
                explicacao: 'Remover espaço antes da pontuação',
                posicao_inicio: m.index, posicao_fim: m.index + m[0].length
            });
        }

        // Latinisms (informative)
        for (const [lat, trad] of Object.entries(this.latinismos)) {
            const regex = new RegExp(this.escapeRegex(lat), 'gi');
            while ((m = regex.exec(text)) !== null) {
                corrections.push({
                    tipo: 'latinismo', severidade: 'info',
                    texto_original: m[0], sugestao: m[0],
                    explicacao: `Latinismo: '${lat}' = ${trad}`,
                    posicao_inicio: m.index, posicao_fim: m.index + m[0].length
                });
            }
        }

        corrections.sort((a, b) => a.posicao_inicio - b.posicao_inicio);

        const counts = {};
        corrections.forEach(c => { counts[c.severidade] = (counts[c.severidade] || 0) + 1; });

        return {
            corrected,
            corrections,
            summary: { total: corrections.length, por_severidade: counts }
        };
    }

    escapeRegex(str) {
        return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }
}


// ═══════════════════════════════════════════════════
// Entity Extraction Module (Client-side)
// ═══════════════════════════════════════════════════

class EntityModule {
    constructor() {
        this.patterns = [
            { tipo: 'lei', regex: /Lei\s+(?:n[°º]?\s*)?(\d[\d.]*(?:\/\d{2,4})?)/gi },
            { tipo: 'lei', regex: /Lei\s+Complementar\s+(?:n[°º]?\s*)?(\d[\d.]*(?:\/\d{2,4})?)/gi },
            { tipo: 'decreto', regex: /Decreto(?:-[Ll]ei)?\s+(?:n[°º]?\s*)?(\d[\d.]*(?:\/\d{2,4})?)/gi },
            { tipo: 'constituicao', regex: /Constituição\s+Federal(?:\s+de\s+(\d{4}))?/gi },
            { tipo: 'constituicao', regex: /CF\/(\d{2,4})/gi },
            { tipo: 'artigo', regex: /Art\.?\s*(\d+)[°º]?/gi },
            { tipo: 'paragrafo', regex: /§\s*(\d+)[°º]?/gi },
            { tipo: 'sumula', regex: /Súmula\s+(?:Vinculante\s+)?(?:n[°º]?\s*)?(\d+)/gi },
            { tipo: 'jurisprudencia', regex: /(RE|REsp|HC|MS|ADI|ADPF|ADC)\s+(?:n[°º]?\s*)?([\d./-]+)/gi },
            { tipo: 'tribunal', regex: /\b(STF|STJ|TST|TSE|STM|TRF\d?|TJ[A-Z]{2}|CNJ)\b/g },
            { tipo: 'orgao', regex: /\b(IBAMA|MAPA|INCRA|FUNAI|ICMBio|ANVISA|CADE|TCU|MPF|OAB|AGU)\b/g },
            { tipo: 'data', regex: /(\d{1,2})\s+de\s+(janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\s+de\s+(\d{4})/gi },
            { tipo: 'prazo', regex: /(\d+)\s+(dias?|meses?|anos?)\s*(?:úteis|corridos)?/gi },
            { tipo: 'valor_monetario', regex: /R\$\s*([\d.,]+)/g },
            { tipo: 'numero_processo', regex: /(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})/g },
            { tipo: 'cpf', regex: /(\d{3}[.\s]?\d{3}[.\s]?\d{3}[.\s-]?\d{2})/g },
        ];

        this.temas = {
            'Direito Agrário': ['reforma agrária', 'propriedade rural', 'função social da terra', 'desapropriação', 'estatuto da terra', 'imóvel rural'],
            'Direito Ambiental': ['licenciamento ambiental', 'preservação permanente', 'reserva legal', 'desmatamento', 'crime ambiental', 'código florestal'],
            'Direito Constitucional': ['direitos fundamentais', 'constituição federal', 'mandado de segurança', 'habeas corpus'],
            'Direito Civil': ['contrato', 'propriedade', 'posse', 'usucapião', 'responsabilidade civil'],
        };
    }

    extract(text) {
        const entities = [];
        const seen = new Set();

        this.patterns.forEach(({ tipo, regex }) => {
            const r = new RegExp(regex.source, regex.flags);
            let match;
            while ((match = r.exec(text)) !== null) {
                const valor = match[1] || match[0];
                const key = `${tipo}:${valor}`;

                // Mask CPF (LGPD)
                let displayVal = valor;
                if (tipo === 'cpf') {
                    const digits = valor.replace(/\D/g, '');
                    if (digits.length === 11) displayVal = `***.***. ${digits.slice(6, 9)}-**`;
                }

                if (!seen.has(key)) {
                    seen.add(key);
                    entities.push({
                        tipo,
                        valor: displayVal,
                        texto_original: match[0],
                        confidence: 0.95
                    });
                }
            }
        });

        // Extract themes
        const textLower = text.toLowerCase();
        for (const [tema, termos] of Object.entries(this.temas)) {
            for (const termo of termos) {
                if (textLower.includes(termo)) {
                    const key = `tema_juridico:${tema}`;
                    if (!seen.has(key)) {
                        seen.add(key);
                        entities.push({
                            tipo: 'tema_juridico',
                            valor: tema,
                            texto_original: termo,
                            confidence: 0.85
                        });
                    }
                    break;
                }
            }
        }

        return entities;
    }
}


// ═══════════════════════════════════════════════════
// Search Module (Client-side)
// ═══════════════════════════════════════════════════

class SearchModule {
    constructor() {
        this.documents = [
            { id: 'lei_4504_art1', content: 'Art. 1º Esta Lei regula os direitos e obrigações concernentes aos bens imóveis rurais, para os fins de execução da Reforma Agrária e promoção da Política Agrícola. § 1º Considera-se Reforma Agrária o conjunto de medidas que visem a promover melhor distribuição da terra, mediante modificações no regime de sua posse e uso.', source: 'Lei 4.504/64 - Estatuto da Terra', metadata: { area: 'direito_agrario' } },
            { id: 'lei_4504_art2', content: 'Art. 2º É assegurada a todos a oportunidade de acesso à propriedade da terra, condicionada pela sua função social. § 1º A propriedade da terra desempenha integralmente a sua função social quando: a) favorece o bem-estar dos proprietários e trabalhadores; b) mantém níveis satisfatórios de produtividade; c) assegura a conservação dos recursos naturais; d) observa as disposições legais que regulam as justas relações de trabalho.', source: 'Lei 4.504/64 - Estatuto da Terra', metadata: { area: 'direito_agrario' } },
            { id: 'cf88_art184', content: 'Art. 184. Compete à União desapropriar por interesse social, para fins de reforma agrária, o imóvel rural que não esteja cumprindo sua função social, mediante prévia e justa indenização em títulos da dívida agrária.', source: 'Constituição Federal 1988', metadata: { area: 'direito_agrario' } },
            { id: 'cf88_art186', content: 'Art. 186. A função social é cumprida quando a propriedade rural atende: I - aproveitamento racional e adequado; II - utilização adequada dos recursos naturais e preservação do meio ambiente; III - observância das disposições que regulam as relações de trabalho; IV - exploração que favoreça o bem-estar.', source: 'Constituição Federal 1988', metadata: { area: 'direito_agrario' } },
            { id: 'lei_8629_art6', content: 'Art. 6º Considera-se propriedade produtiva aquela que, explorada econômica e racionalmente, atinge graus de utilização da terra e de eficiência na exploração. § 1º O grau de utilização da terra deverá ser igual ou superior a 80%.', source: 'Lei 8.629/93', metadata: { area: 'direito_agrario' } },
            { id: 'lei_6938_art2', content: 'Art. 2º A Política Nacional do Meio Ambiente tem por objetivo a preservação, melhoria e recuperação da qualidade ambiental propícia à vida, visando assegurar condições ao desenvolvimento socioeconômico e à proteção da dignidade da vida humana.', source: 'Lei 6.938/81 - Política Nacional do Meio Ambiente', metadata: { area: 'direito_ambiental' } },
            { id: 'lei_9605_art38', content: 'Art. 38. Destruir ou danificar floresta considerada de preservação permanente, mesmo que em formação, ou utilizá-la com infringência das normas de proteção: Pena - detenção, de um a três anos, ou multa, ou ambas cumulativamente.', source: 'Lei 9.605/98 - Crimes Ambientais', metadata: { area: 'direito_ambiental' } },
            { id: 'lei_12651_art3', content: 'Art. 3º Para os efeitos desta Lei, entende-se por: II - Área de Preservação Permanente (APP): área protegida, com a função ambiental de preservar os recursos hídricos, a paisagem, a estabilidade geológica e a biodiversidade.', source: 'Lei 12.651/12 - Código Florestal', metadata: { area: 'direito_ambiental' } },
            { id: 'sumula_stj_456', content: 'Súmula 456 do STJ: É legítima a cobrança de tarifa básica pelo uso dos serviços de telefonia fixa.', source: 'STJ - Súmula 456', metadata: { area: 'direito_civil' } },
            { id: 'stf_adi_3239', content: 'ADI 3239 - Terras Quilombolas: O STF decidiu que o marco temporal para reconhecimento de terras quilombolas não deve se limitar à data da promulgação da CF/88, reconhecendo o direito de propriedade das comunidades quilombolas.', source: 'STF - ADI 3239', metadata: { area: 'direito_agrario' } },
        ];

        this.stopwords = new Set(['a','o','e','é','de','do','da','dos','das','em','no','na','nos','nas','um','uma','por','para','com','que','se','ao','à','ou','como','mais','não','seu','sua','foi','são','ser','ter']);
    }

    tokenize(text) {
        return text.toLowerCase()
            .replace(/[^\w\sáàâãéèêíìîóòôõúùûçü]/g, ' ')
            .split(/\s+/)
            .filter(t => t.length > 1 && !this.stopwords.has(t));
    }

    bm25Score(queryTokens, docTokens) {
        const k1 = 1.5, b = 0.75;
        const avgDl = this.documents.reduce((a, d) => a + this.tokenize(d.content).length, 0) / this.documents.length;
        const dl = docTokens.length;
        const tf = {};
        docTokens.forEach(t => { tf[t] = (tf[t] || 0) + 1; });

        let score = 0;
        queryTokens.forEach(term => {
            if (!tf[term]) return;
            const termFreq = tf[term];
            const df = this.documents.filter(d => this.tokenize(d.content).includes(term)).length;
            const idf = Math.log((this.documents.length - df + 0.5) / (df + 0.5) + 1);
            score += idf * (termFreq * (k1 + 1)) / (termFreq + k1 * (1 - b + b * dl / avgDl));
        });

        return score;
    }

    semanticScore(queryTokens, docTokens) {
        const querySet = new Set(queryTokens);
        const docSet = new Set(docTokens);
        const intersection = [...querySet].filter(t => docSet.has(t));
        const union = new Set([...querySet, ...docSet]);
        return intersection.length / union.size;
    }

    search(query, method = 'hibrido') {
        const queryTokens = this.tokenize(query);
        const results = [];
        const alpha = 0.5;

        this.documents.forEach(doc => {
            const docTokens = this.tokenize(doc.content);
            const bm25 = this.bm25Score(queryTokens, docTokens);
            const semantic = this.semanticScore(queryTokens, docTokens);

            let score;
            if (method === 'bm25') score = bm25;
            else if (method === 'semantico') score = semantic;
            else score = (1 - alpha) * (bm25 / 10) + alpha * semantic; // Normalize BM25

            if (score > 0.01) {
                results.push({
                    id: doc.id,
                    content: doc.content,
                    source: doc.source,
                    score: Math.min(1, score),
                    bm25: bm25 / 10,
                    semantic,
                    metadata: doc.metadata
                });
            }
        });

        results.sort((a, b) => b.score - a.score);
        return results.slice(0, 5);
    }
}


// ═══════════════════════════════════════════════════
// Initialize App
// ═══════════════════════════════════════════════════

const app = new LexAIApp();
