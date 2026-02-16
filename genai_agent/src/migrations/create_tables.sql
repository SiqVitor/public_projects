-- ARGUS Chat Logging — Run once in Supabase SQL Editor
-- =====================================================

-- 1. Conversations (one per browser session / reset)
create table if not exists conversations (
    id uuid primary key default gen_random_uuid(),
    started_at timestamptz default now(),
    user_ip_hash text,
    user_agent text
);

-- 2. Messages (each user ↔ agent exchange)
create table if not exists messages (
    id uuid primary key default gen_random_uuid(),
    conversation_id uuid references conversations(id) on delete cascade,
    sent_at timestamptz default now(),
    role text not null check (role in ('user', 'agent')),
    content text,
    response_time_ms int,
    tokens_estimated int
);

-- 3. Summarizations (when context window is compressed)
create table if not exists summarizations (
    id uuid primary key default gen_random_uuid(),
    conversation_id uuid references conversations(id) on delete cascade,
    created_at timestamptz default now(),
    summary_text text,
    message_count int
);

-- Indexes for common queries
create index if not exists idx_messages_conversation on messages(conversation_id);
create index if not exists idx_summarizations_conversation on summarizations(conversation_id);
create index if not exists idx_conversations_started on conversations(started_at desc);
