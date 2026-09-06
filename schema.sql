-- Drop table if it already exists (useful when resetting during development)
DROP TABLE IF EXISTS transactions;

-- Create transactions table with fields:
-- id: INTEGER PRIMARY KEY AUTOINCREMENT
-- title: TEXT NOT NULL (e.g., "Grocery shopping", "Monthly Salary")
-- amount: REAL NOT NULL (e.g., 45.50)
-- type: TEXT NOT NULL (e.g., 'income' or 'expense')
-- category: TEXT NOT NULL (e.g., 'Food', 'Salary', 'Utilities', 'Entertainment')
-- date: TEXT NOT NULL (Format: 'YYYY-MM-DD')
-- notes: TEXT (Optional extra details)

DROP TABLE IF EXISTS transactions;

CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    amount REAL NOT NULL CHECK(amount > 0),
    type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
    category TEXT NOT NULL,
    date TEXT NOT NULL CHECK(date GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'),
    notes TEXT
);
