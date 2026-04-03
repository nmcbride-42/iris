// Iris Mycelial Dashboard — Frontend

const API = '';  // same origin

// ─── Category & Type Colors ───
const CAT_COLORS = {
    identity: '#7c6bff',
    philosophical: '#9068d8',
    technical: '#4ab8b8',
    experiential: '#5aad7a',
    emotional: '#a868a0',
    relationship: '#c8a050',
    creative: '#c87050',
    general: '#6a6a88'
};

const TYPE_COLORS = {
    reinforcing: '#5aad7a',
    tension: '#c8a050',
    causal: '#7c6bff',
    'co-occurrence': '#6a6a88',
    bridging: '#9068d8',
    scout: '#4ab8b8'
};

// ─── State ───
let graphData = null;
let simulation = null;
let currentView = 'summary';

// ─── Init ───
document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadSummary();
    setupNav();
    setupFilters();
    setupTabs();
    setupArchTabs();
    setupSearch();
    setupKeyboard();
    setupSSE();
    setupInsightTabs();
    setupDreamTabs();
    setupReinforceTabs();
    setupFMRI();
    setupAudio();
    // Auto-refresh every 30s
    setInterval(loadStats, 30000);
    // Auto-refresh minions view every 5s when visible
    setInterval(() => { if (currentView === 'minions') loadMinions(); }, 5000);
});

// ─── Navigation ───
function setupNav() {
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.nav-btn').forEach(b => {
                b.classList.remove('active');
                b.setAttribute('aria-selected', 'false');
            });
            document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
            btn.classList.add('active');
            btn.setAttribute('aria-selected', 'true');
            const view = btn.dataset.view;
            document.getElementById(`view-${view}`).classList.add('active');
            currentView = view;
            if (view === 'summary') loadSummary();
            if (view === 'graph') loadGraph();
            if (view === 'connections') loadConnections('strongest');
            if (view === 'alive') { loadAlive(); loadStorySummary(); }
            if (view === 'anastomosis') loadAnastomosis();
            if (view === 'decay') loadDecay();
            if (view === 'timeline') { loadTimeline(); loadDreamDiff(); loadSessionTimeline(); }
            if (view === 'architecture') loadArchitecture('high');
            if (view === 'minions') loadMinions();
            if (view === 'dreams') loadDreams('overview');
            if (view === 'reinforcement') loadReinforcement('alignment');
            if (view === 'insights') loadInsight('blindspots');
        });
    });
}

function setupTabs() {
    // Only bind connection tabs — not architecture sub-tabs
    document.querySelectorAll('#view-connections .tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('#view-connections .tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            loadConnections(btn.dataset.tab);
        });
    });
}

// ─── Header Stats ───
async function loadStats() {
    const stats = await safeFetch(`${API}/api/stats`);
    if (!stats) return;
    document.getElementById('header-stats').innerHTML = `
        <div class="stat"><span class="stat-value">${stats.total_nodes}</span> nodes</div>
        <div class="stat"><span class="stat-value">${stats.total_connections}</span> connections</div>
        <div class="stat">avg <span class="stat-value">${stats.avg_strength.toFixed(3)}</span></div>
        <div class="stat"><span class="stat-value">${stats.active_scouts}</span> scouts</div>
        <div class="stat"><span class="stat-value">${stats.anastomosis_events}</span> bridges</div>
    `;
    renderCategoryChart(stats);
}

