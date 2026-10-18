CREATE TABLE IF NOT EXISTS transactions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(id),
    paket         TEXT    NOT NULL,
    jumlah_kredit INTEGER NOT NULL,
    harga         INTEGER NOT NULL,
    status        TEXT    NOT NULL DEFAULT 'pending',
    bukti_url     TEXT,
    created_at    DATETIME NOT NULL DEFAULT (datetime('now')),
    confirmed_at  DATETIME
);
