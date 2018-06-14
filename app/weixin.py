from functools import wraps
from app.models import Token, Template, User, Status
from app import db, config
from collections import namedtuple
import requests, json, hashlib, re
import time
import xml.etree.ElementTree as ET


def access_token_required(func):
    @wraps(func)
    def wrapper(wx, *args, **kwargs):
        wx.get_token()
        try:
            ret = func(wx, *args, **kwargs)
        except KeyError: # access_token is invalid or not latest, retry
            wx.get_token(True)
            ret = func(wx, *args, **kwargs)
        return ret
    return wrapper


class Message:
    # 处理XML信息
    def __init__(self, xml):
        root = ET.fromstring(xml)
        for child in root:
            setattr(self, child.tag, child.text)
        if not hasattr(self, 'Content'):
            self.Content = ''

    # 回复用
    def __repr__(self):
        return '<xml> <ToUserName><![CDATA[{}]]></ToUserName> <FromUserName><![CDATA[{}]]></FromUserName>' \
               '<CreateTime>{}</CreateTime> <MsgType><![CDATA[text]]></MsgType> <Content><![CDATA[{}]]>' \
               '</Content> </xml> '.format(getattr(self, 'FromUserName', None),
                                             getattr(self, 'ToUserName', None),
                                             int(time.time()),
                                             getattr(self, 'Content', None))


