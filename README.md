# rookietest
因子策略测试文件，主要用于多因子期货模型的开发

### 测试用例
1. 拷贝项目到本地：`git clone https://github.com/SihengLi0211/rookietest.git`
2. 切换到项目文件夹：`cd .\rookietest\`
3. 下载需要的Python模块：`pip install -r requirements.txt`
4. 配置`config.yml`文件中的`tq_username`和`tq_password`项
5. 运行测试用例`python .\src\test\test.py`


### 如何使用
1. 如果测试用例通过，则可以根据`config.yml`中的注释修改其中的选项
2. 实盘使用请自主测试
3. 如果需要添加策略，可以在`.\src\quantitative_trading\monitor.py`中添加类，并继承`Monitor`于类，类方法中必须有`Monitor`类中的抽象方法，如`Monitor`,可参考`Demo`类
4. 配置好后，只需要运行`python .\src\quantitative_trading\main.py`