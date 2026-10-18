CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id BIGINT  NOT NULL UNIQUE,
    username    TEXT,
    nama        TEXT,
    kredit      INTEGER NOT NULL DEFAULT 5,
    joined_at   DATETIME NOT NULL DEFAULT (datetime('now')),
    is_banned   INTEGER NOT NULL DEFAULT 0
);
