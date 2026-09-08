<div align="center">

# 💰 Personal Finance Tracker & Intelligence Hub

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0+-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)
[![Chart.js](https://img.shields.io/badge/Chart.js-4.0+-FF6384?style=for-the-badge&logo=chartdotjs&logoColor=white)](https://www.chartjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

An intelligent, self-hosted personal finance management web application built with **Python (Flask)**, **SQLite3**, and **Chart.js**. Designed with clean MVC architecture, actionable spending analytics, visual category budgets, and executive-level reporting.

[Explore Features](#-key-features) • [Architecture](#-architecture--data-flow) • [Quick Start](#-quick-start) • [Security & Design](#-security--design-principles)

</div>

---

## 🌟 Key Features

### 📊 1. Executive Analytics & Trend Reporting (Dedicated View)
* **Monthly Expense Trajectory**: Smooth Bezier line chart tracking spending trends over time with area fills.
* **Monthly Cash Flow Comparison**: Grouped dual-bar charts comparing earnings against spending per calendar month.
* **Category Spending Ranking**: Horizontal ranked bar chart organizing expenditures from highest to lowest impact.

### 🎯 2. Active Category Budgeting & Visual Progress
* Set monthly spending thresholds per category (`Food & Dining`, `Rent`, `Utilities`, etc.).
* Dynamic color-coded progress bars:
  * 🟢 **On Track** (< 75% utilized)
  * 🟡 **Near Limit** (75% – 99% utilized)
  * 🔴 **Over Budget** (100%+ utilized with dynamic overflow calculations)
* Built using atomic SQLite `INSERT ... ON CONFLICT DO UPDATE` upserts.

### 🧠 3. Smart Financial Metrics & Runway Intelligence
* **Financial Health Score (0–100)**: Evaluates monthly savings rate based on standard financial benchmarks (50/30/20 rule).
* **Daily Burn Rate**: Computes real daily expense velocity for the current month.
* **Safe Daily Spend**: Calculates the sustainable daily allowance for the remaining days of the month.
* **Runway Projection**: Real-time estimate of how many days current reserves will last.
* **Month-over-Month Badges**: Dynamic percentage changes vs. the previous month (green for reduced spending, red for increased).

### ⚡ 4. Modern UX & Privacy
* **Discreet / Privacy Mode (👁️)**: Instant client-side masking of all currency figures (`$****`) with `localStorage` persistence for public-space use.
* **Smart Category Badges**: Automatic recognition and emoji prefixing (🍔 *Food*, 💼 *Salary*, 🚗 *Transport*, 🏠 *Housing*, 💡 *Utilities*).
* **Zero-Latency Instant Search**: Real-time table filtering across titles, categories, and notes without page reload.
* **In-Memory CSV Export**: One-click download of transactions streamed directly via Python’s `io.StringIO` (Excel / Google Sheets ready).
* **Flash Message Banners**: Contextual alerts for creation, updates, and deletions.

---

## 🏗️ Architecture & Data Flow

The project strictly follows the **Model-View-Controller (MVC)** architectural pattern:

```text
       ┌────────────────────────────────────────────────────────┐
       │                   Browser / Client                     │
       │  (Jinja2 Templates, CSS Grids, Vanilla JS, Chart.js)   │
       └──────────────┬──────────────────────────▲──────────────┘
                      │ HTTP Requests            │ HTML Responses /
                      │ (GET, POST)              │ Streamed CSV
                      ▼                          │
       ┌─────────────────────────────────────────┴──────────────┐
       │                   Flask Controllers                    │
       │     (app.py - Routing, Validation, PRG Pattern)        │
       └──────────────┬──────────────────────────▲──────────────┘
                      │ Parameterized SQL        │ sqlite3.Row
                      │ Queries                  │ Records
                      ▼                          │
       ┌─────────────────────────────────────────┴──────────────┐
       │                   SQLite Data Layer                    │
       │    (db.py, schema.sql, finance.db with Constraints)    │
       └────────────────────────────────────────────────────────┘
