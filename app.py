import os
from flask import Flask, render_template, request, redirect, url_for, flash
from db import get_db_connection

app = Flask(__name__)

# Secret key is REQUIRED by Flask to sign session cookies for flash messages
app.secret_key = 'finance_manager_secret_key_change_in_production'

@app.route('/')
def index():
    conn = get_db_connection()
    transactions = conn.execute(
        'SELECT * FROM transactions ORDER BY date DESC, id DESC'
    ).fetchall()

    total_income = sum(row['amount'] for row in transactions if row['type'] == 'income')
    total_expense = sum(row['amount'] for row in transactions if row['type'] == 'expense')
    balance = total_income - total_expense

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


if __name__ == '__main__':
    app.run(debug=True)