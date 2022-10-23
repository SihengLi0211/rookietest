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
from typing import Dict, List, Union
import yaml
from tq import Tq
from subscription import Subscription
from trade import Trade
import monitor


class Engine:
    PLATFORM = sys.platform  # 获取操作系统平台

    @classmethod
    def get_config(cls) -> dict:
        """
        获取配置文件
        """
        _ = '/'
        if cls.PLATFORM.startswith('win'):
            _ = '\\'
        path = f'{sys.path[0]}{_}..{_}..{_}config.yml'
        with open(path, 'r', encoding='utf-8') as f:
            config = yaml.load(f, Loader=yaml.CLoader)
        return config

    def __init__(self) -> None:
        # 获取配置文件
        self.config = self.get_config()
        # 登录天勤
        self.tq = self._get_tq_api()
        # 订阅合约
        self.subscription = Subscription(self.tq.api)
        self.quotes_dict, self.klines_dict, self.ticks_dict = self._get_subs()
        # 初始化账户
        self.trade = Trade(self.tq.api, self.quotes_dict, self.tq.accounts)
        self.accounts_info = self.trade.accounts_info
        self.positions = self.trade.positions
        self.orders = self.trade.orders

    def _get_tq_api(self) -> Tq:
        """
        登录天勤，返回天勤对象
        """
        return Tq(self.config['tq_username'], self.config['tq_password'],
                  self.config['type'], self.config['gui'],
                  self.config['balance'], self.config['accounts'])

    def _get_subs(self) -> List[Union[dict, None]]:
        """
        获取需要订阅的合约，返回订阅的对象
        """
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

    def run(self) -> None:
        """
        事件循环函数:
        * 实际发出网络数据包(如行情订阅指令或交易指令等).
        * 尝试从服务器接收一个数据包, 并用收到的数据包更新内存中的业务数据截面.
        * 让正在运行中的后台任务获得动作机会(如策略程序创建的后台调仓任务只会在wait_update()时发出交易指令).
        * 如果没有收到数据包，则挂起等待.
        """
        # 初始化持仓对象
        task_dict = self.trade.set_trades()

        # 初始化策略
        self.strategies = []
        strategies = self.config['strategies']
        for name, quote in self.quotes_dict.items():
            kline = self.klines_dict.get(name, None)
            tick = self.ticks_dict.get(name, None)
            exec(f'self.strategies.append(monitor.{strategies}())')
            for s in self.strategies:
                s.init(self.tq.api, self.accounts_info, self.positions,
                       self.orders, quote, kline, tick)  # 初始化策略

        # 事件循环
        # TODO: 添加异步执行
        try:
            while self.tq.api.wait_update():  # 等待更新
                for task in task_dict.values():  # 遍历合约对象
                    for s in self.strategies:  # 遍历策略
                        if volume := s.execution():  # 执行策略
                            self.trade.trading(task, volume)  # 调仓
        except Exception as e:
            self.tq.api.close()


if __name__ == "__main__":
    e = Engine()
    # 打印订阅信息
    print(f'----quotes----:\n{e.quotes_dict}\n')
    print(f'----klines----:\n{e.klines_dict}\n')
    print(f'----ticks----:\n{e.ticks_dict}\n')
    # 打印账户信息
    print(f'----accounts_info----:\n{e.accounts_info}\n')  # 账户资金情况
    e.run()