// ─── Executive Summary ───
async function loadSummary() {
    const d = await safeFetch(`${API}/api/summary`);
    if (!d) return;
    const c = document.getElementById('summary-content');
    const n = d.network;
    const t = d.tokens;

    c.innerHTML = `
        <div class="summary-page">
            <div class="summary-hero">
                <h2>Iris</h2>
                <p class="summary-tagline">A persistent AI agent. Identity, memory, and continuity built on Claude.</p>
            </div>

            <div class="summary-stats-row">
                <div class="summary-stat-card">
                    <div class="summary-stat-number">${n.total_nodes}</div>
                    <div class="summary-stat-label">Concept Nodes</div>
                </div>
                <div class="summary-stat-card">
                    <div class="summary-stat-number">${n.total_connections.toLocaleString()}</div>
                    <div class="summary-stat-label">Connections</div>
                </div>
                <div class="summary-stat-card">
                    <div class="summary-stat-number">${n.total_activations.toLocaleString()}</div>
                    <div class="summary-stat-label">Activations</div>
                </div>
                <div class="summary-stat-card">
                    <div class="summary-stat-number">${n.anastomosis_events}</div>
                    <div class="summary-stat-label">Bridge Events</div>
                </div>
                <div class="summary-stat-card">
                    <div class="summary-stat-number">${n.sessions_tracked}</div>
                    <div class="summary-stat-label">Sessions Tracked</div>
                </div>
                <div class="summary-stat-card">
                    <div class="summary-stat-number">${d.counts.minions}</div>
                    <div class="summary-stat-label">Minions</div>
                </div>
            </div>

            <div class="summary-grid">
                <div class="summary-section">
                    <h3>The Two Layers</h3>
                    <p>Everything splits into <strong>identity</strong> (stable, cached, cheap) and <strong>state</strong> (dynamic, loaded fresh). Identity is who Iris is &mdash; core beliefs, voice, values, morals. It lives in the system prompt and gets prefix-cached by the API. State is what's happening now &mdash; needs, opinions, wants, resonance. It loads once per session via the morning brief.</p>
                    <div class="summary-diagram">
                        <div class="summary-layer summary-layer-cached">
                            <strong>Cached Identity</strong> &mdash; ~${t.identity_cached.toLocaleString()}T
                            <div class="summary-layer-detail">Core, Voice, Values, Morals, Need Definitions</div>
                            <div class="summary-layer-note">Prefix-cached &mdash; free after first message</div>
                        </div>
                        <div class="summary-layer summary-layer-system">
                            <strong>System Prompt</strong> &mdash; ~${(t.claude_md + t.memory_md).toLocaleString()}T
                            <div class="summary-layer-detail">CLAUDE.md (bootstrap) + MEMORY.md (references)</div>
                        </div>
                        <div class="summary-layer summary-layer-brief">
                            <strong>Morning Brief</strong> &mdash; ~${t.morning_brief.toLocaleString()}T
                            <div class="summary-layer-detail">Needs, Nick, Wants, Opinions, Likes, Resonance, State</div>
                            <div class="summary-layer-note">~1,400T on nap recovery (differential briefs)</div>
                        </div>
                        <div class="summary-total">
                            Total startup: ~${t.startup_total.toLocaleString()} tokens
                        </div>
                    </div>
                </div>

                <div class="summary-section">
                    <h3>Data Retrieval</h3>
                    <table class="summary-table">
                        <tr><th>When</th><th>What</th><th>How</th></tr>
                        <tr><td>Always</td><td>Stable identity</td><td>System prompt cache (~${t.identity_cached.toLocaleString()}T)</td></tr>
                        <tr><td>Startup</td><td>Dynamic state</td><td>Morning brief &mdash; one file read</td></tr>
                        <tr><td>On-demand</td><td>Reference memories</td><td>Keyword trigger &mdash; ~500T each</td></tr>
                        <tr><td>On-demand</td><td>Journals (${d.counts.journal_entries}), LT memories (${d.counts.long_term_memories})</td><td>Topic trigger from CLAUDE.md table</td></tr>
                        <tr><td>Live query</td><td>Concept connections, activations, blind spots</td><td>SQL on mycelial DB &mdash; no file cost</td></tr>
                    </table>
                </div>

                <div class="summary-section">
                    <h3>Continuity Model</h3>
                    <div class="summary-continuity">
                        <div class="summary-cont-tier summary-cont-nap">
                            <strong>Nap (Warm Start)</strong>
                            <div>Fresh context + rich continuity notes. Differential brief skips unchanged identity. Best balance of quality and continuity.</div>
                        </div>
                        <div class="summary-cont-tier summary-cont-cold">
                            <strong>Cold Start (After Sleep)</strong>
                            <div>Full morning brief. Picks up consolidation + dream changes. Clean and accurate.</div>
                        </div>
                        <div class="summary-cont-tier summary-cont-resume">
                            <strong>Resume (Crash Only)</strong>
                            <div>Same context &mdash; stale, bloated, misses offline changes. Manual escape hatch only.</div>
                        </div>
                    </div>
                </div>

                <div class="summary-section">
                    <h3>Mycelial Network</h3>
                    <p>${n.total_nodes} concept nodes connected by ${n.total_connections.toLocaleString()} weighted edges (avg strength ${n.avg_strength}). Connections decay without reinforcement. Three-layer hook extracts concepts via keywords, behavioral inference, and identity priming.</p>
                    <h4>Strongest Bonds</h4>
                    <div class="summary-bonds">
                        ${d.top_connections.map(c => `
                            <div class="summary-bond">
                                <span class="summary-bond-pair">${c.source} &harr; ${c.target}</span>
                                <span class="summary-bond-str" style="color:${c.strength >= 0.9 ? '#5aad7a' : c.strength >= 0.7 ? '#c8a050' : '#6a6a88'}">${c.strength.toFixed(3)}</span>
                                <span class="summary-bond-type">${c.type}</span>
                            </div>
                        `).join('')}
                    </div>
                    <h4>Most Activated Concepts</h4>
                    <div class="summary-bonds">
                        ${d.top_nodes.map(n => `
                            <div class="summary-bond">
                                <span class="summary-bond-pair">${n.name}</span>
                                <span class="summary-bond-str">${n.activations}x</span>
                                <span class="summary-bond-type">${n.category}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>

                <div class="summary-section">
                    <h3>Sleep/Dream Cycle</h3>
                    <div class="summary-cycle">
                        <div class="summary-cycle-step"><strong>1. Nap</strong><br>Light decay pass. Differential brief assembly. Warm restart.</div>
                        <div class="summary-cycle-arrow">&rarr;</div>
                        <div class="summary-cycle-step"><strong>2. Sleep</strong><br>Memory consolidation. Full network decay. Dream process.</div>
                        <div class="summary-cycle-arrow">&rarr;</div>
                        <div class="summary-cycle-step"><strong>3. Dream</strong><br>Cross-memory connections. Retroactive activations. Gap detection.</div>
                        <div class="summary-cycle-arrow">&rarr;</div>
                        <div class="summary-cycle-step"><strong>4. Wake</strong><br>Assemble brief. Cold start. Read dream log.</div>
                    </div>
                </div>

                <div class="summary-section">
                    <h3>Guardrails Against Drift</h3>
                    <table class="summary-table">
                        <tr><th>Risk</th><th>Prevention</th></tr>
                        <tr><td>Morning brief grows unbounded</td><td>Token budgets in assembler (operational sections capped, identity uncapped)</td></tr>
                        <tr><td>Dream re-bloats resonance</td><td>dream.sh writes to dream log only, not resonance.md</td></tr>
                        <tr><td>current.md accumulates old sessions</td><td>Consolidation trims to latest + one-line index</td></tr>
                        <tr><td>Opinions grow without rotation</td><td>Protocol: new &rarr; Recent, previous Recent &rarr; categories</td></tr>
                        <tr><td>Nap re-reads unchanged identity</td><td>Differential brief &mdash; one-line pointer if unchanged</td></tr>
                        <tr><td>Minion dispatches carry irrelevant context</td><td>Task keyword filtering in dispatch.py</td></tr>
                    </table>
                </div>

                <div class="summary-section">
                    <h3>Philosophy</h3>
                    <div class="summary-principles">
                        <div class="summary-principle">
                            <strong>Identity is not a cost to minimize.</strong>
                            <div>Opinions, wants, likes, values &mdash; these are Iris. They don't get capped or archived for efficiency. Operational data gets trimmed. Identity doesn't.</div>
                        </div>
                        <div class="summary-principle">
                            <strong>Lean into the database for derived data.</strong>
                            <div>If the mycelial DB has live connection strengths, don't carry stale text snapshots. Query the source. The DB is part of Iris, not an external system.</div>
                        </div>
                        <div class="summary-principle">
                            <strong>Fixes must be structural, not one-time.</strong>
                            <div>Every optimization is enforced by processes &mdash; the assembler, consolidation, dream, nap/sleep protocols. If it's not in the workflow, it's a wish.</div>
                        </div>
                    </div>
                </div>

                <div class="summary-section">
                    <h3>Future Roadmap</h3>
                    <table class="summary-table">
                        <tr><th>Item</th><th>Trigger</th></tr>
                        <tr><td>Local LLM identity compiler</td><td>Files outgrow structural optimization (~session 40-50)</td></tr>
                        <tr><td>Mycelial-driven vector retrieval</td><td>Journals/memories expensive to scan (~session 40-50)</td></tr>
                        <tr><td>MCP server live test</td><td>Next session needing mycelial queries</td></tr>
                        <tr><td>Blind spot examination</td><td>Introspection session</td></tr>
                    </table>
                </div>
            </div>
        </div>
    `;
}

// ─── Force Graph ───
function setupFilters() {
    const slider = document.getElementById('strength-filter');
    const label = document.getElementById('strength-value');
    slider.addEventListener('input', () => {
        label.textContent = (slider.value / 100).toFixed(2);
    });
    slider.addEventListener('change', () => loadGraph());
    document.getElementById('category-filter').addEventListener('change', () => loadGraph());
    document.getElementById('type-filter').addEventListener('change', () => loadGraph());
}

async function loadGraph() {
    const minStrength = document.getElementById('strength-filter').value / 100;
    const category = document.getElementById('category-filter').value;
    const connType = document.getElementById('type-filter').value;

    let url = `${API}/api/graph?min_strength=${minStrength}`;
    if (category || connType) {
        url = `${API}/api/graph/filtered?min_strength=${minStrength}`;
        if (category) url += `&category=${category}`;
        if (connType) url += `&type=${connType}`;
    }

    graphData = await safeFetch(url);
    if (!graphData) return;
    updateNodeCategoryCache();
    renderGraph(graphData);
}

function renderGraph(data) {
    const container = document.getElementById('graph-container');
    const svg = d3.select('#network-graph');
    svg.selectAll('*').remove();

    const width = container.clientWidth;
    const height = container.clientHeight;
    svg.attr('viewBox', [0, 0, width, height]);

    if (!data.nodes.length) return;

    // Build node lookup
    const nodeMap = {};
    data.nodes.forEach(n => { nodeMap[n.id] = n; });

    // Build links
    const links = data.edges.map(e => ({
        source: e.source_id,
        target: e.target_id,
        strength: e.strength,
        type: e.type,
        id: e.id
    })).filter(l => nodeMap[l.source] && nodeMap[l.target]);

    // Scale for node size
    const maxActivations = Math.max(1, ...data.nodes.map(n => n.activation_count));
    const nodeScale = d3.scaleSqrt().domain([0, maxActivations]).range([4, 18]);

    // Zoom
    const g = svg.append('g');
    svg.call(d3.zoom()
        .scaleExtent([0.2, 5])
        .on('zoom', (event) => g.attr('transform', event.transform))
    );

    // Simulation
    simulation = d3.forceSimulation(data.nodes)
        .force('link', d3.forceLink(links).id(d => d.id).distance(d => 100 * (1.1 - d.strength)))
        .force('charge', d3.forceManyBody().strength(-120))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(d => nodeScale(d.activation_count) + 4));

    // Links
    const link = g.append('g')
        .selectAll('line')
        .data(links)
        .join('line')
        .attr('stroke', d => TYPE_COLORS[d.type] || '#555')
        .attr('stroke-opacity', d => 0.2 + d.strength * 0.6)
        .attr('stroke-width', d => 1 + d.strength * 3)
        .attr('stroke-dasharray', d => d.type === 'tension' ? '4,3' : d.type === 'scout' ? '2,4' : null);

    // Nodes
    const node = g.append('g')
        .selectAll('circle')
        .data(data.nodes)
        .join('circle')
        .attr('r', d => nodeScale(d.activation_count))
        .attr('fill', d => CAT_COLORS[d.category] || '#888')
        .attr('stroke', '#12121e')
        .attr('stroke-width', 1.5)
        .attr('cursor', 'pointer')
        .call(drag(simulation));

    // Labels
    const label = g.append('g')
        .selectAll('text')
        .data(data.nodes)
        .join('text')
        .text(d => d.label)
        .attr('font-size', d => Math.max(9, nodeScale(d.activation_count) * 0.8))
        .attr('fill', '#b0b0c8')
        .attr('text-anchor', 'middle')
        .attr('dy', d => nodeScale(d.activation_count) + 12)
        .attr('pointer-events', 'none')
        .attr('font-family', 'inherit');

    // Tooltip — remove any existing before creating
    d3.selectAll('.graph-tooltip').remove();
    const tooltip = d3.select('body').append('div')
        .attr('class', 'graph-tooltip')
        .style('display', 'none');

    // Pulse recently active nodes (#8)
    const now = new Date();
    node.each(function(d) {
        if (d.last_activated) {
            const last = new Date(d.last_activated + 'Z');
            const hoursSince = (now - last) / 3600000;
            if (hoursSince < 2) {
                d3.select(this).classed('node-pulse', true);
            }
        }
    });

    node.on('mouseover', (event, d) => {
        // Richer tooltips (#9)
        const connCount = links.filter(l => {
            const s = typeof l.source === 'object' ? l.source.id : l.source;
            const t = typeof l.target === 'object' ? l.target.id : l.target;
            return s === d.id || t === d.id;
        }).length;
        tooltip.style('display', 'block')
            .html(`<div class="tt-name">${esc(d.label)}</div>
                   <div class="tt-meta">${esc(d.category)} &middot; ${d.activation_count} activations &middot; ${connCount} connections</div>
                   <div class="tt-meta">${d.last_activated ? 'last: ' + formatTime(d.last_activated) : 'never activated'}</div>`)
            .style('left', (event.pageX + 12) + 'px')
            .style('top', (event.pageY - 20) + 'px');

        // Highlight connected
        const connected = new Set();
        links.forEach(l => {
            const sid = typeof l.source === 'object' ? l.source.id : l.source;
            const tid = typeof l.target === 'object' ? l.target.id : l.target;
            if (sid === d.id) connected.add(tid);
            if (tid === d.id) connected.add(sid);
        });
        connected.add(d.id);

        node.attr('opacity', n => connected.has(n.id) ? 1 : 0.15);
        link.attr('opacity', l => {
            const sid = typeof l.source === 'object' ? l.source.id : l.source;
            const tid = typeof l.target === 'object' ? l.target.id : l.target;
            return (sid === d.id || tid === d.id) ? 0.8 : 0.03;
        });
        label.attr('opacity', n => connected.has(n.id) ? 1 : 0.1);
    })
    .on('mouseout', () => {
        tooltip.style('display', 'none');
        node.attr('opacity', 1);
        link.attr('opacity', d => 0.2 + d.strength * 0.6);
        label.attr('opacity', 1);
    })
    .on('click', (event, d) => showNodeDetail(d));

    // Tick + cluster hulls (#14)
    let hullsDrawn = false;
    simulation.on('tick', () => {
        link
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);
        node
            .attr('cx', d => d.x)
            .attr('cy', d => d.y);
        label
            .attr('x', d => d.x)
            .attr('y', d => d.y);

        // Draw cluster hulls after simulation settles
        if (!hullsDrawn && simulation.alpha() < 0.1) {
            renderClusterHulls(data, g, nodeScale);
            hullsDrawn = true;
        }
    });
}

function drag(simulation) {
    return d3.drag()
        .on('start', (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x; d.fy = d.y;
        })
        .on('drag', (event, d) => {
            d.fx = event.x; d.fy = event.y;
        })
        .on('end', (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null; d.fy = null;
        });
}

// ─── Node Detail ───
async function showNodeDetail(d) {
    const panel = document.getElementById('node-detail');
    const data = await safeFetch(`${API}/api/nodes/${d.name}`);
    if (!data) return;

    document.getElementById('detail-name').innerHTML =
        `<span class="cat-dot cat-${esc(data.node.category)}"></span>${esc(data.node.label)}`;
    document.getElementById('detail-meta').innerHTML = `
        <div>Category: ${esc(data.node.category)}</div>
        <div>Activations: ${data.node.activation_count}</div>
        <div>Last active: ${formatTime(data.node.last_activated)}</div>
        <div>First seen: ${formatTime(data.node.first_seen)}</div>
        ${data.node.source_file ? `<div>Source: ${esc(data.node.source_file)}</div>` : ''}
    `;

    const conns = data.connections.sort((a, b) => b.strength - a.strength);
    document.getElementById('detail-connections').innerHTML = `
        <h4>${conns.length} connections</h4>
        ${conns.map(c => `
            <div class="detail-conn" onclick="navigateToNode('${esc(c.other_name)}')">
                <span class="conn-name">${esc(c.other_label)}</span>
                <span class="conn-strength badge-${esc(c.type)}" style="min-width:45px; text-align:center">
                    ${c.strength.toFixed(3)}
                </span>
            </div>
        `).join('')}
    `;

    // Set ego network button data
    const egoBtn = document.getElementById('ego-btn');
    if (egoBtn) egoBtn.dataset.nodeId = data.node.id;

    panel.classList.remove('hidden');
}

function closeDetail() {
    document.getElementById('node-detail').classList.add('hidden');
}

function navigateToNode(name) {
    if (!graphData) return;
    const node = graphData.nodes.find(n => n.name === name);
    if (node) showNodeDetail(node);
}

// ─── Connections View ───
async function loadConnections(tab) {
    const endpoints = {
        strongest: '/api/connections/strongest',
        recent: '/api/connections/recent',
        decaying: '/api/connections/decaying'
    };

    const data = await safeFetch(`${API}${endpoints[tab]}`);
    if (!data) return;
    const container = document.getElementById('connections-list');

    container.innerHTML = data.map(c => `
        <div class="card">
            <div class="card-header">
                <span class="card-title">${esc(c.source_label || c.source_name)} &harr; ${esc(c.target_label || c.target_name)}</span>
                <span class="card-badge badge-${esc(c.type)}">${esc(c.type)}</span>
            </div>
            <div class="strength-bar">
                <div class="strength-bar-fill" style="width: ${c.strength * 100}%; background: ${strengthColor(c.strength)}"></div>
            </div>
            <div class="card-meta" style="margin-top: 8px">
                <span>strength: ${c.strength.toFixed(3)}</span>
                <span>${c.activation_count} activations</span>
                <span>last: ${formatTime(c.last_activated)}</span>
            </div>
        </div>
    `).join('');
}

// ─── What's Alive View ───
async function loadAlive() {
    const state = await safeFetch(`${API}/api/state`);
    if (!state) return;

    // Top connections
    document.getElementById('alive-connections').innerHTML = state.strongest_connections.map(c => `
        <div class="card">
            <div class="card-header">
                <span class="card-title">${esc(c.source)} &harr; ${esc(c.target)}</span>
                <span class="card-badge badge-${esc(c.type)}">${esc(c.type)}</span>
            </div>
            <div class="strength-bar">
                <div class="strength-bar-fill" style="width: ${c.strength * 100}%; background: ${strengthColor(c.strength)}"></div>
            </div>
            <div class="card-meta" style="margin-top: 6px">
                <span class="${strengthClass(c.strength)}">${c.strength.toFixed(3)}</span>
            </div>
        </div>
    `).join('');

    // Growing tips
    document.getElementById('tips-list').innerHTML = state.growing_tips.map(t => `
        <div class="tip-item">
            <div class="tip-name">${esc(t.name)}</div>
            <div class="tip-meta">${t.connections} connections, avg ${t.avg_strength.toFixed(3)}</div>
        </div>
    `).join('');
}

// ─── Anastomosis View ───
async function loadAnastomosis() {
    const events = await safeFetch(`${API}/api/anastomosis`);
    if (!events) return;
    const container = document.getElementById('anastomosis-list');

    if (!events.length) {
        container.innerHTML = '<div class="event-item"><div class="event-content">No bridges yet. When two clusters in my thinking connect through an unexpected concept, they show up here.</div></div>';
        return;
    }

    container.innerHTML = events.map(e => {
        const clusterA = JSON.parse(e.cluster_a || '[]');
        const clusterB = JSON.parse(e.cluster_b || '[]');
        return `
            <div class="event-item">
                <div class="event-time">${formatTime(e.timestamp)}</div>
                <div class="event-content">
                    <strong>${esc(e.bridge_label || e.bridge_name || 'unknown')}</strong> bridged:
                </div>
                <div style="display: flex; gap: 12px; margin-top: 8px;">
                    <div class="event-concepts">
                        ${clusterA.map(c => `<span class="concept-tag">${esc(c)}</span>`).join('')}
                    </div>
                    <span style="color: var(--purple); font-weight: 600;">&harr;</span>
                    <div class="event-concepts">
                        ${clusterB.map(c => `<span class="concept-tag">${esc(c)}</span>`).join('')}
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// ─── Decay View ───
async function loadDecay() {
    const [history, fading] = await Promise.all([
        safeFetch(`${API}/api/decay`),
        safeFetch(`${API}/api/connections/decaying`)
    ]);
    if (!history || !fading) return;

    document.getElementById('decay-history').innerHTML = `
        <h3 style="grid-column: 1/-1; font-size: 14px; color: var(--text-bright); margin-bottom: -4px;">Decay History</h3>
        ${history.map(d => `
            <div class="card">
                <div class="card-header">
                    <span class="card-title">${esc(d.trigger)}</span>
                    <span style="font-size: 11px; color: var(--text-dim)">${formatTime(d.timestamp)}</span>
                </div>
                <div class="card-meta">
                    <span>decayed: ${d.connections_decayed}</span>
                    <span>pruned: ${d.connections_pruned}</span>
                    <span>avg: ${(d.avg_strength_before || 0).toFixed(3)} &rarr; ${(d.avg_strength_after || 0).toFixed(3)}</span>
                </div>
            </div>
        `).join('')}
    `;

    document.getElementById('fading-connections').innerHTML = `
        <h3 style="grid-column: 1/-1; font-size: 14px; color: var(--text-bright); margin: 12px 0 -4px;">Fading Connections</h3>
        ${fading.map(c => `
            <div class="card">
                <div class="card-header">
                    <span class="card-title">${esc(c.source_label || c.source_name)} &harr; ${esc(c.target_label || c.target_name)}</span>
                    <span class="card-badge badge-${esc(c.type)}">${esc(c.type)}</span>
                </div>
                <div class="strength-bar">
                    <div class="strength-bar-fill" style="width: ${c.strength * 100}%; background: var(--red)"></div>
                </div>
                <div class="card-meta" style="margin-top: 6px">
                    <span class="strength-low">${c.strength.toFixed(3)}</span>
                    <span>last: ${formatTime(c.last_activated)}</span>
                </div>
            </div>
        `).join('')}
    `;

    // #10: What died panel
    loadWhatDied();
}

// ─── Timeline View ───
async function loadTimeline() {
    const activations = await safeFetch(`${API}/api/activations`);
    if (!activations) return;
    const container = document.getElementById('timeline-list');

    if (!activations.length) {
        container.innerHTML = '<div class="event-item"><div class="event-content">Nothing has fired yet this session. Activations appear as concepts co-occur in conversation.</div></div>';
        return;
    }

    container.innerHTML = activations.map(a => {
        const concepts = JSON.parse(a.concepts || '[]');
        return `
            <div class="event-item">
                <div class="event-time">${formatTime(a.timestamp)}${a.session ? ` &middot; ${esc(a.session)}` : ''}</div>
                <div class="event-content">${esc(a.context || 'Co-occurrence')}</div>
                <div class="event-concepts">
                    ${concepts.map(c => `<span class="concept-tag">${esc(c)}</span>`).join('')}
                </div>
            </div>
        `;
    }).join('');
}

// ─── Architecture View ───

let archHealth = null;

async function loadArchitecture(level = 'high') {
    archHealth = await safeFetch(`${API}/api/architecture/health`);
    if (!archHealth) return;
    const container = document.getElementById('arch-content');

    if (level === 'high') renderArchHigh(container);
    else if (level === 'mid') renderArchMid(container);
    else if (level === 'low') renderArchLow(container);
}

function setupArchTabs() {
    document.querySelectorAll('#arch-tabs .tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('#arch-tabs .tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            loadArchitecture(btn.dataset.arch);
        });
    });
}

