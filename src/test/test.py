#!/usr/bin/env python
#-*- coding: utf-8 -*-
#FILE: main.py
#CREATE_TIME: 2022-09-09
#AUTHOR: Sancho
"""
测试用例
"""
import datetime
import sys
import yaml
from tqsdk import TqApi, TqAuth, TqSim


class Tq:
    def __init__(
        self,
        username: str,
        password: str,
    ) -> None:
        """
        登录天勤,请在`config.yml`配置登录信息,`tq_username`和`tq_password`项
        Args:
            config:天勤账号 \n
            password:天勤密码 \n
        """
        # 初始化变量
        self.auth = TqAuth(username, password)  # 填充账密
        self.sim = TqSim()
        # 模式选择
        try:
            self.api = self._type_moni()
        except Exception as e:
            print(f"{e}\n认证失败!")

    def _type_moni(self):
        self.accounts = [self.sim]
        return self._get_api(self.accounts[0])

    def _get_api(self, _type=None):
        return TqApi(_type, auth=self.auth)


class Subscription:
    """订阅合约"""
    def __init__(self, api: TqApi) -> None:
        self.api = api

    def get_quotes(self, quotes: list) -> dict:
        """订阅实时行情"""
        return {symbol: self.api.get_quote(symbol)
                for symbol in quotes}  # {'symbol1':quote,'symbol2':quote, ...}

    def get_klines(self, klines: dict, merge: bool = False) -> dict:
        """
        订阅K线
        
        Args:
            merge: 是否以第一个合约为基准合并K线(默认不合并) \n
        """
        if merge:
            # 获取klines下第一个合约的数据周期
            _ = list(klines.values())[0]
            duration_seconds = _[0]
            data_length = _[1]
            symbol_list = list(klines.keys())
            return {
                symbol_list[0]:
                self.api.get_kline_serial(symbol_list, duration_seconds,
                                          data_length)
            }
        return {
            symbol: self.api.get_kline_serial(symbol, l[0], l[1])
            for symbol, l in klines.items()
        }

    def get_ticks(self, ticks: dict) -> dict:
        """订阅tick级数据"""
        return {
            symbol: self.api.get_tick_serial(symbol, data_length)
            for symbol, data_length in ticks.items()
        }


class Tread:
    def __init__(self, api: TqApi) -> None:
        """
        设置交易模式
        args:
            api: 天勤API \n
        """
        self.api = api
        self.accounts_info, self.positions, self.orders = [], [], []
        # 拉取账户情况
        self.accounts_info.append(self.api.get_account())  # 账户资金情况


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
        self.tread = Tread(self.tq.api)
        self.accounts_info = self.tread.accounts_info

    def _get_tq_api(self):
        # 登录天勤，获取API
        return Tq(self.config['tq_username'], self.config['tq_password'])

    def _get_subs(self) -> list:
        # 获取需要订阅的合约，返回订阅的对象
        subs = []
        subs.append(self.subscription.get_quotes(['KQ.m@DCE.a']))
        subs.append(self.subscription.get_klines({'KQ.m@DCE.a': [20, 200]}))
        subs.append(self.subscription.get_ticks({'KQ.m@DCE.a': 200}))
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