import os
import io
import csv
import calendar
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, Response
from db import get_db_connection

app = Flask(__name__)
app.secret_key = 'finance_manager_secret_key_change_in_production'


def calculate_financial_health(total_income, total_expense):
    if total_income <= 0:
        return {
            'savings_rate': 0,
            'score': 0,
            'status': 'No Income Recorded',
            'color': '#64748b'
        }

    savings = total_income - total_expense
    savings_rate = round((savings / total_income) * 100, 1)

    if savings_rate >= 30:
        score = min(100, int(85 + (savings_rate - 30) * 0.5))
        status = 'Excellent'
        color = '#16a34a'
    elif savings_rate >= 20:
        score = int(75 + (savings_rate - 20))
        status = 'Good'
        color = '#2563eb'
    elif savings_rate > 0:
        score = int(45 + (savings_rate * 1.5))
        status = 'Fair'
        color = '#f59e0b'
    else:
        score = max(10, int(40 + savings_rate))
        status = 'Needs Attention'
        color = '#dc2626'

    return {
        'savings_rate': savings_rate,
        'score': score,
        'status': status,
        'color': color
    }


def calculate_burn_rate_and_runway(total_expense, balance):
    today = datetime.now()
    day_of_month = today.day
    _, total_days_in_month = calendar.monthrange(today.year, today.month)
    days_remaining = max(1, total_days_in_month - day_of_month + 1)

    daily_burn_rate = round(total_expense / max(1, day_of_month), 2)

    if balance > 0:
        safe_daily_spend = round(balance / days_remaining, 2)
    else:
        safe_daily_spend = 0.0

    if balance > 0 and daily_burn_rate > 0:
        runway_days = int(balance / daily_burn_rate)
    elif balance <= 0:
        runway_days = 0
    else:
        runway_days = None

    return {
        'daily_burn_rate': daily_burn_rate,
        'safe_daily_spend': safe_daily_spend,
        'days_remaining': days_remaining,
        'runway_days': runway_days
    }


def get_month_comparison(conn):
    today = datetime.now()
    cur_month = today.strftime('%Y-%m')

    first_of_this_month = today.replace(day=1)
    prev_month_date = first_of_this_month - timedelta(days=1)
    prev_month = prev_month_date.strftime('%Y-%m')

    query = '''
        SELECT 
            type,
            strftime('%Y-%m', date) as month,
            SUM(amount) as total
        FROM transactions
        WHERE strftime('%Y-%m', date) IN (?, ?)
        GROUP BY type, month
    '''
    rows = conn.execute(query, (cur_month, prev_month)).fetchall()

    data = {
        'cur_income': 0.0, 'prev_income': 0.0,
        'cur_expense': 0.0, 'prev_expense': 0.0
    }

    for row in rows:
        if row['month'] == cur_month:
            if row['type'] == 'income':
                data['cur_income'] = row['total']
            else:
                data['cur_expense'] = row['total']
        elif row['month'] == prev_month:
            if row['type'] == 'income':
                data['prev_income'] = row['total']
            else:
                data['prev_expense'] = row['total']

    if data['prev_expense'] > 0:
        expense_change = round(((data['cur_expense'] - data['prev_expense']) / data['prev_expense']) * 100, 1)
    else:
        expense_change = None

    if data['prev_income'] > 0:
        income_change = round(((data['cur_income'] - data['prev_income']) / data['prev_income']) * 100, 1)
    else:
        income_change = None

    return {
        'expense_change': expense_change,
        'income_change': income_change,
        'prev_month_name': prev_month_date.strftime('%b')
    }


def get_budget_progress(conn):
    """
    Computes spending progress against category budgets for current month.
    """
    today = datetime.now()
    cur_month = today.strftime('%Y-%m')

    # Ensure budgets table exists
    conn.execute('''
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT UNIQUE NOT NULL,
            monthly_limit REAL NOT NULL CHECK(monthly_limit > 0)
        )
    ''')

    budgets = conn.execute('SELECT * FROM budgets ORDER BY category ASC').fetchall()
    progress_list = []

    for b in budgets:
        cat = b['category']
        limit = b['monthly_limit']

        # Query this month's expense for this category
        spent_row = conn.execute('''
            SELECT SUM(amount) as total
            FROM transactions
            WHERE type = 'expense' 
              AND category = ? 
              AND strftime('%Y-%m', date) = ?
        ''', (cat, cur_month)).fetchone()

        spent = spent_row['total'] if spent_row and spent_row['total'] else 0.0
        percent = round((spent / limit) * 100, 1)
        remaining = round(limit - spent, 2)

        # Color coding: Green (<75%), Amber (75-99%), Red (>=100%)
        if percent >= 100:
            color = '#dc2626' # Red
            status = 'Over Budget'
        elif percent >= 75:
            color = '#f59e0b' # Amber
            status = 'Near Limit'
        else:
            color = '#16a34a' # Green
            status = 'On Track'

        progress_list.append({
            'category': cat,
            'limit': limit,
            'spent': spent,
            'percent': min(100, percent),
            'real_percent': percent,
            'remaining': remaining,
            'color': color,
            'status': status
        })

    return progress_list


