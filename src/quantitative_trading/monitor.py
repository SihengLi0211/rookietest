#!/usr/bin/env python
#-*- coding: utf-8 -*-
#FILE: monitor.py
#CREATE_TIME: 2022-09-22
#AUTHOR: Sancho
"""
策略库
"""

from abc import ABCMeta, abstractmethod
import pandas
from tqsdk import TqApi, TargetPosTask, TqAccount
from typing import Union, List, Any
from tqsdk.objs import Position, Order, Quote


class Monitor(metaclass=ABCMeta):
    def __init__(self) -> None:
        pass

    def init(self, api: TqApi, account: TqAccount, position: Position,
             order: Order, quote: Quote, kline: pandas.DataFrame,
             tick: pandas.DataFrame):
        """
        初始化策略函数
        """
        self.api = api
        self.account = account
        self.position = position
        self.order = order
        self.quote = quote
        self.kline = kline
        self.tick = tick

    @abstractmethod
    def execution(self):
        """
        执行策略函数
        """
        pass

    def changed(self,
                obj: Any,
                key: Union[str, List[str], None] = None) -> bool:
        """
        判断序列是否发生改变
        
        Args:
            obj: 序列
            key: 表头

        Example:
            changed(quote, "last_price")
        """
        return self.api.is_changing(obj, key)

    def send():
        pass


"""
添加策略时，需要继承`Monitor`类，并实现其中被`@abstractmethod`装饰的函数
使用策略时，在`config.yml`中`strategies`项中指定策略的类，如`DualThrust`
"""


class Demo(Monitor):
    """
    添加策略示例
    """
    def __init__(self) -> None:
        super().__init__()

    def execution(self):
        """
        自定义策略: 打印最新价格
        """
        print('---------- 执行策略 ----------')
        if self.changed(self.quote, 'last_price'):
            print(f"最新价: {self.quote['last_price']}")
        if self.changed(self.kline.iloc[-1]):
            print(f"最新K线: {self.kline.iloc[-1]}")
        print('---------- 策略结束 ----------')
        return 0


class DualThrust(Monitor):
    """
    Dual Thrust策略 (难度：中级)
    参考: https://www.shinnytech.com/blog/dual-thrust
    注: 该示例策略仅用于功能示范, 实盘时请根据自己的策略/经验进行修改
    """
    NDAY = 5  # 天数
    K1 = 0.2  # 上轨K值
    K2 = 0.2  # 下轨K值

    def __init__(self, *args) -> None:
        super().__init__(*args)
        # 获取上下轨
        self.buy_line, self.sell_line = self.dual_thrust(self.kline)

    def dual_thrust(self, kline: pandas.DataFrame):
        current_open = kline.iloc[-1]["open"]
        HH = max(kline['high'].iloc[-self.NDAY - 1:-1])  # N日最高价的最高价
        HC = max(kline['close'].iloc[-self.NDAY - 1:-1])  # N日收盘价的最高价
        LC = min(kline['close'].iloc[-self.NDAY - 1:-1])  # N日收盘价的最低价
        LL = min(kline['low'].iloc[-self.NDAY - 1:-1])  # N日最低价的最低价
        _range = max(HH - LC, HC - LL)
        buy_line = current_open + _range * self.K1  # 上轨
        sell_line = current_open - _range * self.K2  # 下轨
        print("当前开盘价: %f, 上轨: %f, 下轨: %f" %
              (current_open, buy_line, sell_line))
        return buy_line, sell_line

    def execution(self):
        # 新产生一根日线或开盘价发生变化: 重新计算上下轨
        if self.changed(self.kline.iloc[-1], ["datetime", "open"]):
            self.buy_line, self.sell_line = self.dual_thrust(self.kline)

        # 如果最新价发生改变则判断信号
        if self.changed(self.quote, "last_price"):
            if self.quote['last_price'] > self.buy_line:  # 高于上轨
                print("高于上轨,目标持仓 多头3手")
                return 3
            elif self.quote['last_price'] < self.sell_line:  # 低于下轨
                print("低于下轨,目标持仓 空头3手")
                return -3
            print('未穿越上下轨,不调整持仓')
            return 0