## 多币种定投程序（基础版）
1. 在config文件夹中的配置文件中填写自己的api secret和数据库配置。
2. 若使用OKEX交易所，则支持使用余币宝的划转功能，可自行选择是否开启。
3. 若需要存储历史交易数据，进行收益统计，则需要开启数据库功能。

#### 使用的库
ccxt、sqlalchemy


#### 如何使用
在定时任务中写入
```angular2
python pwd/regular_invest_service/regular_invest_by_time.py
```

enjoy it！