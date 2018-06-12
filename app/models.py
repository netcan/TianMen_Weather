from app import db

templates = db.Table('templates_users',
                     db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
                     db.Column('template_id', db.Integer, db.ForeignKey('template.id'), primary_key=True)
                     )


class Token(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    access_token = db.Column(db.String(512))
    expires_in = db.Column(db.Integer)
    timestamp = db.Column(db.Integer)

    def __repr__(self):
        return '<Token %r>' % self.access_token


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    open_id = db.Column(db.String(120), unique=True) # openid
    templates = db.relationship('Template',
                                secondary=templates,
                                lazy='subquery',
                                backref=db.backref('users', lazy=True))

    def __repr__(self):
        return '<User %r>' % self.open_id


class Template(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.String(120), unique=True) # template_id
    content = db.Column(db.String(256))

    def __repr__(self):
        return '<Template %r>' % self.template_id
