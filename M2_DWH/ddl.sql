-- ============================================================
-- Olist DWH — Phase 2 DDL
-- Target: PostgreSQL 12+ (tested on 16)
-- Apply with:  psql -d olist_dwh -f dwh/ddl.sql
-- ============================================================
-- Idempotent: drop everything first so re-running is safe
-- during development. CASCADE handles FK ordering automatically.
-- ============================================================

DROP TABLE IF EXISTS Fact_OrderItems    CASCADE;
DROP TABLE IF EXISTS Dim_Date           CASCADE;
DROP TABLE IF EXISTS Dim_Products       CASCADE;
DROP TABLE IF EXISTS Dim_Sellers        CASCADE;
DROP TABLE IF EXISTS Dim_Customers      CASCADE;
DROP TABLE IF EXISTS Dim_Category_Group CASCADE;
DROP TABLE IF EXISTS Dim_Region         CASCADE;

-- ============================================================
-- 1. Dim_Region  (NEW vs Phase 1: enables region-aware features)
-- ============================================================
CREATE TABLE Dim_Region (
    region_id     SERIAL PRIMARY KEY,
    state         TEXT UNIQUE NOT NULL,
    macro_region  TEXT NOT NULL          -- Norte / Nordeste / Centro-Oeste / Sudeste / Sul
);

-- ============================================================
-- 2. Dim_Category_Group  (NEW vs Phase 1: data-driven roll-up)
-- ============================================================
CREATE TABLE Dim_Category_Group (
    group_id    SERIAL PRIMARY KEY,
    group_name  TEXT UNIQUE NOT NULL,    -- e.g. "home_living"
    description TEXT
);

-- ============================================================
-- 3. Dim_Customers  (Phase 1 columns + region_id FK)
-- ============================================================
CREATE TABLE Dim_Customers (
    customer_id              TEXT PRIMARY KEY,
    customer_unique_id       TEXT,
    customer_zip_code_prefix TEXT,
    customer_city            TEXT,
    customer_state           TEXT,
    region_id                INT REFERENCES Dim_Region(region_id)   -- NEW
);

-- ============================================================
-- 4. Dim_Sellers  (Phase 1 columns, unchanged)
-- ============================================================
CREATE TABLE Dim_Sellers (
    seller_id              TEXT PRIMARY KEY,
    seller_zip_code_prefix TEXT,
    seller_city            TEXT,
    seller_state           TEXT
);

-- ============================================================
-- 5. Dim_Products  (Phase 1 columns + category_group_id FK)
-- ============================================================
CREATE TABLE Dim_Products (
    product_id                    TEXT PRIMARY KEY,
    product_category_name         TEXT,
    product_category_name_english TEXT,
    product_weight_g              INT,
    product_length_cm             INT,
    product_height_cm             INT,
    product_width_cm              INT,
    product_photos_qty            INT,
    category_group_id             INT REFERENCES Dim_Category_Group(group_id)  -- NEW
);

-- ============================================================
-- 6. Dim_Date  (Phase 1 columns + 5 enrichment columns)
-- ============================================================
CREATE TABLE Dim_Date (
    date          DATE PRIMARY KEY,   -- matches Phase 1 "Date"
    day           INT,                -- matches Phase 1 "Day"
    monthnumber   INT,                -- matches Phase 1 "MonthNumber" (folded)
    monthname     TEXT,               -- matches Phase 1 "MonthName"   (folded)
    quarter       INT,                -- matches Phase 1 "Quarter"
    weekday       TEXT,               -- matches Phase 1 "Weekday"
    year          INT,                -- matches Phase 1 "Year"
    is_holiday    BOOLEAN,            -- NEW
    holiday_name  TEXT,               -- NEW
    is_weekend    BOOLEAN,            -- NEW
    season        TEXT,               -- NEW
    payday_window BOOLEAN             -- NEW
);

-- ============================================================
-- 7. Fact_OrderItems  (Phase 1 grain: one row per item per order)
-- ============================================================
CREATE TABLE Fact_OrderItems (
    order_item_key   BIGSERIAL PRIMARY KEY,
    order_id         TEXT NOT NULL,
    order_item_id    INT  NOT NULL,
    customer_id      TEXT REFERENCES Dim_Customers(customer_id),
    seller_id        TEXT REFERENCES Dim_Sellers(seller_id),
    product_id       TEXT REFERENCES Dim_Products(product_id),
    orderdate        DATE REFERENCES Dim_Date(date),       -- matches Phase 1 "OrderDate"
    price            NUMERIC(10,2),
    freight_value    NUMERIC(10,2),
    total_item_value NUMERIC(10,2) GENERATED ALWAYS AS (price + freight_value) STORED
);

-- ============================================================
-- Done. Indexes are created AFTER load (Day 2, Step 9)
-- so the bulk insert is fast.
-- ============================================================
