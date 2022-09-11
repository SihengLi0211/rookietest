#!/usr/bin/env python
#-*- coding: utf-8 -*-
#FILE: main.py
#CREATE_TIME: 2022-09-09
#AUTHOR: Sancho
"""
量化交易策略框架
天勤库的轻量级封装
"""
import datetime
import sys
import yaml
import pandas
from tqsdk import TqApi, TqAuth, TqAccount, TqKq, TqSim, TqBacktest, TqMultiAccount


class Tq:
    def __init__(self,
                 config,
                 _type: str = None,
                 web_gui: str = False) -> None:
        """
        登录天勤,请在`config.yml`配置登录信息

        Args:
            config:配置文件 \n
            _type:`moni`=模拟(默认),`shipan`=实盘,`kq`=快期模拟,`huice`=回测 \n
            web_gui:开启网页可视化，默认`False`，`True`=随机端口，或使用固定端口如`:9876` \n
        """
        # 初始化变量
        self.web_gui = web_gui
        self.config = config
        self.auth = TqAuth(self.config['tq_username'],
                           self.config['tq_password'])  # 填充账密
        sim = self.get_sim()  # 获取虚拟资金
        # 模式选择
        try:
            if _type == "shipan":
                self.api = self._type_shipan()
            elif _type == "kq":
                self.api = self._type_kq()
            elif _type == "huice":
                self.api = self._type_huice(sim)
            else:
                self.api = self._type_moni(sim)
        except Exception as e:
            print(f"{e}\n认证失败!")

    def _type_shipan(self):
        accounts = self.config['accounts']
        self.accounts_count = len(accounts)
        if self.accounts_count == 1:  # 1个账户
            account = accounts[0]
            return self.get_api(
                TqAccount(account['com'],
                          account['account'],
                          account['password'],
                          td_url=account['tcp']))
        # 多账户模式
        accounts = [
            TqAccount(account['com'],
                      account['account'],
                      account['password'],
                      td_url=account['tcp']) for account in accounts
        ]
        return self.get_api(TqMultiAccount(accounts))

    def _type_kq(self):
        return self.get_api(TqKq())

    def _type_moni(self, sim):
        return self.get_api(sim)

    def _type_huice(self, sim):
        start_dt = datetime.date(*self.config['start_dt'])
        end_dt = datetime.date(*self.config['end_dt'])
        return self.get_api_huice(sim, TqBacktest(start_dt, end_dt))

    def get_api(self, _type=None):
        return TqApi(_type, auth=self.auth, web_gui=self.web_gui)

    def get_api_huice(self, sim, backtest):
        return TqApi(sim,
                     auth=self.auth,
                     backtest=backtest,
                     web_gui=self.web_gui)

    def get_sim(self):
        return TqSim(init_balance=self.config['balance'])


class Subscription:
    """订阅合约"""
    def __init__(self, api: TqAccount) -> None:
        self.api = api

    def get_quotes(self, symbols: list) -> dict:
        """订阅实时行情，支持订阅多合约"""
        # {'symbol1':quote,'symbol2':quote}
        return {symbol: self.api.get_quote(symbol) for symbol in symbols}

    # TODO: 异步订阅实时行情

    def get_kline(self, symbol: str,
                  duration_seconds: int) -> pandas.DataFrame:
        """
        订阅K线
        
        Args:
            symbol: 将订阅的k线如`DCE.m2109` \n
            duration_seconds: 订阅周期(秒) \n
        """
        return self.api.get_kline_serial(symbol, duration_seconds)

    def get_klines(self,
                   symbols: list,
                   duration_seconds: list,
                   merge=False) -> dict:
        """
        订阅多条K线
        
        Args:
            symbol: 将订阅的k线如`DCE.m2109` \n
            duration_seconds: 订阅周期(秒) \n
            merge: 是否以第一个合约为基准合并K线(默认不合并) \n
        """
        if len(symbols) > len(duration_seconds):
            merge = True
        if merge:
            duration_seconds = duration_seconds[0]
            return {
                symbol: self.get_kline(symbol, duration_seconds)
                for symbol in symbols
            }
        return {
            symbol: self.get_kline(symbol, d)
            for symbol, d in zip(symbols, duration_seconds)
        }

    def get_ticks(self, symbols: list, data_lenth: int = 200) -> dict:
        """
        订阅tick级数据

        symbols:合约列表
        data_lenth:获取的长度(最大:8000)
        """
        return {
            symbol: self.api.get_tick_serial(symbol, data_lenth)
            for symbol in symbols
        }


def get_config():
    # 检查操作系统，定义目录分隔符
    _ = '/'
    if PLATFORM.startswith('win'):
        _ = '\\'
    # 获取config目录
    path = f'{sys.path[0]}{_}..{_}..{_}config.yml'
    # 获取config内容
    with open(path, 'r', encoding='utf-8') as f:
        config = yaml.load(f, Loader=yaml.CLoader)
    return config


if __name__ == "__main__":
    PLATFORM = sys.platform  # 获取操作系统平台
    config = get_config()  # 获取配置信息
    tq = Tq(config)  # 登录天勤
    # 订阅合约
    sub = Subscription(tq.api)
    klines = sub.get_klines(['KQ.m@DCE.a', 'KQ.m@DCE.m'], [20])
    print(klines['KQ.m@DCE.a'])
    print(klines['KQ.m@DCE.m'])
    # 退出程序
    tq.api.close()