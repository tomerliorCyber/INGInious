# -*- coding: utf-8 -*-
#
# This file is part of INGInious. See the LICENSE and the COPYRIGHTS files for
# more information about the licensing of this file.
#
# This code is based on Flask-Session, copyright (c) 2014 by Shipeng Feng.
# https://flasksession.readthedocs.io/

import re
from datetime import datetime
from bson.objectid import ObjectId

try:
    import cPickle as pickle
except ImportError:
    import pickle

from itsdangerous import Signer, BadSignature, want_bytes
from flask.sessions import SessionMixin
from werkzeug.datastructures import CallbackDict
from flask.sessions import SessionInterface
from werkzeug.exceptions import HTTPException
from inginious.frontend.pages.lti import LTILaunchPage


class MongoDBSession(CallbackDict, SessionMixin):
    """Baseclass for server-side based sessions."""

    def __init__(self, initial=None, sid=None, permanent=None, cookieless=False):
        def on_update(self):
            self.modified = True
        CallbackDict.__init__(self, initial, on_update)
        self.sid = sid
        self.modified = False
        self.cookieless = cookieless
        if permanent:
            self.permanent = permanent


class MongoDBSessionInterface(SessionInterface):
    """A Session interface that uses mongodb as backend.
    :param client: A ``pymongo.MongoClient`` instance.
    :param db: The database you want to use.
    :param collection: The collection you want to use.
    :param use_signer: Whether to sign the session id cookie or not.
    :param permanent: Whether to use permanent session or not.
    """

    serializer = pickle
    session_class = MongoDBSession

    def __init__(self, client, db, collection, use_signer=False,
                 permanent=True):
        self.client = client
        self.store = client[db][collection]
        self.store.create_index('expiration')  # ensure index
        self.use_signer = use_signer
        self.permanent = permanent

    def _generate_sid(self):
        return str(ObjectId())

    def _get_signer(self, app):
        if not app.secret_key:
            return None
        return Signer(app.secret_key, salt='flask-session',
                      key_derivation='hmac')

    def open_session(self, app, request):
        # Check for cookieless session in the path
        path_session = re.match(r"(/@)([a-f0-9A-F_]*)(@)", request.path)

        # Check if currently accessed URL is LTI launch page
        try:
            # request.url_rule is not set yet here.
            endpoint, _ = app.create_url_adapter(request).match()
            is_lti_launch = endpoint == LTILaunchPage.endpoint
        except HTTPException:
            is_lti_launch = False

        if path_session:  # Cookieless session
            cookieless = True
            sid = path_session.group(2)
        elif is_lti_launch:
            cookieless = True
            sid = None
        else:
            cookieless = False
            sid = request.cookies.get(app.session_cookie_name)

        if not sid:
            sid = self._generate_sid()
            return self.session_class(sid=sid, permanent=self.permanent, cookieless=cookieless)
        if not path_session and self.use_signer:
            signer = self._get_signer(app)
            if signer is None:
                return None
            try:
                sid_as_bytes = signer.unsign(sid)
                sid = sid_as_bytes.decode()
            except BadSignature:
                sid = self._generate_sid()
                return self.session_class(sid=sid, permanent=self.permanent, cookieless=cookieless)

        store_id = sid
        document = self.store.find_one({'_id': store_id})
        if document and document.get('expiration') <= datetime.utcnow():
            # Delete expired session
            self.store.delete_one({'_id': store_id})
            document = None
        if document is not None:
            try:
                val = document['data']
                data = self.serializer.loads(want_bytes(val))
                return self.session_class(data, sid=sid, cookieless=cookieless)
            except:
                return self.session_class(sid=sid, permanent=self.permanent, cookieless=cookieless)
        return self.session_class(sid=sid, permanent=self.permanent, cookieless=cookieless)

    def save_session(self, app, session, response):
        domain = self.get_cookie_domain(app)
        path = self.get_cookie_path(app)
        store_id = session.sid
        if not session:
            if session.modified:
                self.store.delete_one({'_id': store_id})
                response.delete_cookie(app.session_cookie_name,
                                       domain=domain, path=path)
            return

        httponly = self.get_cookie_httponly(app)
        secure = self.get_cookie_secure(app)
        expires = self.get_expiration_time(app, session)
        cookieless = session.cookieless
        val = self.serializer.dumps(dict(session))
        self.store.update_one({'_id': store_id},
                              {"$set": {'data': val, 'expiration': expires, 'cookieless': cookieless}},
                              upsert=True)
        if self.use_signer:
            session_id = self._get_signer(app).sign(want_bytes(session.sid))
        else:
            session_id = session.sid
        if not cookieless:
            response.set_cookie(app.session_cookie_name, session_id,
                                expires=expires, httponly=httponly,
                                domain=domain, path=path, secure=secure)
