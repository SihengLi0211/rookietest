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
from tqsdk import TqApi, TqAuth, TqAccount, TqKq, TqSim, TqBacktest, TqMultiAccount, TargetPosTask, TqMultiAccount


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
        # REVIEW: 未测试
        accounts = self.config['accounts']
        self.accounts_count = len(accounts)
        if self.accounts_count == 1:  # 1个账户
            accounts = accounts[0]
            self.accounts = [
                TqAccount(accounts['com'],
                          accounts['account'],
                          accounts['password'],
                          td_url=accounts['tcp'])
            ]

            return self.get_api(self.accounts[0])
        # 多账户模式
        self.accounts = [
            TqAccount(account['com'],
                      account['account'],
                      account['password'],
                      td_url=account['tcp']) for account in accounts
        ]
        return self.get_api(TqMultiAccount(self.accounts))

    def _type_kq(self):
        self.accounts = [TqKq()]
        return self.get_api(self.accounts[0])

    def _type_moni(self, sim):
        self.accounts = [sim]
        return self.get_api(self.accounts[0])

    def _type_huice(self, sim):
        # REVIEW: 未测试
        self.accounts = [sim]
        start_dt = datetime.date(*self.config['start_dt'])
        end_dt = datetime.date(*self.config['end_dt'])
        return self.get_api_huice(self.accounts[0],
                                  TqBacktest(start_dt, end_dt))

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
    def __init__(self, api: TqAccount, config: yaml) -> None:
        self.api = api
        self.config = config

    def get_quotes(self) -> dict:
        """订阅实时行情"""
        return {
            symbol: self.api.get_quote(symbol)
            for symbol in self.config['quotes']
        }  # {'symbol1':quote,'symbol2':quote, ...}

    # TODO: 异步订阅实时行情

    def get_klines(self, merge: bool = False) -> dict:
        """
        订阅K线
        
        Args:
            merge: 是否以第一个合约为基准合并K线(默认不合并) \n
        """
        if merge:
            # 获取klines下第一个合约的数据周期
            _ = list(self.config['klines'].values())[0]
            duration_seconds = _[0]
            data_length = _[1]
            symbol_list = list(self.config['klines'].keys())
            return {
                symbol_list[0]:
                self.api.get_kline_serial(symbol_list, duration_seconds,
                                          data_length)
            }
        return {
            symbol: self.api.get_kline_serial(symbol, l[0], l[1])
            for symbol, l in self.config['klines'].items()
        }

    def get_ticks(self) -> dict:
        """订阅tick级数据"""
        return {
            symbol: self.api.get_tick_serial(symbol, data_length)
            for symbol, data_length in self.config['ticks'].items()
        }


class Tread:
    def __init__(self,
                 api: TqApi,
                 quotes: dict,
                 accounts: list = None) -> None:
        """
        设置交易模式

        args:
            api: 天勤API \n
            quotes: 订阅的quote，接收字典 \n
            accounts: 设置多账户列表，元素类型为`TqAccount` \n
        """
        self.api = api
        self.quotes = quotes
        self.accounts = accounts
        if not self.accounts:
            # 获取账户
            self.accounts = [self.api._account]
        self.accounts_info, self.positions, self.orders = [], [], []
        # 拉取账户情况
        for account in self.accounts:
            self.accounts_info.append(self.api.get_account(account))  # 账户资金情况
            self.positions.append(
                self.api.get_position(account=account))  # 持仓情况
            self.orders.append(self.api.get_order(account=account))  # 委托单情况

    def set_tread(self,
                  symbol,
                  price='ACTIVE',
                  offset_priority='今昨,开',
                  min_volume=None,
                  max_volume=None,
                  account=None) -> TargetPosTask:
        """设置目标持仓对象"""
        return TargetPosTask(self.api,
                             symbol,
                             price,
                             offset_priority,
                             min_volume,
                             max_volume,
                             account=account)

    def set_treads(self, account=None) -> dict:
        """批量设置多合约目标持仓对象(单账户)"""
        return {
            name: self.set_tread(quote.instrument_id, account)
            for name, quote in self.quotes.items()
        }

    def set_treads_accounts(self) -> dict:
        """批量设置多账户目标持仓对象"""
        return {account: self.set_treads(account) for account in self.accounts}


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
        # REVIEW: 重构时需要减少config的传递，使用值传递减少耦合
        self.tq = Tq(self.config)  # 登录天勤
        # 订阅合约
        self.subscription = Subscription(self.tq.api, self.config)
        subs = self.get_subs()
        if not any(subs):
            raise "\n请正确传入需要订阅的合约"
        quotes_dict, klines_dict, ticks_dict = subs

        print(quotes_dict)
        print(klines_dict)
        print(ticks_dict)

        self.tq.api.close()

        # 初始化交易
        # tread = Tread(tq.api, config, tq.accounts)
        # print(tread.accounts_info)  # 账户资金情况
        # print(tread.positions) # 账户持仓情况
        # print(tread.orders) # 账户详单情况

    def get_subs(self) -> list:
        # 获取需要订阅的合约，返回订阅的对象
        subs = []
        # quotes
        if self.config.get('quotes', None):
            subs.append(self.subscription.get_quotes())
        else:
            subs.append(None)
        # klines
        if self.config.get('klines', None):
            subs.append(self.subscription.get_klines(self.config['merge']))
        else:
            subs.append(None)
        # ticks
        if self.config.get('ticks', None):
            subs.append(self.subscription.get_ticks())
        else:
            subs.append(None)
        return subs


if __name__ == "__main__":
    e = Engine()