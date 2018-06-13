from app import db
from werkzeug.security import generate_password_hash, check_password_hash

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


class Manager(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, index=True) # username
    password = db.Column(db.String(120), nullable=False)

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    open_id = db.Column(db.String(120), unique=True, index=True) # openid
    templates = db.relationship('Template',
                                secondary=templates,
                                lazy='subquery',
                                backref=db.backref('users', lazy=True))

    def __repr__(self):
        return '<User %r>' % self.open_id


class Template(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.String(120), unique=True, index=True) # template_id
    content = db.Column(db.String(256))
    title = db.Column(db.String(120)) # 模板标题
    industry = db.Column(db.String(120)) # 行业

    def __repr__(self):
        return '<Template %r>' % self.template_id
