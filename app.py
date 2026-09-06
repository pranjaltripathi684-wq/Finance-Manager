# 1. Import Flask and render_template from the flask package

# 2. Initialize the Flask application instance (app = Flask(__name__))

# 3. Define a root route ("/") that responds to GET requests
#    - For now, create a function (e.g., index or home) that returns a simple welcome message or test string

# 4. Add the standard Python entry point check:
#    if __name__ == '__main__':
#        run the app with debug mode enabled (debug=True)

                                    
# 1. Import get_db_connection from db
# 2. Import request, redirect, url_for, flash (optional) from flask

# 3. Create route '/add' supporting both methods=['GET', 'POST']:
#    - If request.method == 'POST':
#        - Extract form values: request.form['title'], request.form['amount'], etc.
#        - Basic validation (check if required fields are present)
#        - Connect to DB: conn = get_db_connection()
#        - Execute INSERT query:
#          conn.execute('INSERT INTO transactions (title, amount, type, category, date, notes) VALUES (?, ?, ?, ?, ?, ?)',
#                       (title, amount, type, category, date, notes))
#        - conn.commit() and conn.close()
#        - Redirect to root URL: redirect(url_for('index'))
#    - If GET request:
#        - Render template 'add_transaction.html'
import os
from flask import Flask, render_template, request, redirect, url_for
from db import get_db_connection

app = Flask(__name__)

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
        type = request.form['type']
        category = request.form['category'].strip()
        date = request.form['date']
        notes = request.form.get('notes', '').strip()

        if not title or not amount or not type or not category or not date:
            return "All fields except notes are required.", 400

        try:
            amount = float(amount)
            if amount <= 0:
                return "Amount must be greater than zero.", 400
        except ValueError:
            return "Invalid amount format.", 400

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO transactions (title, amount, type, category, date, notes) VALUES (?, ?, ?, ?, ?, ?)',
            (title, amount, type, category, date, notes)
        )
        conn.commit()
        conn.close()

        return redirect(url_for('index'))

    return render_template('add_transaction.html')


@app.route('/delete/<int:id>', methods=['POST'])
def delete_transaction(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM transactions WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))


@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_transaction(id):
    conn = get_db_connection()

    if request.method == 'POST':
        title = request.form['title'].strip()
        amount = request.form['amount'].strip()
        type = request.form['type']
        category = request.form['category'].strip()
        date = request.form['date']
        notes = request.form.get('notes', '').strip()

        if not title or not amount or not type or not category or not date:
            conn.close()
            return "All fields except notes are required.", 400

        try:
            amount = float(amount)
            if amount <= 0:
                conn.close()
                return "Amount must be greater than zero.", 400
        except ValueError:
            conn.close()
            return "Invalid amount format.", 400

        conn.execute(
            'UPDATE transactions SET title=?, amount=?, type=?, category=?, date=?, notes=? WHERE id=?',
            (title, amount, type, category, date, notes, id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    transaction = conn.execute(
        'SELECT * FROM transactions WHERE id = ?', (id,)
    ).fetchone()
    conn.close()

    if transaction is None:
        return "Transaction not found.", 404

    return render_template('edit_transaction.html', transaction=transaction)


if __name__ == '__main__':
    app.run(debug=True)