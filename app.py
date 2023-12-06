import csv
import sqlite3
from flask import Flask, render_template, request, make_response, redirect
from util import *


# CONSTANTS #
# SERVER CONSTANTS
SERVE_PORT = 5001

# FILE PATHS
DATABASE_PATH = "Database.db"
CSV_PATH = "demo_data.csv"

# INDEXES
ID_INDEX = 0
TITLE_INDEX = 1
LOG_DETAIL_INDEX = 2
WATCH_DATE_INDEX = 3
RATING_INDEX = 4
RELEASE_YEAR_INDEX = 5

# APP AND DATABASE
app = Flask(__name__)
conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)


def send_not_found_page() -> str:
    """Renders the page for a 404 error."""
    return render_template('error.html', not_found=True)


def get_all_logged_movies() -> list:
    """Retrieves every logged movie from the database, unpacks them, then returns them."""
    movies = conn.execute("SELECT * FROM Movies").fetchall()
    
    return [
        (
            *movie[:-2],  # All elements up to rating
            int(movie[-2]) if movie[-2] is not None and movie[-2] != "" else None,  # Removes decimal point from rating (if exists)
            *movie[-1:],  # Last element
        )
        for movie in movies # Do this for each movie
    ]


def get_average_rating() -> float:
    """Retrieves the average rating for a movie."""
    entries = conn.execute('SELECT rating, movie_name FROM Movies').fetchall()
    ratings = [entry[0] for entry in entries if entry[0] != ''] # Go through each entry and only take ones with a rating
    if len(ratings) == 0: # If the ratings is empty, then the sum will be 0 too
        return 0
    return round(sum(ratings) / len(ratings), 2)


def get_total_logged() -> int:
    """Grabs every id from the db in a list of tuples and returns the length."""
    return len(conn.execute('SELECT id FROM Movies').fetchall()) 


def extract_movie_details_from_log(log):
    """Extracts log information from existing log."""
    title = log[TITLE_INDEX]
    log_details = log[LOG_DETAIL_INDEX]
    watch_date = log[WATCH_DATE_INDEX]
    rating = None  # This cannot use string_to_number() as we do not care if it does not exist
    try:
        rating = int(log[RATING_INDEX])
    except (ValueError, TypeError):
        pass # Handle it by not handling it
    release_year = log[RELEASE_YEAR_INDEX]
    return title, log_details, watch_date, rating, release_year


def extract_movie_details_from_form():
    """Extract log details from form input (typically /edit or /create)."""
    title = request.form.get("movie-title", None).strip()
    date_watched = string_to_date(request.form.get("watch-date", None))
    rating = request.form.get("rating", None)
    log_details = request.form.get("log-details", None)
    if log_details:
        log_details = log_details.strip()
    release_year = string_to_number(request.form.get("release_year", None))

    return title, log_details, date_watched, rating, release_year # There will never be an error, no need to check for one.


def reset_database() -> None:
    """Sets up the database and inputs demo data."""
    conn.execute("DROP TABLE IF EXISTS Movies")
    conn.execute(
        """CREATE TABLE Movies(
            id INTEGER PRIMARY KEY,
            movie_name VARCHAR(255),
            log_details TEXT,
            watched_date DATE,
            rating FLOAT, 
            release_year INTEGER
    )"""
    )
    with open(CSV_PATH, "r", encoding="utf-8") as csv_file:
        reader = csv.reader(csv_file)  # Opens the file in the reader
        rows = []
        for row in reader:  # Go through each row and add it to the rows list
            rows.append(row)
        del rows[ID_INDEX]  # Remove the first row which has the row names
        for movie in rows:  # Insert each demo row in the database.
            conn.execute(
                "INSERT INTO Movies(movie_name, log_details, watched_date, rating, release_year) VALUES (?,?,?,?,?)",
                (
                    movie[TITLE_INDEX - 1],
                    movie[LOG_DETAIL_INDEX - 1],
                    movie[WATCH_DATE_INDEX - 1],
                    movie[RATING_INDEX - 1],
                    movie[RELEASE_YEAR_INDEX - 1],
                ),
            )
        conn.commit()  # Save the changes


@app.route("/", methods=["GET"])
def send_index_page() -> str:
    """Sends the user the home page."""
    return render_template("index.html")


