CREATE DATABASE IF NOT EXISTS price_tracker
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE price_tracker;

CREATE TABLE IF NOT EXISTS products (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    product_url VARCHAR(2048) NOT NULL,
    product_name VARCHAR(500) NOT NULL,
    current_price DECIMAL(12,2) NOT NULL,
    target_price DECIMAL(12,2) NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'INR',
    alert_email VARCHAR(254) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_checked_at DATETIME NULL,
    last_alerted_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_products_url_email (product_url(500), alert_email),
    KEY idx_products_active (is_active),
    KEY idx_products_target (target_price)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS price_history (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    product_id BIGINT UNSIGNED NOT NULL,
    price DECIMAL(12,2) NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'INR',
    recorded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_status VARCHAR(30) NOT NULL DEFAULT 'success',
    PRIMARY KEY (id),
    KEY idx_history_product_date (product_id, recorded_at),
    CONSTRAINT fk_price_history_product
      FOREIGN KEY (product_id) REFERENCES products(id)
      ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE OR REPLACE VIEW vw_powerbi_price_tracking AS
SELECT
    p.id AS product_id,
    p.product_name,
    p.product_url,
    p.target_price,
    p.current_price,
    p.currency,
    p.alert_email,
    p.is_active,
    p.created_at AS product_created_at,
    h.id AS price_history_id,
    h.price AS historical_price,
    h.recorded_at,
    h.source_status,
    ROUND(
      CASE WHEN h.price > 0
        THEN ((h.price - p.target_price) / h.price) * 100
        ELSE NULL
      END, 2
    ) AS discount_to_target_pct
FROM products p
LEFT JOIN price_history h ON h.product_id = p.id;
