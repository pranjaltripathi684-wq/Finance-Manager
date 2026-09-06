# 💰 Personal Finance Tracker

A clean, responsive personal finance web application built with **Python (Flask)**, **SQLite**, and **Chart.js**. It enables users to track their incomes, expenses, and net balance in real-time, accompanied by an interactive category breakdown chart.

---

## ✨ Features

- **Full CRUD Operations**: Add, view, edit, and delete financial transactions with instant UI updates.
- **Financial Health Summary**: Real-time calculations of Total Income, Total Expenses, and Net Balance.
- **Interactive Visualizations**: Dynamic expense category breakdown powered by **Chart.js** (doughnut chart).
- **Data Integrity & Safety**:
  - SQLite check constraints ensure non-negative amounts, strict ISO date formatting (`YYYY-MM-DD`), and valid transaction types (`income` or `expense`).
  - Parameterized SQL queries prevent SQL injection attacks.
  - Destructive actions (deletions) use `POST` methods with user confirmation dialogues.
- **Responsive Layout**: Designed with clean, modern CSS cards and tables that work smoothly across mobile, tablet, and desktop screens.

---

## 🛠️ Tech Stack

- **Backend**: Python 3, Flask
- **Database**: SQLite3
- **Frontend**: HTML5, Modern CSS, Jinja2 Template Engine
- **Data Visualization**: Chart.js

---

## 📁 Project Structure

```text
Finance-Manager/
│
├── app.py                  # Main Flask routes and application logic
├── db.py                   # SQLite connection & database initialization helpers
├── schema.sql              # Database schema definition with constraints
├── requirements.txt        # Python package dependencies
├── .gitignore              # Files and folders to exclude from version control
├── README.md               # Project documentation
│
└── templates/              # Jinja2 HTML templates
    ├── base.html           # Base layout with navbar, embedded CSS, and CDN links
    ├── index.html          # Dashboard view with summary cards, table, and charts
    ├── add_transaction.html # Transaction creation form
    └── edit_transaction.html# Pre-filled transaction editing form
