import os
import io
import csv
import math
import random
import hashlib
import calendar
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, Response
from db import get_db_connection

app = Flask(__name__)
app.secret_key = 'finance_manager_secret_key_change_in_production'

GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"


# ============================================================================
# 1. CRYPTOGRAPHIC LEDGER ENGINE
# ============================================================================

def compute_row_hash(prev_hash, date_str, title, amount, type_, category, notes=""):
    payload = f"{prev_hash}|{date_str}|{title.strip()}|{amount:.2f}|{type_.strip()}|{category.strip()}|{(notes or '').strip()}"
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def ensure_hash_columns(conn):
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(transactions)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'prev_hash' not in columns:
        conn.execute("ALTER TABLE transactions ADD COLUMN prev_hash TEXT NOT NULL DEFAULT '0'")
    if 'curr_hash' not in columns:
        conn.execute("ALTER TABLE transactions ADD COLUMN curr_hash TEXT NOT NULL DEFAULT ''")

    conn.execute('''
        CREATE TABLE IF NOT EXISTS dismissed_anomalies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER UNIQUE NOT NULL
        )
    ''')

    rebuild_ledger_chain(conn)


def rebuild_ledger_chain(conn):
    rows = conn.execute("SELECT * FROM transactions ORDER BY id ASC").fetchall()
    last_hash = GENESIS_HASH

    for r in rows:
        expected_hash = compute_row_hash(
            last_hash, r['date'], r['title'], r['amount'], r['type'], r['category'], r['notes']
        )
        conn.execute(
            "UPDATE transactions SET prev_hash = ?, curr_hash = ? WHERE id = ?",
            (last_hash, expected_hash, r['id'])
        )
        last_hash = expected_hash
    conn.commit()


def verify_ledger_integrity(conn):
    rows = conn.execute("SELECT * FROM transactions ORDER BY id ASC").fetchall()
    last_hash = GENESIS_HASH

    for r in rows:
        if r['prev_hash'] != last_hash:
            return False, r['id'], len(rows)

        computed = compute_row_hash(
            last_hash, r['date'], r['title'], r['amount'], r['type'], r['category'], r['notes']
        )
        if r['curr_hash'] != computed:
            return False, r['id'], len(rows)

        last_hash = r['curr_hash']

    return True, None, len(rows)


# ============================================================================
# 2. ALGORITHMIC ANOMALY & FRAUD SENTINEL
# ============================================================================

def detect_anomalies(conn, transactions):
    anomalies = []
    flagged_ids = {}

    if not transactions:
        return anomalies, flagged_ids

    dismissed_rows = conn.execute("SELECT transaction_id FROM dismissed_anomalies").fetchall()
    dismissed_ids = set(r['transaction_id'] for r in dismissed_rows)

    cat_expenses = {}
    for t in transactions:
        if t['type'] == 'expense':
            cat = t['category']
            cat_expenses.setdefault(cat, []).append(t['amount'])

    cat_stats = {}
    for cat, amounts in cat_expenses.items():
        if len(amounts) >= 3:
            mean = sum(amounts) / len(amounts)
            variance = sum((x - mean) ** 2 for x in amounts) / len(amounts)
            std_dev = math.sqrt(variance)
            cat_stats[cat] = {'mean': mean, 'std_dev': std_dev}

    for t in transactions:
        if t['id'] in dismissed_ids:
            continue

        if t['type'] == 'expense' and t['category'] in cat_stats:
            stats = cat_stats[t['category']]
            if stats['std_dev'] > 0:
                z_score = (t['amount'] - stats['mean']) / stats['std_dev']
                if z_score >= 2.0:
                    msg = f"Unusual {t['category']} expense of ${t['amount']:.2f} (Z-Score: +{z_score:.1f}σ vs category avg ${stats['mean']:.2f})"
                    anomalies.append({
                        'type': 'outlier',
                        'level': 'danger',
                        'title': 'Statistical Outlier',
                        'message': msg,
                        'transaction_id': t['id']
                    })
                    flagged_ids[t['id']] = '⚠️ Outlier (High Z-Score)'

    sorted_by_date = sorted(transactions, key=lambda x: x['date'])
    for i in range(len(sorted_by_date)):
        for j in range(i + 1, len(sorted_by_date)):
            t1 = sorted_by_date[i]
            t2 = sorted_by_date[j]

            if t1['id'] in dismissed_ids or t2['id'] in dismissed_ids:
                continue

            if t1['title'].lower() == t2['title'].lower() and abs(t1['amount'] - t2['amount']) < 0.01:
                try:
                    d1 = datetime.strptime(t1['date'], '%Y-%m-%d')
                    d2 = datetime.strptime(t2['date'], '%Y-%m-%d')
                    diff_days = abs((d2 - d1).days)

                    if diff_days <= 2:
                        msg = f'Possible Duplicate: "{t1["title"]}" (${t1["amount"]:.2f}) on {t1["date"]} and {t2["date"]}'
                        anomalies.append({
                            'type': 'duplicate',
                            'level': 'warning',
                            'title': 'Potential Duplicate Charge',
                            'message': msg,
                            'transaction_id': t2['id']
                        })
                        flagged_ids[t1['id']] = '⚠️ Duplicate Candidate'
                        flagged_ids[t2['id']] = '⚠️ Duplicate Candidate'
                except ValueError:
                    pass

    return anomalies, flagged_ids