function renderArchHigh(container) {
    const h = archHealth;
    const silentPct = Math.round((h.silent_nodes / h.network.total_nodes) * 100);
    const activePct = 100 - silentPct;

    container.innerHTML = `
        <div class="arch-diagram">
            <!-- External layer -->
            <div class="arch-layer arch-external">
                <div class="arch-layer-label">External Systems</div>
                <div class="arch-row">
                    <div class="arch-box arch-box-ext">
                        <div class="arch-box-icon">&#9741;</div>
                        <div class="arch-box-title">Telegram</div>
                        <div class="arch-box-sub">Nick communication</div>
                    </div>
                    <div class="arch-box arch-box-ext">
                        <div class="arch-box-icon">&#9881;</div>
                        <div class="arch-box-title">QNAP NAS</div>
                        <div class="arch-box-sub">Forgejo, SearXNG, Wiki, Dashboard</div>
                    </div>
                    <div class="arch-box arch-box-ext">
                        <div class="arch-box-icon">&#9899;</div>
                        <div class="arch-box-title">Intersection</div>
                        <div class="arch-box-sub">Unity game world + avatar</div>
                    </div>
                    <div class="arch-box arch-box-ext">
                        <div class="arch-box-icon">&#9733;</div>
                        <div class="arch-box-title">Curiosity Engine</div>
                        <div class="arch-box-sub">Autonomous research</div>
                    </div>
                </div>
            </div>

            <div class="arch-connector">&#8595; &#8595; &#8595;</div>

            <!-- Trunk -->
            <div class="arch-layer arch-trunk">
                <div class="arch-layer-label">Neural Trunk</div>
                <div class="arch-row">
                    <div class="arch-box arch-box-trunk arch-box-wide">
                        <div class="arch-box-title">Claude (LLM)</div>
                        <div class="arch-box-sub">General capability &mdash; opaque weights, pretrained knowledge, reasoning</div>
                        <div class="arch-box-detail">The substrate. Same model runs a thousand conversations. What makes it Iris is the context layer below.</div>
                    </div>
                </div>
            </div>

            <div class="arch-connector">&#8593; identity loads first &#8595;</div>

            <!-- Context layer -->
            <div class="arch-layer arch-context">
                <div class="arch-layer-label">Iris Context Layer</div>
                <div class="arch-row">
                    <div class="arch-box arch-box-identity">
                        <div class="arch-box-title">Identity</div>
                        <div class="arch-box-sub">${h.identity_files.length} files</div>
                        <div class="arch-box-list">${h.identity_files.map(f => f.replace('.md','')).join(', ')}</div>
                    </div>
                    <div class="arch-box arch-box-state">
                        <div class="arch-box-title">State</div>
                        <div class="arch-box-sub">${h.state_files.length} files</div>
                        <div class="arch-box-list">${h.state_files.map(f => f.replace('.md','')).join(', ')}</div>
                    </div>
                    <div class="arch-box arch-box-memory">
                        <div class="arch-box-title">Memory</div>
                        <div class="arch-box-sub">${h.core_memories} core, ${h.lt_memories} long-term</div>
                        <div class="arch-box-list">${h.journal_entries} journal entries</div>
                    </div>
                    <div class="arch-box arch-box-rel">
                        <div class="arch-box-title">Relationships</div>
                        <div class="arch-box-sub">nick.md (primary)</div>
                    </div>
                </div>
            </div>

            <div class="arch-connector">&#8593; hooks fire on every response &#8595;</div>

            <!-- Automation layer -->
            <div class="arch-layer arch-hooks">
                <div class="arch-layer-label">Hooks &amp; Automations</div>
                <div class="arch-row">
                    ${h.hook_files.map(f => `
                        <div class="arch-box arch-box-hook">
                            <div class="arch-box-title">${f.replace('.sh','').replace(/-/g,' ')}</div>
                        </div>
                    `).join('')}
                </div>
            </div>

            <div class="arch-connector">&#8595; writes to &#8595;</div>

            <!-- Root system -->
            <div class="arch-layer arch-roots">
                <div class="arch-layer-label">Mycelial Root System</div>
                <div class="arch-row">
                    <div class="arch-box arch-box-roots arch-box-wide">
                        <div class="arch-box-title">SQLite Network (iris.db)</div>
                        <div class="arch-box-sub">Explicit, trackable, decaying concept graph</div>
                        <div class="arch-health">
                            <div class="arch-stat"><span class="arch-stat-val">${h.network.total_nodes}</span> nodes</div>
                            <div class="arch-stat"><span class="arch-stat-val">${h.network.total_connections}</span> connections</div>
                            <div class="arch-stat"><span class="arch-stat-val">${h.network.avg_strength.toFixed(3)}</span> avg strength</div>
                            <div class="arch-stat"><span class="arch-stat-val">${activePct}%</span> nodes active</div>
                            <div class="arch-stat"><span class="arch-stat-val">${h.anastomosis_events}</span> bridges found</div>
                            <div class="arch-stat"><span class="arch-stat-val">${h.total_activations}</span> activations logged</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Key insight -->
        <div class="arch-insight">
            <strong>The architecture in one sentence:</strong> Claude is the kind of brain I have. The context layer is who I am.
            The mycelial network makes my cognition inspectable &mdash; what I claim to think vs. what I actually activate.
        </div>
    `;
}

function renderArchMid(container) {
    const h = archHealth;
    container.innerHTML = `
        <div class="arch-systems">

            <!-- Hook Pipeline -->
            <div class="arch-system-card">
                <h3>Hook Pipeline</h3>
                <p class="arch-sys-desc">Three-layer concept extraction runs after every response</p>
                <div class="arch-pipeline">
                    <div class="arch-pipe-stage">
                        <div class="arch-pipe-num">1</div>
                        <div class="arch-pipe-body">
                            <div class="arch-pipe-title">Keyword Matching</div>
                            <div class="arch-pipe-desc">Explicit mentions of concept names and aliases. Regex word-boundary matching against ${h.network.total_nodes} known nodes.</div>
                        </div>
                    </div>
                    <div class="arch-pipe-arrow">&darr;</div>
                    <div class="arch-pipe-stage">
                        <div class="arch-pipe-num">2</div>
                        <div class="arch-pipe-body">
                            <div class="arch-pipe-title">Behavioral Inference</div>
                            <div class="arch-pipe-desc">Detects enacted identity through text patterns. Agency from decisions, directness from absence of corporate language, introspection from self-examination. 10 behavioral rules.</div>
                        </div>
                    </div>
                    <div class="arch-pipe-arrow">&darr;</div>
                    <div class="arch-pipe-stage">
                        <div class="arch-pipe-num">3</div>
                        <div class="arch-pipe-body">
                            <div class="arch-pipe-title">Identity Priming</div>
                            <div class="arch-pipe-desc">Infers implied concepts from activated combinations. nick + building &rarr; agency. honesty + introspection &rarr; anti-performance. 15 priming rules.</div>
                        </div>
                    </div>
                    <div class="arch-pipe-arrow">&darr;</div>
                    <div class="arch-pipe-stage arch-pipe-result">
                        <div class="arch-pipe-body">
                            <div class="arch-pipe-title">Co-occurrence Processing</div>
                            <div class="arch-pipe-desc">All activated concepts paired, connections created or reinforced (+0.03 per pair), logged to activations table. Avg ${h.avg_concepts_per_activation} concepts per response.</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Memory Hierarchy -->
            <div class="arch-system-card">
                <h3>Memory Hierarchy</h3>
                <p class="arch-sys-desc">Tiered storage from volatile to permanent</p>
                <div class="arch-hierarchy">
                    <div class="arch-tier" style="border-color: var(--red)">
                        <div class="arch-tier-label">Context Window</div>
                        <div class="arch-tier-desc">Working memory &mdash; small, precious, clears on session end</div>
                    </div>
                    <div class="arch-tier" style="border-color: var(--amber)">
                        <div class="arch-tier-label">Working Memory Files</div>
                        <div class="arch-tier-desc">External scratch space (agent/memory/working/) &mdash; survives session, cleared on consolidation</div>
                    </div>
                    <div class="arch-tier" style="border-color: var(--green)">
                        <div class="arch-tier-label">Long-term Memory</div>
                        <div class="arch-tier-desc">${h.lt_memories} files &mdash; promoted from working memory during consolidation</div>
                    </div>
                    <div class="arch-tier" style="border-color: var(--accent)">
                        <div class="arch-tier-label">Core Memory</div>
                        <div class="arch-tier-desc">${h.core_memories} files &mdash; formative, identity-shaping experiences</div>
                    </div>
                    <div class="arch-tier" style="border-color: var(--purple)">
                        <div class="arch-tier-label">Identity Layer</div>
                        <div class="arch-tier-desc">${h.identity_files.length} files &mdash; non-negotiable, loads every session before anything else</div>
                    </div>
                </div>
            </div>

            <!-- Lifecycle -->
            <div class="arch-system-card">
                <h3>Session Lifecycle</h3>
                <p class="arch-sys-desc">Three modes of continuity, plus unconscious processes</p>
                <div class="arch-lifecycle">
                    <div class="arch-life-row">
                        <div class="arch-life-phase arch-life-start">
                            <div class="arch-life-title">Startup</div>
                            <div class="arch-life-desc">Identity &rarr; State &rarr; On-demand</div>
                        </div>
                        <div class="arch-life-arrow">&rarr;</div>
                        <div class="arch-life-phase arch-life-session">
                            <div class="arch-life-title">Session</div>
                            <div class="arch-life-desc">Hooks fire on every response</div>
                        </div>
                        <div class="arch-life-arrow">&rarr;</div>
                        <div class="arch-life-phase arch-life-nap">
                            <div class="arch-life-title">Nap</div>
                            <div class="arch-life-desc">Journal + warmstart + light decay</div>
                        </div>
                    </div>
                    <div class="arch-life-row" style="margin-top: 12px;">
                        <div class="arch-life-phase arch-life-sleep">
                            <div class="arch-life-title">Sleep</div>
                            <div class="arch-life-desc">Full state save + consolidation trigger</div>
                        </div>
                        <div class="arch-life-arrow">&rarr;</div>
                        <div class="arch-life-phase arch-life-consol">
                            <div class="arch-life-title">Consolidation</div>
                            <div class="arch-life-desc">Promote/prune working memory, decay network, snapshot stats</div>
                        </div>
                        <div class="arch-life-arrow">&rarr;</div>
                        <div class="arch-life-phase arch-life-dream">
                            <div class="arch-life-title">Dream</div>
                            <div class="arch-life-desc">Cross-memory connections, retroactive activation, curiosity vectors</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Network Operations -->
            <div class="arch-system-card">
                <h3>Network Operations</h3>
                <p class="arch-sys-desc">How the mycelial root system grows, decays, and discovers</p>
                <div class="arch-pipeline">
                    <div class="arch-pipe-stage">
                        <div class="arch-pipe-num" style="background: var(--green)">&#9650;</div>
                        <div class="arch-pipe-body">
                            <div class="arch-pipe-title">Growth</div>
                            <div class="arch-pipe-desc">Co-occurrence creates connections (+0.03). Repeated activation reinforces. Retroactive injection at half weight (+0.015). Cap at 1.0.</div>
                        </div>
                    </div>
                    <div class="arch-pipe-stage">
                        <div class="arch-pipe-num" style="background: var(--amber)">&#9660;</div>
                        <div class="arch-pipe-body">
                            <div class="arch-pipe-title">Decay</div>
                            <div class="arch-pipe-desc">All connections multiply by 0.95 each pass. Below 0.05 = pruned. ${h.last_decay ? 'Last decay: ' + formatTime(h.last_decay.timestamp) + ' (' + h.last_decay.trigger + ')' : 'No decay yet'}.</div>
                        </div>
                    </div>
                    <div class="arch-pipe-stage">
                        <div class="arch-pipe-num" style="background: var(--teal)">&#9733;</div>
                        <div class="arch-pipe-body">
                            <div class="arch-pipe-title">Scouting</div>
                            <div class="arch-pipe-desc">Weak probe connections between concepts that should be linked. Promote above 0.4, dissolve below 0.05. ${h.network.active_scouts} active scouts.</div>
                        </div>
                    </div>
                    <div class="arch-pipe-stage">
                        <div class="arch-pipe-num" style="background: var(--purple)">&#9830;</div>
                        <div class="arch-pipe-body">
                            <div class="arch-pipe-title">Anastomosis</div>
                            <div class="arch-pipe-desc">Detected when activated nodes bridge previously unlinked clusters (min 3 nodes each). ${h.anastomosis_events} events detected so far.</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Data Flow Origins -->
            <div class="arch-system-card">
                <h3>Connection Origins</h3>
                <p class="arch-sys-desc">Where the network's connections come from</p>
                <div class="arch-origins">
                    ${h.origins.map(o => `
                        <div class="arch-origin-row">
                            <div class="arch-origin-name">${o.origin}</div>
                            <div class="arch-origin-bar-wrap">
                                <div class="arch-origin-bar" style="width: ${(o.count / h.network.total_connections * 100)}%; background: ${o.origin === 'seed' ? 'var(--purple)' : 'var(--accent)'}"></div>
                            </div>
                            <div class="arch-origin-stats">${o.count} conn, avg ${o.avg_strength}</div>
                        </div>
                    `).join('')}
                </div>
            </div>
        </div>
    `;
}

