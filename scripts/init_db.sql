CREATE TABLE IF NOT EXISTS projects (
    id                TEXT PRIMARY KEY,
    idea              TEXT NOT NULL,
    business_analysis TEXT,
    prd               TEXT,
    architecture      TEXT,
    tasks             TEXT,
    exports           TEXT DEFAULT '[]',
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at        TEXT NOT NULL DEFAULT (datetime('now'))
);
