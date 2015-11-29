# 用来测试orm模块是否可以顺利工作的测试代码

import orm, asyncio
from models import User, Blog, Comment

def test(loop):
	#创建数据库连接池，用户名：www-data, 密码：www-data ,访问的数据库为：awesome
	#在这之前必须现在mysql里创建好awesome数据库，以及对应的表，否则会显示can't connect
	#可以通过命令行输入：mysql -u root -p <schema.sql ，来执行schema.sql脚本来实现数据库的初始化，schema.sql和本文件在同一目录下
	yield from orm.create_pool(loop = loop, user = 'www-data', password='www-data', db='awesome')

	#创建User model
	u = User(name = 'Test', email = 'test1@example.com', passwd = '123', image = 'about:blank')
	#同时同步到awesome数据库的users表下，插入一条user数据，对应字段的值就是u的传参
	yield from u.save()

	# yield from u.find('passwd')

#获取runloop
loop = asyncio.get_event_loop()
#在loop下加入test事件，开始运行
loop.run_until_complete(test(loop))
#关闭loop
loop.close()