@app.route('/')
def index():
    conn = get_db_connection()
    transactions = conn.execute(
        'SELECT * FROM transactions ORDER BY date DESC, id DESC'
    ).fetchall()

    total_income = sum(row['amount'] for row in transactions if row['type'] == 'income')
    total_expense = sum(row['amount'] for row in transactions if row['type'] == 'expense')
    balance = total_income - total_expense

    health_stats = calculate_financial_health(total_income, total_expense)
    burn_stats = calculate_burn_rate_and_runway(total_expense, balance)
    comparison = get_month_comparison(conn)
    budget_progress = get_budget_progress(conn)

    category_data = conn.execute(
        'SELECT category, SUM(amount) as total FROM transactions WHERE type = ? GROUP BY category',
        ('expense',)
    ).fetchall()

    chart_labels = [row['category'] for row in category_data]
    chart_data = [row['total'] for row in category_data]

    conn.close()

    return render_template(
        'index.html',
        transactions=transactions,
        total_income=total_income,
        total_expense=total_expense,
        balance=balance,
        health_stats=health_stats,
        burn_stats=burn_stats,
        comparison=comparison,
        budget_progress=budget_progress,
        chart_labels=chart_labels,
        chart_data=chart_data
    )


@app.route('/add', methods=['GET', 'POST'])
def add_transaction():
    if request.method == 'POST':
        title = request.form['title'].strip()
        amount = request.form['amount'].strip()
        type_ = request.form['type']
        category = request.form['category'].strip()
        date = request.form['date']
        notes = request.form.get('notes', '').strip()

        if not title or not amount or not type_ or not category or not date:
            flash('All fields except notes are required.', 'error')
            return redirect(url_for('add_transaction'))

        try:
            amount = float(amount)
            if amount <= 0:
                flash('Amount must be greater than zero.', 'error')
                return redirect(url_for('add_transaction'))
        except ValueError:
            flash('Invalid amount format.', 'error')
            return redirect(url_for('add_transaction'))

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO transactions (title, amount, type, category, date, notes) VALUES (?, ?, ?, ?, ?, ?)',
            (title, amount, type_, category, date, notes)
        )
        conn.commit()
        conn.close()

        flash('Transaction added successfully!', 'success')
        return redirect(url_for('index'))

    return render_template('add_transaction.html')


@app.route('/delete/<int:id>', methods=['POST'])
def delete_transaction(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM transactions WHERE id = ?', (id,))
    conn.commit()
    conn.close()

    flash('Transaction deleted successfully!', 'warning')
    return redirect(url_for('index'))


@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_transaction(id):
    conn = get_db_connection()

    if request.method == 'POST':
        title = request.form['title'].strip()
        amount = request.form['amount'].strip()
        type_ = request.form['type']
        category = request.form['category'].strip()
        date = request.form['date']
        notes = request.form.get('notes', '').strip()

        if not title or not amount or not type_ or not category or not date:
            conn.close()
            flash('All fields except notes are required.', 'error')
            return redirect(url_for('edit_transaction', id=id))

        try:
            amount = float(amount)
            if amount <= 0:
                conn.close()
                flash('Amount must be greater than zero.', 'error')
                return redirect(url_for('edit_transaction', id=id))
        except ValueError:
            conn.close()
            flash('Invalid amount format.', 'error')
            return redirect(url_for('edit_transaction', id=id))

        conn.execute(
            'UPDATE transactions SET title=?, amount=?, type=?, category=?, date=?, notes=? WHERE id=?',
            (title, amount, type_, category, date, notes, id)
        )
        conn.commit()
        conn.close()

        flash('Transaction updated successfully!', 'info')
        return redirect(url_for('index'))

    transaction = conn.execute(
        'SELECT * FROM transactions WHERE id = ?', (id,)
    ).fetchone()
    conn.close()

    if transaction is None:
        flash('Transaction not found.', 'error')
        return redirect(url_for('index'))

    return render_template('edit_transaction.html', transaction=transaction)


# NEW: Manage Budgets Route
@app.route('/budgets', methods=['GET', 'POST'])
def manage_budgets():
    conn = get_db_connection()

    if request.method == 'POST':
        category = request.form['category'].strip()
        limit_raw = request.form['monthly_limit'].strip()

        if not category or not limit_raw:
            flash('Category and monthly limit are required.', 'error')
            return redirect(url_for('manage_budgets'))

        try:
            limit = float(limit_raw)
            if limit <= 0:
                flash('Monthly limit must be greater than zero.', 'error')
                return redirect(url_for('manage_budgets'))
        except ValueError:
            flash('Invalid limit number.', 'error')
            return redirect(url_for('manage_budgets'))

        # Insert or replace budget if already exists for this category
        conn.execute('''
            INSERT INTO budgets (category, monthly_limit)
            VALUES (?, ?)
            ON CONFLICT(category) DO UPDATE SET monthly_limit = excluded.monthly_limit
        ''', (category, limit))
        conn.commit()
        conn.close()

        flash(f'Budget for "{category}" updated successfully!', 'success')
        return redirect(url_for('manage_budgets'))

    budgets = conn.execute('SELECT * FROM budgets ORDER BY category ASC').fetchall()
    conn.close()
    return render_template('budgets.html', budgets=budgets)


@app.route('/budgets/delete/<int:id>', methods=['POST'])
def delete_budget(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM budgets WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Budget removed successfully!', 'warning')
    return redirect(url_for('manage_budgets'))


@app.route('/export/csv')
def export_csv():
    conn = get_db_connection()
    transactions = conn.execute(
        'SELECT * FROM transactions ORDER BY date DESC, id DESC'
    ).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(['ID', 'Date', 'Title', 'Category', 'Type', 'Amount ($)', 'Notes'])

    for t in transactions:
        writer.writerow([
            t['id'],
            t['date'],
            t['title'],
            t['category'],
            t['type'].capitalize(),
            f"{t['amount']:.2f}",
            t['notes'] or ''
        ])

    output.seek(0)
    filename = f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


if __name__ == '__main__':
    app.run(debug=True)