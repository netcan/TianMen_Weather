from app import app, config, db
from app.weixin import WeiXin, Message, wx
from app.models import Manager, Template, Template_Task, User, Status
from functools import wraps
from flask import request, session, render_template, redirect, url_for
from datetime import datetime
import time, json, threading


TEMPLATE_MSG_PREPARE, TEMPLATE_MSG_SENDING, TEMPLATE_MSG_SENT = range(3)
TEMPLATE_ARG_TEXT, TEMPLATE_ARG_DATETIME, TEMPLATE_ARG_SELECT = range(3)


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
                m.Content = '定制灾害预警请输入1\n定制每日天气预报请输入2\n取消定制所有服务请输入TD'
                return str(m)
            elif m.Content.strip() == '1':
                wx.put_openid_to_template(open_id, config.disaster_warning_template_id)
                m.Content = '已定制灾害预警服务'
                return str(m)
            elif m.Content.strip().lower() == 'td':
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
    return s.replace("\n", "<br/>") if s is not None else ''


@app.template_filter('ts2time')
def ts2time(s):
    return datetime.fromtimestamp(s).strftime('%Y-%m-%d %H:%M:%S') if s is not None else ''


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
    ) if s is not None else ''


@app.template_filter('sex')
def sex(s):
    return User.SEX_VALUE[int(s)] if s is not None else ''


@app.template_filter('subscribe_scene')
def subscribe_scene(s):
    return User.SUBSCRIBE_SCENE_VALUE[s] if s is not None else ''


@app.template_filter('template_example')
def template_example(s, content):
    data = json.loads(s)
    for k, v in data.items():
        content = content.replace('{{{{{}.DATA}}}}'.format(k),
                                  '<font color={}>{}</font>'.format(v['color'], v['value']) if v else '')
    return content


@app.template_filter('template_arg_select')
def template_arg_select(s):
    if not s: return ''
    ret = ''
    for o in s.split(' '):
        ret += '<option value="{}">{}</option>'.format(o, o)
    return ret


@app.route('/admin/template-message', methods=["GET", "POST"])
@login_required
def template_msg():
    update_status = Status.query.get('templates_update_status')
    update_status = False if update_status is None \
        else int(update_status.value)

    return render_template('template_msg.html', templates=Template.query.all(), update_status=update_status)


@app.route('/admin/template-message/refresh/',
           methods=["GET"])
@login_required
def template_msg_refresh():
    threading.Thread(target=wx.update_templates).start()
    return redirect(request.referrer or url_for('template_msg'))


@app.route('/admin/template-message/task/',
           methods=["GET"])
@login_required
def template_msg_task_list():
    return render_template('template_msg_task_list.html',
                           tasks=Template_Task.query.order_by(Template_Task.create_at.desc()).all())




@app.route('/admin/template-message/task/<int:task_id>/delete',
           methods=["GET"])
@login_required
def template_msg_task_delete(task_id):
    task = Template_Task.query.get(task_id)
    if task is None:
        return redirect(url_for('template_msg_task_list'))
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for('template_msg_task_list'))


@app.route('/admin/template-message/task/<int:task_id>/edit',
           methods=["GET", "POST"])
@login_required
def template_msg_task_edit(task_id):
    task = Template_Task.query.get(task_id)
    if task is None:
        return redirect(url_for('template_msg_task_list'))

    if request.method == 'GET':
        keys = WeiXin.extract_template_keys(task.template.content)
        data = json.loads(task.data)
        return render_template('template_msg_task.html',
                               template=task.template,
                               config=json.loads(task.template.config) if task.template.config else None,
                               keys=keys,
                               data=data,
                               )
    elif request.method == 'POST':
        kwargs = get_template_data_from_request(request)
        if task.status == 0:
            task.last_updated = int(time.time())
            task.data = json.dumps(WeiXin.build_template_data(task.template.content, **kwargs))
        else:
            new_task = Template_Task(
                data=json.dumps(WeiXin.build_template_data(task.template.content, **kwargs))
            )
            new_task.template = task.template
            db.session.add(new_task)

        db.session.commit()
        return redirect(url_for('template_msg_task_list'))


@app.route('/admin/template-message/task/<int:task_id>/send',
           methods=["GET"])
@login_required
def template_msg_task_send(task_id):
    task = Template_Task.query.get(task_id)
    if task is None or task.status != TEMPLATE_MSG_PREPARE:
        return redirect(url_for('template_msg_task_list'))

    task.status = TEMPLATE_MSG_SENDING # 发送中
    db.session.commit()
    db.session.expire(task)

    def sending(task):
        task = db.session.merge(task)
        task.success = wx.send_template(task.template.template_id, json.loads(task.data))
        task.status = TEMPLATE_MSG_SENT # 已发送
        db.session.commit()

    threading.Thread(target=sending, args=(task, )).start()

    return redirect(url_for('template_msg_task_list'))


def get_template_data_from_request(request):
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
    return kwargs


def get_template_config_from_request(request):
    config = {}
    for k, v in request.form.items():
        if len(k.split('-')) != 2:
            continue
        key, typ = k.split('-')
        if key not in config:
            config[key] = {'name': key, 'type': TEMPLATE_ARG_TEXT, 'value': ''}

        if v and v.strip():
            config[key][typ] = v.strip()
    return config




@app.route('/admin/template-message/users/<template_id>/')
@login_required
def template_msg_users(template_id=None):
    if not template_id:
        return redirect(url_for('template_msg'))
    template = Template.query.filter_by(template_id=template_id).first()
    if template is None:
        return redirect(url_for('template_msg'))
    users_update_status = Status.query.get('users_update_status')
    users_update_status = False if users_update_status is None \
        else int(users_update_status.value)

    return render_template("users_list.html", users=template.users,
                           users_update_status=users_update_status,
                           title=template.title)


@app.route('/admin/template-message/config/<template_id>/',
           methods=["GET", "POST"])
@login_required
def template_msg_config(template_id=None):
    if not template_id:
        return redirect(url_for('template_msg'))
    template = Template.query.filter_by(template_id=template_id).first()
    if template is None:
        return redirect(url_for('template_msg'))
    keys = WeiXin.extract_template_keys(template.content)

    if request.method == "GET":
        return render_template('template_msg_config.html',
                               template=template,
                               config=json.loads(template.config) if template.config else None,
                               keys=keys)
    elif request.method == "POST":
        config = get_template_config_from_request(request)
        template.config = json.dumps(config)
        db.session.commit()
        return redirect(url_for('template_msg'))


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
                               config=json.loads(template.config) if template.config else None,
                               keys=keys)
    elif request.method == "POST":
        # print(request.form)
        kwargs = get_template_data_from_request(request)
        task = Template_Task(data=json.dumps(WeiXin.build_template_data(template.content, **kwargs)))
        task.template = template
        db.session.add(task)
        db.session.commit()
        return redirect(url_for('template_msg_task_list'))


@app.route('/admin/users')
@login_required
def users():
    users_update_status = Status.query.get('users_update_status')
    users_update_status = False if users_update_status is None \
        else int(users_update_status.value)
    return render_template("users_list.html", users=User.query.all(),
                           users_update_status=users_update_status)


@app.route('/admin/users/refresh')
@login_required
def users_refresh():
    threading.Thread(target=wx.update_user_info).start()
    return redirect(request.referrer or url_for('users'))


@app.route('/admin', methods=["GET"])
@login_required
def admin():
    return redirect(url_for('template_msg'))


@app.route('/admin/logout', methods=["GET"])
def logout():
    if session.get('username'):
        session.pop('username')
    return redirect(url_for('admin'))


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

