#!/usr/bin/env python
#-*- coding: utf-8 -*-
#FILE: subscription.py
#CREATE_TIME: 2022-09-21
#AUTHOR: Sancho

from tqsdk import TqApi


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