class WeiXin:
    def __init__(self):
        self.appid = config.appid
        self.appsecret = config.appsecret
        self.token = Token.query.first()

        self.menu = config.Menu.menu

    @staticmethod
    def auth(request):
        my_signature = request.args.get('signature', '')
        my_timestamp = request.args.get('timestamp', '')
        my_nonce = request.args.get('nonce', '')

        data = [config.token, my_timestamp, my_nonce]
        data.sort()

        mysignature = hashlib.sha1(''.join(data).encode()).hexdigest()
        return True if my_signature == mysignature else False

    def get_token(self, update=False):
        if self.token:
            self.token = db.session.merge(self.token)
        if self.token is None or update or self.token.expires_in + self.token.timestamp <= int(time.time()) + 10:
            data = dict(
                grant_type='client_credential',
                appid=self.appid,
                secret=self.appsecret
            )
            res = requests.get('https://api.weixin.qq.com/cgi-bin/token', data).json()
            try:
                if self.token is None:
                    token = Token(access_token=res["access_token"],
                                  expires_in=res["expires_in"],
                                  timestamp=int(time.time()))
                    self.token = token
                    db.session.add(token)
                else: # update
                    self.token.access_token = res["access_token"]
                    self.token.expires_in = res["expires_in"]
                    self.token.timestamp = int(time.time())

                db.session.commit()
            except KeyError:
                print(res)

    @access_token_required
    def get_templates(self, update=False):
        Templte = namedtuple('Template', ['title', 'content', 'industry'])
        if update or Template.query.count() == 0:
            res = requests.get('https://api.weixin.qq.com/cgi-bin/template/get_all_private_template', dict(
                access_token=self.token.access_token
            )).json()
            for template_item in res["template_list"]:
                template = Template.query.filter_by(template_id=template_item["template_id"]).first()
                if template is None:
                    template = Template(template_id=template_item['template_id'],
                                        content=template_item['content'],
                                        title=template_item['title'],
                                        industry='{} - {}'.format(template_item["primary_industry"],
                                                                  template_item["deputy_industry"]))
                    db.session.add(template)
                else:
                    template.template_id = template_item["template_id"]
                    template.content = template_item["content"]
                    template.title = template_item["title"]
                    template.industry = '{} - {}'.format(template_item["primary_industry"],
                                                         template_item["deputy_industry"])

            db.session.commit()

            return {template['template_id']: Templte(title=template['title'],
                                                     content=template['content'],
                                                     industry='{} - {}'.format(
                                                         template_item["primary_industry"],
                                                         template_item["deputy_industry"]))
                    for template in res['template_list']}
        else:
            return {template.template_id: Templte(title=template.title,
                                                  content=template.content,
                                                  industry=template.industry)
                    for template in Template.query.all()}

    @access_token_required
    def get_users(self, update=False):
        if update or User.query.count() == 0:
            res = requests.post('https://api.weixin.qq.com/cgi-bin/user/get', params=dict(
                access_token=self.token.access_token
            )).json()
            users_openid = res["data"]["openid"]
            while res["count"] < res["total"]:
                res = requests.get('https://api.weixin.qq.com/cgi-bin/user/get', params=dict(
                    access_token=self.token.access_token,
                    next_openid=users_openid[-1]
                )).json()
                users_openid.extend(res["data"]["openid"])

            for uid in users_openid:
                if User.query.filter_by(open_id=uid).first() is None:
                    user = User(open_id=uid)
                    db.session.add(user)
            db.session.commit()
            return users_openid
        else:
            return [user.open_id for user in User.query.all()]


    @access_token_required
    def get_tags(self):
        # 获取所有标签
        res = requests.get('https://api.weixin.qq.com/cgi-bin/tags/get', params=dict(
            access_token=self.token.access_token
        )).json()
        # print(res)
        return {
            tag["name"]: tag["id"] for tag in res["tags"]
        }

    @access_token_required
    def get_user_info(self, openid):
        res = requests.get('https://api.weixin.qq.com/cgi-bin/user/info', params=dict(
            access_token=self.token.access_token,
            openid=openid
        )).json()
        return res if 'errcode' not in res else None

    @access_token_required
    def batch_get_user_info(self, users_openid, max_cnt=100):
        user_info_list = []
        for i in range(0, len(users_openid), max_cnt):
            users_list = [{"openid": u}
                          for u in users_openid[i:i+max_cnt]]

            res = requests.post('https://api.weixin.qq.com/cgi-bin/user/info/batchget', params=dict(
                access_token=self.token.access_token,
            ), data=json.dumps({
                "user_list": users_list
            })).json()
            user_info_list.extend(res["user_info_list"])
        return user_info_list

    def update_user_info(self):
        update_status = Status.query.get('users_update_status')
        if update_status is None:
            update_status = Status(key='users_update_status', value="0")
            db.session.add(update_status)
            db.session.commit()
        if int(update_status.value):  # 更新中
            return

        update_status.value = "1"
        db.session.commit()

        # user_count = User.query.count()
        self.get_users(True) # fetch from api
        for idx, info in enumerate(self.batch_get_user_info(self.get_users())): # fetch from database
            user = User.query.filter_by(open_id=info["openid"]).first()
            if info is None or info['subscribe'] == 0: # 信息不存在、或者未关注
                db.session.delete(user)
                continue
            column = ['nickname', 'sex', 'city',
                      'country', 'province', 'headimgurl',
                      'subscribe_time', 'subscribe_scene']
            for col in column:
                setattr(user, col, str(info[col]).strip())
            # print('{}/{}'.format(idx+1, user_count))

        update_status.value = "0"
        db.session.commit()

    @access_token_required
    def get_openid_by_tag(self, tagid):
        # 获取标签下的用户
        res = requests.post('https://api.weixin.qq.com/cgi-bin/user/tag/get', params=dict(
            access_token=self.token.access_token
        ), data=json.dumps({
            "tagid": tagid,
            "next_openid": None
        })).json()
        return res["data"]["openid"]

    @access_token_required
    def put_openid_to_template(self, open_id, template_id):
        # 将用户放到模板消息发送列表中
        user = User.query.filter_by(open_id=open_id).first()
        if user is None:
            user = User(open_id=open_id)
            db.session.add(user)
        template = Template.query.filter_by(template_id=template_id).first()
        user.templates.append(template)
        db.session.commit()

    @access_token_required
    def delete_openid_from_template(self, open_id, template_id):
        user = User.query.filter_by(open_id=open_id).first()
        if user is None:
            return
        template = Template.query.filter_by(template_id=template_id).first()
        try:
            user.templates.remove(template)
            db.session.commit()
        except:
            db.session.rollback()

    @access_token_required
    def put_tag_openid_to_template(self, tagid, template_id):
        # 将标签下的用户进行模板消息提醒，手动调用
        users = self.get_openid_by_tag(tagid)
        template = Template.query.filter_by(template_id=template_id).first()
        for uid in users:
            user = User.query.filter_by(open_id=uid).first()
            template.users.append(user)
        db.session.commit()


    @staticmethod
    def extract_template_keys(template_content):
        return re.findall('{{\s*(.+?).DATA\s*}}', template_content)

    @staticmethod
    def build_template_data(template_content, **kwargs):
        return {
            arg: {
                "value": kwargs[arg][0],
                "color": kwargs[arg][1]
            } if arg in kwargs else None
            for arg in WeiXin.extract_template_keys(template_content)
        }

    @access_token_required
    def send_template_to_openid(self, template_id, template_args, openid, **kwargs):
        # 将模板推送至openid用户
        # kwargs附加参数，例如设置颜色
        data = {
            "touser": openid,
            "template_id": template_id,
            "data": template_args
        }
        data.update(kwargs)
        res = requests.post('https://api.weixin.qq.com/cgi-bin/message/template/send', params=dict(
            access_token=self.token.access_token
        ), data=json.dumps(data)).json()
        # print(data)
        return res["errcode"] == 0

    @access_token_required
    def send_template(self, template_id, template_args, **kwargs):
        cnt = 0
        template = Template.query.filter_by(template_id=template_id).first()
        db.session.refresh(template)
        for user in template.users:
            cnt += self.send_template_to_openid(template_id, template_args, user.open_id, **kwargs)
        return cnt

    @access_token_required
    def create_menu(self):
        # 手动调用
        res = requests.post('https://api.weixin.qq.com/cgi-bin/menu/create?access_token', params=dict(
            access_token=self.token.access_token
        ), data=json.dumps(self.menu, ensure_ascii=False).encode('utf-8')).json()
        print(res)
        return res["errcode"] == 0

wx = WeiXin()
