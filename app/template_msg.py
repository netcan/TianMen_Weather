from app.weixin import wx
from app import config
import re


def disaster_warning_msg(msg_file):
    # templates = wx.get_templates()
    templates = {}
    with open(msg_file) as f:
        msg = ''.join(f.readlines()).strip()

    unit, time, signal, msg = re.findall('([^\d]*)(\d+.*)发布(.*):(.*)', msg)[0]
    signal_color = None

    for n, c in config.template_colors.items():
        if n in signal:
            signal_color = c
            break

    template_arg = wx.build_template_data(templates[config.disaster_warning_template_id],
                                          first=(signal + '\n', signal_color),
                                          keyword1=(unit, config.template_font_color),
                                          keyword2=(time, config.template_font_color),
                                          keyword3=(msg, config.template_font_color)
                                          )
    # print(template_arg)
    return wx.send_template(config.disaster_warning_template_id, template_arg)


def disaster_warning_txt(txt_file):
    with open(txt_file) as f:
        txt_content = f.readlines()

    unit = re.findall('\S+', txt_content[2])[0].strip()
    signal = txt_content[4].strip() + '\n'
    time = re.findall('发布时间：(.*)', txt_content[-1])[0].strip()
    fangyu_line = 0

    for idx, f in enumerate(txt_content):
        if '防御指南:' in f:
            fangyu_line = idx
            break
    msg = ''.join(txt_content[5:fangyu_line]).strip()
    fangyu = '防御指南：\n' + ''.join(txt_content[fangyu_line+1:-2]).strip()
    signal_color = None
    for n, c in config.template_colors.items():
        if n in signal:
            signal_color = c
            break