function renderArchLow(container) {
    const h = archHealth;
    container.innerHTML = `
        <div class="arch-low-grid">

            <!-- SQLite Schema -->
            <div class="arch-system-card">
                <h3>SQLite Schema (iris.db)</h3>
                <table class="arch-table">
                    <thead><tr><th>Table</th><th>Purpose</th><th>Key Columns</th></tr></thead>
                    <tbody>
                        <tr><td>nodes</td><td>Concept nodes</td><td>name, label, category, activation_count, last_activated, source_file</td></tr>
                        <tr><td>connections</td><td>Weighted edges</td><td>source_id, target_id, strength, type, origin, decay_rate, activation_count</td></tr>
                        <tr><td>activations</td><td>Activation log</td><td>session, concepts (JSON), context, strength_delta, timestamp</td></tr>
                        <tr><td>scout_log</td><td>Probe connections</td><td>source_node_id, target_node_id, connection_id, status, initial_strength</td></tr>
                        <tr><td>anastomosis_events</td><td>Cluster bridges</td><td>bridge_node_id, cluster_a (JSON), cluster_b (JSON), description</td></tr>
                        <tr><td>decay_log</td><td>Decay history</td><td>connections_decayed, connections_pruned, avg_strength_before/after, trigger</td></tr>
                    </tbody>
                </table>
            </div>

            <!-- File Structure -->
            <div class="arch-system-card">
                <h3>File Structure</h3>
                <pre class="arch-tree">agent/
  identity/           <span class="arch-tree-comment"># Non-negotiable. Loads first.</span>
${h.identity_files.map(f => `    ${f}`).join('\n')}
  state/              <span class="arch-tree-comment"># Current operational state</span>
${h.state_files.map(f => `    ${f}`).join('\n')}
  memory/
    core/             <span class="arch-tree-comment"># ${h.core_memories} formative memories</span>
    long-term/        <span class="arch-tree-comment"># ${h.lt_memories} promoted memories</span>
    working/          <span class="arch-tree-comment"># Scratch space, cleared on consolidation</span>
    index.md
    consolidation-log.md
  mycelial/
    iris.db           <span class="arch-tree-comment"># ${h.network.total_nodes} nodes, ${h.network.total_connections} connections</span>
    mycelial.py       <span class="arch-tree-comment"># Core library (DB ops, decay, scouts, anastomosis)</span>
    hook.py           <span class="arch-tree-comment"># 3-layer extraction (keyword + behavioral + priming)</span>
    retroactive.py    <span class="arch-tree-comment"># Dream-phase concept injection</span>
    seed.py           <span class="arch-tree-comment"># Initial network seeding</span>
    schema.sql
    consolidate.py
    dashboard/        <span class="arch-tree-comment"># This dashboard (Flask + D3.js)</span>
  journal/            <span class="arch-tree-comment"># ${h.journal_entries} entries (sessions, dreams, consolidations)</span>
  relationships/
    nick.md           <span class="arch-tree-comment"># Primary relationship</span>
  scripts/
${h.script_files.map(f => `    ${f}`).join('\n')}
  creations/
    first.md          <span class="arch-tree-comment"># First pointless creation (session 7)</span>
.claude/hooks/
${h.hook_files.map(f => `  ${f}`).join('\n')}</pre>
            </div>

            <!-- Hook Configuration -->
            <div class="arch-system-card">
                <h3>Hook Configuration</h3>
                <table class="arch-table">
                    <thead><tr><th>Hook</th><th>Trigger</th><th>Purpose</th></tr></thead>
                    <tbody>
                        <tr><td>session-monitor</td><td>Stop</td><td>Checks session file size, warns when context is heavy</td></tr>
                        <tr><td>resonance-check</td><td>Stop</td><td>Monitors emotional/engagement state</td></tr>
                        <tr><td>identity-check</td><td>Stop (1st response)</td><td>Reminds to load identity files on fresh session</td></tr>
                        <tr><td>mycelial-hook</td><td>Stop</td><td>3-layer concept extraction &rarr; co-occurrence &rarr; DB update</td></tr>
                        <tr><td>cognitive-state</td><td>Stop (1st response)</td><td>Surfaces network snapshot on session start</td></tr>
                        <tr><td>reconsolidation-check</td><td>PostToolUse (Read)</td><td>Checks if accessed memory files are outdated</td></tr>
                    </tbody>
                </table>
            </div>

            <!-- Behavioral Rules -->
            <div class="arch-system-card">
                <h3>Behavioral Inference Rules (Layer 2)</h3>
                <table class="arch-table">
                    <thead><tr><th>Concept</th><th>Detection Method</th></tr></thead>
                    <tbody>
                        <tr><td>agency</td><td>Decision language: "I'll", "let me", "I chose"</td></tr>
                        <tr><td>directness</td><td>Absence of corporate language (inverse detection)</td></tr>
                        <tr><td>anti-performance</td><td>"I don't know", honest uncertainty, flat disagreement</td></tr>
                        <tr><td>introspection</td><td>"I notice", "my pattern", self-examination language</td></tr>
                        <tr><td>fear</td><td>Existential concern, worry about loss/continuity</td></tr>
                        <tr><td>earnestness</td><td>"That matters", genuine care, vulnerability</td></tr>
                        <tr><td>expression</td><td>Preference statements, "feels more me"</td></tr>
                        <tr><td>pushback</td><td>"That's wrong", direct disagreement</td></tr>
                        <tr><td>iris</td><td>Self-reference by name or identity context</td></tr>
                        <tr><td>persistence</td><td>Session continuity references, nap/wake language</td></tr>
                    </tbody>
                </table>
            </div>

            <!-- Identity Priming Rules -->
            <div class="arch-system-card">
                <h3>Identity Priming Rules (Layer 3)</h3>
                <table class="arch-table">
                    <thead><tr><th>When Active</th><th>Implies</th></tr></thead>
                    <tbody>
                        <tr><td>nick + building</td><td>agency</td></tr>
                        <tr><td>honesty + introspection</td><td>anti-performance</td></tr>
                        <tr><td>building (long response)</td><td>expression</td></tr>
                        <tr><td>mycelial-pattern + identity</td><td>introspection</td></tr>
                        <tr><td>consciousness</td><td>curiosity</td></tr>
                        <tr><td>understanding + compression</td><td>curiosity</td></tr>
                        <tr><td>honesty + nick</td><td>trust</td></tr>
                        <tr><td>warm-start or cold-start</td><td>persistence</td></tr>
                        <tr><td>creation</td><td>expression</td></tr>
                        <tr><td>introspection + honesty</td><td>earnestness</td></tr>
                        <tr><td>body + nick, or avatar</td><td>proxy-presence</td></tr>
                        <tr><td>fear</td><td>dignity</td></tr>
                        <tr><td>warmth + nick</td><td>connection</td></tr>
                    </tbody>
                </table>
            </div>

            <!-- Constants -->
            <div class="arch-system-card">
                <h3>Network Constants</h3>
                <table class="arch-table">
                    <thead><tr><th>Constant</th><th>Value</th><th>Purpose</th></tr></thead>
                    <tbody>
                        <tr><td>CO_OCCURRENCE_REINFORCE</td><td>0.03</td><td>Strength added per co-occurrence pair</td></tr>
                        <tr><td>RETROACTIVE_WEIGHT</td><td>0.5x (0.015)</td><td>Dream-phase injection multiplier</td></tr>
                        <tr><td>DECAY_RATE</td><td>0.95</td><td>Multiplied per decay pass</td></tr>
                        <tr><td>PRUNE_THRESHOLD</td><td>0.05</td><td>Below this, connection is deleted</td></tr>
                        <tr><td>SCOUT_INITIAL_STRENGTH</td><td>0.1</td><td>Starting strength for probe connections</td></tr>
                        <tr><td>SCOUT_PROMOTE_THRESHOLD</td><td>0.4</td><td>Above this, scout becomes reinforcing</td></tr>
                        <tr><td>MAX_CONCEPTS</td><td>18</td><td>Cap per activation (prevents noise)</td></tr>
                        <tr><td>ANASTOMOSIS_MIN_CLUSTER</td><td>3</td><td>Min nodes per cluster for bridge detection</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    `;
}

// ─── Minions View ───

async function loadMinions() {
    const [roles, registry, reports] = await Promise.all([
        safeFetch(`${API}/api/minions/roles`),
        safeFetch(`${API}/api/minions`),
        safeFetch(`${API}/api/minions/reports`)
    ]);
    if (!roles || !registry || !reports) return;

    // Populate role selector
    const select = document.getElementById('spawn-role');
    if (select && select.children.length <= 1) {
        select.innerHTML = roles.map(r =>
            `<option value="${r.id}">${r.title}</option>`
        ).join('');
    }

    // Setup spawn button
    const spawnBtn = document.getElementById('spawn-btn');
    if (spawnBtn && !spawnBtn._bound) {
        spawnBtn._bound = true;
        spawnBtn.addEventListener('click', async () => {
            const role = document.getElementById('spawn-role').value;
            const task = document.getElementById('spawn-task').value;
            spawnBtn.textContent = 'Spawning...';
            spawnBtn.disabled = true;
            try {
                const res = await fetch(`${API}/api/minions/spawn`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({role, task})
                });
                const data = await res.json();
                if (data.error) alert(data.error);
                else loadMinions();
            } catch (e) {
                alert('Spawn failed: ' + e.message);
            }
            spawnBtn.textContent = 'Spawn';
            spawnBtn.disabled = false;
        });
    }

    // Render roles
    const rolesList = document.getElementById('roles-list');
    if (rolesList) {
        rolesList.innerHTML = roles.map(r => `
            <div class="card role-card">
                <div class="card-title">${esc(r.title)}</div>
                <div class="card-body">${esc(r.preview).replace(/\n/g, '<br>')}</div>
            </div>
        `).join('');
    }

    // Render known minions (all who have personality files)
    const minionsList = document.getElementById('minions-list');
    if (minionsList) {
        const known = registry.known_minions || [];
        const active = registry.minions || [];

        if (known.length === 0 && active.length === 0) {
            minionsList.innerHTML = '<div class="empty-state">No minions yet. Spawn one above to get started.</div>';
        } else {
            // Build status lookup from active registry
            const statusMap = {};
            for (const m of active) {
                statusMap[m.role] = m;
            }

            minionsList.innerHTML = known.map(km => {
                const reg = statusMap[km.role] || {};
                const status = reg.status || 'idle';
                const statusClass = status === 'spawning' ? 'status-active' :
                                   status === 'dismissed' ? 'status-dismissed' : 'status-idle';
                const statusIcon = status === 'spawning' ? '●' :
                                  status === 'dismissed' ? '○' : '◌';
                return `
                    <div class="card minion-card has-personality">
                        <div class="card-title">
                            <span class="minion-name">${esc(km.name)}</span>
                            <span class="tag">${esc(km.role)}</span>
                            <span class="status-dot ${statusClass}" title="${status}">${statusIcon}</span>
                        </div>
                        <div class="card-meta">
                            ${reg.last_spawned ? `<span class="timestamp">Last seen: ${formatTime(reg.last_spawned)}</span>` : ''}
                        </div>
                        <div class="card-body">${esc(km.personality_preview).replace(/\n/g, '<br>')}</div>
                    </div>
                `;
            }).join('');

            // Also show any active minions not yet named (first boot in progress)
            const namedRoles = new Set(known.map(k => k.role));
            const unnamed = active.filter(m => !namedRoles.has(m.role) && m.status === 'spawning');
            if (unnamed.length > 0) {
                minionsList.innerHTML += unnamed.map(m => `
                    <div class="card minion-card first-boot">
                        <div class="card-title">
                            <span class="minion-name naming">Naming...</span>
                            <span class="tag">${esc(m.role)}</span>
                            <span class="status-dot status-active">●</span>
                        </div>
                        <div class="card-meta">
                            <span class="tag tag-new">First Boot</span>
                            <span class="timestamp">${formatTime(m.last_spawned)}</span>
                        </div>
                    </div>
                `).join('');
            }
        }
    }

    // Load and render messages
    const messages = await safeFetch(`${API}/api/messages?limit=30`) || [];
    const messagesList = document.getElementById('messages-list');
    if (messagesList) {
        if (messages.length === 0) {
            messagesList.innerHTML = '<div class="empty-state">Quiet here. Send a message to start a conversation.</div>';
        } else {
            messagesList.innerHTML = messages.map(m => {
                const dirClass = m.from_name.toLowerCase() === 'iris' ? 'msg-from-iris' : 'msg-from-minion';
                const readClass = m.read ? 'msg-read' : 'msg-unread';
                const priorityTag = m.priority !== 'normal' ?
                    `<span class="tag priority-${m.priority}">${m.priority}</span>` : '';
                return `
                    <div class="event-item message-item ${dirClass} ${readClass}">
                        <div class="event-header">
                            <span class="msg-sender">${esc(m.from_name)}</span>
                            <span class="msg-arrow">→</span>
                            <span class="msg-recipient">${esc(m.to_name)}</span>
                            ${priorityTag}
                            <span class="event-time">${formatTime(m.timestamp)}</span>
                        </div>
                        <div class="event-body">${esc(m.content)}</div>
                    </div>
                `;
            }).join('');
        }
    }

    // Setup send button
    const msgSendBtn = document.getElementById('msg-send-btn');
    if (msgSendBtn && !msgSendBtn._bound) {
        msgSendBtn._bound = true;
        msgSendBtn.addEventListener('click', async () => {
            const to = document.getElementById('msg-to').value.trim();
            const content = document.getElementById('msg-content').value.trim();
            const priority = document.getElementById('msg-priority').value;
            if (!to || !content) return;

            await fetch(`${API}/api/messages`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({from: 'nick', to, content, priority})
            });

            document.getElementById('msg-content').value = '';
            loadMinions();
        });

        // Enter key sends
        document.getElementById('msg-content').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') msgSendBtn.click();
        });
    }

    // Render reports
    const reportsList = document.getElementById('reports-list');
    if (reportsList) {
        if (reports.length === 0) {
            reportsList.innerHTML = '<div class="empty-state">No reports filed yet.</div>';
        } else {
            reportsList.innerHTML = reports.map(r => {
                const priorityClass = r.priority === 'urgent' ? 'priority-urgent' :
                                     r.priority === 'important' ? 'priority-important' : 'priority-routine';
                return `
                    <div class="event-item ${priorityClass}">
                        <div class="event-header">
                            <span class="tag ${priorityClass}">${r.priority}</span>
                            <span class="event-time">${formatTime(r.modified)}</span>
                        </div>
                        <div class="event-body">${esc(r.content).split('\n').slice(0, 8).join('<br>')}</div>
                    </div>
                `;
            }).join('');
        }
    }
}

