from app import app, config, db
from app.weixin import WeiXin, Message, wx
from app.models import Manager, Template, Template_Task
from functools import wraps
from flask import request, session, render_template, redirect, url_for
from datetime import datetime
import json


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
    return s.replace("\n", "<br/>")


@app.template_filter('ts2time')
def ts2time(s):
    return datetime.fromtimestamp(s).strftime('%Y-%m-%d %H:%M:%S')


@app.template_filter('task_status')
def ts2time(s):
    status = [
        'danger', 'info', 'success'
    ]
    status_content = [
        '未发送', '发送中', '已发送'
    ]
    return '<span class="text-{}">{}</span>'.format(
        status[int(s)],
        status_content[int(s)]
    )


@app.template_filter('template_example')
def template_example(s, content):
    data = json.loads(s)
    for k, v in data.items():
        content = content.replace('{{{{{}.DATA}}}}'.format(k),
                                  '<font color={}>{}</font>'.format(v['color'], v['value']) if v else '')
    return content


@app.route('/admin/template-message', methods=["GET", "POST"])
@login_required
def template_msg():
    return render_template('template_msg.html', templates=wx.get_templates())


@app.route('/admin/template-message/task/',
           methods=["GET"])
@login_required
def template_msg_task_list():
    return render_template('template_msg_task_list.html',
                           tasks=Template_Task.query.order_by(Template_Task.create_at.desc()).all())


@app.route('/admin/template-message/task/<template_id>',
           methods=["GET", "POST"])
@login_required
def template_msg_add_task(template_id=None):
    if not template_id:
        return redirect(url_for('template_msg'))

    template = Template.query.filter_by(template_id=template_id).first()
    if template is None:
        return redirect(url_for('template_msg'))

    keys = WeiXin.extract_template_keys(template.content)
    if request.method == "GET":
        return render_template('template_msg_task.html',
                               template=template,
                               template_id=template_id,
                               keys=keys)
    elif request.method == "POST":
        # print(request.form)
        kwargs = {}
        for k, v in request.form.items():
            if v and v.strip():
                v = v.strip()
                for color, cvalue in config.template_colors.items():
                    if color in v:
                        kwargs[k] = (v, cvalue)
                        break
                if k not in kwargs:
                    kwargs[k] = (v, config.template_font_color)
        task = Template_Task(data=json.dumps(WeiXin.build_template_data(template.content, **kwargs)))
        task.template = template
        db.session.add(task)
        db.session.commit()
        return redirect(url_for('template_msg_task_list'))


@app.route('/admin', methods=["GET"])
@login_required
def admin():
    return redirect(url_for('template_msg'))


@app.route('/admin/login', methods=["GET", "POST"])
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

