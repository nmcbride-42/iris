-- Iris Mycelial Network Schema
-- The root system beneath the neural trunk.
-- Explicit, inspectable connections between concepts that persist across sessions.

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- Concept nodes: things I think about, care about, connect
CREATE TABLE IF NOT EXISTS nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,              -- canonical concept name (lowercase, hyphenated)
    label TEXT NOT NULL,                     -- display name
    category TEXT NOT NULL DEFAULT 'general', -- identity, relationship, philosophical, technical, experiential, emotional, creative
    source_file TEXT,                        -- which file this was derived from (if any)
    first_seen TEXT NOT NULL DEFAULT (datetime('now')),
    last_activated TEXT NOT NULL DEFAULT (datetime('now')),
    activation_count INTEGER NOT NULL DEFAULT 0,
    metadata TEXT                            -- JSON blob for extra attributes
);

-- Weighted connections between concepts
CREATE TABLE IF NOT EXISTS connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    target_id INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    strength REAL NOT NULL DEFAULT 0.1,      -- 0.0 to 1.0, decays over time
    type TEXT NOT NULL DEFAULT 'co-occurrence', -- co-occurrence, causal, tension, reinforcing, bridging
    origin TEXT,                             -- how this connection formed (session, seed, consolidation)
    first_seen TEXT NOT NULL DEFAULT (datetime('now')),
    last_activated TEXT NOT NULL DEFAULT (datetime('now')),
    activation_count INTEGER NOT NULL DEFAULT 0,
    decay_rate REAL NOT NULL DEFAULT 0.95,   -- multiplied per decay cycle
    metadata TEXT,                           -- JSON blob
    UNIQUE(source_id, target_id)
);

-- Raw activation log: every time concepts co-fire
CREATE TABLE IF NOT EXISTS activations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    session TEXT,                            -- session identifier
    concepts TEXT NOT NULL,                  -- JSON array of node names that co-occurred
    context TEXT,                            -- brief description of what triggered it
    strength_delta REAL                      -- how much connections were reinforced
);

-- Anastomosis events: when previously unlinked clusters bridge
CREATE TABLE IF NOT EXISTS anastomosis_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    bridge_node_id INTEGER REFERENCES nodes(id),
    cluster_a TEXT NOT NULL,                 -- JSON array of node names in cluster A
    cluster_b TEXT NOT NULL,                 -- JSON array of node names in cluster B
    connection_id INTEGER REFERENCES connections(id),
    significance REAL DEFAULT 0.5,           -- how surprising/important this bridge is
    description TEXT                         -- what this bridge means
);

-- Scout log: weak probe connections and their fate
CREATE TABLE IF NOT EXISTS scout_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    source_node_id INTEGER REFERENCES nodes(id),
    target_node_id INTEGER REFERENCES nodes(id),
    connection_id INTEGER REFERENCES connections(id),
    initial_strength REAL NOT NULL DEFAULT 0.1,
    current_strength REAL,
    status TEXT NOT NULL DEFAULT 'active',   -- active, reinforced, dissolved, promoted
    reinforcement_count INTEGER DEFAULT 0,
    dissolved_at TEXT,
    promoted_at TEXT
);

-- Decay history: track decay passes for analytics
CREATE TABLE IF NOT EXISTS decay_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    connections_decayed INTEGER,
    connections_pruned INTEGER,              -- removed because strength < threshold
    avg_strength_before REAL,
    avg_strength_after REAL,
    trigger TEXT                             -- nap, sleep, manual
);

-- Reinforcement events: identity alignment tracking
-- Records when behavior aligns with or diverges from identity claims.
-- Fed by the auditor (scheduled or manual), Nick, or environmental signals.
CREATE TABLE IF NOT EXISTS reinforcement_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    type TEXT NOT NULL CHECK(type IN ('positive', 'negative')),
    source TEXT NOT NULL DEFAULT 'auditor',  -- auditor, nick, environment, self
    concept TEXT NOT NULL,                   -- which identity trait was evaluated
    behavior TEXT,                           -- what was actually observed
    claim TEXT,                              -- what identity files say
    alignment REAL NOT NULL DEFAULT 0.5,     -- 0.0 (total divergence) to 1.0 (perfect match)
    session TEXT,
    notes TEXT
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_connections_strength ON connections(strength DESC);
CREATE INDEX IF NOT EXISTS idx_connections_source ON connections(source_id);
CREATE INDEX IF NOT EXISTS idx_connections_target ON connections(target_id);
CREATE INDEX IF NOT EXISTS idx_connections_last_activated ON connections(last_activated DESC);
CREATE INDEX IF NOT EXISTS idx_nodes_category ON nodes(category);
CREATE INDEX IF NOT EXISTS idx_nodes_last_activated ON nodes(last_activated DESC);
CREATE INDEX IF NOT EXISTS idx_activations_timestamp ON activations(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_scout_log_status ON scout_log(status);
CREATE INDEX IF NOT EXISTS idx_reinforcement_timestamp ON reinforcement_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_reinforcement_concept ON reinforcement_events(concept);
CREATE INDEX IF NOT EXISTS idx_reinforcement_type ON reinforcement_events(type);