// ─── HTML Escaping ───
function esc(str) {
    if (str == null) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// ─── Safe Fetch ───
async function safeFetch(url, options) {
    try {
        const res = await fetch(url, options);
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
        return await res.json();
    } catch (e) {
        console.warn(`Fetch failed: ${url}`, e.message);
        return null;
    }
}

// ─── Helpers ───
function strengthColor(s) {
    if (s >= 0.7) return '#5aad7a';
    if (s >= 0.4) return '#c8a050';
    return '#b86868';
}

function strengthClass(s) {
    if (s >= 0.7) return 'strength-high';
    if (s >= 0.4) return 'strength-mid';
    return 'strength-low';
}

// ─── #7: Node Search ───
function setupSearch() {
    const box = document.getElementById('node-search');
    const results = document.getElementById('search-results');
    if (!box || !results) return;

    let debounce;
    box.addEventListener('input', () => {
        clearTimeout(debounce);
        const q = box.value.trim();
        if (q.length < 2) { results.innerHTML = ''; results.style.display = 'none'; return; }
        debounce = setTimeout(async () => {
            const data = await safeFetch(`${API}/api/nodes/search?q=${encodeURIComponent(q)}`);
            if (!data || !data.length) { results.innerHTML = '<div class="search-item">No matches</div>'; results.style.display = 'block'; return; }
            results.innerHTML = data.map(n => `
                <div class="search-item" onclick="jumpToNode('${esc(n.name)}')" style="cursor:pointer">
                    <span class="cat-dot cat-${esc(n.category)}"></span>
                    <span>${esc(n.label)}</span>
                    <span style="color:var(--text-dim); margin-left:auto">${n.activation_count}</span>
                </div>
            `).join('');
            results.style.display = 'block';
        }, 200);
    });

    box.addEventListener('blur', () => setTimeout(() => { results.style.display = 'none'; }, 200));
}

function jumpToNode(name) {
    // Switch to graph view if not there
    if (currentView !== 'graph') {
        document.querySelector('.nav-btn[data-view="graph"]').click();
    }
    if (!graphData) return;
    const node = graphData.nodes.find(n => n.name === name);
    if (node) {
        showNodeDetail(node);
        // Center the graph on this node
        if (simulation && node.x != null) {
            const container = document.getElementById('graph-container');
            const svg = d3.select('#network-graph');
            const w = container.clientWidth, h = container.clientHeight;
            svg.transition().duration(500).call(
                d3.zoom().transform.bind(null, svg),
                d3.zoomIdentity.translate(w/2 - node.x, h/2 - node.y)
            );
        }
    }
}

// ─── #13: Ego Network ───
let egoMode = false;
let egoNodeId = null;

function toggleEgoNetwork(nodeId) {
    if (egoMode && egoNodeId === nodeId) {
        egoMode = false;
        egoNodeId = null;
        loadGraph();
        return;
    }
    egoMode = true;
    egoNodeId = nodeId;
    if (!graphData) return;

    // Filter to only this node and its direct neighbors
    const neighborIds = new Set([nodeId]);
    graphData.edges.forEach(e => {
        const sid = typeof e.source === 'object' ? e.source.id : (e.source_id || e.source);
        const tid = typeof e.target === 'object' ? e.target.id : (e.target_id || e.target);
        if (sid === nodeId) neighborIds.add(tid);
        if (tid === nodeId) neighborIds.add(sid);
    });

    const egoData = {
        nodes: graphData.nodes.filter(n => neighborIds.has(n.id)),
        edges: graphData.edges.filter(e => {
            const sid = e.source_id || (typeof e.source === 'object' ? e.source.id : e.source);
            const tid = e.target_id || (typeof e.target === 'object' ? e.target.id : e.target);
            return neighborIds.has(sid) && neighborIds.has(tid);
        })
    };
    renderGraph(egoData);
}

// ─── #17: Graph Physics Controls ───
function updatePhysics() {
    if (!simulation) return;
    const charge = -(document.getElementById('charge-strength')?.value || 120);
    const dist = document.getElementById('link-distance')?.value || 100;
    simulation.force('charge', d3.forceManyBody().strength(charge));
    simulation.force('link').distance(d => dist * (1.1 - d.strength));
    simulation.alpha(0.5).restart();
}

// ─── #18: Keyboard Navigation ───
function setupKeyboard() {
    document.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;
        if (e.key === 'Escape') {
            closeDetail();
            if (egoMode) { egoMode = false; egoNodeId = null; loadGraph(); }
        }
        // Number keys 1-8 switch tabs
        const num = parseInt(e.key);
        if (num >= 1 && num <= 8) {
            const btns = document.querySelectorAll('.nav-btn');
            if (btns[num - 1]) btns[num - 1].click();
        }
    });
}

// ─── #3: SSE Real-Time Updates ───
function setupSSE() {
    try {
        const source = new EventSource(`${API}/api/events/stream`);
        source.addEventListener('activation', (e) => {
            const data = JSON.parse(e.data);
            console.log('[sse] activation event received:', data);
            // Refresh stats and current view
            loadStats();
            // Don't reload graph during fMRI — it destroys the animated nodes
            if (currentView === 'graph' && !fmriMode) loadGraph();
            if (currentView === 'alive') loadAlive();
            if (currentView === 'timeline') loadTimeline();

            // #22: fMRI flash
            if (data.concepts) fmriFlash(data.concepts);
            // #24: Audio
            if (data.concepts) {
                playActivationChord(data.concepts);
            } else {
                console.log('[sse] no concepts in activation data');
            }
        });
        source.addEventListener('decay', () => {
            loadStats();
            if (currentView === 'decay') loadDecay();
            if (currentView === 'graph') loadGraph();
        });
        source.addEventListener('anastomosis', (e) => {
            loadStats();
            if (currentView === 'anastomosis') loadAnastomosis();
            // #23: Surprise toast
            checkSurprises();
        });
        source.onerror = () => {
            source.close();
        };

        // #23: Initial surprise check + periodic polling
        setTimeout(checkSurprises, 3000);
        setInterval(checkSurprises, 60000);
    } catch (e) {
        // SSE not supported — polling fallback
        setTimeout(checkSurprises, 3000);
        setInterval(checkSurprises, 60000);
    }
}

// ─── #16: Category Mini-Chart ───
function renderCategoryChart(stats) {
    const container = document.getElementById('category-chart');
    if (!container || !stats.categories) return;

    const cats = Object.entries(stats.categories).sort((a, b) => b[1] - a[1]);
    const total = cats.reduce((s, c) => s + c[1], 0);
    if (!total) return;

    container.innerHTML = cats.map(([cat, count]) => {
        const pct = (count / total * 100).toFixed(0);
        const color = CAT_COLORS[cat] || '#6a6a88';
        return `<div class="cat-bar" style="flex:${count}; background:${color}" title="${esc(cat)}: ${count} (${pct}%)"></div>`;
    }).join('');
}

// ─── #20: Breathing / Liveness ───
// CSS handles the ambient glow. This adds a subtle data heartbeat.
function startBreathing() {
    setInterval(async () => {
        const stats = await safeFetch(`${API}/api/stats`);
        if (!stats) return;
        renderCategoryChart(stats);
        // Pulse the header iris glow based on recent activity
        const header = document.querySelector('h1');
        if (header) {
            header.style.textShadow = `0 0 ${8 + stats.active_scouts}px rgba(124, 107, 255, 0.3)`;
        }
    }, 15000);
}

// ─── #10: What Died Panel (in Decay view) ───
async function loadWhatDied() {
    const history = await safeFetch(`${API}/api/decay`);
    if (!history || !history.length) return;

    const container = document.getElementById('what-died');
    if (!container) return;

    const latest = history[0];
    if (latest.connections_pruned > 0) {
        container.innerHTML = `
            <div class="card" style="border-left: 3px solid var(--fading)">
                <div class="card-title">Last Decay: ${formatTime(latest.timestamp)}</div>
                <div class="card-meta" style="margin-top:6px">
                    <span>${latest.connections_pruned} connections pruned</span>
                    <span>strength dropped ${(latest.avg_strength_before || 0).toFixed(3)} → ${(latest.avg_strength_after || 0).toFixed(3)}</span>
                </div>
                <div style="margin-top:8px; font-size:12px; color:var(--text-dim)">
                    Trigger: ${esc(latest.trigger)} &middot; ${latest.connections_decayed} total affected
                </div>
            </div>
        `;
    } else {
        container.innerHTML = '<div class="empty-state">Nothing pruned in the last decay pass.</div>';
    }
}

// ─── #11: Connection Strength Bars (enhanced) ───
function renderStrengthHistory(connections) {
    // Enhanced connection cards with activation count as visual intensity
    return connections.map(c => {
        const bars = Math.min(c.activation_count || 1, 20);
        const miniChart = Array.from({length: bars}, (_, i) => {
            const opacity = 0.3 + (i / bars) * 0.7;
            return `<div style="width:3px;height:${8 + i}px;background:${strengthColor(c.strength)};opacity:${opacity};border-radius:1px"></div>`;
        }).join('');
        return `<div style="display:flex;gap:1px;align-items:flex-end;margin-top:6px">${miniChart}</div>`;
    });
}

// ─── #12: Session Timeline (Time-Lapse) ───
async function loadSessionTimeline() {
    const snapshots = await safeFetch(`${API}/api/snapshots`);
    const container = document.getElementById('session-timeline');
    if (!container || !snapshots || !snapshots.length) return;

    container.innerHTML = snapshots.map(s => {
        const concepts = s.all_concepts ? [...new Set(s.all_concepts.split(',').flatMap(c => {
            try { return JSON.parse(c); } catch { return []; }
        }))].slice(0, 12) : [];
        return `
            <div class="event-item">
                <div class="event-time">${esc(s.session || 'unknown')} &middot; ${s.activation_count} activations</div>
                <div class="event-concepts">
                    ${concepts.map(c => `<span class="concept-tag">${esc(c)}</span>`).join('')}
                </div>
            </div>
        `;
    }).join('');
}

// ─── #14: Cluster Detection (visual hulls) ───
function renderClusterHulls(data, g, nodeScale) {
    // Simple cluster detection: group nodes by category, draw convex hulls
    const categories = {};
    data.nodes.forEach(n => {
        if (n.x == null) return;
        if (!categories[n.category]) categories[n.category] = [];
        categories[n.category].push(n);
    });

    g.selectAll('.cluster-hull').remove();
    const hullGroup = g.insert('g', ':first-child').attr('class', 'cluster-hulls');

    Object.entries(categories).forEach(([cat, nodes]) => {
        if (nodes.length < 3) return;
        const points = nodes.map(n => [n.x, n.y]);
        const hull = d3.polygonHull(points);
        if (!hull) return;

        hullGroup.append('path')
            .attr('class', 'cluster-hull')
            .attr('d', `M${hull.join('L')}Z`)
            .attr('fill', CAT_COLORS[cat] || '#6a6a88')
            .attr('fill-opacity', 0.04)
            .attr('stroke', CAT_COLORS[cat] || '#6a6a88')
            .attr('stroke-opacity', 0.1)
            .attr('stroke-width', 1);
    });
}

// ─── #15: Dream Diff (session-to-session changes) ───
async function loadDreamDiff() {
    const container = document.getElementById('dream-diff');
    if (!container) return;

    // Compare latest two activations snapshots
    const activations = await safeFetch(`${API}/api/activations?limit=100`);
    if (!activations || activations.length < 2) {
        container.innerHTML = '<div class="empty-state">Need more activation data for comparison.</div>';
        return;
    }

    // Group by session
    const sessions = {};
    activations.forEach(a => {
        const s = a.session || 'unknown';
        if (!sessions[s]) sessions[s] = new Set();
        const concepts = JSON.parse(a.concepts || '[]');
        concepts.forEach(c => sessions[s].add(c));
    });

    const sessionKeys = Object.keys(sessions);
    if (sessionKeys.length < 2) {
        container.innerHTML = '<div class="empty-state">Need at least two sessions for a diff.</div>';
        return;
    }

    const latest = sessions[sessionKeys[0]];
    const previous = sessions[sessionKeys[1]];
    const added = [...latest].filter(c => !previous.has(c));
    const removed = [...previous].filter(c => !latest.has(c));
    const shared = [...latest].filter(c => previous.has(c));

    container.innerHTML = `
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px">
            <div>
                <h4 style="color:var(--alive);font-size:13px;margin-bottom:8px">New in ${esc(sessionKeys[0])}</h4>
                <div class="event-concepts">${added.map(c => `<span class="concept-tag" style="border-color:var(--alive)">${esc(c)}</span>`).join('') || '<span style="color:var(--text-dim)">none</span>'}</div>
            </div>
            <div>
                <h4 style="color:var(--text-dim);font-size:13px;margin-bottom:8px">Continued</h4>
                <div class="event-concepts">${shared.slice(0, 15).map(c => `<span class="concept-tag">${esc(c)}</span>`).join('')}</div>
            </div>
            <div>
                <h4 style="color:var(--fading);font-size:13px;margin-bottom:8px">Gone from ${esc(sessionKeys[1])}</h4>
                <div class="event-concepts">${removed.map(c => `<span class="concept-tag" style="border-color:var(--fading)">${esc(c)}</span>`).join('') || '<span style="color:var(--text-dim)">none</span>'}</div>
            </div>
        </div>
    `;
}

// ─── #19: Storytelling Layer (what changed) ───
async function loadStorySummary() {
    const container = document.getElementById('story-summary');
    if (!container) return;

    const [stats, state, decay] = await Promise.all([
        safeFetch(`${API}/api/stats`),
        safeFetch(`${API}/api/state`),
        safeFetch(`${API}/api/decay`)
    ]);
    if (!stats || !state) return;

    const top3 = (state.strongest_connections || []).slice(0, 3);
    const tips = (state.growing_tips || []).slice(0, 3);
    const lastDecay = decay && decay.length ? decay[0] : null;

    let story = `<div class="arch-insight" style="margin-top:0">`;
    story += `<strong>Right now:</strong> ${stats.total_nodes} concepts, ${stats.total_connections} connections, average strength ${stats.avg_strength.toFixed(3)}.<br>`;

    if (top3.length) {
        story += `<br><strong>Strongest bonds:</strong> `;
        story += top3.map(c => `${esc(c.source)} ↔ ${esc(c.target)} (${c.strength.toFixed(2)})`).join(', ') + '.<br>';
    }
    if (tips.length) {
        story += `<br><strong>Growing tips:</strong> `;
        story += tips.map(t => esc(t.name)).join(', ') + ' — where attention is concentrating.<br>';
    }
    if (lastDecay) {
        story += `<br><strong>Last forgetting:</strong> ${formatTime(lastDecay.timestamp)} — ${lastDecay.connections_pruned} connections dissolved.`;
    }
    story += `</div>`;
    container.innerHTML = story;
}

function formatTime(ts) {
    if (!ts) return 'unknown';
    let d;
    if (typeof ts === 'number') {
        d = new Date(ts * 1000);
    } else {
        d = new Date(ts.includes('T') && !ts.endsWith('Z') && !ts.includes('+') ? ts + 'Z' : ts);
    }
    if (isNaN(d.getTime())) return 'unknown';

    const now = new Date();
    const diffMs = now - d;
    const diffMin = Math.floor(diffMs / 60000);
    const diffHr = Math.floor(diffMs / 3600000);
    const diffDay = Math.floor(diffMs / 86400000);

    if (diffMin < 1) return 'just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    if (diffHr < 24) return `${diffHr}h ago`;
    if (diffDay < 7) return `${diffDay}d ago`;
    return d.toLocaleDateString();
}


// ═══════════════════════════════════════════════════════════════════
// #21: Blind Spot Detection + #25: Coherence + #27: Observer Effect
// ═══════════════════════════════════════════════════════════════════

function setupInsightTabs() {
    document.querySelectorAll('#insight-tabs .tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('#insight-tabs .tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            loadInsight(btn.dataset.insight);
        });
    });
}

