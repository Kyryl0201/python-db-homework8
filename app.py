import functools
import os

from dateutil import parser

from sqlalchemy import select, delete, update, func

import database, time

from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask import session

import models
from models import ActorsFilms

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
app.config['JSON_AS_ASCII'] = False
app.json.ensure_ascii = False



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
    database.init_db()
    smth = select(models.Film).order_by(models.Film.added_at.desc()).limit(10)
    film = database.db_session.execute(smth).scalars().all()
    return render_template("main.html",films=film)


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

    database.init_db()
    session_user_id = session.get('user_id')
    if request.method == 'POST':
        if int(user_id) != session_user_id:
            return 'You can edit only your profile'

        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']
        birth_date = parser.parse(request.form['birth_date'])
        phone = request.form['phone']
        photo = request.form['photo']
        additional_info = request.form['additional_info']

        stmt = update(models.User).where(models.User.id == user_id).values(first_name=first_name, last_name=last_name, email=email, password=password, birth_date=birth_date, phone_number=phone, photo=photo, additional_info=additional_info)
        database.db_session.execute(stmt)
        database.db_session.commit()
        return f'User {user_id} updated'

    else:

        query_user_by_id = select(models.User).where(models.User.id == user_id)
        user_by_id = database.db_session.execute(query_user_by_id).scalar_one()

        if session_user_id is None:
            user_by_session = "No user in session"
        else:
            query_user_by_session = select(models.User).where(models.User.id == session_user_id)
            user_by_session = database.db_session.execute(query_user_by_session).scalar_one()


        database.db_session.commit()
    return render_template("user_page.html", user=user_by_id, user_session=user_by_session)
    #return f'You logged in as {user_by_session}, user {user_id}, data: {user_by_id}'

@app.route('/user/<user_id>/delete', methods=['GET'])
@decorator_check_login
def user_delete(user_id):
    session_user_id = session.get('user_id')
    if int(user_id) == session_user_id:
        return f'User {user_id} deleted'
    else:
        return 'You can delete only your profile'

@app.route('/films', methods=['GET'])
@decorator_check_login
def films():
    filter_params = request.args
    filter_list_texts = []
    films_query = select(models.Film)
    for key, value in filter_params.items():
        if value:
            if key == 'name':
                films_query = films_query.where(models.Film.name.like(f"%{value}%"))
            elif key == 'rating':
                    value = float(value)
                    films_query = films_query.where(models.Film.rating == value)
            elif key == 'country':
                    films_query = films_query.where(models.Film.country == value)
            elif key == 'year':
                    films_query = films_query.where(models.Film.year == int(value))

    films = films_query.order_by(models.Film.added_at.desc())
    result_films = database.db_session.execute(films).scalars()
    countries = select(models.Country)
    result_countries = database.db_session.execute(countries).scalars()

    return render_template("films.html", films=result_films, countries=result_countries)


@app.route('/films', methods=['POST'])
@decorator_check_login
def films_add():
    database.init_db()

    data = request.get_json() or {}
    name = data.get("name")
    poster = data.get("poster")
    description = data.get("description")
    rating = data.get("rating")
    country = data.get("country")
    year = data.get("year")
    duration = data.get("duration")

    if not name or not country or year is None or duration is None:
        return jsonify({"error": "name, country, year, duration are required"}), 400

    new_film = models.Film(
        name=name,
        poster=poster,
        rating=rating,
        country=country,
        year=int(year),
        duration=int(duration),
        added_at=int(time.time())
    )


    if hasattr(new_film, "description"):
        new_film.description = description
    else:
        new_film.description = description

    database.db_session.add(new_film)
    database.db_session.commit()

    return jsonify({"film_id": new_film.id}), 201


@app.route('/films/<int:film_id>', methods=['GET'])
def films_info(film_id):
    database.init_db()

    film_by_id = select(models.Film).where(models.Film.id == film_id)
    result_film_by_id = database.db_session.execute(film_by_id).scalar_one()

    actors = select(models.Actor).join(models.ActorsFilms, models.Actor.id == models.ActorsFilms.actor_id).where(models.ActorsFilms.film_id == film_id)
    result_actors = database.db_session.execute(actors).scalars().all()

    genres = (select(models.Genre).join(models.GenresFilm, models.Genre.genre == models.GenresFilm.genre_id).where(models.GenresFilm.film_id == film_id))
    result_genres = database.db_session.execute(genres).scalars().all()

    return jsonify({
        "id": result_film_by_id.id,
        "name": result_film_by_id.name,
        "poster": result_film_by_id.poster,
        "description": result_film_by_id.description,
        "rating": result_film_by_id.rating,
        "country": result_film_by_id.country,
        "added_at": result_film_by_id.added_at,
        "actors": [itm.to_dict() for itm in result_actors],
        "genres": [itm.to_dict() for itm in result_genres]
    })


