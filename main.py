from app.template_msg import disaster_warning_msg
from datetime import datetime
import os, config, sys


if __name__ == "__main__":
    today = datetime.today().strftime('%Y%m%d')
    print('[{}] '.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')), end='', flush=True)
    # 程序锁，防止同时运行
    if os.path.exists(config.lock_file):
        print("it's runing.")
        sys.exit(-1)

    open(config.lock_file, 'a').close()

    msg_file = None
    for file in os.listdir(config.msg_path):
        if today in file:
            msg_file = file
            break

    if msg_file:
        msg_file = os.path.join(config.msg_path, msg_file)
        send_cnt = disaster_warning_msg(msg_file)
        print("msg has been sent: ", msg_file, send_cnt)
        if send_cnt > 0:
            os.remove(msg_file)
    else:
        print("nothing to do")

    os.remove(config.lock_file)

