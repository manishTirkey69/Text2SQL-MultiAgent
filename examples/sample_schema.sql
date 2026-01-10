-- Sample e-commerce database schema for testing

-- Users table
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    country VARCHAR(50)
);

-- Products table
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    price DECIMAL(10, 2) NOT NULL,
    stock_quantity INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Orders table
CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending',
    total_amount DECIMAL(10, 2),
    shipping_address TEXT
);

-- Order items table
CREATE TABLE order_items (
    item_id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(order_id),
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    subtotal DECIMAL(10, 2)
);

-- Reviews table
CREATE TABLE reviews (
    review_id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    review_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample data
INSERT INTO users (username, email, first_name, last_name, country) VALUES
('john_doe', 'john@example.com', 'John', 'Doe', 'USA'),
('jane_smith', 'jane@example.com', 'Jane', 'Smith', 'UK'),
('bob_wilson', 'bob@example.com', 'Bob', 'Wilson', 'Canada'),
('alice_brown', 'alice@example.com', 'Alice', 'Brown', 'USA'),
('charlie_davis', 'charlie@example.com', 'Charlie', 'Davis', 'Australia');

INSERT INTO products (product_name, category, price, stock_quantity) VALUES
('Laptop Pro 15', 'Electronics', 1299.99, 50),
('Wireless Mouse', 'Electronics', 29.99, 200),
('Office Chair', 'Furniture', 199.99, 30),
('Desk Lamp', 'Furniture', 49.99, 100),
('USB-C Cable', 'Accessories', 12.99, 500),
('Notebook Set', 'Stationery', 15.99, 150),
('Mechanical Keyboard', 'Electronics', 89.99, 75),
('Monitor 27inch', 'Electronics', 349.99, 40),
('Standing Desk', 'Furniture', 599.99, 15),
('Webcam HD', 'Electronics', 79.99, 60);

INSERT INTO orders (user_id, status, total_amount) VALUES
(1, 'completed', 1329.98),
(2, 'completed', 449.98),
(3, 'pending', 89.99),
(1, 'completed', 62.98),
(4, 'shipped', 799.98);

INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal) VALUES
(1, 1, 1, 1299.99, 1299.99),
(1, 2, 1, 29.99, 29.99),
(2, 8, 1, 349.99, 349.99),
(2, 4, 2, 49.99, 99.98),
(3, 7, 1, 89.99, 89.99),
(4, 5, 2, 12.99, 25.98),
(4, 6, 1, 15.99, 15.99),
(5, 9, 1, 599.99, 599.99),
(5, 3, 1, 199.99, 199.99);

INSERT INTO reviews (product_id, user_id, rating, review_text) VALUES
(1, 1, 5, 'Excellent laptop, very fast and reliable!'),
(1, 2, 4, 'Great performance but a bit expensive'),
(2, 1, 5, 'Perfect wireless mouse for productivity'),
(8, 2, 5, 'Crystal clear display, highly recommended'),
(7, 3, 4, 'Good keyboard but a bit loud'),
(3, 4, 5, 'Very comfortable office chair'),
(9, 5, 5, 'Best standing desk I ever bought');

-- Create indexes for performance
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);
CREATE INDEX idx_reviews_product_id ON reviews(product_id);
CREATE INDEX idx_reviews_user_id ON reviews(user_id);
