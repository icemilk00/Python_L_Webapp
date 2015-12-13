# Python_L_Webapp
This is a Demo only for learning python

这是学习python的实践代码，为[廖雪峰官网教程](http://diaoblog.com>http://www.liaoxuefeng.com/wiki/0014316089557264a6b348958f449949df42a6d3a2e542c000)
代码为最后的实践代码，我自己会加上比较详细的注释，目的是巩固前面学的python知识，以及灵活运用


一些官方参考文档
===
[python官方文档](https://docs.python.org/3/contents.html)  
[aiohttp官方文档](http://aiohttp.readthedocs.org/en/stable/)  
[aiomysql官方文档](http://aiomysql.readthedocs.org/en/latest/)  
[jinja2官方文档](http://docs.jinkan.org/docs/jinja2/)  
[uikit官方文档](http://www.getuikit.net/docs/documentation_get-started.html)  
[flask官方文档](http://dormousehole.readthedocs.org/en/latest/)  

遇到的一些问题
===
1.在Day10的教程中，会遇到提交注册表单之后服务器没反应的状况:  
---
由于你用的uikit版本和教程里的uikit版本不一样导致static目录下的文件不一样，你在提交表单时，代码里要加载的js文件，其实你的static目录里根本没有，导致加载不上，而运行失败。  
解决办法就是把教程github上的源代码static目录覆盖掉你的static，保证你的static目录和教程的static目录里文件一样。  

2.在Day11的教程中，会遇到创建博客日志需要登录，登录完后创建仍需登录的问题：
---
由于是需要管理员才能创建日志的，所以你需要新注册一个管理员用户，可以在代码中写判断，如果是管理员的邮箱的话，在插入user表的时候，把admin字段设为YES就ok了。或者直接手动在数据库中添加条目，并把admin字段设为YES

3.实践项目中，最后会遇到首页，点击下一页，但是无响应的问题，就是跳转不了页数：
---
需要在handlers.py中的 index(*, page='1') 函数中的 page = Page(num) 改成 page = Page(num, page_index)

	#首页，会显示博客列表
	@get('/')
	def index(*, page='1'):
		#获取到要展示的博客页数是第几页
		page_index = get_page_index(page)
		#查找博客表里的条目数
		num = yield from Blog.findNumber('count(id)')
		#通过Page类来计算当前页的相关信息
		page = Page(num, page_index)
		#如果表里没有条目，则不需要系那是
		if num == 0:
			blogs = []
		else:
			#否则，根据计算出来的offset(取的初始条目index)和limit(取的条数)，来取出条目
			blogs = yield from Blog.findAll(orderBy='created_at desc', limit=(page.offset, page.limit))
			#返回给浏览器
		return {
			'__template__': 'blogs.html',
			'page': page,
			'blogs': blogs
		}


其实之前还遇到很多问题，但是由于没有及时记录已经忘记好多，如果有缘分能再遇到的话，会及时记录到这里

总结
===
廖老师的教程是很棒的一篇教程，尤其在实践部分的代码，是有很干得代码，包括封装思路，模块解耦，代码设计等，而且实践里的orm模块和web框架都是自己写的，能让初学者学到除了python语法之外的很多东西。十分推荐。  


