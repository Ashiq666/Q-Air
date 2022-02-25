import os

from flask import (Blueprint, flash, redirect, render_template, request,
                   session, url_for)
from qair.users.forms import RegisterForm, LoginForm, ResetPasswordForm
from qair import bcrypt, db
from qair.models import User
from flask_login import login_user as login_user_function, login_required, logout_user as logout_user_function, current_user
from qair.users.utils import generate_token, password_reset_key_mail_body
from qair.mails import send_mail
from qair.users.forms import ForgetPasswordForm, ResetPasswordForm

users = Blueprint("users", __name__, url_prefix="/users")


@users.route("/login", methods=["GET", "POST"])
def login_user():
    if current_user.is_authenticated:
        return redirect(url_for('users.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        # Fetching the user
        fetched_user = User.query.filter_by(email=form.email.data).first()
        # Checking the email and password
        if fetched_user and bcrypt.check_password_hash(fetched_user.password, form.password.data):
            login_user_function(fetched_user, remember=form.remember_me.data)
            next_page = request.args.get("next")
            response = redirect(next_page) if next_page else redirect(
                url_for('users.dashboard'))
            flash("Login Successfull.", "success")
            return response
        else:
            flash("Login Failed! Please Check Email and Password.", "danger")
    return render_template("users/login.html", form=form)


@users.route("/register", methods=["GET", "POST"])
def register_user():
    if current_user.is_authenticated:
        return redirect(url_for('users.dashboard'))
    form = RegisterForm()
    if form.validate_on_submit():
        # Generating token
        generated_token_for_email = generate_token(6)
        # Hashing
        hashed_password = bcrypt.generate_password_hash(
            form.password.data).decode("utf-8")
        hashed_token = bcrypt.generate_password_hash(
            generated_token_for_email).decode("utf-8")
        user = User(form.email.data, hashed_password,
                    form.full_name.data, form.passport.data)
        db.session.add(user)
        db.session.commit()
        # Sending email
        send_mail(user.email, "Email Verification Code",
                  f"Your Token is {generated_token_for_email}")
        fetched_user = User.query.filter_by(id=user.id).first()
        flash(f"Account created for {user.full_name}", "success")
        return redirect(url_for("users.login_user"))
    return render_template("users/register.html", form=form)


@users.route("/", methods=["GET", "POST"])
def dashboard():
    return render_template("mains/homepage.html")


@users.route("/logout")
@login_required
def logout_user():
    logout_user_function()
    return redirect(url_for("users.login_user"))

@users.route("/forget_password", methods=["GET", "POST"])
def forget_password():
    if current_user.is_authenticated:
        return redirect(url_for('mains.homepage'))
    form = ForgetPasswordForm()
    if form.validate_on_submit():
        # Fetching the user
        user = User.query.filter_by(email=form.email.data).first()
        # Sending email
        send_mail(user.email, "Password Reset Token",
                  password_reset_key_mail_body(user.id, user.get_reset_token(), int(os.getenv("EXPIRE_TIME"))))
        flash(f"Check your email to continue.", "primary")
        return redirect(url_for('users.login_user'))
    return render_template("users/forget_password.html", form=form)

@users.route("/reset_password/<int:id>/<string:token>", methods=["GET", "POST"])
def reset_password(id: int, token: str):
    if current_user.is_authenticated:
        return redirect(url_for('mains.homepage'))
    # Verifying the token
    veridication_result = User.verify_reset_key(
        id, token, int(os.getenv("EXPIRE_TIME")))
    if not veridication_result["is_authenticate"]:
        return render_template("mains/errors.html", status=400, message=f"{veridication_result['message']}")
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(
            form.password.data).decode("utf-8")
        user = User.query.get(id)
        user.password = hashed_password
        db.session.commit()
        flash(f"{veridication_result['message']}", "success")
        return redirect(url_for("users.login_user"))
    return render_template("users/reset_password.html", form=form)
