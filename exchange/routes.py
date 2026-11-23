"""HTML pages for the wallet, a new transaction, and the chain."""

from flask import Blueprint, render_template

pages = Blueprint("pages", __name__)


@pages.get("/")
def wallet():
    return render_template("wallet.html", page="wallet")


@pages.get("/transaction/new")
def new_transaction():
    return render_template("new_transaction.html", page="new")


@pages.get("/transaction/view")
def view_transaction():
    return render_template("view_transaction.html", page="chain")
