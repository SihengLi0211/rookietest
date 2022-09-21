#!/usr/bin/env python
#-*- coding: utf-8 -*-
#FILE: main.py
#CREATE_TIME: 2022-09-09
#AUTHOR: Sancho
"""
量化交易策略框架
天勤库的轻量级封装
"""

import sys
import yaml
from tq import Tq
from subscription import Subscription
from tread import Tread


class Engine:
    PLATFORM = sys.platform  # 获取操作系统平台

    @classmethod
    def get_config(cls) -> yaml:
        # 获取配置文件
        _ = '/'
        if cls.PLATFORM.startswith('win'):
            _ = '\\'
        path = f'{sys.path[0]}{_}..{_}..{_}config.yml'
        with open(path, 'r', encoding='utf-8') as f:
            config = yaml.load(f, Loader=yaml.CLoader)
        return config

    def __init__(self) -> None:
        self.config = self.get_config()  # 获取配置文件
        self.tq = self._get_tq_api()  # 登录天勤
        # 订阅合约
        self.subscription = Subscription(self.tq.api)
        self.quotes_dict, self.klines_dict, self.ticks_dict = self._get_subs()
        # 初始化账户
        self.tread = Tread(self.tq.api, self.quotes_dict, self.tq.accounts)
        self.accounts_info = self.tread.accounts_info
        self.positions = self.tread.positions
        self.orders = self.tread.orders

    def _get_tq_api(self):
        # 登录天勤，获取API
        return Tq(self.config['tq_username'], self.config['tq_password'],
                  self.config['type'], self.config['gui'],
                  self.config['balance'], self.config['accounts'])

    def _get_subs(self) -> list:
        # 获取需要订阅的合约，返回订阅的对象
        subs = []
        # quotes
        if quotes := self.config.get('quotes', None):
            subs.append(self.subscription.get_quotes(quotes))
        else:
            subs.append(None)
        # klines
        if klines := self.config.get('klines', None):
            subs.append(
                self.subscription.get_klines(klines, self.config['merge']))
        else:
            subs.append(None)
        # ticks
        if ticks := self.config.get('ticks', None):
            subs.append(self.subscription.get_ticks(ticks))
        else:
            subs.append(None)
        if not any(subs):
            raise "\n请正确传入需要订阅的合约"
        return subs


if __name__ == "__main__":
    e = Engine()
    # 打印订阅信息
    print(f'----quotes----:\n{e.quotes_dict}\n')
    print(f'----klines----:\n{e.klines_dict}\n')
    print(f'----ticks----:\n{e.ticks_dict}\n')
    # 打印账户信息
    print(f'----accounts_info----:\n{e.accounts_info}\n')  # 账户资金情况

    e.tq.api.close()