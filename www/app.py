# -*- coding: utf-8 -*-

import logging; logging.basicConfig(level=logging.INFO)
import asyncio, json, os, time
from datetime import datetime

from aiohttp import web
from jinja2 import Environment, FileSystemLoader

from config import configs
import orm

from coroweb import add_routes, add_static

def init_jinja2(app, **kw):
	logging.info('init jinja2...')
	#初始化模板配置，包括模板运行代码的开始结束标识符，变量的开始结束标识符等
	options = dict(
		autoescape = kw.get('autoescape', True),	#是否转义设置为True，就是在渲染模板时自动把变量中的<>&等字符转换为&lt;&gt;&amp;
		block_start_string = kw.get('block_start_string', '{%'),	#运行代码的开始标识符
		block_end_string = kw.get('block_end_string', '%}'),		#运行代码的结束标识符
		variable_start_string = kw.get('variable_start_string', '{{'),	#变量开始标识符
		variable_end_string = kw.get('variable_end_string', '}}'),		#变量结束标识符
		auto_reload = kw.get('auto_reload', True)	#Jinja2会在使用Template时检查模板文件的状态，如果模板有修改， 则重新加载模板。如果对性能要求较高，可以将此值设为False
	)
	#从参数中获取path字段，即模板文件的位置
	path = kw.get('path', None)
	#如果没有，则默认为当前文件目录下的 templates 目录
	if path is None:
		path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
	logging.info('set jinja2 template path: %s' % path)
	#Environment是Jinja2中的一个核心类，它的实例用来保存配置、全局对象，以及从本地文件系统或其它位置加载模板。
	#这里把要加载的模板和配置传给Environment，生成Environment实例
	env = Environment(loader=FileSystemLoader(path), **options)
	#从参数取filter字段
	# filters: 一个字典描述的filters过滤器集合, 如果非模板被加载的时候, 可以安全的添加filters或移除较早的.
	filters = kw.get('filters', None)
	#如果有传入的过滤器设置，则设置为env的过滤器集合
	if filters is not None:
		for name, f in filters.items():
			env.filters[name] = f
	#给webapp设置模板
	app['__templating__'] = env

@asyncio.coroutine
def logger_factory(app, handler):
	@asyncio.coroutine
	def logger(request):
		logging.info('Requst : %s, %s' % (request.method, request.path))
		return (yield from handler(request))
	return logger

@asyncio.coroutine
def data_factory(app, handler):
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
	
@asyncio.coroutine
def response_factory(app, handler):
	@asyncio.coroutine
	def response(request):
		logging.info('Response handler...')
		r = yield from handler(request)
		if isinstance(r, web.StreamResponse):
			return r
		if isinstance(r, bytes):
			resp = web.Response(body=r)
			resp.content_type = 'application/octet-stream'
			return resp
		if isinstance(r, str):
			if r.startswith('redirect:'):
				return web.HTTPFound(r[9:])
			resp = web.Response(body=r.encode('utf-8'))
			resp.content_type = 'text/html;charset=utf-8'
			return resp
		if isinstance(r, dict):
			template = r.get('__template__')
			if template is None:
				resp = web.Response(body=json.dumps(r, ensure_ascii=False, default=lambda o: o.__dict__).encode('utf-8'))
				resp.content_type = 'application/json;charset=utf-8'
				return resp
			else:
				resp = web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
				resp.content_type = 'text/html;charset=utf-8'
				return resp
		if isinstance(r, int) and t >= 100 and t < 600:
			return web.Response(t)
		if isinstance(r, tuple) and len(r) == 2:
			t, m = r
			if isinstance(t, int) and t >= 100 and t < 600:
				return web.Response(t, str(m))
			# default:
			resp = web.Response(body=str(r).encode('utf-8'))
			resp.content_type = 'text/plain;charset=utf-8'
			return resp
	return response

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
	app = web.Application(loop=loop, middlewares=[
		logger_factory, response_factory
	])
	#初始化jinja2模板
	init_jinja2(app, filters=dict(datetime=datetime_filter))
	#添加请求的handlers，即各请求相对应的处理函数
	add_routes(app, 'handlers')
	#添加静态文件所在地址
	add_static(app)
	#启动
	srv = yield from loop.create_server(app.make_handler(), '127.0.0.1', 9000)
	logging.info('server started at http://127.0.0.1:9000...')
	return srv


#入口，固定写法
#获取eventloop然后加入运行事件
loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
