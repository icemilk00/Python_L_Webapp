def get(path):
	def decorator(func):
		@functools.wraps(func)
		def wrapper(*args, **kw):
			return func(*args, **kw)
		wrapper.__method__ = 'GET'
		wrapper.__route__ = path
		return wrapper
	return decorator

def post(path):
	def decorator(func):
		@functools.wraps(func)
		def wrapper(*args, **kw):
			return func(*args, **kw)
		wrapper.__method__ = 'POST'
		wrapper.__route__ = path
		return wrapper
	return decorator

#关于inspect.Parameter 的  kind 类型有5种：
#POSITIONAL_ONLY		只能是位置参数
#POSITIONAL_OR_KEYWORD	可以是位置参数也可以是关键字参数
#VAR_POSITIONAL			相当于是 *args
#KEYWORD_ONLY			关键字参数且提供了key，相当于是 *,key
#VAR_KEYWORD			相当于是 **kw

def get_required_kw_args(fn):
	args = []
	params = inspect.signature(fn).parameters
	logging.info(' %s : params = %s ' % (__name__, params))
	for name, param in params.items():
		if param.kind = inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
			args.append(name)	
	return tuple(args)

def get_named_kw_args(fn):
	args = []
	params = inspect.signature(fn).parameters
	logging.info(' %s : params = %s ' % (__name__, params))
	for name, param in params.items():
		if param.kind = inspect.Parameter.KEYWORD_ONLY:
			args.append(name)	
	return tuple(args)

def has_named_kw_args(fn):
    params = inspect.signature(fn).parameters
    logging.info(' %s : params = %s' % (__name__, params))
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True

def has_var_kw_arg(fn):
    params = inspect.signature(fn).parameters
    logging.info(' %s : params = %s' % (__name__, params))
    for name, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True

def has_request_arg(fn):
    sig = inspect.signature(fn)
    params = sig.parameters
    found = False
    for name, param in params.items():
        if name == 'request':
            found = True
            continue
        if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):
            raise ValueError('request parameter must be the last named parameter in function: %s%s' % (fn.__name__, str(sig)))
    return found

class RequestHandler(object):
	"""docstring for RequestHandler"""
	def __init__(self, app, fn):
		self._app = app
		self._fn = fn
		self._has_request_arg = has_request_arg(fn)
		self._has_var_kw_arg = has_var_kw_arg(fn)
		self._has_named_kw_arg = has_named_kw_arg(fn)
		self._named_kw_args = get_named_kw_args(fn)
		self._required_kw_args = get_required_kw_args(fn)

	@asyncio.coroutine
	def  __call__(self, request):
		kw = None
		if self._has_var_kw_arg or self._has_named_kw_arg or self._required_kw_args:
			
		
		

def add_route(app, fn):
	method = getattr(fn, '__method__', None)
	path = getattr(fn, '__route__', None)
	if path is None or method is None:
		raise ValueError('@get or @post not defined in %s.' % str(fn))
	if not asyncio.iscoroutine(fn) and not inspect.isgeneratorfunction(fn):
		fn = asyncio.coroutine(fn)
	logging.info('add route %s %s => %s (%s)' % (method, path, fn.__name__, ', '.join(inspect.signature(fn).parameters.keys())))
	app.route.add_route(method, path, RequestHandler(app, fn))
	

def add_routes(app, module_name):
	n = module_name.rfind('.')
	if n == (-1)
		mod = __import__(module_name, globals(), locals())
	else:
		name = module_name[n+1:]
		mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)
	for attr in dir(mod):
		if attr.startswith('_'):
			continue
		fn = getattr(mod, attr)
		if callable(fn):
			method = getattr(fn, '__method__', None)
			path = getattr(fn, '__route__', None)
			if method and path:
				add_route(app, fn)
	