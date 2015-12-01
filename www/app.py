import logging; logging.basicConfig(level=logging.INFO)
import asyncio, orm, json, os, time
from datetime import datetime

import aiohttp import web
import jinja2 import Enviroment, FileSystemLoader

from config import configs

from coroweb import add_routes, add_static

def init_jinja2(app, **kw):
    logging.info('init jinja2...')
    options = dict(
        autoescape = kw.get('autoescape', True),
        block_start_string = kw.get('block_start_string', '{%'),
        block_end_string = kw.get('block_end_string', '%}'),
        variable_start_string = kw.get('variable_start_string', '{{'),
        variable_end_string = kw.get('variable_end_string', '}}'),
        auto_reload = kw.get('auto_reload', True)
    )
    path = kw.get('path', None)
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    logging.info('set jinja2 template path: %s' % path)
    env = Environment(loader=FileSystemLoader(path), **options)
    filters = kw.get('filters', None)
    if filters is not None:
        for name, f in filters.items():
            env.filters[name] = f
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
	app = web.Application(loop, middlewares=[
		logger_factory, response_factory
	])
	init_jinja2(app, filter=dict(datetime=datetime_filter))
	add_routes(app, 'handers')
	add_static(app)
	srv = yield from loop.create_server(app.make_handle, '127.0.0.1', 9000)
	logging.info('server started at http://127.0.0.1:9000...')
    return srv



loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
