CREATE TABLE IF NOT EXISTS projects (
    id                UUID PRIMARY KEY,
    idea              TEXT NOT NULL,
    business_analysis JSONB,
    prd               JSONB,
    architecture      JSONB,
    tasks             JSONB,
    exports           JSONB DEFAULT '[]'::jsonb,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
