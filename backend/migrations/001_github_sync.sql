-- Chạy một lần trên database github_recommender

-- 1. Bảng users: cho phép user GitHub không có mật khẩu, lưu thông tin GitHub
ALTER TABLE users
    ALTER COLUMN password_hash DROP NOT NULL,
    ADD COLUMN IF NOT EXISTS auth_provider VARCHAR(20) NOT NULL DEFAULT 'local',
    ADD COLUMN IF NOT EXISTS github_id BIGINT UNIQUE,
    ADD COLUMN IF NOT EXISTS github_login VARCHAR(100),
    ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500);

-- 2. Bảng lưu GitHub access token (đã mã hóa bằng TOKEN_ENCRYPTION_KEY)
CREATE TABLE IF NOT EXISTS github_accounts (
    user_id          INT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    github_id        BIGINT UNIQUE NOT NULL,
    access_token_enc TEXT NOT NULL,
    scopes           VARCHAR(255),
    last_synced_at   TIMESTAMP WITH TIME ZONE
);

-- 3. Index để lấy repo GitHub của user theo loại
CREATE INDEX IF NOT EXISTS idx_interactions_user_source_type
    ON interactions(user_id, source, interaction_type);

-- 4. Tùy chọn: tăng tốc tìm kiếm ILIKE theo tên và mô tả
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX IF NOT EXISTS idx_repos_fullname_trgm ON repositories USING gin (full_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_repos_desc_trgm ON repositories USING gin (description gin_trgm_ops);
