import logging; logging.basicConfig(level=logging.INFO)
import asyncio, orm, json, os, time
from datetime import datetime

import aiohttp import web
import jinja2 import Enviroment, FileSystemLoader

from config import configs

from coroweb import add_routes, add_static

@asyncio.coroutine
def logger_factory(app, handler):
	@asyncio.coroutine
	def logger(request):
		logging.info('Requst : %s, %s' % (request.method, request.path))
		return (yield from handler(request))
	return logger

@asyncio.coroutine
def response_factory():
	@asyncio.coroutine
	def parse_data(request):
		if request.method == 'POST':
			if request.content_type.startswith('application/json'):
				request.__data__ = yield from request.json()
				logging.info('request json : %s' % str(request.__data__))
			elif request.content_type.startswith('application/x-www-form-urlencoded'):
				request.__data__ = yield from request.post()
				logging.info('request form : %s' % str(request.__data__))
		return (yield from handler(request))
	return parse_data
	
def datetime_filter(t):
    delta = int(time.time() - t)
    if delta < 60:
        return u'1分钟前'
    if delta < 3600:
        return u'%s分钟前' % (delta // 60)
    if delta < 86400:
        return u'%s小时前' % (delta // 3600)
    if delta < 604800:
        return u'%s天前' % (delta // 86400)
    dt = datetime.fromtimestamp(t)
    return u'%s年%s月%s日' % (dt.year, dt.month, dt.day)

@asyncio.coroutine
def init(loop):
	#创建数据库连接池，db参数传配置文件里的配置db
	yield from orm.create_pool(loop=loop, **configs.db)
	#middlewares设置两个中间处理函数
	#middlewares的最后一个Handle为响应处理函数
	app = web.Application(loop, middlewares=[
		logger_factory, response_factory
	])
	init_jinja2(app, filter=dict(datetime=datetime_filter))
	add_routes(app, 'handers')



loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
