create extension if not exists pgcrypto;

create table if not exists devices (
    device_id text primary key,
    status text,
    model text,
    version text,
    latest_seen_at timestamptz,
    last_payload_at timestamptz,
    raw_info jsonb default '{}'::jsonb,
    received_at timestamptz default now()
);

create table if not exists uploads (
    id uuid primary key default gen_random_uuid(),
    device_id text,
    upload_type text not null,
    packet_count integer default 0,
    payload_bytes integer default 0,
    source_ip text,
    parse_status text,
    error text,
    raw_hex text,
    raw_json jsonb default '{}'::jsonb,
    received_at timestamptz default now()
);

create table if not exists packets (
    id uuid primary key default gen_random_uuid(),
    upload_id uuid references uploads(id) on delete cascade,
    device_id text,
    protocol_code integer,
    protocol_name text,
    payload_hex text,
    payload_json jsonb default '{}'::jsonb,
    packet_length integer,
    crc integer,
    received_at timestamptz default now()
);

create table if not exists health_measurements (
    id uuid primary key default gen_random_uuid(),
    device_id text,
    measured_at timestamptz,
    metric_type text not null,
    values jsonb default '{}'::jsonb,
    source_packet_id uuid references packets(id) on delete set null,
    received_at timestamptz default now()
);

create table if not exists location_points (
    id uuid primary key default gen_random_uuid(),
    device_id text,
    measured_at timestamptz,
    latitude numeric,
    longitude numeric,
    gps_type integer,
    raw jsonb default '{}'::jsonb,
    source_packet_id uuid references packets(id) on delete set null,
    received_at timestamptz default now()
);

create table if not exists alarms (
    id uuid primary key default gen_random_uuid(),
    device_id text,
    alarm_type text not null,
    alarm_time timestamptz,
    values jsonb default '{}'::jsonb,
    source_packet_id uuid references packets(id) on delete set null,
    received_at timestamptz default now()
);

create table if not exists call_logs (
    id uuid primary key default gen_random_uuid(),
    device_id text,
    call_type text,
    status integer,
    call_number text,
    start_time timestamptz,
    end_time timestamptz,
    raw jsonb default '{}'::jsonb,
    received_at timestamptz default now()
);

create table if not exists sos_events (
    id uuid primary key default gen_random_uuid(),
    device_id text,
    alarm_time timestamptz,
    latitude numeric,
    longitude numeric,
    call_logs jsonb default '[]'::jsonb,
    raw jsonb default '{}'::jsonb,
    received_at timestamptz default now()
);

create table if not exists device_status_events (
    id uuid primary key default gen_random_uuid(),
    device_id text,
    status text,
    event_time timestamptz,
    raw jsonb default '{}'::jsonb,
    received_at timestamptz default now()
);

create table if not exists command_logs (
    id uuid primary key default gen_random_uuid(),
    command_key text,
    path text,
    method text,
    device_id text,
    status_code integer,
    return_code integer,
    request_body jsonb default '{}'::jsonb,
    response_body jsonb default '{}'::jsonb,
    error text,
    received_at timestamptz default now()
);

create table if not exists sleep_results (
    id uuid primary key default gen_random_uuid(),
    device_id text,
    sleep_date date,
    start_time timestamptz,
    end_time timestamptz,
    deep_sleep integer,
    light_sleep integer,
    weak_sleep integer,
    eyemove_sleep integer,
    score integer,
    osahs_risk integer,
    spo2_score integer,
    sleep_hr integer,
    raw jsonb default '{}'::jsonb,
    received_at timestamptz default now()
);