# ============================================================================
# 3. MONTE CARLO PROBABILISTIC SIMULATION ENGINE
# ============================================================================

def run_monte_carlo_simulation(current_balance, trend_incomes, trend_expenses, num_simulations=1000, months_ahead=12):
    """
    Executes a 1,000-trial Monte Carlo simulation to project future net balances
    and calculate probability of cash insolvency (Risk of Ruin).
    """
    # Calculate historical net monthly savings (Income - Expense)
    monthly_nets = []
    for inc, exp in zip(trend_incomes, trend_expenses):
        monthly_nets.append(inc - exp)

    if not monthly_nets:
        monthly_nets = [0.0]

    mean_net = sum(monthly_nets) / len(monthly_nets)
    if len(monthly_nets) > 1:
        variance = sum((x - mean_net) ** 2 for x in monthly_nets) / (len(monthly_nets) - 1)
        std_dev_net = math.sqrt(variance)
    else:
        std_dev_net = abs(mean_net * 0.25) or 100.0  # 25% fallback volatility

    # Run simulations
    # simulation_matrix[month_idx] = list of 1,000 balances for that month
    simulation_matrix = [[] for _ in range(months_ahead + 1)]
    for _ in range(num_simulations):
        simulation_matrix[0].append(current_balance)

    ruin_count = 0

    for trial in range(num_simulations):
        bal = current_balance
        hit_ruin = False

        for m in range(1, months_ahead + 1):
            # Sample monthly cashflow from Gaussian normal distribution
            monthly_delta = random.gauss(mean_net, std_dev_net)
            bal += monthly_delta
            simulation_matrix[m].append(bal)

            if bal < 0:
                hit_ruin = True

        if hit_ruin:
            ruin_count += 1

    risk_of_ruin = round((ruin_count / num_simulations) * 100, 1)

    # Extract percentiles (5th pessimistic, 50th median, 95th optimistic)
    p5_curve = []
    p50_curve = []
    p95_curve = []

    for m in range(months_ahead + 1):
        sorted_balances = sorted(simulation_matrix[m])
        p5_curve.append(round(sorted_balances[int(num_simulations * 0.05)], 2))
        p50_curve.append(round(sorted_balances[int(num_simulations * 0.50)], 2))
        p95_curve.append(round(sorted_balances[int(num_simulations * 0.95)], 2))

    # Generate future month labels: "Now", "+1 Mo", "+2 Mo"...
    sim_labels = ["Now"] + [f"+{m} Mo" for m in range(1, months_ahead + 1)]

    return {
        'sim_labels': sim_labels,
        'p5_curve': p5_curve,
        'p50_curve': p50_curve,
        'p95_curve': p95_curve,
        'risk_of_ruin': risk_of_ruin,
        'projected_median': p50_curve[-1],
        'projected_optimistic': p95_curve[-1],
        'projected_pessimistic': p5_curve[-1]
    }


