from app import app, request, config
from app.weixin import WeiXin, Message, wx


@app.route('/wx', methods=["GET", "POST"])
def index():
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


@app.route('/test', methods=["GET"])
def test():
    return 'test'

