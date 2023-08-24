from functools import wraps

from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, declarative_base
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm , RegisterForm, LoginForm,CommentForm
from flask_gravatar import Gravatar

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


def admin_only(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.id!=1:
            return abort(404)

        return func(*args, **kwargs)
    return wrapper


##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


login_manager=LoginManager()
login_manager.init_app(app)



@login_manager.user_loader
def loader_user(user_id):
    return User.query.filter_by(email=user_id).first()










##CONFIGURE TABLES
class User(UserMixin,db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email=db.Column(db.String(250), nullable=False)
    password=db.Column(db.String(250), nullable=False)
    name=db.Column(db.String(250), nullable=False)
    posts = relationship('BlogPost',back_populates="author")
    comments=relationship('Comment',back_populates='comment_author')

    def is_active(self):
        """True, as all users are active."""
        return True

    def is_authenticated(self):
        """Return True if the user is authenticated."""
        return self.authenticated

    def get_id(self):
        """Return the email address to satisfy Flask-Login's requirements."""
        return self.email

    def is_anonymous(self):
        """False, as anonymous users aren't supported."""
        return False


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    author=relationship("User",back_populates="posts")
    blog_comments=relationship("Comment",back_populates="parent_post")

class Comment(db.Model):
    __tablename__="commnets"
    id=db.Column(db.Integer, primary_key=True)
    author_id=db.Column(db.Integer,db.ForeignKey("users.id"))
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    text=db.Column(db.Text, nullable=False)
    comment_author=relationship("User",back_populates="comments")
    parent_post=relationship("BlogPost",back_populates="blog_comments")








@app.route('/')
def get_all_posts():
    with app.app_context():
        posts = BlogPost.query.all()
        user=User.query.filter_by
    return render_template("index.html", all_posts=posts,user=user)


@app.route('/register',methods=["POST","GET"])
def register():
    register_form=RegisterForm()
    if register_form.validate_on_submit():
        if User.query.filter_by(email=register_form.email.data).first():
            flash("You have already signed up with email, log in instead!")
            return redirect("/login")
        else:
            with app.app_context():
                new_user=User(name=register_form.name.data,email=register_form.email.data,password=generate_password_hash(register_form.password.data,salt_length=8,method="pbkdf2:sha256"))
                db.session.add(new_user)
                db.session.commit()
                login_user(new_user)
                return redirect("/")
    return render_template("register.html",form=register_form)


@app.route('/login',methods=["POST","GET"])
def login():
    login_form=LoginForm()
    if login_form.validate_on_submit():
        with app.app_context():
            user=User.query.filter_by(email=login_form.email.data).first()
            if user:
                if check_password_hash(user.password,login_form.password.data):
                    login_user(user)
                    return redirect("/")
                else:
                    flash("Password incorrect, please try again!")
                    return redirect("/login")
            else:
                flash("That email does not exist, please try again!")
                return redirect("/login")
    return render_template("login.html",form=login_form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>",methods=["POST","GET"])
def show_post(post_id):
    comment_form=CommentForm()
    comments=Comment.query.all()
    requested_post = BlogPost.query.get(post_id)
    if comment_form.validate_on_submit():
        if current_user.is_authenticated:
            with app.app_context():
                comment=Comment(text=comment_form.comment.data,author_id=current_user.id,post_id=post_id)
                db.session.add(comment)
                db.session.commit()
        else:
            flash("Please Log in for making comments!")
            return redirect("/login")
    return render_template("post.html", post=requested_post,form=comment_form,comments=comments)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact",methods=["GET","POST"])
def contact():
    return render_template("contact.html")


@app.route("/new-post",methods=["POST","GET"])
@login_required
@admin_only
def add_new_post():
        form = CreatePostForm()
        if form.validate_on_submit():
            with app.app_context():
                new_post = BlogPost(
                title=form.title.data,
                subtitle=form.subtitle.data,
                body=form.body.data,
                img_url=form.img_url.data,
                author_id=current_user.id,
                date=date.today().strftime("%B %d, %Y"),
                )
                db.session.add(new_post)
                db.session.commit()
            return redirect("/")
        return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>",methods=["POST","GET"])
@login_required
@admin_only
def edit_post(post_id):
    is_edit=True
    with app.app_context():
            post = BlogPost.query.get(post_id)
            edit_form = CreatePostForm(
            title=post.title,
            subtitle=post.subtitle,
            img_url=post.img_url,
            body=post.body
            )
    if edit_form.validate_on_submit():
        with app.app_context():
                post.title = edit_form.title.data
                post.subtitle = edit_form.subtitle.data
                post.img_url = edit_form.img_url.data
                post.body = edit_form.body.data
                db.session.add(post)
                db.session.commit()
                return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form,is_edit=is_edit)


@app.route("/delete/<int:post_id>")
@login_required
@admin_only
def delete_post(post_id):
        with app.app_context():
            post_to_delete = BlogPost.query.get(post_id)
            db.session.delete(post_to_delete)
            db.session.commit()
        return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
