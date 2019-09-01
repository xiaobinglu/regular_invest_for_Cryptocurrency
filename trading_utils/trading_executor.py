# -*- coding: utf-8 -*-
# @Time    : 2019/5/1 22:24
# @Author  : luxblive
# @FileName: trading_executor.py

import okex_sdk_api_v3.account_api as account
import okex_sdk_api_v3.spot_api as spot


class TradingExecutor:
    def __init__(self, exchange, api_key, secret, password=None):
        """根据实例化的交易所对象和api密钥，来初始化一个具体的交易所

        :param exchange: 一个交易所的实例化
        :param api_key: 该交易的交易密钥
        :param secret: 同上
        """
        self.exchange = exchange
        self.exchange.apiKey = api_key
        self.exchange.secret = secret
        if password is not None:
            self.exchange.password = password

    def fetch_balance(self):
        return self.exchange.fetch_balance()

    def get_order_data(self, order_id, symbol=None):
        """根据订单id查询该订单的信息

        :param order_id: 订单的id号
        :param symbol: 在okex中查询订单需要symbol参数！火币不需要，所以还需要区分处理！
        :return: 订单数据
        """
        # 若订单的状态已完成，则将标志位flag置为0，退出循环
        flag = 1
        # 设置重试的次数最多为30次
        count = 30
        order = 0
        while flag and count:
            if symbol is not None:
                order = self.exchange.fetch_order(id=order_id, symbol=symbol)
            else:
                order = self.exchange.fetch_order(id=order_id)
            if order["status"] == "closed":
                flag = 0
            else:
                count = count - 1
        return order

    def get_market_price(self, symbol):
        """根据传进来的交易对符号，查询现在该交易对的市场价

        :param symbol: 交易对的符号
        :return: 该交易对现在的市场价
        """
        # 获取价格重试的最大次数为30次
        count = 30
        # bid表示买1价，ask表示卖1价，市价买入，也就只能参考卖1价了
        while count:
            order_book = self.exchange.fetch_order_book(symbol=symbol)
            ask = order_book['asks'][0][0] if len(order_book['asks']) > 0 else None
            if ask:
                return ask
            else:
                count = count - 1
        if count == 0:
            return 0

    def place_order_with_market_price_on_huobi(self, symbol, usdt_amount):
        self.exchange.options["marketBuyPrice"] = True
        transaction = self.exchange.create_order(symbol=symbol, type="market", side="buy", amount=1, price=usdt_amount)
        print(transaction)
        transaction_status = transaction["info"]["status"]
        if transaction_status == "ok":
            order_id = transaction["info"]["data"]
            order = self.get_order_data(order_id)
            average_price = order["average"]
            cost_currency = order["cost"]
            buy_amount = order["filled"]
            return order_id, average_price, cost_currency, buy_amount
        else:
            return None, None, None, None

    def place_order_with_market_price_on_okex(self, symbol, usdt_amount):
        self.exchange.options["marketBuyPrice"] = True
        transaction = self.exchange.create_order(symbol=symbol, type="market", side="buy", amount=1, price=usdt_amount)
        # 返回数据的格式为：'info': {'result': True, 'order_id': xx}
        transaction_result = transaction["info"]["result"]
        if transaction_result:
            order_id = transaction["info"]["order_id"]
            # 注意，okex交易所在查询订单的时候，okex fetchOrder requires a symbol parameter，所以必须带上交易对符号
            order = self.get_order_data(order_id, symbol)
            average_price = order["average"]
            cost_currency = order["cost"]
            buy_amount = order["filled"]
            return order_id, average_price, cost_currency, buy_amount
        else:
            return None, None, None, None

    def sell_order_with_market_price_on_okex(self, symbol, usdt_amount):
        # self.exchange.options["marketSellPrice"] = True
        ask = self.get_market_price(symbol=symbol)
        coin_amount = usdt_amount / ask
        transaction = self.exchange.create_market_sell_order(symbol=symbol, amount=coin_amount)
        # 返回数据的格式为：'info': {'result': True, 'order_id': xx}
        transaction_result = transaction["info"]["result"]
        if transaction_result:
            order_id = transaction["info"]["order_id"]
            # 注意，okex交易所在查询订单的时候，okex fetchOrder requires a symbol parameter，所以必须带上交易对符号
            order = self.get_order_data(order_id, symbol)
        else:
            order_id = 0
            order = 0
        return order_id, order

    def transfer_coin_on_okex(self, currency, amount, coin_from, coin_to):
        """okex上资金账户的资金划转功能，主要用于余币宝和币币账户的相互划转

        :param currency: 币种，如USDT
        :param amount: 划转数量
        :param coin_from: 转出账户
        :param coin_to: 转入账户
        :return:
        """
        account_api = account.AccountAPI(self.exchange.apiKey, self.exchange.secret, self.exchange.password, True)
        result = account_api.coin_transfer(currency=currency, amount=amount, account_from=coin_from, account_to=coin_to)
        print(result)

    def get_okex_balance(self, symbol):
        """使用ccxt查询OKEX账户余额的返回值不同，如果不是几个大币种，余额为0的币不会显示的，所以直接查询BCH余额就会报错，那么使用官方的SDK
        指定查询的币种，才会正常显示！

        :param symbol: 查询账户余额的币种符号
        :return:
        """
        spot_api = spot.SpotAPI(self.exchange.apiKey, self.exchange.secret, self.exchange.password, True)
        balance = spot_api.get_coin_account_info(symbol=symbol)
        return balance
