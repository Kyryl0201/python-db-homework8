from sqlalchemy import Column, Integer, String, Date, ForeignKey
from database import Base

class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    password = Column(String(50), nullable=False)
    login = Column(String(50), nullable=False, unique=True)
    email = Column(String(120), unique=True)
    phone_number = Column(String(20))
    photo = Column(String(255))
    additional_info = Column(String(255))
    birth_date = Column(Date)

    def __repr__(self):
        return f'<User {self.login!r}>'

class Actor(Base):
    __tablename__ = 'actor'
    id = Column(Integer, primary_key=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    birth_date = Column(Date)
    death_date = Column(Date)
    description = Column(String(255))

    def __repr__(self):
        return f'<Actor {self.last_name!r}>'

class Film(Base):
    __tablename__ = 'film'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    year = Column(Integer, nullable=False)
    poster = Column(String(255))
    description = Column(String(255))
    rating = Column(Integer)
    duration = Column(Integer, nullable=False)
    added_at = Column(Integer, nullable=False)
    country = Column(String(50), nullable=False)

    def __repr__(self):
        return f'<Film {self.name!r}>'

class Genre(Base):
    __tablename__ = 'genre'
    genre = Column(String(50), nullable=False, primary_key=True)

    def __repr__(self):
        return f'<Genre {self.genre!r}>'

class GenresFilm(Base):
    __tablename__ = 'genre_film'
    id = Column(Integer, primary_key=True)
    genre_id = Column(String(50), ForeignKey('genre.genre'))
    film_id = Column(Integer, ForeignKey('film.id'))

class ActorsFilms(Base):
    __tablename__ = 'actor_film'
    id = Column(Integer, primary_key=True)
    actor_id = Column(Integer, ForeignKey('actor.id'))
    film_id = Column(Integer, ForeignKey('film.id'))

class List(Base):
    __tablename__ = 'list'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    film_id = Column(Integer, ForeignKey('film.id'))

class FilmList(Base):
    __tablename__ = 'film_list'
    id = Column(Integer, primary_key=True)
    film_id = Column(Integer, ForeignKey('film.id'))
    list_id = Column(Integer, ForeignKey('list.id'))

class Feedback(Base):
    __tablename__ = 'feedback'
    id = Column(Integer, primary_key=True)
    film_id = Column(Integer, ForeignKey('film.id'))
    user_id = Column(Integer, ForeignKey('user.id'))
    grade = Column(Integer)
    description = Column(String(255))

class Country(Base):
    __tablename__ = 'country'
    country_name = Column(String(50), primary_key=True, unique=True)