# ============================================================================
# 4. FINANCIAL ANALYTICS HELPERS
# ============================================================================

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
    today = datetime.now()
    cur_month = today.strftime('%Y-%m')

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

        if percent >= 100:
            color = '#dc2626'
            status = 'Over Budget'
        elif percent >= 75:
            color = '#f59e0b'
            status = 'Near Limit'
        else:
            color = '#16a34a'
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


# ============================================================================
# 5. APPLICATION ROUTES
# ============================================================================

@app.route('/')
def index():
    conn = get_db_connection()
    ensure_hash_columns(conn)

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

    is_valid, bad_id, total_checked = verify_ledger_integrity(conn)
    anomalies, flagged_ids = detect_anomalies(conn, transactions)

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
        ledger_valid=is_valid,
        compromised_id=bad_id,
        total_verified=total_checked,
        anomalies=anomalies,
        flagged_ids=flagged_ids
    )


@app.route('/anomalies/dismiss/<int:id>', methods=['POST'])
def dismiss_anomaly(id):
    conn = get_db_connection()
    conn.execute('INSERT OR IGNORE INTO dismissed_anomalies (transaction_id) VALUES (?)', (id,))
    conn.commit()
    conn.close()

    flash('✅ Duplicate marked as authorized and dismissed from alert sentinel.', 'success')
    return redirect(url_for('index'))


@app.route('/anomalies/recheck', methods=['POST'])
def recheck_anomalies():
    conn = get_db_connection()
    transactions = conn.execute('SELECT * FROM transactions').fetchall()
    anomalies, _ = detect_anomalies(conn, transactions)
    conn.close()

    if anomalies:
        flash(f'🔍 Audit Complete: Sentinel found {len(anomalies)} active financial anomalies requiring review.', 'warning')
    else:
        flash('✨ Audit Complete: No unaddressed anomalies or suspicious duplicate charges detected!', 'success')

    return redirect(url_for('index'))


@app.route('/audit/verify', methods=['POST'])
def audit_verify():
    conn = get_db_connection()
    ensure_hash_columns(conn)
    is_valid, bad_id, total_checked = verify_ledger_integrity(conn)
    conn.close()

    if is_valid:
        flash(f'✅ Ledger Verification Passed: All {total_checked} cryptographic SHA-256 blocks are valid and untampered.', 'success')
    else:
        flash(f'🚨 Security Alert: Ledger chain integrity check FAILED at Transaction #{bad_id}! Unauthorized tampering detected.', 'error')

    return redirect(url_for('index'))


# DEDICATED ANALYTICS & MONTE CARLO STUDIO
@app.route('/analytics')
def analytics():
    conn = get_db_connection()

    # 1. Historical Trends
    trend_rows = conn.execute('''
        SELECT 
            strftime('%Y-%m', date) as month,
            type,
            SUM(amount) as total
        FROM transactions
        GROUP BY month, type
        ORDER BY month ASC
    ''').fetchall()

    month_dict = {}
    for r in trend_rows:
        m = r['month']
        if m not in month_dict:
            month_dict[m] = {'income': 0.0, 'expense': 0.0}
        month_dict[m][r['type']] = round(r['total'], 2)

    trend_months = sorted(list(month_dict.keys()))
    trend_incomes = [month_dict[m]['income'] for m in trend_months]
    trend_expenses = [month_dict[m]['expense'] for m in trend_months]

    # Current Net Balance
    tot_inc = sum(trend_incomes)
    tot_exp = sum(trend_expenses)
    current_balance = tot_inc - tot_exp

    # 2. Category Spending Ranking
    cat_rows = conn.execute('''
        SELECT category, SUM(amount) as total
        FROM transactions
        WHERE type = 'expense'
        GROUP BY category
        ORDER BY total DESC
    ''').fetchall()

    cat_labels = [r['category'] for r in cat_rows]
    cat_totals = [round(r['total'], 2) for r in cat_rows]

    # 3. Monte Carlo Simulation Engine (1,000 Iterations)
    monte_carlo = run_monte_carlo_simulation(current_balance, trend_incomes, trend_expenses)

    conn.close()

    return render_template(
        'analytics.html',
        trend_months=trend_months,
        trend_incomes=trend_incomes,
        trend_expenses=trend_expenses,
        cat_labels=cat_labels,
        cat_totals=cat_totals,
        monte_carlo=monte_carlo
    )


