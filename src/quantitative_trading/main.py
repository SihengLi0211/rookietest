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
                 username: str,
                 password: str,
                 _type: str = None,
                 web_gui: str = False,
                 balance: int = 9999999,
                 accounts: list = None,
                 start_dt: list = None,
                 end_dt: list = None) -> None:
        """
        登录天勤,请在`config.yml`配置登录信息

        Args:
            config:天勤账号 \n
            password:天勤密码 \n
            _type:`moni`=模拟(默认),`shipan`=实盘,`kq`=快期模拟,`huice`=回测 \n
            web_gui:开启网页可视化，默认`False`，`True`=随机端口，或使用固定端口如`:9876` \n
            balance:模拟的初始资金 \n
            accounts:实盘账户列表 \n
            start_dt:回测开始时间，如`[2022,01,01] `\n
            end_dt:回测结束时间 \n
        """
        # 初始化变量
        self.web_gui = web_gui
        self.auth = TqAuth(username, password)  # 填充账密
        self.sim = TqSim(init_balance=balance)
        self.start_dt = start_dt
        self.end_dt = end_dt
        self.accounts = accounts
        # 模式选择
        try:
            if _type == "huice":
                self.api = self._type_huice()
            elif _type == "kq":
                self.api = self._type_kq()
            elif _type == "shipan":
                self.api = self._type_shipan()
            else:
                self.api = self._type_moni()
        except Exception as e:
            print(f"{e}\n认证失败!")

    def _type_shipan(self):
        # REVIEW: 未测试
        self.accounts_count = len(self.accounts)
        if not self.accounts_count:
            raise '请正确输入实盘账户(accounts)\n'
        elif self.accounts_count == 1:  # 1个账户
            accounts = self.accounts[0]
            self.accounts = [
                TqAccount(accounts['com'],
                          accounts['account'],
                          accounts['password'],
                          td_url=accounts['tcp'])
            ]

            return self._get_api(self.accounts[0])
        # 多账户模式
        self.accounts = [
            TqAccount(account['com'],
                      account['account'],
                      account['password'],
                      td_url=account['tcp']) for account in accounts
        ]
        return self._get_api(TqMultiAccount(self.accounts))

    def _type_kq(self):
        self.accounts = [TqKq()]
        return self._get_api(self.accounts[0])

    def _type_moni(self):
        self.accounts = [self.sim]
        return self._get_api(self.accounts[0])

    def _type_huice(self):
        # REVIEW: 未测试
        self.accounts = [self.sim]
        start_dt = datetime.date(*self.start_dt)
        end_dt = datetime.date(*self.end_dt)
        return self._get_api_huice(self.accounts[0],
                                   TqBacktest(start_dt, end_dt))

    def _get_api(self, _type=None):
        return TqApi(_type, auth=self.auth, web_gui=self.web_gui)

    def _get_api_huice(self, sim, backtest):
        return TqApi(sim,
                     auth=self.auth,
                     backtest=backtest,
                     web_gui=self.web_gui)


class Subscription:
    """订阅合约"""
    def __init__(self, api: TqApi) -> None:
        self.api = api

    def get_quotes(self, quotes: list) -> dict:
        """订阅实时行情"""
        return {symbol: self.api.get_quote(symbol)
                for symbol in quotes}  # {'symbol1':quote,'symbol2':quote, ...}

    # TODO: 异步订阅实时行情

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
    def __init__(self,
                 api: TqApi,
                 quotes: dict,
                 accounts: list = None) -> None:
        """
        设置交易模式

        args:
            api: 天勤API \n
            quotes: 订阅的quote，接收字典 \n
            accounts: （可选）设置多账户列表，元素类型为`TqAccount` \n
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
            self.accounts_info.append(
                self.api.get_account(account=account))  # 账户资金情况
            self.positions.append(
                self.api.get_position(account=account))  # 持仓情况
            self.orders.append(self.api.get_order(account=account))  # 委托单情况

    def _set_tread(self,
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
        """批量设置合约目标持仓对象(单账户)"""
        # REVIEW: 未测试
        return {
            name: self._set_tread(quote.instrument_id, account)
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
    print(e.quotes_dict)
    print(e.klines_dict)
    print(e.ticks_dict)
    # 打印账户信息
    print(e.accounts_info)  # 账户资金情况
    print(e.positions)  # 账户持仓情况
    print(e.orders)  # 账户详单情况

    e.tq.api.close()