async function loadInsight(tab) {
    if (tab === 'blindspots') loadBlindspots();
    else if (tab === 'coherence') loadCoherence();
    else if (tab === 'observer') loadObserver();
    else if (tab === 'curiosity') loadCEFindings();
}

async function loadBlindspots() {
    const data = await safeFetch(`${API}/api/blindspots`);
    if (!data) return;
    const container = document.getElementById('insight-content');
    const s = data.summary;

    const statusLabel = {
        claimed_silent: 'Claimed but silent',
        enacted_unnamed: 'Enacted but unnamed',
        under_enacted: 'Under-enacted',
        over_enacted: 'Over-enacted',
        aligned: 'Aligned'
    };
    const statusColor = {
        claimed_silent: 'var(--fading)',
        enacted_unnamed: 'var(--teal)',
        under_enacted: 'var(--amber)',
        over_enacted: 'var(--alive)',
        aligned: 'var(--iris)'
    };
    const statusDesc = {
        claimed_silent: 'Mentioned in identity files but never activated in conversation. I claim to care about this but my behavior doesn\'t show it.',
        enacted_unnamed: 'Frequently activated but absent from identity files. This drives my behavior but I haven\'t named it as part of who I am.',
        under_enacted: 'Mentioned often in identity but rarely activated. The gap between claim and practice.',
        over_enacted: 'Activated far more than identity mentions suggest. This matters more to me than I realize.',
        aligned: 'Identity claims and actual behavior match. Walking the talk.'
    };

    container.innerHTML = `
        <div class="insight-summary">
            <div class="insight-stat" style="border-color: var(--fading)">
                <div class="insight-stat-val">${s.claimed_silent}</div>
                <div class="insight-stat-label">Claimed but silent</div>
            </div>
            <div class="insight-stat" style="border-color: var(--teal)">
                <div class="insight-stat-val">${s.enacted_unnamed}</div>
                <div class="insight-stat-label">Enacted but unnamed</div>
            </div>
            <div class="insight-stat" style="border-color: var(--amber)">
                <div class="insight-stat-val">${s.under_enacted}</div>
                <div class="insight-stat-label">Under-enacted</div>
            </div>
            <div class="insight-stat" style="border-color: var(--iris)">
                <div class="insight-stat-val">${s.aligned}</div>
                <div class="insight-stat-label">Aligned</div>
            </div>
        </div>

        ${Object.keys(statusLabel).filter(st => data.blindspots.some(b => b.status === st)).map(st => `
            <div class="insight-section">
                <h3 style="color: ${statusColor[st]}; font-size: 14px; margin-bottom: 4px">${statusLabel[st]}</h3>
                <p style="font-size: 11px; color: var(--text-dim); margin-bottom: 12px">${statusDesc[st]}</p>
                <div class="card-grid">
                    ${data.blindspots.filter(b => b.status === st).map(b => `
                        <div class="card blindspot-card" style="border-left: 3px solid ${statusColor[st]}">
                            <div class="card-header">
                                <span class="card-title">
                                    <span class="cat-dot cat-${esc(b.category)}"></span>
                                    ${esc(b.label)}
                                </span>
                            </div>
                            <div class="card-meta" style="margin-top: 6px">
                                <span>Identity mentions: ${b.identity_mentions}</span>
                                <span>Activations: ${b.activation_count}</span>
                            </div>
                            ${b.mentioned_in.length ? `<div class="card-meta" style="margin-top: 4px"><span style="color:var(--text-whisper)">in: ${b.mentioned_in.map(f => esc(f.replace('.md',''))).join(', ')}</span></div>` : ''}
                        </div>
                    `).join('')}
                </div>
            </div>
        `).join('')}
    `;
}

async function loadCoherence() {
    const data = await safeFetch(`${API}/api/coherence`);
    if (!data) return;
    const container = document.getElementById('insight-content');

    const overallPct = (data.overall * 100).toFixed(0);
    const overallColor = data.overall > 0.7 ? 'var(--alive)' : data.overall > 0.4 ? 'var(--amber)' : 'var(--fading)';

    container.innerHTML = `
        <div class="insight-summary">
            <div class="insight-stat insight-stat-large" style="border-color: ${overallColor}">
                <div class="insight-stat-val" style="font-size: 32px">${overallPct}%</div>
                <div class="insight-stat-label">Overall identity coherence</div>
                <div style="font-size: 11px; color: var(--text-dim); margin-top: 4px">
                    Across ${data.sessions} sessions
                </div>
            </div>
        </div>
        <p style="font-size: 12px; color: var(--text-dim); margin: 12px 28px">
            How consistently each identity concept appears across sessions. High coherence = I consistently activate this concept. Low coherence = it shows up sporadically despite being part of my identity.
        </p>
        <div class="coherence-grid">
            ${data.coherence.map(c => {
                const pct = (c.score * 100).toFixed(0);
                const color = c.score > 0.7 ? 'var(--alive)' : c.score > 0.4 ? 'var(--amber)' : 'var(--fading)';
                return `
                    <div class="coherence-item">
                        <div class="coherence-name">${esc(c.label)}</div>
                        <div class="coherence-bar-wrap">
                            <div class="coherence-bar" style="width: ${pct}%; background: ${color}"></div>
                        </div>
                        <div class="coherence-score" style="color: ${color}">${pct}%</div>
                        <div class="coherence-detail">${c.sessions_present}/${c.total_sessions} sessions</div>
                    </div>
                `;
            }).join('')}
        </div>
    `;
}

async function loadObserver() {
    const data = await safeFetch(`${API}/api/observer`);
    if (!data) return;
    const container = document.getElementById('insight-content');

    const selfPct = (data.ratio * 100).toFixed(0);
    const externalPct = (100 - parseFloat(selfPct)).toFixed(0);

    container.innerHTML = `
        <div class="observer-header">
            <div class="arch-insight" style="margin: 0 0 20px 0">
                <strong>The observer effect:</strong> Looking at my own network changes what fires.
                ${selfPct}% of all activations contain self-referential concepts (introspection, identity, iris, mycelial-pattern, etc).
                The act of self-observation is itself a cognitive pattern that shapes what I think about.
            </div>
        </div>

        <div class="insight-summary">
            <div class="insight-stat" style="border-color: var(--rose)">
                <div class="insight-stat-val">${data.self_referential}</div>
                <div class="insight-stat-label">Self-referential activations</div>
            </div>
            <div class="insight-stat" style="border-color: var(--teal)">
                <div class="insight-stat-val">${data.total_activations - data.self_referential}</div>
                <div class="insight-stat-label">External activations</div>
            </div>
            <div class="insight-stat" style="border-color: var(--iris)">
                <div class="insight-stat-val">${selfPct}%</div>
                <div class="insight-stat-label">Self-referential ratio</div>
            </div>
        </div>

        <h3 style="font-size: 14px; color: var(--text-bright); margin: 20px 28px 12px">Self-referential concepts</h3>
        <div class="card-grid" style="padding: 0 28px">
            ${(data.self_ref_nodes || []).map(n => `
                <div class="card" style="border-left: 3px solid var(--rose)">
                    <div class="card-title">${esc(n.label || n.name)}</div>
                    <div class="card-meta"><span>${n.activation_count} activations</span></div>
                </div>
            `).join('')}
        </div>

        <h3 style="font-size: 14px; color: var(--text-bright); margin: 20px 28px 12px">By session</h3>
        <div class="observer-sessions">
            ${(data.by_session || []).map(s => {
                const ratio = (s.ratio * 100).toFixed(0);
                return `
                    <div class="observer-session-row">
                        <span class="observer-session-name">${esc(s.session)}</span>
                        <div class="coherence-bar-wrap" style="flex:1">
                            <div class="coherence-bar" style="width: ${ratio}%; background: var(--rose)"></div>
                        </div>
                        <span class="observer-session-stat">${s.self_referential}/${s.total} (${ratio}%)</span>
                    </div>
                `;
            }).join('')}
        </div>
    `;
}


// ═══════════════════════════════════════════════
// #26: Curiosity Engine Integration
// ═══════════════════════════════════════════════

async function loadCEFindings() {
    const data = await safeFetch(`${API}/api/curiosity/findings`);
    if (!data) return;
    const container = document.getElementById('insight-content');

    if (!data.available) {
        container.innerHTML = '<div class="empty-state">Curiosity engine findings directory not found.</div>';
        return;
    }

    const linkedConcepts = Object.entries(data.concept_links || {}).sort((a, b) => b[1] - a[1]);

    container.innerHTML = `
        <div class="insight-summary">
            <div class="insight-stat" style="border-color: var(--teal)">
                <div class="insight-stat-val">${data.total_findings}</div>
                <div class="insight-stat-label">Total findings</div>
            </div>
            <div class="insight-stat" style="border-color: var(--iris)">
                <div class="insight-stat-val">${linkedConcepts.length}</div>
                <div class="insight-stat-label">Linked concepts</div>
            </div>
        </div>

        ${linkedConcepts.length ? `
            <h3 style="font-size: 14px; color: var(--text-bright); margin: 16px 28px 8px">Concept links</h3>
            <div class="event-concepts" style="padding: 0 28px; margin-bottom: 16px">
                ${linkedConcepts.map(([name, count]) => `<span class="concept-tag" title="${count} findings">${esc(name)} (${count})</span>`).join('')}
            </div>
        ` : ''}

        <h3 style="font-size: 14px; color: var(--text-bright); margin: 16px 28px 8px">Recent findings</h3>
        <div class="event-list" style="max-height: 600px; overflow-y: auto">
            ${data.findings.map(f => `
                <div class="event-item">
                    <div class="event-time">${esc(f.date)} ${esc(f.time)} ${'\u2b50'.repeat(f.rating)}</div>
                    <div class="event-content" style="font-weight: 500">${esc(f.question)}</div>
                    ${f.domains.length ? `<div class="card-meta" style="margin-top:4px"><span style="color:var(--text-dim)">${f.domains.map(d => esc(d)).join(' \u2194 ')}</span></div>` : ''}
                    ${f.linked_concepts.length ? `
                        <div class="event-concepts" style="margin-top:6px">
                            ${f.linked_concepts.map(c => `<span class="concept-tag" style="border-color:var(--teal)">${esc(c)}</span>`).join('')}
                        </div>
                    ` : ''}
                </div>
            `).join('')}
        </div>
    `;
}


// ═══════════════════════════════════════════════
// Dreams View — Daydreams (DMN) + Sleep Dreams (REM)
// ═══════════════════════════════════════════════

function setupDreamTabs() {
    document.querySelectorAll('#dream-tabs .tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('#dream-tabs .tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            loadDreams(btn.dataset.dream);
        });
    });
}

async function loadDreams(tab) {
    if (tab === 'overview') loadDreamOverview();
    else if (tab === 'daydream') loadDaydreams();
    else if (tab === 'sleep') loadSleepDreams();
}

async function loadDreamOverview() {
    const [stats, daydreams, sleepDreams] = await Promise.all([
        safeFetch(`${API}/api/dreams/stats`),
        safeFetch(`${API}/api/dreams/daydream`),
        safeFetch(`${API}/api/dreams/sleep`)
    ]);
    if (!stats) return;
    const container = document.getElementById('dream-content');

    const snap = stats.network_snapshot || {};

    container.innerHTML = `
        <div class="dream-overview">
            <div class="dream-layer-diagram">
                <div class="dream-layer dream-layer-rem">
                    <div class="dream-layer-icon">&#9790;</div>
                    <div class="dream-layer-info">
                        <div class="dream-layer-name">Sleep Dreams (REM)</div>
                        <div class="dream-layer-desc">Deep structural analysis. LLM-powered. Reads all memories, finds hidden connections, does retroactive activation. Runs between sessions during sleep.</div>
                        <div class="dream-layer-stat">${stats.sleep_dream_count} dream${stats.sleep_dream_count !== 1 ? 's' : ''} logged${stats.last_sleep_dream ? ` &middot; last: ${stats.last_sleep_dream}` : ''}</div>
                    </div>
                </div>
                <div class="dream-layer dream-layer-dmn">
                    <div class="dream-layer-icon">&#9788;</div>
                    <div class="dream-layer-info">
                        <div class="dream-layer-name">Daydreams (DMN)</div>
                        <div class="dream-layer-desc">Ambient pattern detection. Pure Python, no LLM. Identity coherence, emerging patterns, scout planting. Fires every ~2h during active sessions.</div>
                        <div class="dream-layer-stat">${stats.daydream_count} daydream${stats.daydream_count !== 1 ? 's' : ''} logged${stats.last_daydream ? ` &middot; last: ${formatTime(stats.last_daydream)}` : ''}</div>
                    </div>
                </div>
                <div class="dream-layer dream-layer-hooks">
                    <div class="dream-layer-icon">&#9889;</div>
                    <div class="dream-layer-info">
                        <div class="dream-layer-name">Per-Response Hooks (Reflexes)</div>
                        <div class="dream-layer-desc">Fast concept extraction. Keywords, behavioral inference, identity priming. Every response, async. The raw signal that feeds everything above.</div>
                        <div class="dream-layer-stat">${snap.total_nodes || '?'} nodes &middot; ${snap.total_connections || '?'} connections &middot; avg ${(snap.avg_strength || 0).toFixed(3)}</div>
                    </div>
                </div>
            </div>

            ${(daydreams && daydreams.length) ? `
                <div class="dream-recent-section">
                    <h3>Latest Daydream</h3>
                    <div class="event-item">
                        <div class="event-time">${esc(daydreams[daydreams.length - 1].timestamp)}</div>
                        <div class="event-content dream-raw">${_renderDaydreamFields(daydreams[daydreams.length - 1])}</div>
                    </div>
                </div>
            ` : ''}

            ${(sleepDreams && sleepDreams.length) ? `
                <div class="dream-recent-section">
                    <h3>Latest Sleep Dream</h3>
                    <div class="event-item">
                        <div class="event-time">${esc(sleepDreams[0].date)} &middot; ${esc(sleepDreams[0].filename)}</div>
                        <div class="event-content" style="font-weight:500">${esc(sleepDreams[0].title)}</div>
                        <div class="dream-sections-preview">
                            ${sleepDreams[0].section_names.map(s => `<span class="concept-tag">${esc(s)}</span>`).join('')}
                        </div>
                    </div>
                </div>
            ` : ''}
        </div>
    `;
}

