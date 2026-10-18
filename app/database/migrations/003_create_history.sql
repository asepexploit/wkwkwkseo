CREATE TABLE IF NOT EXISTS history_cek (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    domain     TEXT    NOT NULL,
    da         INTEGER,
    pa         INTEGER,
    ss         TEXT,
    age        TEXT,
    dr         INTEGER,
    bc         TEXT,
    bc_df      INTEGER,
    rd         TEXT,
    rd_df      INTEGER,
    checked_at DATETIME NOT NULL DEFAULT (datetime('now'))
);
