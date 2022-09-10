#!/usr/bin/env python
#-*- coding: utf-8 -*-
#FILE: main.py
#CREATE_TIME: 2022-09-09
#AUTHOR: Sancho
"""
量化交易策略框架
"""
import datetime
import sys
import yaml
from tqsdk import TqApi, TqAuth, TqAccount, TqKq, TqSim, TqBacktest


class Tq:
    def __init__(self, _type: str = None, web_gui: str = False) -> None:
        """
        登录天勤,请在`config.yml`配置登录信息

        Args:
            _type:`moni`=模拟(默认),`shipan`=实盘,`kq`=快期模拟,`huice`=回测 
            web_gui:开启网页可视化，默认`False`，`True`=随机端口，或使用固定端口如`:9876` 
        """
        self.config = get_config()
        self.auth = TqAuth(self.config['tq_username'],
                           self.config['tq_password'])
        sim = self.get_sim()

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
        return self.get_api(
            TqAccount(self.config['com'],
                      self.config['account'],
                      self.config['password'],
                      td_url=self.config['tcp']))

    def _type_kq(self):
        return self.get_api(TqKq())

    def _type_moni(self, sim):
        return self.get_api(sim)

    def _type_huice(self, sim):
        start_dt = datetime.date(*self.config['start_dt'])
        end_dt = datetime.date(*self.config['end_dt'])
        return self.get_api_huice(sim, TqBacktest(start_dt, end_dt))

    def get_api(self, _type=None, web_gui=False):
        return TqApi(_type, auth=self.auth, web_gui=web_gui)

    def get_api_huice(self, sim, backtest, web_gui=False):
        return TqApi(sim, auth=self.auth, backtest=backtest, web_gui=web_gui)

    def get_sim(self):
        return TqSim(init_balance=self.config['balance'])


def get_config():
    _ = '/'
    if sys.platform.startswith('win'):
        _ = '\\'
    path = f'{sys.path[0]}{_}..{_}..{_}config.yml'
    with open(path, 'r', encoding='utf-8') as f:
        config = yaml.load(f, Loader=yaml.CLoader)
    return config


if __name__ == "__main__":
    tq = Tq()
    conts = tq.api.query_his_cont_quotes(symbol='KQ.m@DCE.a', n=20)
    print(conts)
    tq.api.close()