@app.route("/movies", methods=["GET"])
def send_movies_page() -> str:
    """Retrieves a list of the logged movies, and returns a page back with them."""
    return render_template("movies.html", movies=get_all_logged_movies(), admin=is_admin())


@app.route("/create", methods=["GET"])
def send_log_form() -> str:
    """Returns the form to log a movie."""
    return render_template("create_log.html")


@app.route("/create", methods=["POST"])
def upload_log() -> str:
    """Retrieves information from the log movie form and uploads it into the database, then
    displays a success message to the user."""
    title, log_details, date_watched, rating, release_year = extract_movie_details_from_form()
    conn.execute(
        """INSERT INTO Movies (movie_name, watched_date, rating, log_details, release_year) VALUES (?,?,?,?,?)""",
        (title, date_watched, rating, log_details, release_year),
    ) # Inserts the log into the database
    conn.commit()  # Commits the operation
    id = conn.execute('SELECT id FROM Movies').fetchall()[-1][0] # Retrieve most recent log id 
    return redirect(f'/view/{id}') # Redirect user to the log 


@app.route("/edit/<id>", methods=["GET"])
def edit_form(id=None) -> str:
    """Send the user a filled-in form to edit an existing log."""
    id = string_to_number(id)
    log = conn.execute("SELECT * FROM Movies WHERE id=?", (id,)).fetchone()
    if log is None:
        return send_not_found_page()
    title, log_details, watch_date, rating, release_year = extract_movie_details_from_log(log)
    return render_template(
        "edit_log.html",
        title=title,
        log_details=log_details,
        watch_date=watch_date,
        rating=rating,
        release_year=release_year,
    )


@app.route("/edit/<id>", methods=["POST"])
def edit_post(id=None) -> str:
    """Retrieves information from the /edit form and updates the db."""
    id = string_to_number(id)
    title, log_details, watch_date, rating, release_year = extract_movie_details_from_form()
    original_log = conn.execute('SELECT movie_name FROM MOVIES WHERE id=?', (id,)).fetchone()
    if not title or title == '':
        title = original_log[TITLE_INDEX-1]
    conn.execute(
        """UPDATE Movies SET movie_name=?, log_details=?, watched_date=?, rating=?, release_year=? WHERE id=?""",
        (title, log_details, watch_date, rating, release_year, id),
    )  # Inserts the log into the database
    conn.commit()  # Commits the operation
    return redirect(f"/view/{id}")  # Send user back to their log to view their changes.


@app.route("/view/<id>", methods=["GET"])
def view_entry(id=None):
    id = string_to_number(id)
    log_query = "SELECT * FROM Movies WHERE id=?"
    movie = conn.execute(log_query, (id,)).fetchone()
    if movie is None:
        return render_template("error.html", not_found=True)
    title, log_details, watch_date, rating, release_year = extract_movie_details_from_log(movie)
    return render_template(
        "view.html",
        title=title,
        watch_date=watch_date,
        rating=rating,
        release_year=release_year,
        log_details=log_details,
    )


@app.route("/delete/<id>", methods=["GET"])
def delete_entry(id=None):
    """Deletes a log from the Database."""
    id = string_to_number(id)
    conn.execute("DELETE FROM Movies WHERE id=?", (id,))
    conn.commit()
    return redirect("/movies")


@app.route("/reset-db")
def reset_db():
    """Resets the database then sends the user to the setup page."""
    reset_database()
    return render_template("reset_database.html")


@app.route("/toggle-admin")
def toggle_admin():
    """Toggles administration mode and sends the user to the index page."""
    resp = make_response(redirect("/movies"))  # Redirect user back to main page
    resp.set_cookie(
        "admin", str((not is_admin())) # Cookies must be set to strings
    )  # Toggles the admin value (True to False...)
    return resp


@app.route('/stats')
def get_stats_page():
    """Sends the user their statistics."""
    return render_template('stats.html', average_rating=get_average_rating(), total_logged=get_total_logged())
    

@app.errorhandler(404)
def not_found(e):
    """Handles page not found errors."""
    return send_not_found_page()
    

def start():
    """Begins serving the website on port 5001."""
    try:
        conn.execute("SELECT * FROM Movies")
    except sqlite3.OperationalError:
        reset_database()
    app.run(port=SERVE_PORT, debug=True)
    

if __name__ == "__main__":
    start()
