
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pprint import pprint
from loguru import logger
import httpx
import os

# 夸克
kps = os.getenv("QUARK_KPS")
sign = os.getenv("QUARK_SIGN")
vcode = os.getenv("QUARK_VCODE")

if kps is None or sign is None or vcode is None:
    logger.error("请设置 QUARK_KPS 或者 QUARK_SIGN 或者 QUARK_VCODE")
    raise ValueError("请设置 QUARK_KPS 或者 QUARK_SIGN 或者 QUARK_VCODE")

# Push Plus 通知配置
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "ff015b049b064d1bbf8e064729e90e4e")  # 默认提供的token

config_is_ok = False

if PUSHPLUS_TOKEN:
    config_is_ok = True


def query_balance():
    """
    查询抽奖余额
    """
    url = "https://coral2.quark.cn/currency/v1/queryBalance"
    querystring = {
        "moduleCode": "1f3563d38896438db994f118d4ff53cb",
        "kps": kps,
    }
    response = httpx.get(url=url, params=querystring)
    response.raise_for_status()
    pprint(response.json())


def human_unit(bytes_: int) -> str:
    """
    人类可读单位
    :param bytes_: 字节数
    :return: 返回 MB GB TB
    """
    units = ("MB", "GB", "TB", "PB")
    bytes_ = bytes_ / 1024 / 1024
    i = 0
    while bytes_ >= 1024:
        bytes_ /= 1024
        i += 1
    return f"{bytes_:.2f} {units[i]}"


def send_notification(body: str):
    """使用Push Plus发送通知"""
    if not PUSHPLUS_TOKEN:
        logger.error("Push Plus Token未配置，无法发送通知")
        return
        
    title = "夸克网盘自动签到"
    url = "http://www.pushplus.plus/send"
    
    try:
        params = {
            "token": PUSHPLUS_TOKEN,
            "title": title,
            "content": body
        }
        
        response = httpx.get(url, params=params)
        response.raise_for_status()
        
        result = response.json()
        if result.get("code") == 200:
            logger.info("Push Plus通知发送成功")
        else:
            logger.error(f"Push Plus通知发送失败: {result.get('msg', '未知错误')}")
            
    except Exception as e:
        logger.error(f"发送通知时发生错误: {e}")


def user_info():
    """
    获取用户信息
    :return: None
    """
    url = "https://drive-m.quark.cn/1/clouddrive/capacity/growth/info"
    querystring = {
        "pr": "ucpro",
        "fr": "android",
        "kps": kps,
        "sign": sign,
        "vcode": vcode,
    }
    response = httpx.get(url=url, params=querystring)
    response.raise_for_status()
    content = response.json()
    if content["code"] != 0:
        logger.warning(content["message"])
    else:
        data = content["data"]
        super_vip_exp_at = "未知"
        if not data.get('super_vip_exp_at', None) is None:
            super_vip_exp_at = datetime.fromtimestamp(
                data["super_vip_exp_at"] / 1000
            ).strftime("%Y-%m-%d %H:%M:%S")
        cap_sign = data["cap_sign"]
        notify_message = ""
        if cap_sign["sign_daily"]:
            notify_message += (f"今日已签到，获得容量: {human_unit(cap_sign['sign_daily_reward'])},"
                               f" 签到进度: {cap_sign['sign_progress']}\n")
        notify_message += (f"会员类型：{data['member_type']}, 过期时间：{super_vip_exp_at}, 总计容量："
                           f"{human_unit(data['total_capacity'])}, 使用容量：{human_unit(data['use_capacity'])}, "
                           f"使用百分比：{data['use_capacity'] / data['total_capacity'] * 100:.2f}%")
        logger.info(notify_message)
        if config_is_ok:
            send_notification(notify_message)


def checkin():
    """
    签到
    :return: None
    """
    url = "https://drive-m.quark.cn/1/clouddrive/capacity/growth/sign"
    querystring = {
        "pr": "ucpro",
        "fr": "android",
        "kps": kps,
        "sign": sign,
        "vcode": vcode,
    }
    response = httpx.post(url=url, json={"sign_cyclic": True}, params=querystring)
    if response.status_code == 200:
        if response.json()["code"] != 0:
            logger.warning(response.json()["message"])
        else:
            reward_msg = f"签到成功，获得容量: {human_unit(response.json()['data']['sign_daily_reward'])}"
            logger.success(reward_msg)
            # 发送签到成功通知
            if config_is_ok:
                send_notification(reward_msg)
    else:
        logger.warning(f"已经签到，请勿重复签到")


if __name__ == "__main__":
    checkin()
    user_info()
