# -*- coding: utf-8 -*-
# @Time    : 2019/5/1 21:59
# @Author  : luxblive
# @FileName: send_email.py

# 自动发送邮件
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from email.utils import formataddr


def send_email(subject, content, to_address, from_address, password, if_add_time=True):
    """邮件发送报表信息

    :param subject: 邮件的主题
    :param content: 邮件的内容
    :param to_address: 发送到的邮箱地址
    :param from_address: 发送到的邮箱地址
    :param password: 邮箱的密码
    :param if_add_time: 是否在邮件中加入当前的时间信息
    :return:
    """

    try:
        msg = MIMEMultipart('mixed')
        msg["Subject"] = subject
        msg["From"] = formataddr(["每日数据推送", from_address])
        msg["To"] = formataddr(["定投数据接收", to_address])

        if if_add_time:
            text_plain = MIMEText(datetime.datetime.now().strftime("%m-%d %H:%M:%S") + '\n\n' + content, 'plain',
                                  'utf-8')
        else:
            text_plain = MIMEText(content, 'plain', 'utf-8')
        msg.attach(text_plain)

        username = from_address

        server = smtplib.SMTP_SSL('smtp.163.com', port=465)
        server.login(username, password)
        server.sendmail(from_address, [to_address, ], msg.as_string())
        server.quit()

        print('邮件发送成功')
    except Exception as err:
        print('邮件发送失败', err)
