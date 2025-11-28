from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.json.ensure_ascii = False


def get_db_connection():
    conn = sqlite3.connect('a1.db')
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/', methods=['GET'])
def main_page():
    conn = get_db_connection()
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT id, poster, name
        FROM film
        ORDER BY added_at DESC
        LIMIT 10
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/films', methods=['GET'])
def films():
    conn = get_db_connection()
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT id, poster, name, description, rating, country, added_at
        FROM film
        ORDER BY added_at DESC
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/films', methods=['POST'])
def films_add():
    data = request.get_json() or {}
    name = data.get("name")
    poster = data.get("poster")
    description = data.get("description")
    rating = data.get("rating")
    country = data.get("country")

    if not name:
        return jsonify({"error": "name is required"}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO film (name, poster, description, rating, country, added_at)
        VALUES (?, ?, ?, ?, ?, strftime('%s','now'))
    """, (name, poster, description, rating, country))
    conn.commit()
    film_id = cur.lastrowid
    conn.close()
    return jsonify({"film_id": film_id}), 201


@app.route('/films/<int:film_id>', methods=['GET'])
def films_info(film_id):
    conn = get_db_connection()
    cur = conn.cursor()

    film = cur.execute("""
        SELECT id, name, poster, description, rating, country, added_at
        FROM film
        WHERE id = ?
    """, (film_id,)).fetchone()

    if film is None:
        conn.close()
        return jsonify({"error": "Film not found"}), 404

    actors = cur.execute("""
        SELECT a.id, a.first_name, a.last_name, a.birth_day, a.death_day, a.description
        FROM actor a
        JOIN actor_film af ON a.id = af.actor_id
        WHERE af.film_id = ?
    """, (film_id,)).fetchall()

    genres = cur.execute("""
        SELECT g.id, g.name
        FROM genre g
        JOIN genre_film gf ON g.id = gf.genre_id
        WHERE gf.film_id = ?
    """, (film_id,)).fetchall()

    conn.close()

    return jsonify({
        "id": film["id"],
        "name": film["name"],
        "poster": film["poster"],
        "description": film["description"],
        "rating": film["rating"],
        "country": film["country"],
        "added_at": film["added_at"],
        "actors": [dict(a) for a in actors],
        "genres": [dict(g) for g in genres]
    })


@app.route('/films/<int:film_id>', methods=['PUT'])
def films_update(film_id):
    data = request.get_json() or {}
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE film
        SET name = COALESCE(?, name),
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
    conn.commit()
    updated = cur.rowcount
    conn.close()

    if updated == 0:
        return jsonify({"error": "Film not found"}), 404

    return jsonify({"film_id": film_id})


@app.route('/films/<int:film_id>', methods=['DELETE'])
def films_delete(film_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM film WHERE id = ?", (film_id,))
    conn.commit()
    deleted = cur.rowcount
    conn.close()

    if deleted == 0:
        return jsonify({"error": "Film not found"}), 404

    return jsonify({"film_id": film_id})


@app.route('/films/search', methods=['GET'])
def films_search():
    name = request.args.get('name', '')
    conn = get_db_connection()
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT id, name, poster, description, rating, country, added_at
        FROM film
        WHERE name LIKE ?
        ORDER BY added_at DESC
    """, (f"%{name}%",)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/films/filter', methods=['GET'])
def films_filter():
    name = request.args.get('name')
    genre = request.args.get('genre')
    country = request.args.get('country')

    query = """
        SELECT DISTINCT f.id, f.name, f.poster, f.description, f.rating, f.country, f.added_at
        FROM film f
        LEFT JOIN genre_film gf ON f.id = gf.film_id
        LEFT JOIN genre g ON g.id = gf.genre_id
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

    conn = get_db_connection()
    rows = conn.cursor().execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/films/<int:film_id>/rating', methods=['GET'])
def films_ratings_info(film_id):
    conn = get_db_connection()
    cur = conn.cursor()

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

    conn.close()

    return jsonify({
        "film_id": film_id,
        "average_rating": avg["avg_rating"],
        "ratings_count": avg["cnt"],
        "ratings": [dict(r) for r in ratings]
    })


@app.route('/films/<int:film_id>/rating', methods=['POST'])
def films_rating_add(film_id):
    data = request.get_json() or {}
    user_id = data.get("user_id")
    grade = data.get("grade")
    description = data.get("description")

    if user_id is None or grade is None:
        return jsonify({"error": "user_id and grade are required"}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO feedback (user_id, film_id, grade, description)
        VALUES (?, ?, ?, ?)
    """, (user_id, film_id, grade, description))
    conn.commit()
    feedback_id = cur.lastrowid
    conn.close()

    return jsonify({"feedback_id": feedback_id}), 201


@app.route('/films/<int:film_id>/rating/<int:feedback_id>', methods=['DELETE'])
def films_ratings_delete(film_id, feedback_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM feedback
        WHERE id = ? AND film_id = ?
    """, (feedback_id, film_id))
    conn.commit()
    deleted = cur.rowcount
    conn.close()

    if deleted == 0:
        return jsonify({"error": "feedback not found"}), 404

    return jsonify({"feedback_id": feedback_id})


@app.route('/films/<int:film_id>/rating/<int:feedback_id>', methods=['PUT'])
def films_ratings_update(film_id, feedback_id):
    data = request.get_json() or {}
    grade = data.get("grade")
    description = data.get("description")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE feedback
        SET grade = COALESCE(?, grade),
            description = COALESCE(?, description)
        WHERE id = ? AND film_id = ?
    """, (grade, description, feedback_id, film_id))
    conn.commit()
    updated = cur.rowcount
    conn.close()

    if updated == 0:
        return jsonify({"error": "feedback not found"}), 404

    return jsonify({"feedback_id": feedback_id})


if __name__ == '__main__':
    app.run(debug=True)
