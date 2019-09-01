# -*- coding: utf-8 -*-
# @Time    : 2019/5/2 22:00
# @Author  : luxblive
# @FileName: orm_tables.py

from sqlalchemy import Column, Integer, VARCHAR
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

"""
Transaction类型的数据表用来记录当天定投的购买情况，用来做数据统计。
"""


class Transaction(Base):
    __tablename__ = 'transaction'
    transaction_id = Column(VARCHAR(30), primary_key=True)
    coin_symbol = Column(VARCHAR(40))
    coin_amount = Column(VARCHAR(40))
    currency_symbol = Column(VARCHAR(40))
    currency_amount = Column(VARCHAR(40))
    price = Column(VARCHAR(40))
    date = Column(VARCHAR(255))


"""
Cost类型的数据表用来记录一段时期内购买该交易对的平均成本，用来做数据统计。
"""


class Cost(Base):
    __tablename__ = 'chengben'
    id = Column(Integer, primary_key=True, autoincrement=True)
    currency_symbol = Column(VARCHAR(40))
    currency_amount = Column(VARCHAR(40))
    coin_symbol = Column(VARCHAR(40))
    coin_amount = Column(VARCHAR(40))
    average_price = Column(VARCHAR(40))
