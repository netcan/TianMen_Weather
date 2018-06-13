from app import app, config
from app.weixin import WeiXin, Message, wx
from app.models import Manager
from functools import wraps
from flask import request, session, render_template, redirect, url_for


@app.route('/wx', methods=["GET", "POST"])
def weixin():
    if WeiXin.auth(request):
        if request.method == "GET":
            return request.args.get('echostr')
        elif request.method == "POST":
            open_id=request.args.get('openid')
            # print(request.data)

            m = Message(request.data.decode('utf8'))
            if getattr(m, 'MsgType', None) == 'event' and getattr(m, 'EventKey', None) == 'subscribe':
                m.Content = '定制灾害预警请输入1\n定制每日天气预报请输入2\n取消定制所有服务请输入9'
                return str(m)
            elif m.Content.strip() == '1':
                wx.put_openid_to_template(open_id, config.disaster_warning_template_id)
                m.Content = '已定制灾害预警服务'
                return str(m)
            elif m.Content.strip() == '9':
                wx.delete_openid_from_template(open_id, config.disaster_warning_template_id)
                m.Content = '已取消订阅所有服务'
                return str(m)

            return 'success'
    else:
        return '', 401


def login_required(func):
    """ 登陆检查装饰器 """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get('username'):
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    return wrapper


@app.template_filter('nl2br')
def nl2br(s):
    return s.replace("\n", "<br />")


@app.route('/admin/template-message', methods=["GET", "POST"])
@login_required
def template_msg():
    return render_template('template_msg.html', templates=wx.get_templates())


@app.route('/admin/template-message/task/')
@app.route('/admin/template-message/task/<template_id>',
           methods=["GET", "POST"])
@login_required
def template_msg_task(template_id=None):
    templates = wx.get_templates()
    if not template_id or template_id not in templates:
        return redirect(url_for('template_msg'))

    keys = WeiXin.extract_template_keys(templates[template_id].content)
    if request.method == "GET":
        return render_template('template_msg_task.html',
                               template=templates[template_id],
                               template_id=template_id,
                               keys=keys)
    elif request.method == "POST":
        print(request.form)
        return 'success'


@app.route('/admin', methods=["GET"])
@login_required
def admin():
    return redirect(url_for('template_msg'))


@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template('login.html')
    elif request.method == "POST":
        username = request.form.get('username', None)
        password = request.form.get('password', None)
        if username and password:
            user = Manager.query.filter_by(username=username).first()
            if user and user.check_password(password):
                session['username'] = username
                return redirect(url_for('admin'))

        error = '无效的用户名/密码'
        return render_template('login.html', error=error)

