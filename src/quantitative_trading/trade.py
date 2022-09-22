#!/usr/bin/env python
#-*- coding: utf-8 -*-
#FILE: trade.py
#CREATE_TIME: 2022-09-21
#AUTHOR: Sancho

from tqsdk import TqApi, TargetPosTask


class Trade:
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

    def _set_trade(self,
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

    def set_trades(self,
                   price='ACTIVE',
                   offset_priority='今昨,开',
                   min_volume=None,
                   max_volume=None,
                   account=None) -> dict:
        """批量设置合约目标持仓对象(单账户)"""
        return {
            name: self._set_trade(quote.instrument_id, price, offset_priority,
                                  min_volume, max_volume, account)
            for name, quote in self.quotes.items()
        }

    def set_trades_accounts(self) -> dict:
        # REVIEW: 未测试
        """批量设置多账户目标持仓对象"""
        return {account: self.set_trades(account) for account in self.accounts}

    def trading(self, target_pos_task: TargetPosTask, volume: int):
        """
        Args:
            target_pos_task (TargetPosTask): 目标持仓对象
            volume (int): 目标持仓手数，正数表示多头，负数表示空头，0表示空仓
        """
        target_pos_task.set_target_volume(volume)
