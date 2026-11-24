-- Тестова база даних «Інтернет-магазин» для модульних та інтеграційних тестів SQL Driver.
-- Містить усі види обмежень цілісності, які має перевіряти драйвер.

PRAGMA foreign_keys = ON;

CREATE TABLE categories (
    id    INTEGER PRIMARY KEY,
    name  TEXT    NOT NULL UNIQUE
);

CREATE TABLE goods (
    id           INTEGER PRIMARY KEY,
    category_id  INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    name         TEXT    NOT NULL,
    price        REAL    NOT NULL CHECK (price > 0),
    stock        INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    UNIQUE (category_id, name)
);

CREATE TABLE customers (
    id     INTEGER PRIMARY KEY,
    name   TEXT NOT NULL,
    email  TEXT NOT NULL UNIQUE
);

CREATE TABLE orders (
    id           INTEGER PRIMARY KEY,
    customer_id  INTEGER NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    created_at   TEXT    NOT NULL,
    status       TEXT    NOT NULL DEFAULT 'NEW'
                 CHECK (status IN ('NEW', 'PAID', 'SHIPPED', 'CANCELLED'))
);

CREATE TABLE order_items (
    order_id  INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    goods_id  INTEGER NOT NULL REFERENCES goods(id) ON DELETE RESTRICT,
    quantity  INTEGER NOT NULL CHECK (quantity > 0),
    price     REAL    NOT NULL CHECK (price > 0),
    PRIMARY KEY (order_id, goods_id)
);

CREATE INDEX idx_goods_category ON goods(category_id);
CREATE INDEX idx_orders_customer ON orders(customer_id);

-- Представлення: сума кожного замовлення.
CREATE VIEW order_totals AS
SELECT o.id AS order_id, c.name AS customer, o.status,
       SUM(i.quantity * i.price) AS total
FROM orders o
JOIN customers c ON c.id = o.customer_id
JOIN order_items i ON i.order_id = o.id
GROUP BY o.id;
