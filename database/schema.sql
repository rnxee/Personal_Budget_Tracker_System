CREATE DATABASE IF NOT EXISTS CCCS105
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE CCCS105;

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS savings_goals;
DROP TABLE IF EXISTS budgets;
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS users;
SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE users (
  user_id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) NOT NULL UNIQUE,
  full_name VARCHAR(100) NOT NULL,
  email VARCHAR(120) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role ENUM('admin', 'member') NOT NULL DEFAULT 'member',
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE categories (
  category_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  name VARCHAR(80) NOT NULL,
  type ENUM('income', 'expense') NOT NULL,
  description VARCHAR(255),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_categories_user
    FOREIGN KEY (user_id) REFERENCES users(user_id)
    ON DELETE CASCADE,
  CONSTRAINT uq_categories_user_name_type
    UNIQUE (user_id, name, type)
);

CREATE TABLE transactions (
  transaction_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  category_id INT NOT NULL,
  transaction_type ENUM('income', 'expense') NOT NULL,
  amount DECIMAL(10,2) NOT NULL,
  transaction_date DATE NOT NULL,
  description VARCHAR(255) NOT NULL,
  payment_method ENUM('cash', 'gcash', 'card', 'bank_transfer', 'other') NOT NULL DEFAULT 'cash',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_transactions_user
    FOREIGN KEY (user_id) REFERENCES users(user_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_transactions_category
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_transactions_amount
    CHECK (amount > 0),
  INDEX idx_transactions_user_date (user_id, transaction_date),
  INDEX idx_transactions_type (transaction_type),
  INDEX idx_transactions_category (category_id)
);

CREATE TABLE budgets (
  budget_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  category_id INT NOT NULL,
  month DATE NOT NULL,
  limit_amount DECIMAL(10,2) NOT NULL,
  notes VARCHAR(255),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_budgets_user
    FOREIGN KEY (user_id) REFERENCES users(user_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_budgets_category
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
    ON DELETE RESTRICT,
  CONSTRAINT uq_budgets_user_category_month
    UNIQUE (user_id, category_id, month),
  CONSTRAINT chk_budgets_amount
    CHECK (limit_amount > 0),
  INDEX idx_budgets_user_month (user_id, month)
);

CREATE TABLE savings_goals (
  goal_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  goal_name VARCHAR(100) NOT NULL,
  target_amount DECIMAL(10,2) NOT NULL,
  current_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  target_date DATE NOT NULL,
  status ENUM('active', 'paused', 'completed') NOT NULL DEFAULT 'active',
  notes VARCHAR(255),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_goals_user
    FOREIGN KEY (user_id) REFERENCES users(user_id)
    ON DELETE CASCADE,
  CONSTRAINT chk_goals_target_amount
    CHECK (target_amount > 0),
  CONSTRAINT chk_goals_current_amount
    CHECK (current_amount >= 0),
  INDEX idx_goals_user_status (user_id, status)
);
