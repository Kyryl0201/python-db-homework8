import functools
import os
from dateutil import parser

from sqlalchemy import select

import database

from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask import session
import sqlite3

import models

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
app.config['JSON_AS_ASCII'] = False
app.json.ensure_ascii = False


def film_dictionary(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def get_db_results(query, params=()):
    conn = sqlite3.connect("a1.db")
    conn.row_factory = film_dictionary
    cursor = conn.cursor()
    cursor.execute(query, params)
    result = cursor.fetchall()
    conn.close()
    return result



class db_connection:
    def __init__(self):
        self.conn = sqlite3.connect('a1.db')
        self.conn.row_factory = film_dictionary
        self.cur = self.conn.cursor()

    def __enter__(self):
        return self.cur

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.commit()
        self.conn.close()


def decorator_check_login(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if session.get('logged_in'):
            return func(*args, **kwargs)
        else:
            return redirect(url_for('user_login'))
    return wrapper

@app.route('/')
@decorator_check_login
def main_page():
    with db_connection() as cur:
        result = cur.execute("""SELECT * FROM film ORDER BY added_at DESC LIMIT 10""").fetchall()
    return render_template("main.html",films=result)


@app.route('/register', methods=['GET'])
def register_page():
    return render_template("register.html")


@app.route('/register', methods=['POST'])
def user_register():
    first_name = request.form['fname']
    last_name = request.form['lname']
    password = request.form['password']
    login = request.form['login']
    email = request.form['email']
    birth_date = parser.parse(request.form['birth_date'])

    database.init_db()

    new_user = models.User(first_name=first_name, last_name=last_name, password=password, login=login, email=email, birth_date=birth_date)

    database.db_session.add(new_user)
    database.db_session.commit()

    return 'Register'


@app.route('/login', methods=['GET'])
def user_login():
    return render_template("login.html")


@app.route('/login', methods=['POST'])
def user_login_post():
    login = request.form['login']
    password = request.form['password']


    database.init_db()

    stmt = select(models.User).where(models.User.login == login, models.User.password == password)
    data = database.db_session.execute(stmt).fetchall()
    if data:
        user_obj = data[0][0]

    result = database.db_session.query(models.User).filter_by(login=login, password=password).first()
    # result == user_obj

    if result:
        session['logged_in'] = True
        session['user_id'] = result.id
        return f'Login with user {result}'
    return 'Login failed'

@app.route('/logout', methods=['GET'])
@decorator_check_login
def user_logout():
    session.clear()
    return 'Logout'

@app.route('/user/<user_id>', methods=['GET', 'POST'])
@decorator_check_login
def user_profile(user_id):
    session_user_id = session.get('user_id')
    if request.method == 'POST':
        if int(user_id) != session_user_id:
            return 'You can edit only your profile'

        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']
        birth_date = request.form['birth_date']
        phone = request.form['phone']
        photo = request.form['photo']
        additional_info = request.form['additional_info']
        with db_connection() as cur:
            cur.execute(f"UPDATE user SET first_name='{first_name}', last_name='{last_name}', email='{email}', password='{password}', birth_date='{birth_date}', phone_number='{phone}', photo='{photo}', additional_info='{additional_info}' WHERE id={user_id}")

            return f'User {user_id} updated'
    else:
        with db_connection() as cur:
            cur.execute(f"SELECT * FROM user WHERE id={user_id}")
            user_by_id = cur.fetchone()

        if session_user_id is None:
            user_by_session = "No user in session"
        else:
            cur.execute(f"SELECT * FROM user WHERE id={session_user_id}")
            user_by_session = cur.fetchone()
    return render_template("user_page.html", user=user_by_id, user_session=user_by_session)
    #return f'You logged in as {user_by_session}, user {user_id}, data: {user_by_id}'

@app.route('/user/<user_id>/delete', methods=['GET'])
@decorator_check_login
def user_delete(user_id):
    session_user_id = session.get('user_id')
    if user_id == session_user_id:
        return f'User {user_id} deleted'
    else:
        return 'You can delete only your profile'

@app.route('/films', methods=['GET'])
@decorator_check_login
def films():
    filter_params = request.args
    filter_list_texts = []
    for key, value in filter_params.items():
        if value:
            if key == 'name':
                filter_list_texts.append(f"name LIKE '%{value}%'")
            else:
                filter_list_texts.append(f"{key}='{value}'")
    additional_filter = ""
    if filter_list_texts:
        additional_filter = " where " + " and ".join(filter_list_texts)
    result = get_db_results(f"""SELECT * FROM film {additional_filter} ORDER BY added_at DESC""")
    countries = get_db_results("select * from country")
    return render_template("films.html", films=result, countries=countries)


@app.route('/films', methods=['POST'])
@decorator_check_login
def films_add():
    data = request.get_json() or {}
    name = data.get("name")
    poster = data.get("poster")
    description = data.get("description")
    rating = data.get("rating")
    country = data.get("country")

    if not name:
        return jsonify({"error": "name is required"}), 400

    with db_connection() as cur:
        cur.execute("""
            INSERT INTO film (name, poster, description, rating, country, added_at)
            VALUES (?, ?, ?, ?, ?, strftime('%s','now'))
        """, (name, poster, description, rating, country))
        film_id = cur.lastrowid

    return jsonify({"film_id": film_id}), 201


@app.route('/films/<int:film_id>', methods=['GET'])
def films_info(film_id):
    with db_connection() as cur:
        film = cur.execute("""
            SELECT id, name, poster, description, rating, country, added_at
            FROM film
            WHERE id = ?
        """, (film_id,)).fetchone()

        actors = cur.execute("""
            SELECT a.id, a.first_name, a.last_name, a.birth_day, a.death_day, a.description
            FROM actor a
            JOIN actor_film af ON a.id = af.actor_id
            WHERE af.film_id = ?
        """, (film_id,)).fetchall()

        genres = cur.execute("""SELECT g.genre FROM genre g JOIN genre_film gf ON g.genre = gf.genre_id
            WHERE gf.film_id = ?
        """, (film_id,)).fetchall()

    return jsonify({
        "id": film["id"],
        "name": film["name"],
        "poster": film["poster"],
        "description": film["description"],
        "rating": film["rating"],
        "country": film["country"],
        "added_at": film["added_at"],
        "actors": actors,
        "genres": genres
    })


@app.route('/films/<int:film_id>', methods=['PUT'])
@decorator_check_login
def films_update(film_id):
    data = request.get_json() or {}

    with db_connection() as cur:
        cur.execute("""UPDATE film SET name = COALESCE(?, name),
                poster = COALESCE(?, poster),
                description = COALESCE(?, description),
                rating = COALESCE(?, rating),
                country = COALESCE(?, country)
            WHERE id = ?
        """, (
            data.get("name"),
            data.get("poster"),
            data.get("description"),
            data.get("rating"),
            data.get("country"),
            film_id
        ))
        updated = cur.rowcount

    if updated == 0:
        return jsonify({"error": "Film not found"}), 404

    return jsonify({"film_id": film_id})


@app.route('/films/<int:film_id>', methods=['DELETE'])
@decorator_check_login
def films_delete(film_id):
    with db_connection() as cur:
        cur.execute("DELETE FROM film WHERE id = ?", (film_id,))
        deleted = cur.rowcount

    if deleted == 0:
        return jsonify({"error": "Film not found"}), 404

    return jsonify({"film_id": film_id})


@app.route('/films/search', methods=['GET'])
def films_search():
    name = request.args.get('name', '')

    with db_connection() as cur:
        rows = cur.execute("""
            SELECT id, name, poster, description, rating, country, added_at
            FROM film
            WHERE name LIKE ?
            ORDER BY added_at DESC
        """, (f"%{name}%",)).fetchall()

    return jsonify(rows)


@app.route('/films/filter', methods=['GET'])
def films_filter():
    name = request.args.get('name')
    genre = request.args.get('genre')
    country = request.args.get('country')

    query = """
        SELECT DISTINCT f.id, f.name, f.poster, f.description, f.rating, f.country, f.added_at
        FROM film f
        LEFT JOIN genre_film gf ON f.id = gf.film_id
        LEFT JOIN genre g ON g.genre = gf.genre_id
        WHERE 1=1
    """
    params = []

    if name:
        query += " AND f.name LIKE ?"
        params.append(f"%{name}%")

    if genre:
        query += " AND g.name = ?"
        params.append(genre)

    if country:
        query += " AND f.country = ?"
        params.append(country)

    query += " ORDER BY f.added_at DESC"

    with db_connection() as cur:
        rows = cur.execute(query, params).fetchall()

    return jsonify(rows)


@app.route('/films/<int:film_id>/rating', methods=['GET'])
def films_ratings_info(film_id):
    with db_connection() as cur:
        ratings = cur.execute("""
            SELECT id, user_id, grade, description
            FROM feedback
            WHERE film_id = ?
        """, (film_id,)).fetchall()

        avg = cur.execute("""
            SELECT AVG(grade) AS avg_rating, COUNT(*) AS cnt
            FROM feedback
            WHERE film_id = ?
        """, (film_id,)).fetchone()

    return jsonify({
        "film_id": film_id,
        "average_rating": avg["avg_rating"],
        "ratings_count": avg["cnt"],
        "ratings": ratings
    })


@app.route('/films/<int:film_id>/rating', methods=['POST'])
@decorator_check_login
def films_rating_add(film_id):
    data = request.get_json() or {}
    user_id = data.get("user_id")
    grade = data.get("grade")
    description = data.get("description")

    if user_id is None or grade is None:
        return jsonify({"error": "user_id and grade are required"}), 400

    with db_connection() as cur:
        cur.execute("""
            INSERT INTO feedback (user_id, film_id, grade, description)
            VALUES (?, ?, ?, ?)
        """, (user_id, film_id, grade, description))
        feedback_id = cur.lastrowid

    return jsonify({"feedback_id": feedback_id}), 201


@app.route('/films/<int:film_id>/rating/<int:feedback_id>', methods=['DELETE'])
@decorator_check_login
def films_ratings_delete(film_id, feedback_id):
    with db_connection() as cur:
        cur.execute("""
            DELETE FROM feedback
            WHERE id = ? AND film_id = ?
        """, (feedback_id, film_id))
        deleted = cur.rowcount

    if deleted == 0:
        return jsonify({"error": "feedback not found"}), 404

    return jsonify({"feedback_id": feedback_id})


@app.route('/films/<int:film_id>/rating/<int:feedback_id>', methods=['PUT'])
@decorator_check_login
def films_ratings_update(film_id, feedback_id):
    data = request.get_json() or {}
    grade = data.get("grade")
    description = data.get("description")

    with db_connection() as cur:
        cur.execute("""
            UPDATE feedback
            SET grade = COALESCE(?, grade),
                description = COALESCE(?, description)
            WHERE id = ? AND film_id = ?
        """, (grade, description, feedback_id, film_id))
        updated = cur.rowcount

    if updated == 0:
        return jsonify({"error": "feedback not found"}), 404

    return jsonify({"feedback_id": feedback_id})


if __name__ == '__main__':
    app.run(debug=True)
