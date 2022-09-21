#!/usr/bin/env python
#-*- coding: utf-8 -*-
#FILE: tq.py
#CREATE_TIME: 2022-09-21
#AUTHOR: Sancho

import datetime
from tqsdk import TqApi, TqAuth, TqAccount, TqKq, TqSim, TqBacktest, TqMultiAccount, TqMultiAccount


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
