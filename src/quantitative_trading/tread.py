#!/usr/bin/env python
#-*- coding: utf-8 -*-
#FILE: tread.py
#CREATE_TIME: 2022-09-21
#AUTHOR: Sancho

from tqsdk import TqApi, TargetPosTask


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

    # TODO: 自定义函数下单方式(TargetPosTask(price=fun))

    def set_treads(self, account=None) -> dict:
        """批量设置合约目标持仓对象(单账户)"""
        return {
            name: self._set_tread(quote.instrument_id, account)
            for name, quote in self.quotes.items()
        }

    def set_treads_accounts(self) -> dict:
        # REVIEW: 未测试
        """批量设置多账户目标持仓对象"""
        return {account: self.set_treads(account) for account in self.accounts}
