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

遇到的一些问题
===
1.在Day10的教程中，会遇到提交注册表单之后服务器没反应的状况:  

由于你用的uikit版本和教程里的uikit版本不一样导致static目录下的文件不一样，你在提交表单时，代码里要加载的js文件，其实你的static目录里根本没有，导致加载不上，而运行失败。  
解决办法就是把教程github上的源代码static目录覆盖掉你的static，保证你的static目录和教程的static目录里文件一样。  