-- Тестові дані. Значення підібрано так, щоб результати запитів у тестах були відомі заздалегідь.

INSERT INTO categories (id, name) VALUES
    (1, 'Ноутбуки'), (2, 'Смартфони'), (3, 'Аксесуари'), (4, 'Порожня категорія');

INSERT INTO goods (id, category_id, name, price, stock) VALUES
    (1, 1, 'Ноутбук Lenovo IdeaPad 5', 32999.00, 7),
    (2, 1, 'Ноутбук ASUS VivoBook 15', 24499.00, 12),
    (3, 2, 'Смартфон Samsung Galaxy A55', 15999.00, 20),
    (4, 2, 'Смартфон Motorola G84', 9999.00, 15),
    (5, 3, 'Миша Logitech M185', 549.00, 60),
    (6, 3, 'Навушники JBL Tune 520BT', 1899.00, 35),
    (7, 3, 'Чохол O''Neil для смартфона', 299.00, 0);

INSERT INTO customers (id, name, email) VALUES
    (1, 'Іваненко Олена', 'ivanenko@example.com'),
    (2, 'Коваль Максим', 'koval@example.com'),
    (3, 'Шевчук Ірина', 'shevchuk@example.com');

INSERT INTO orders (id, customer_id, created_at, status) VALUES
    (1, 1, '2026-10-28', 'PAID'),
    (2, 2, '2026-10-30', 'NEW'),
    (3, 1, '2026-11-01', 'SHIPPED');

INSERT INTO order_items (order_id, goods_id, quantity, price) VALUES
    (1, 1, 1, 32999.00),
    (1, 5, 2, 549.00),
    (2, 3, 1, 15999.00),
    (2, 6, 1, 1899.00),
    (3, 4, 2, 9999.00);
