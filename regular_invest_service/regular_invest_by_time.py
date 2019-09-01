# -*- coding: utf-8 -*-
# @Time    : 2019/9/1 11:29
# @Author  : luxblive
# @File    : regular_invest_by_time.py


import ccxt
import time
import json
import pymysql
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys

sys.path.append("/home/regular_invest/")
from trading_utils.trading_executor import *
from trading_utils.send_email import *
from statistics_model.orm_tables import *

with open("../config/config.json", 'r') as config_file:
    config = json.load(config_file)
    apiKey = config["api_config"]["apiKey"]
    secret = config["api_config"]["secret"]
    password = config["api_config"]["password"]
    exchange_name = config["exchange_name"]
    use_database = config["use_database"]
    assets_to_buy = config["assets_to_buy"]
    transaction_fee = float(config["transaction_fee"])

if exchange_name == "okex":
    exchange = ccxt.okex3()
elif exchange_name == "huobi":
    exchange = ccxt.huobipro()
    password = None
else:
    exchange = None
    print("暂时不支持{}交易所".format(exchange_name))
    exit()

trading_executor = TradingExecutor(exchange=exchange, api_key=apiKey, secret=secret, password=password)
if use_database:
    with open("../config/database.json", 'r') as database_file:
        database_config = json.load(database_file)
        user = database_config["user"]
        password = database_config["password"]
        host = database_config["host"]
        port = database_config["port"]
        database = database_config["database"]

    config_string = "mysql+pymysql://{user}:{password}@{host}:{port}/{database_name}".format(user=user,
                                                                                             password=password,
                                                                                             host=host, port=port,
                                                                                             database_name=database)
    engine = create_engine(config_string)
    # 创建与数据库通信的session，这个就是cursor的功能！
    Session = sessionmaker(bind=engine)
    session = Session()
else:
    session = None

for asset_to_buy in assets_to_buy:
    currency = asset_to_buy["currency"]
    coin = asset_to_buy["coin"]
    symbol = "{coin}/{currency}".format(coin=coin, currency=currency)
    currency_amount = float(asset_to_buy["amount"])

    # 每个交易所封装之后的细节还是略有不同，故需要分别处理
    if exchange_name == "okex":
        if asset_to_buy["currency_has_yubibao"] is True:
            # 若currency存在余币宝，则在购买coin之前，先将所需的currency从余币宝中划转到币币账户中
            trading_executor.transfer_coin_on_okex(currency=currency, amount=currency_amount, coin_from=8, coin_to=1)
        currency_balance_before = trading_executor.get_okex_balance(symbol=currency)["balance"]
        coin_balance_before = trading_executor.get_okex_balance(symbol=coin)["balance"]
        order_id, average_price, cost_currency, buy_amount = trading_executor.place_order_with_market_price_on_okex(
            symbol=symbol,
            usdt_amount=currency_amount)
        # 2019.8.1开始，okex不再支持点卡抵扣手续费，所以下单金额还要扣除手续费,所以真实所得的币种数目还需要扣除该手续费
        buy_amount = buy_amount / (1 + transaction_fee)
        if order_id is None:
            print("创建{}订单时发生网络错误，终止交易！".format(symbol))
            exit()
        currency_balance_after = trading_executor.get_okex_balance(symbol=currency)["balance"]
        coin_balance_after = trading_executor.get_okex_balance(symbol=coin)["balance"]
        if asset_to_buy["coin_has_yubibao"] is True:
            # 若coin可以存入余币宝，则在购买coin之后，先所有coin转入余币宝
            trading_executor.transfer_coin_on_okex(currency=coin, amount=buy_amount, coin_from=1, coin_to=8)
    elif exchange_name == "huobi":
        wallet_balance = trading_executor.fetch_balance()
        currency_balance_before = wallet_balance[currency]["total"]
        coin_balance_before = wallet_balance[coin]["total"]
        order_id, average_price, cost_currency, buy_amount = trading_executor.place_order_with_market_price_on_huobi(
            symbol=symbol,
            usdt_amount=currency_amount)
        wallet_balance = trading_executor.fetch_balance()
        currency_balance_after = wallet_balance[currency]["total"]
        coin_balance_after = wallet_balance[coin]["total"]
    else:
        order_id, cost_currency, buy_amount, average_price = None, None, None, None
        print("暂时不支持{}交易所".format(exchange_name))
        exit()

    # 购买完成之后发送报表邮件
    text = ("本次交易花费{cost_currency}个{currency},\n购买{coin}{buy_amount}个，\n"
            "本次购买{coin}的均价为{average_price}个{currency}\n "
            .format(cost_currency=cost_currency, currency=currency, coin=coin, buy_amount=buy_amount,
                    average_price=average_price))
    # 若要统计数据，则需要开启数据库功能
    if use_database:
        date = time.strftime("%Y-%m-%d %H:%M", time.localtime())
        transaction_record = Transaction(transaction_id=order_id, coin_symbol=coin, coin_amount=buy_amount,
                                         currency_symbol=currency, currency_amount=cost_currency,
                                         price=average_price, date=date)
        session.add(transaction_record)
        session.commit()
        # 接下来进行成本计算并更新数据库的记录
        # 直接在filter中添加多个条件即表示与逻辑
        cost_query = session.query(Cost).filter(Cost.currency_symbol == currency, Cost.coin_symbol == coin)
        if len(cost_query.all()) > 1:
            text_add = ""
            print("{}成本记录有重复条目，请检查数据库数据异常".format(symbol))
            exit()
        # 若不存在该交易对的成本记录条目，则新增一个记录
        elif len(cost_query.all()) == 0:
            cost = Cost(currency_symbol=currency, currency_amount=cost_currency, coin_symbol=coin,
                        coin_amount=buy_amount, average_price=average_price)
            session.add(cost)
            session.commit()
            ask = trading_executor.get_market_price(symbol=symbol)
            profit = (ask / float(average_price) - 1) * 100
            text_add = ("累计定投{coin}一共{coin_amount}个，花费{currency}一共{currency_amount}个，"
                        "{symbol}的均价为{average_price}，目前盈利{profit}%\n"
                        .format(coin=coin, coin_amount=buy_amount, currency=currency, currency_amount=cost_currency,
                                symbol=symbol, average_price=average_price, profit=profit))
        else:
            cost_record = cost_query.first()
            last_currency_amount = cost_record.currency_amount
            last_coin_amount = cost_record.coin_amount
            total_currency_amount = float(last_currency_amount) + float(cost_currency)
            total_coin_amount = float(last_coin_amount) + float(buy_amount)
            total_coin_average = total_currency_amount / total_coin_amount
            cost_query.update({Cost.currency_amount: total_currency_amount, Cost.coin_amount: total_coin_amount,
                               Cost.average_price: total_coin_average})
            session.commit()
            ask = trading_executor.get_market_price(symbol=symbol)
            profit = (ask / float(average_price) - 1) * 100
            text_add = (("累计定投{coin}一共{coin_amount}个，花费{currency}一共{currency_amount}个，"
                         "{symbol}的均价为{average_price}，目前盈利{profit}%\n"
                         .format(coin=coin, coin_amount=total_coin_amount, currency=currency,
                                 currency_amount=total_currency_amount, symbol=symbol, average_price=total_coin_average,
                                 profit=profit)))
    else:
        text_add = ""
    text += text_add
    subject = "每日定投购买{symbol}数据".format(symbol=symbol)
    send_email(subject, text)

# 全部币种定投结束之后，如果使用了数据库，则关闭数据库的连接
if use_database:
    session.close()
