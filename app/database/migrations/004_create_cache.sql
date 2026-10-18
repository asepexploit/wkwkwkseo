CREATE TABLE IF NOT EXISTS cache_domain (
    domain     TEXT    PRIMARY KEY,
    da         INTEGER,
    pa         INTEGER,
    ss         TEXT,
    age        TEXT,
    dr         INTEGER,
    bc         TEXT,
    bc_df      INTEGER,
    rd         TEXT,
    rd_df      INTEGER,
    cached_at  DATETIME NOT NULL DEFAULT (datetime('now')),
    expired_at DATETIME NOT NULL
);
