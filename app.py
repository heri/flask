#!/usr/bin/env python
from functools import partial
import json
from operator import attrgetter
import os
from random import randint
import sys
from email.utils import formatdate

import flask
from flask import Flask, request, render_template, make_response, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.ext import baked

if sys.version_info[0] == 3:
    xrange = range

_is_pypy = hasattr(sys, 'pypy_version_info')

DBDRIVER = 'mysql+pymysql' if _is_pypy else 'mysql'  # mysqlclient is slow on PyPy
DBHOST = 'tfb-database'


# setup

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DBDRIVER + '://heri:pass@%s:3306/users?charset=utf8' % DBHOST
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
db = SQLAlchemy(app)
dbraw_engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'], connect_args={'autocommit': True}, pool_reset_on_return=None)

bakery = baked.bakery()


# models

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.String, primary_key=True)
    firstName = db.Column(db.String)
    lastName = db.Column(db.String)

    # http://stackoverflow.com/questions/7102754/jsonify-a-sqlalchemy-result-set-in-flask
    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'id'         : self.id,
            'firstName': self.firstName,
            'lastName': self.lastName,
        }

    @staticmethod
    def get(ident):
        baked_query = bakery(lambda s: s.query(User))
        return baked_query(db.session()).get(ident)

# flask.jsonify doesn't allow array at top level for security concern.
# So we should have oriiginal one.
def json_response(obj):
    res = make_response(json.dumps(obj))
    res.mimetype = "application/json"
    return add_date_header(res)


def add_date_header(res):
    res.headers['Date'] = formatdate(timeval=None, localtime=False, usegmt=True)
    return res
    
@app.route("/users")
def get_Users():
    users = list(User.query.all())
    users.sort(key=attrgetter('id'))
    return add_date_header(make_response(render_template('users.html', Users=users)))

@app.route("/webhook")
def update():
    connection = dbraw_engine.connect()
    try:
        id = request.args.get('id')
        firstName = request.args.get('firstName')
        lastName = request.args.get('lastName')

        user = connection.execute("UPDATE Users SET firstName=%s, lastName=%s WHERE id=%s", (firstName, lastName, id))
        return json_response(user)
    finally:
        connection.close()


try:
    import meinheld
    meinheld.server.set_access_logger(None)
    meinheld.set_keepalive(120)
except ImportError:
    pass

# entry point for debugging
if __name__ == "__main__":
    app.run(debug=True)
