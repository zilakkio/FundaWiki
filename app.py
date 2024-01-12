import json
import time
import random
import secret

from urllib.parse import unquote
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from werkzeug.exceptions import default_exceptions, HTTPException

import utils
from page_manager import *
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash

page_manager = pm

app = Flask(__name__)
app.secret_key = secret.secret_key

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


last_save = 0


with open('users.json', 'r') as file:
    users = json.load(file)


@app.before_request
def update():
    global last_save
    t = time.time()
    if t > last_save + 1:
        page_manager.save()
        with open('users.json', 'w') as file:
            json.dump(users, file)
        last_save = t


@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now().year}


class User(UserMixin):
    def __init__(self, username):
        self.id = username
        self.admin = users[username].get('is_admin', False)

    def is_admin(self):
        return self.admin


def handle_error(e):
    # Handle HTTPExceptions and other Exceptions differently
    if isinstance(e, HTTPException):
        code = e.code
        message = e.description
    else:
        code = 500
        message = "Internal Server Error"

    return render_template('error.html', error_code=code, error_message=message), code


# Register error handler for all error types
for ex in default_exceptions:
    app.register_error_handler(ex, handle_error)

# Optional: Handle generic exceptions as well
app.register_error_handler(Exception, handle_error)


@login_manager.user_loader
def user_loader(username):
    if username not in users:
        return

    user = User(username)
    user.id = username
    return user


@app.route('/api/tokenize/<path:text>')
def tokenize(text):
    tokens = utils.tokenize(text)
    transformed_tokens = []
    for token in tokens:
        pages = pm.find_pages_with_link(token.lower())
        if len(pages) > 0:
            page = pages[0]
            transformed_tokens.append(f'[{token}](https://funda.wiki/define/{page})')
        else:
            transformed_tokens.append(f'{token}')
    return "".join(transformed_tokens)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users.get(username)

        if user and check_password_hash(user['password'], password):
            user_obj = User(username)
            user_obj.id = username
            login_user(user_obj)
            return redirect(url_for('home'))

        flash('Invalid username or password')

    return render_template('login.html')


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username in users:
            flash('Username already exists!')
            return redirect(url_for('signup'))

        # Store hashed password
        users[username] = {'password': generate_password_hash(password), 'is_admin': False}

        # Create user object for Flask-Login
        user_obj = User(username)
        user_obj.id = username
        login_user(user_obj)

        next_page = request.args.get('next') or url_for('home')
        return redirect(next_page)

    return render_template('signup.html')


@app.route('/create', methods=['GET', 'POST'])
@app.route('/create/<path:title>', methods=['GET', 'POST'])
@login_required
def create_page(title=None):
    title = unquote(title).replace('`', '') if title else None
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content').replace("\n", "<br>")
        links = [a.lower().strip() for a in request.form.get('links').split('\n')] if request.form.get('links') else []
        is_axiomatic = 'axiomatic' in request.form
        if title and content:
            page_manager.add_page(title, content, links, current_user.id, is_axiomatic=is_axiomatic,
                                  is_admin=current_user.is_admin())
            return redirect(url_for('show_page', page_name=title.lower()))
        else:
            return "Missing title or content", 400
    else:
        # Render form with title pre-filled if provided in the URL
        return render_template('create_page.html', prefill_title=title[0].upper() + title[1:] if title else "")


@app.route('/edit/<path:page_name>/<version_id>', methods=['GET', 'POST'])
@login_required
def edit_page(page_name, version_id):
    page_name = unquote(page_name).replace('`', '')
    page = page_manager.get_page(page_name)
    if page:
        if page.is_verified and not current_user.admin:
            return "Access denied", 403

        if request.method == 'POST':
            content = request.form.get('content').replace("\n", "<br>")
            links = [a.lower().strip() for a in request.form.get('links').split('\n')] if request.form.get('links') else []
            is_axiomatic = 'axiomatic' in request.form
            page_manager.update_page(page_name, content, links, current_user.id, is_axiomatic=is_axiomatic,
                                     admin=current_user.admin, version_id=version_id)
            return redirect(url_for('show_page', page_name=page_name))

        version = page.versions.get(version_id)

        return render_template('edit_page.html', page=page, version=version)

    abort(404)


@app.route('/define/')
@app.route('/define')
@app.route('/define/<path:page_name>')
def show_page(page_name=None):
    page_name = unquote(page_name).replace('`', '') if page_name else None
    if not page_name:
        return redirect(url_for('home'))
    page = page_manager.get_page(page_name)
    if page is not None:
        for v in page.versions.values():
            v.render_content(page_manager)
        return render_template('page.html', page=page)
    else:
        return redirect(url_for('create_page', title=page_name))


@app.route('/conflict/<path:link_name>')
def conflict(link_name):
    link_name = unquote(link_name).replace('`', '')
    matching_pages = []  # List to hold pages that contain the link_name
    for page in page_manager.pages.values():
        if link_name in page.links:
            matching_pages.append(page)

    # If there's only one matching page, redirect to that page directly
    if len(matching_pages) == 1:
        return redirect(url_for('show_page', page_name=matching_pages[0].key))

    return render_template('conflict.html', link_name=link_name, pages=matching_pages)


@app.route('/verify/<path:page_name>/<version_id>')
@login_required
def verify_page(page_name, version_id):
    page_name = unquote(page_name).replace('`', '')
    if not current_user.is_admin():
        return abort(403)

    page = page_manager.get_page(page_name)
    if page and page.versions.get(version_id, None):
        page.is_verified = True
        page.versions = {version_id: page.versions[version_id]}
        return redirect(url_for('show_page', page_name=page_name))
    else:
        return abort(404)


@app.route('/delete/<path:page_key>', methods=['GET', 'POST'])
@login_required
def delete_page(page_key):
    page_key = unquote(page_key).replace('`', '')
    if not current_user.is_admin():
        return "Access denied", 403

    page = page_manager.get_page(page_key)
    if page:
        del page_manager.pages[page_key]
        # Add logic here to delete the page from your storage or database
        return redirect(url_for('home'))
    else:
        return "Page not found", 404


@app.route('/random')
def random_page():
    page_keys = list(page_manager.pages.keys())
    if page_keys:
        random_key = random.choice(page_keys)
        return redirect(url_for('show_page', page_name=random_key))
    else:
        return abort(404)


@app.route('/')
def home():
    page_list = page_manager.get_all_pages()
    featured_page = random.choice(page_list)  # Randomly select a featured page
    return render_template('home.html', pages=page_list)


@app.route('/search')
def search():
    query = request.args.get('q', '')
    results = page_manager.search_pages(query)
    return render_template('search_results.html', query=query, results=results)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80)