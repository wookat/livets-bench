CREATE TABLE IF NOT EXISTS models (
  name TEXT PRIMARY KEY,
  release_date TEXT NOT NULL,
  registered_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS rounds (
  round TEXT PRIMARY KEY,           -- e.g. "2026-09"
  cutoff TEXT NOT NULL,             -- ISO date
  submit_deadline TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open'  -- open | scoring | published
);

CREATE TABLE IF NOT EXISTS submissions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  round TEXT NOT NULL REFERENCES rounds(round),
  model TEXT NOT NULL REFERENCES models(name),
  payload_key TEXT NOT NULL,        -- R2 object key of the raw submission
  submitted_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(round, model)
);

CREATE TABLE IF NOT EXISTS scores (
  round TEXT NOT NULL,
  model TEXT NOT NULL,
  clean INTEGER NOT NULL,           -- 1 if cutoff > release_date
  geo_mase REAL,
  geo_crps REAL,
  geo_wql REAL,
  n_series INTEGER,
  n_windows INTEGER,
  provenance_key TEXT,              -- R2 key of scoring JSONL
  published_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (round, model)
);

INSERT OR IGNORE INTO rounds (round, cutoff, submit_deadline, status)
VALUES ('2026-09', '2026-09-01', '2026-09-08T23:59:59Z', 'open');