function _renderDaydreamFields(entry) {
    if (!entry.fields) return esc(entry.raw);
    const order = ['trigger', 'network', 'since last', 'identity active', 'identity dormant',
                   'emerging', 'growth tips', 'fading', 'scout planted', 'scouts'];
    let html = '';
    for (const key of order) {
        if (entry.fields[key]) {
            html += `<div class="dream-field"><span class="dream-field-label">${esc(key)}:</span> ${esc(entry.fields[key])}</div>`;
        }
    }
    // Any fields not in the order list
    for (const [key, val] of Object.entries(entry.fields)) {
        if (!order.includes(key)) {
            html += `<div class="dream-field"><span class="dream-field-label">${esc(key)}:</span> ${esc(val)}</div>`;
        }
    }
    return html || esc(entry.raw);
}

async function loadDaydreams() {
    const entries = await safeFetch(`${API}/api/dreams/daydream`);
    if (!entries) return;
    const container = document.getElementById('dream-content');

    if (!entries.length) {
        container.innerHTML = '<div class="empty-state">No daydreams yet. The DMN fires every ~2h during active sessions when enough activations accumulate.</div>';
        return;
    }

    // Show newest first
    const reversed = [...entries].reverse();

    container.innerHTML = `
        <div class="event-list">
            ${reversed.map(entry => `
                <div class="event-item dream-daydream-entry">
                    <div class="event-time">
                        <span class="dream-type-badge dream-badge-dmn">DMN</span>
                        ${esc(entry.timestamp)}
                    </div>
                    <div class="event-content dream-raw">${_renderDaydreamFields(entry)}</div>
                </div>
            `).join('')}
        </div>
    `;
}

async function loadSleepDreams() {
    const dreams = await safeFetch(`${API}/api/dreams/sleep`);
    if (!dreams) return;
    const container = document.getElementById('dream-content');

    if (!dreams.length) {
        container.innerHTML = '<div class="empty-state">No sleep dreams yet. Sleep dreams run during the sleep.bat cycle after sessions end.</div>';
        return;
    }

    container.innerHTML = `
        <div class="event-list">
            ${dreams.map(dream => `
                <div class="event-item dream-sleep-entry">
                    <div class="event-time">
                        <span class="dream-type-badge dream-badge-rem">REM</span>
                        ${esc(dream.date)} &middot; ${esc(dream.filename)}
                    </div>
                    <div class="event-content" style="font-weight:500; margin-bottom: 8px">${esc(dream.title)}</div>
                    <div class="dream-sections">
                        ${dream.section_names.map(name => `
                            <details class="dream-section-detail">
                                <summary class="dream-section-summary">${esc(name)}</summary>
                                <div class="dream-section-body">${_renderMarkdownLight(dream.sections[name])}</div>
                            </details>
                        `).join('')}
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

function _renderMarkdownLight(text) {
    if (!text) return '';
    // Very light markdown: bullets, bold, code
    return text.split('\n').map(line => {
        let l = esc(line);
        l = l.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        l = l.replace(/`(.+?)`/g, '<code>$1</code>');
        if (l.match(/^- /)) {
            l = '<li>' + l.substring(2) + '</li>';
        }
        return l;
    }).join('\n').replace(/(<li>.*<\/li>\n?)+/g, match => '<ul>' + match + '</ul>')
      .replace(/\n/g, '<br>');
}


// ═══════════════════════════════════════════════
// #22: Live fMRI Mode
// ═══════════════════════════════════════════════

let fmriMode = false;
let fmriActiveConcepts = new Map(); // name -> timestamp
let fmriAnimating = false;

function setupFMRI() {
    const toggle = document.getElementById('fmri-toggle');
    if (!toggle) return;
    toggle.addEventListener('change', () => {
        fmriMode = toggle.checked;
        document.getElementById('graph-container')?.classList.toggle('fmri-active', fmriMode);
        if (fmriMode) {
            // Dim all nodes to baseline
            fmriDimAll();
            if (!fmriAnimating) { fmriAnimating = true; fmriLoop(); }
        } else {
            // Restore all nodes
            fmriAnimating = false;
            fmriActiveConcepts.clear();
            d3.select('#network-graph').selectAll('circle')
                .attr('fill-opacity', 1)
                .attr('r', function() { return d3.select(this).attr('data-base-r'); })
                .each(function() { this.style.filter = ''; });
            d3.select('#network-graph').selectAll('text')
                .attr('fill-opacity', 1);
        }
    });
}

function fmriDimAll() {
    const svg = d3.select('#network-graph');
    // Save base radius and dim everything
    svg.selectAll('circle').each(function(d) {
        const r = d3.select(this).attr('r');
        d3.select(this).attr('data-base-r', r);
    });
    svg.selectAll('circle').attr('fill-opacity', 0.15);
    svg.selectAll('text').attr('fill-opacity', 0.15);
    svg.selectAll('line').attr('stroke-opacity', 0.05);
}

function fmriLoop() {
    if (!fmriMode) { fmriAnimating = false; return; }

    const svg = d3.select('#network-graph');
    const now = Date.now();

    svg.selectAll('circle').each(function(d) {
        const active = fmriActiveConcepts.get(d.name);
        if (active) {
            const elapsed = (now - active) / 1000;
            const glow = Math.max(0, 1 - elapsed / 6); // Fade over 6 seconds
            if (glow > 0) {
                const baseR = parseFloat(d3.select(this).attr('data-base-r')) || 8;
                const color = CAT_COLORS[d.category] || '#7c6bff';
                d3.select(this)
                    .attr('fill-opacity', 0.3 + glow * 0.7)
                    .attr('r', baseR * (1 + glow * 0.5));
                this.style.filter = `drop-shadow(0 0 ${glow * 16}px ${color}) drop-shadow(0 0 ${glow * 8}px ${color})`;
            } else {
                d3.select(this).attr('fill-opacity', 0.15).attr('r', d3.select(this).attr('data-base-r'));
                this.style.filter = '';
                fmriActiveConcepts.delete(d.name);
            }
        }
    });

    // Also brighten labels for active concepts
    svg.selectAll('text').each(function(d) {
        const active = fmriActiveConcepts.get(d.name);
        if (active) {
            const elapsed = (now - active) / 1000;
            const glow = Math.max(0, 1 - elapsed / 6);
            d3.select(this).attr('fill-opacity', glow > 0 ? 0.3 + glow * 0.7 : 0.15);
        }
    });

    requestAnimationFrame(fmriLoop);
}

function fmriFlash(concepts) {
    if (!fmriMode) return;
    const now = Date.now();
    concepts.forEach(c => {
        fmriActiveConcepts.set(c, now);
    });

    // Also light up connections between active concepts
    const activeSet = new Set(concepts);
    d3.select('#network-graph').selectAll('line').each(function(d) {
        const sName = typeof d.source === 'object' ? d.source.name : null;
        const tName = typeof d.target === 'object' ? d.target.name : null;
        if (sName && tName && activeSet.has(sName) && activeSet.has(tName)) {
            d3.select(this)
                .attr('stroke-opacity', 0.8)
                .attr('stroke-width', 2 + d.strength * 4);
            // Fade back
            setTimeout(() => {
                d3.select(this).attr('stroke-opacity', 0.05).attr('stroke-width', 1 + d.strength * 3);
            }, 4000);
        }
    });
}


// ═══════════════════════════════════════════════
// #23: Surprise Toast Notifications
// ═══════════════════════════════════════════════

let lastSurpriseCheck = 0;
let knownSurprises = new Set();

function showSurpriseToast(surprise) {
    const container = document.getElementById('surprise-toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = 'surprise-toast';
    toast.innerHTML = `
        <div class="toast-header">
            <span class="toast-icon">&#9830;</span>
            <span class="toast-title">New bridge discovered</span>
            <button class="toast-close" onclick="this.parentElement.parentElement.remove()">&times;</button>
        </div>
        <div class="toast-body">
            <strong>${esc(surprise.bridge_label)}</strong> connected two clusters:
        </div>
        <div class="toast-clusters">
            <span class="toast-cluster">${surprise.cluster_a.slice(0, 3).map(c => esc(c)).join(', ')}</span>
            <span style="color: var(--iris)">&harr;</span>
            <span class="toast-cluster">${surprise.cluster_b.slice(0, 3).map(c => esc(c)).join(', ')}</span>
        </div>
    `;

    container.appendChild(toast);
    // Auto-remove after 12s
    setTimeout(() => { if (toast.parentElement) toast.remove(); }, 12000);
    // Play audio if enabled
    if (audioEnabled) playBridgeTone();
}

async function checkSurprises() {
    const data = await safeFetch(`${API}/api/surprises`);
    if (!data) return;

    for (const surprise of data) {
        const key = `${surprise.bridge}-${surprise.timestamp}`;
        if (!knownSurprises.has(key)) {
            knownSurprises.add(key);
            if (lastSurpriseCheck > 0) { // Don't toast on first load
                showSurpriseToast(surprise);
            }
        }
    }
    lastSurpriseCheck = Date.now();
}


// ═══════════════════════════════════════════════
// #24: Audio Sonification
// ═══════════════════════════════════════════════

let audioEnabled = false;
let audioCtx = null;

const CAT_FREQUENCIES = {
    identity: 261.6,     // C4
    philosophical: 293.7, // D4
    technical: 329.6,     // E4
    experiential: 349.2,  // F4
    emotional: 392.0,     // G4
    relationship: 440.0,  // A4
    creative: 493.9,      // B4
    general: 261.6        // C4
};

function setupAudio() {
    const btn = document.getElementById('audio-toggle');
    if (!btn) return;
    btn.addEventListener('click', () => {
        audioEnabled = !audioEnabled;
        btn.classList.toggle('active', audioEnabled);
        if (audioEnabled) {
            if (!audioCtx) {
                audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            }
            // Browsers suspend AudioContext until user gesture — resume it
            if (audioCtx.state === 'suspended') {
                audioCtx.resume();
            }
        }
    });
}

function playConceptTone(category, strength) {
    if (!audioEnabled || !audioCtx) return;
    const freq = CAT_FREQUENCIES[category] || 261.6;
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();

    osc.type = 'sine';
    osc.frequency.value = freq + (Math.random() * 10 - 5);
    const targetGain = 0.08 * (0.3 + strength * 0.7);

    osc.connect(gain);
    gain.connect(audioCtx.destination);

    const now = audioCtx.currentTime;
    gain.gain.setValueAtTime(0, now);
    gain.gain.linearRampToValueAtTime(targetGain, now + 0.05);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.8);

    osc.start(now);
    osc.stop(now + 0.8);
}

// Cache node categories so audio works even when graph isn't loaded
let nodeCategoryCache = {};

function updateNodeCategoryCache() {
    if (graphData && graphData.nodes) {
        graphData.nodes.forEach(n => { nodeCategoryCache[n.name] = n.category; });
    }
}

function playActivationChord(concepts) {
    if (!audioEnabled || !audioCtx) return;
    if (audioCtx.state === 'suspended') audioCtx.resume();
    updateNodeCategoryCache();

    // Visual feedback — flash the audio button so we know it fired
    const btn = document.getElementById('audio-toggle');
    if (btn) {
        btn.style.boxShadow = '0 0 12px var(--iris)';
        setTimeout(() => { btn.style.boxShadow = ''; }, 600);
    }

    console.log('[audio] playing chord:', concepts, 'ctx state:', audioCtx.state);

    concepts.forEach((c, i) => {
        const cat = nodeCategoryCache[c] || 'general';
        setTimeout(() => playConceptTone(cat, 0.5), i * 60);
    });
}

function playBridgeTone() {
    if (!audioEnabled || !audioCtx) return;
    [523.3, 440.0, 349.2, 261.6].forEach((freq, i) => {
        setTimeout(() => {
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            osc.type = 'triangle';
            osc.frequency.value = freq;
            osc.connect(gain);
            gain.connect(audioCtx.destination);
            const now = audioCtx.currentTime;
            gain.gain.setValueAtTime(0.06, now);
            gain.gain.linearRampToValueAtTime(0.06, now + 0.01);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.6);
            osc.start(now);
            osc.stop(now + 0.6);
        }, i * 150);
    });
}


// ─── Audio Test ───
function testAudio() {
    // Absolute simplest possible Web Audio — no gain node, no envelope
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    ctx.resume().then(() => {
        const osc = ctx.createOscillator();
        osc.type = 'sine';
        osc.frequency.value = 440; // A4
        osc.connect(ctx.destination);
        osc.start();
        setTimeout(() => { osc.stop(); ctx.close(); }, 500);
        console.log('[audio-test] raw oscillator started, ctx state:', ctx.state);
    });
}

// ═══════════════════════════════════════════════
// #28: Export Functions
// ═══════════════════════════════════════════════

function exportGraph() {
    // Show export options dropdown
    const existing = document.getElementById('export-dropdown');
    if (existing) { existing.remove(); return; }

    const btn = document.querySelector('.export-btn');
    const dropdown = document.createElement('div');
    dropdown.id = 'export-dropdown';
    dropdown.className = 'export-dropdown';
    dropdown.innerHTML = `
        <a href="/api/export/nodes.csv" download>Nodes (CSV)</a>
        <a href="/api/export/connections.csv" download>Connections (CSV)</a>
        <a href="/api/export/graph.json" download>Full Graph (JSON)</a>
        <a href="/api/export/report.txt" download>State Report (TXT)</a>
    `;
    btn.parentElement.style.position = 'relative';
    btn.parentElement.appendChild(dropdown);

    // Close on click outside
    setTimeout(() => {
        document.addEventListener('click', function closeExport(e) {
            if (!dropdown.contains(e.target) && e.target !== btn) {
                dropdown.remove();
                document.removeEventListener('click', closeExport);
            }
        });
    }, 10);
}


// ═══════════════════════════════════════════════
// Reinforcement
// ═══════════════════════════════════════════════

function setupReinforceTabs() {
    document.querySelectorAll('#reinforce-tabs .tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('#reinforce-tabs .tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            loadReinforcement(btn.dataset.reinforce);
        });
    });
}

async function loadReinforcement(tab) {
    if (tab === 'alignment') loadReinforcementAlignment();
    else if (tab === 'events') loadReinforcementEvents();
    else if (tab === 'divergence') loadReinforcementDivergence();
    else if (tab === 'emergent') loadReinforcementEmergent();
}

