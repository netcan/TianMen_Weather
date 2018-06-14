from app import db
import time
from werkzeug.security import generate_password_hash, check_password_hash

templates = db.Table('templates_users',
                     db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
                     db.Column('template_id', db.Integer, db.ForeignKey('template.id'), primary_key=True)
                     )


class Status(db.Model): # 存放内部状态，kv数据库
    key = db.Column(db.String(32), primary_key=True, nullable=False)
    value = db.Column(db.Text, nullable=False)


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
    SEX_VALUE = ['未知', '男', '女']
    SUBSCRIBE_SCENE_VALUE = {
        'ADD_SCENE_SEARCH': '公众号搜索',
        'ADD_SCENE_ACCOUNT_MIGRATION': '公众号迁移',
        'ADD_SCENE_PROFILE_CARD': '名片分享',
        'ADD_SCENE_QR_CODE': '扫描二维码',
        'ADD_SCENE_PROFILE_LINK': '图文页内名称点击',
        'ADD_SCENE_PROFILE_ITEM': '图文页右上角菜单',
        'ADD_SCENE_PAID': '支付后关注',
        'ADD_SCENE_OTHERS': '其他'
    }

    id = db.Column(db.Integer, primary_key=True)
    open_id = db.Column(db.String(120), unique=True, index=True) # openid
    nickname = db.Column(db.String(64)) # 用户名
    sex = db.Column(db.String(10)) # 性别，值为1时是男性，值为2时是女性，值为0时是未知
    city = db.Column(db.String(64)) # 城市
    country = db.Column(db.String(64)) # 国家
    province = db.Column(db.String(64)) # 省份
    headimgurl = db.Column(db.String(120)) # 头像
    subscribe_time = db.Column(db.Integer) # 关注的时间
    subscribe_scene = db.Column(db.String(64)) # 关注的渠道来源

    templates = db.relationship('Template',
                                secondary=templates,
                                lazy='subquery',
                                backref=db.backref('users', lazy=True))

    def __repr__(self):
        return '<User %r>' % self.nickname


class Template(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.String(120), unique=True, index=True) # template_id
    content = db.Column(db.String(256))
    title = db.Column(db.String(120)) # 模板标题
    industry = db.Column(db.String(120)) # 行业

    def __repr__(self):
        return '<Template %r>' % self.template_id


class Template_Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    create_at = db.Column(db.Integer, default=int(time.time()))
    last_updated = db.Column(db.Integer, default=int(time.time()))
    success = db.Column(db.Integer, default=0)
    status = db.Column(db.Integer, default=False) # 0 未发送，1发送中，2已发送
    data = db.Column(db.Text)
    template_id = db.Column(db.Integer, db.ForeignKey('template.id'), nullable=False)
    template = db.relationship('Template', backref=db.backref('tasks', lazy=True))