@app.route('/films/<int:film_id>', methods=['PUT'])
@decorator_check_login
def films_update(film_id):
    data = request.get_json() or {}
    database.init_db()

    new_film_query = select(models.Film).where(models.Film.id == film_id)
    new_film = database.db_session.execute(new_film_query).scalar_one()

    new_film.name = data.get("name")
    new_film.poster = data.get("poster")
    new_film.description = data.get("description")
    new_film.rating = data.get("rating")
    new_film.country = data.get("country")
    database.db_session.add(new_film)
    database.db_session.commit()


    return jsonify({"film_id": film_id})


@app.route('/films/<int:film_id>', methods=['DELETE'])
@decorator_check_login
def films_delete(film_id):
    database.init_db()

    stmt = delete(models.Film).where(models.Film.id == film_id)
    res = database.db_session.execute(stmt)
    database.db_session.commit()

    if res.rowcount == 0:
        return jsonify({"error": "Film not found"}), 404

    return jsonify({"film_id": film_id})


@app.route('/films/search', methods=['GET'])
def films_search():
    name = request.args.get('name', '')

    films_search_query = (select(models.Film).where(models.Film.name.like(f"%{name}%")).order_by(models.Film.added_at.desc()))
    result_films_search = database.db_session.execute(films_search_query).scalars().all()
    return jsonify([itm.to_dict() for itm in result_films_search])


@app.route('/films/filter', methods=['GET'])
def films_filter():
    database.init_db()
    name = request.args.get('name')
    genre = request.args.get('genre')
    country = request.args.get('country')

    stmt = select(models.Film).distinct()

    if genre:
        stmt = stmt.join(models.GenresFilm, models.GenresFilm.film_id == models.Film.id) \
            .join(models.Genre, models.Genre.genre == models.GenresFilm.genre_id) \
            .where(models.Genre.genre == genre)

    if name:
        stmt = stmt.where(models.Film.name.like(f"%{name}%"))
    if country:
        stmt = stmt.where(models.Film.country == country)

    film = database.db_session.execute(stmt).scalars().all()
    return jsonify([f.to_dict() for f in film])


@app.route('/films/<int:film_id>/rating', methods=['GET'])
def films_ratings_info(film_id):
    database.init_db()

    ratings_query = select(models.Feedback).where(models.Feedback.film == film_id)
    ratings = database.db_session.execute(ratings_query).scalars().all()

    grades_query = (
        select(
            func.avg(models.Feedback.grade).label('average'),
            func.count(models.Feedback.id).label('ratings_count')
        )
        .where(models.Feedback.film == film_id)
    )
    avg_rating, ratings_count = database.db_session.execute(grades_query).one()

    return jsonify({
        "film_id": film_id,
        "average_rating": avg_rating,
        "ratings_count": ratings_count,
        "ratings": [
            {
                "id": r.id,
                "user": r.user,
                "grade": r.grade,
                "description": r.descripyion
            } for r in ratings
        ]
    })


@app.route('/films/<int:film_id>/rating', methods=['POST'])
@decorator_check_login
def films_rating_add(film_id):
    database.init_db()
    data = request.get_json() or {}

    fb = models.Feedback(
        film=film_id,
        user=data["user_id"],
        grade=data.get("grade"),
        description=data.get("description")
    )
    database.db_session.add(fb)
    database.db_session.commit()

    return jsonify({"feedback_id": fb.id}), 201


@app.route('/films/<int:film_id>/rating/<int:feedback_id>', methods=['DELETE'])
@decorator_check_login
def films_ratings_delete(film_id, feedback_id):
    database.init_db()

    stmt = delete(models.Feedback).where(
        models.Feedback.id == feedback_id,
        models.Feedback.film == film_id
    )
    res = database.db_session.execute(stmt)
    database.db_session.commit()

    if res.rowcount == 0:
        return jsonify({"error": "feedback not found"}), 404

    return jsonify({"feedback_id": feedback_id})


@app.route('/films/<int:film_id>/rating/<int:feedback_id>', methods=['PUT'])
@decorator_check_login
def films_ratings_update(film_id, feedback_id):
    database.init_db()
    data = request.get_json() or {}

    stmt = (
        update(models.Feedback)
        .where(models.Feedback.id == feedback_id, models.Feedback.film == film_id)
        .values(
            grade=data.get("grade"),
            descripyion=data.get("description")
        )
    )
    res = database.db_session.execute(stmt)
    database.db_session.commit()

    if res.rowcount == 0:
        return jsonify({"error": "feedback not found"}), 404

    return jsonify({"feedback_id": feedback_id})



if __name__ == '__main__':
    database.init_db()
    app.run(debug=True)