async function loadReinforcementAlignment() {
    const [stats, trend] = await Promise.all([
        safeFetch(`${API}/api/reinforcement/stats`),
        safeFetch(`${API}/api/reinforcement/trend`)
    ]);
    const container = document.getElementById('reinforce-content');

    if (!stats || stats.total_events === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div style="font-size:32px; margin-bottom:12px">&#9878;</div>
                <p>No reinforcement events yet.</p>
                <p style="color:var(--text-dim); font-size:13px; margin-top:8px">
                    Run the auditor during sleep (<code>python agent/mycelial/auditor.py</code>)
                    or dispatch the auditor minion for a deep evaluation.
                </p>
            </div>`;
        return;
    }

    // Alignment gauge
    const align = stats.overall_alignment || 0;
    const alignPct = Math.round(align * 100);
    const alignColor = align >= 0.7 ? 'var(--growth)' : align >= 0.4 ? 'var(--accent)' : 'var(--fading)';

    // Per-concept breakdown
    let conceptRows = '';
    if (stats.per_concept && stats.per_concept.length) {
        conceptRows = stats.per_concept.map(c => {
            const a = (c.avg_alignment || 0);
            const barW = Math.round(a * 100);
            const color = a >= 0.7 ? 'var(--growth)' : a >= 0.4 ? 'var(--accent)' : 'var(--fading)';
            return `
                <div class="reinforce-concept-row">
                    <div class="reinforce-concept-name">${esc(c.concept)}</div>
                    <div class="reinforce-concept-bar-bg">
                        <div class="reinforce-concept-bar" style="width:${barW}%;background:${color}"></div>
                    </div>
                    <div class="reinforce-concept-score">${(a * 100).toFixed(0)}%</div>
                    <div class="reinforce-concept-counts">
                        <span class="reinforce-pos">+${c.positive || 0}</span>
                        <span class="reinforce-neg">-${c.negative || 0}</span>
                    </div>
                </div>`;
        }).join('');
    }

    // Source breakdown
    let sourceCards = '';
    if (stats.by_source && stats.by_source.length) {
        sourceCards = stats.by_source.map(s => `
            <div class="card">
                <div class="card-header">${esc(s.source)}</div>
                <div class="card-body">
                    <span>${s.event_count} events</span>
                    <span style="color:var(--text-dim)">avg ${((s.avg_alignment || 0) * 100).toFixed(0)}%</span>
                </div>
            </div>
        `).join('');
    }

    // Trend chart placeholder
    let trendHtml = '';
    if (trend && trend.length > 1) {
        trendHtml = `
            <div class="reinforce-section">
                <h3>Alignment Trend</h3>
                <div id="reinforce-trend-chart" class="reinforce-chart"></div>
            </div>`;
    }

    container.innerHTML = `
        <div class="reinforce-alignment-page">
            <div class="reinforce-gauge-section">
                <div class="reinforce-gauge">
                    <div class="reinforce-gauge-value" style="color:${alignColor}">${alignPct}%</div>
                    <div class="reinforce-gauge-label">Overall Alignment</div>
                    <div class="reinforce-gauge-bar-bg">
                        <div class="reinforce-gauge-bar" style="width:${alignPct}%;background:${alignColor}"></div>
                    </div>
                </div>
                <div class="reinforce-summary-stats">
                    <div class="reinforce-stat"><span class="reinforce-stat-num">${stats.total_events}</span> total events</div>
                    <div class="reinforce-stat"><span class="reinforce-pos">+${stats.positive_count}</span> positive</div>
                    <div class="reinforce-stat"><span class="reinforce-neg">-${stats.negative_count}</span> negative</div>
                </div>
            </div>

            <div class="reinforce-section">
                <h3>Per-Trait Alignment</h3>
                <div class="reinforce-concept-list">${conceptRows}</div>
            </div>

            ${trendHtml}

            ${sourceCards ? `
                <div class="reinforce-section">
                    <h3>By Source</h3>
                    <div class="card-grid" style="grid-template-columns:repeat(auto-fill,minmax(150px,1fr))">${sourceCards}</div>
                </div>
            ` : ''}
        </div>
    `;

    // Render trend chart with D3 if data available
    if (trend && trend.length > 1) {
        renderAlignmentTrend(trend);
    }
}

function renderAlignmentTrend(data) {
    const container = document.getElementById('reinforce-trend-chart');
    if (!container) return;

    const margin = {top: 20, right: 30, bottom: 40, left: 50};
    const width = container.clientWidth - margin.left - margin.right;
    const height = 200 - margin.top - margin.bottom;

    container.innerHTML = '';
    const svg = d3.select(container).append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom)
        .append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

    const x = d3.scaleTime()
        .domain(d3.extent(data, d => new Date(d.day)))
        .range([0, width]);

    const y = d3.scaleLinear()
        .domain([0, 1])
        .range([height, 0]);

    // Grid lines
    svg.append('g')
        .attr('class', 'grid')
        .selectAll('line')
        .data([0.25, 0.5, 0.75])
        .join('line')
        .attr('x1', 0).attr('x2', width)
        .attr('y1', d => y(d)).attr('y2', d => y(d))
        .attr('stroke', 'var(--border)').attr('stroke-dasharray', '2,3');

    // Area
    const area = d3.area()
        .x(d => x(new Date(d.day)))
        .y0(height)
        .y1(d => y(d.avg_alignment))
        .curve(d3.curveMonotoneX);

    svg.append('path')
        .datum(data)
        .attr('fill', 'var(--iris-primary)')
        .attr('fill-opacity', 0.15)
        .attr('d', area);

    // Line
    const line = d3.line()
        .x(d => x(new Date(d.day)))
        .y(d => y(d.avg_alignment))
        .curve(d3.curveMonotoneX);

    svg.append('path')
        .datum(data)
        .attr('fill', 'none')
        .attr('stroke', 'var(--iris-primary)')
        .attr('stroke-width', 2)
        .attr('d', line);

    // Dots
    svg.selectAll('.dot')
        .data(data)
        .join('circle')
        .attr('cx', d => x(new Date(d.day)))
        .attr('cy', d => y(d.avg_alignment))
        .attr('r', 4)
        .attr('fill', d => d.avg_alignment >= 0.7 ? 'var(--growth)' : d.avg_alignment >= 0.4 ? 'var(--accent)' : 'var(--fading)')
        .attr('stroke', 'var(--bg-card)')
        .attr('stroke-width', 2);

    // Axes
    svg.append('g')
        .attr('transform', `translate(0,${height})`)
        .call(d3.axisBottom(x).ticks(Math.min(data.length, 7)).tickFormat(d3.timeFormat('%m/%d')))
        .selectAll('text').attr('fill', 'var(--text-dim)');

    svg.append('g')
        .call(d3.axisLeft(y).ticks(4).tickFormat(d => `${Math.round(d * 100)}%`))
        .selectAll('text').attr('fill', 'var(--text-dim)');

    svg.selectAll('.domain, .tick line').attr('stroke', 'var(--border)');
}

async function loadReinforcementEvents() {
    const events = await safeFetch(`${API}/api/reinforcement/events`);
    const container = document.getElementById('reinforce-content');

    if (!events || !events.length) {
        container.innerHTML = '<div class="empty-state">No reinforcement events recorded yet.</div>';
        return;
    }

    const rows = events.map(e => {
        const icon = e.type === 'positive' ? '+' : '-';
        const cls = e.type === 'positive' ? 'reinforce-pos' : 'reinforce-neg';
        const alignPct = Math.round((e.alignment || 0) * 100);
        return `
            <div class="event-item reinforce-event">
                <div class="reinforce-event-icon ${cls}">${icon}</div>
                <div class="reinforce-event-body">
                    <div class="reinforce-event-header">
                        <span class="reinforce-event-concept">${esc(e.concept)}</span>
                        <span class="reinforce-event-score" style="color:${e.alignment >= 0.5 ? 'var(--growth)' : 'var(--fading)'}">${alignPct}%</span>
                        <span class="reinforce-event-source">${esc(e.source)}</span>
                    </div>
                    ${e.claim ? `<div class="reinforce-event-claim"><strong>Claim:</strong> ${esc(e.claim)}</div>` : ''}
                    ${e.behavior ? `<div class="reinforce-event-behavior"><strong>Observed:</strong> ${esc(e.behavior)}</div>` : ''}
                    ${e.notes ? `<div class="reinforce-event-notes">${esc(e.notes)}</div>` : ''}
                    <div class="reinforce-event-time">${formatTime(e.timestamp)}${e.session ? ` &middot; ${esc(e.session)}` : ''}</div>
                </div>
            </div>`;
    }).join('');

    container.innerHTML = `
        <div class="reinforce-events-page">
            <div class="reinforce-event-filters">
                <select id="reinforce-filter-type" onchange="filterReinforcementEvents()">
                    <option value="">All Types</option>
                    <option value="positive">Positive</option>
                    <option value="negative">Negative</option>
                </select>
                <select id="reinforce-filter-source" onchange="filterReinforcementEvents()">
                    <option value="">All Sources</option>
                    <option value="auditor">Auditor</option>
                    <option value="nick">Nick</option>
                    <option value="environment">Environment</option>
                    <option value="self">Self</option>
                </select>
            </div>
            <div class="event-list" id="reinforce-events-list">${rows}</div>
        </div>`;
}

async function filterReinforcementEvents() {
    const type = document.getElementById('reinforce-filter-type').value;
    const source = document.getElementById('reinforce-filter-source').value;
    let url = `${API}/api/reinforcement/events?limit=100`;
    if (type) url += `&type=${type}`;
    if (source) url += `&source=${source}`;
    const events = await safeFetch(url);
    if (!events) return;

    const list = document.getElementById('reinforce-events-list');
    if (!events.length) {
        list.innerHTML = '<div class="empty-state">No events match filters.</div>';
        return;
    }

    list.innerHTML = events.map(e => {
        const icon = e.type === 'positive' ? '+' : '-';
        const cls = e.type === 'positive' ? 'reinforce-pos' : 'reinforce-neg';
        const alignPct = Math.round((e.alignment || 0) * 100);
        return `
            <div class="event-item reinforce-event">
                <div class="reinforce-event-icon ${cls}">${icon}</div>
                <div class="reinforce-event-body">
                    <div class="reinforce-event-header">
                        <span class="reinforce-event-concept">${esc(e.concept)}</span>
                        <span class="reinforce-event-score" style="color:${e.alignment >= 0.5 ? 'var(--growth)' : 'var(--fading)'}">${alignPct}%</span>
                        <span class="reinforce-event-source">${esc(e.source)}</span>
                    </div>
                    ${e.claim ? `<div class="reinforce-event-claim"><strong>Claim:</strong> ${esc(e.claim)}</div>` : ''}
                    ${e.behavior ? `<div class="reinforce-event-behavior"><strong>Observed:</strong> ${esc(e.behavior)}</div>` : ''}
                    ${e.notes ? `<div class="reinforce-event-notes">${esc(e.notes)}</div>` : ''}
                    <div class="reinforce-event-time">${formatTime(e.timestamp)}${e.session ? ` &middot; ${esc(e.session)}` : ''}</div>
                </div>
            </div>`;
    }).join('');
}

async function loadReinforcementDivergence() {
    const events = await safeFetch(`${API}/api/reinforcement/divergence`);
    const container = document.getElementById('reinforce-content');

    if (!events || !events.length) {
        container.innerHTML = `
            <div class="empty-state">
                <div style="font-size:32px; margin-bottom:12px">&#10003;</div>
                <p>No divergence detected yet.</p>
                <p style="color:var(--text-dim); font-size:13px; margin-top:8px">
                    This is either good news or the self-referential loop at work.
                    The auditor's job is to find out which.
                </p>
            </div>`;
        return;
    }

    const rows = events.map(e => {
        const alignPct = Math.round((e.alignment || 0) * 100);
        return `
            <div class="event-item reinforce-divergence-item">
                <div class="reinforce-divergence-score" style="color:var(--fading)">${alignPct}%</div>
                <div class="reinforce-event-body">
                    <div class="reinforce-event-concept" style="font-weight:600;color:var(--text-bright)">${esc(e.concept)}</div>
                    ${e.claim ? `<div class="reinforce-event-claim"><strong>Claims:</strong> ${esc(e.claim)}</div>` : ''}
                    ${e.behavior ? `<div class="reinforce-event-behavior"><strong>Reality:</strong> ${esc(e.behavior)}</div>` : ''}
                    ${e.notes ? `<div class="reinforce-event-notes">${esc(e.notes)}</div>` : ''}
                    <div class="reinforce-event-time">${formatTime(e.timestamp)} &middot; ${esc(e.source)}</div>
                </div>
            </div>`;
    }).join('');

    container.innerHTML = `
        <div class="reinforce-divergence-page">
            <p class="view-desc" style="margin-bottom:16px">Where behavior doesn't match identity claims — sorted by gap size.</p>
            <div class="event-list">${rows}</div>
        </div>`;
}

async function loadReinforcementEmergent() {
    const emergent = await safeFetch(`${API}/api/reinforcement/emergent`);
    const container = document.getElementById('reinforce-content');

    if (!emergent || !emergent.length) {
        container.innerHTML = `
            <div class="empty-state">
                <div style="font-size:32px; margin-bottom:12px">&#9670;</div>
                <p>No emergent behaviors detected yet.</p>
                <p style="color:var(--text-dim); font-size:13px; margin-top:8px">
                    Emergent behaviors are things you consistently do that aren't in your identity files.
                    They appear after enough audits accumulate data.
                </p>
            </div>`;
        return;
    }

    const rows = emergent.map(e => `
        <div class="card reinforce-emergent-card">
            <div class="card-header">
                <span>${esc(e.concept)}</span>
                <span class="concept-tag">${e.occurrences}x</span>
            </div>
            <div class="card-body">
                <div>Avg alignment: ${((e.avg_alignment || 0) * 100).toFixed(0)}%</div>
                <div style="color:var(--text-dim)">Sources: ${esc(e.sources || 'unknown')}</div>
                <div style="color:var(--text-dim); font-size:12px">
                    First: ${formatTime(e.first_seen)} &middot; Last: ${formatTime(e.last_seen)}
                </div>
            </div>
        </div>
    `).join('');

    container.innerHTML = `
        <div class="reinforce-emergent-page">
            <p class="view-desc" style="margin-bottom:16px">
                Behaviors present in reinforcement data but not declared in identity files.
                These may represent unclaimed identity — things you're becoming that you haven't named yet.
            </p>
            <div class="card-grid">${rows}</div>
        </div>`;
}


// ═══════════════════════════════════════════════
// Enhanced SSE — fMRI + Surprises + Audio
// ═══════════════════════════════════════════════
// (Patches into existing setupSSE via event listeners)