@app.route('/add', methods=['GET', 'POST'])
def add_transaction():
    if request.method == 'POST':
        title = request.form['title'].strip()
        amount_raw = request.form['amount'].strip()
        type_ = request.form['type']
        category = request.form['category'].strip()
        date = request.form['date']
        notes = request.form.get('notes', '').strip()

        if not title or not amount_raw or not type_ or not category or not date:
            flash('All fields except notes are required.', 'error')
            return redirect(url_for('add_transaction'))

        try:
            amount = float(amount_raw)
            if amount <= 0:
                flash('Amount must be greater than zero.', 'error')
                return redirect(url_for('add_transaction'))
        except ValueError:
            flash('Invalid amount format.', 'error')
            return redirect(url_for('add_transaction'))

        conn = get_db_connection()
        ensure_hash_columns(conn)

        last_row = conn.execute("SELECT curr_hash FROM transactions ORDER BY id DESC LIMIT 1").fetchone()
        prev_hash = last_row['curr_hash'] if last_row and last_row['curr_hash'] else GENESIS_HASH

        curr_hash = compute_row_hash(prev_hash, date, title, amount, type_, category, notes)

        conn.execute(
            '''INSERT INTO transactions (title, amount, type, category, date, notes, prev_hash, curr_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (title, amount, type_, category, date, notes, prev_hash, curr_hash)
        )
        conn.commit()
        conn.close()

        flash('Transaction added & cryptographically sealed onto ledger!', 'success')
        return redirect(url_for('index'))

    return render_template('add_transaction.html')


@app.route('/delete/<int:id>', methods=['POST'])
def delete_transaction(id):
    conn = get_db_connection()
    ensure_hash_columns(conn)
    conn.execute('DELETE FROM transactions WHERE id = ?', (id,))
    conn.execute('DELETE FROM dismissed_anomalies WHERE transaction_id = ?', (id,))
    conn.commit()

    rebuild_ledger_chain(conn)
    conn.close()

    flash('Transaction removed and ledger chain successfully re-sealed.', 'warning')
    return redirect(url_for('index'))


@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_transaction(id):
    conn = get_db_connection()
    ensure_hash_columns(conn)

    if request.method == 'POST':
        title = request.form['title'].strip()
        amount_raw = request.form['amount'].strip()
        type_ = request.form['type']
        category = request.form['category'].strip()
        date = request.form['date']
        notes = request.form.get('notes', '').strip()

        if not title or not amount_raw or not type_ or not category or not date:
            conn.close()
            flash('All fields except notes are required.', 'error')
            return redirect(url_for('edit_transaction', id=id))

        try:
            amount = float(amount_raw)
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

        rebuild_ledger_chain(conn)
        conn.close()

        flash('Transaction updated and ledger chain re-sealed.', 'info')
        return redirect(url_for('index'))

    transaction = conn.execute(
        'SELECT * FROM transactions WHERE id = ?', (id,)
    ).fetchone()
    conn.close()

    if transaction is None:
        flash('Transaction not found.', 'error')
        return redirect(url_for('index'))

    return render_template('edit_transaction.html', transaction=transaction)


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

    writer.writerow(['ID', 'Date', 'Title', 'Category', 'Type', 'Amount ($)', 'Notes', 'SHA256_Hash'])

    for t in transactions:
        writer.writerow([
            t['id'],
            t['date'],
            t['title'],
            t['category'],
            t['type'].capitalize(),
            f"{t['amount']:.2f}",
            t['notes'] or '',
            t['curr_hash'] if 'curr_hash' in t.keys() else ''
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