
import asyncio, logging
import aiomysql

def log(sql, args=()):
    logging.info('SQL: %s' % sql)

@asyncio.coroutine
def create_pool(loop, **kw):
	logging.info('create database connecting pool ...')
	global __pool
	__pool = yield from aiomysql.create_pool(
		host = kw.get('host', 'localhost'),
		port = kw.get('port', 3306),
		user = kw['user'],
		password = kw['password'],
		db = kw['db'],
		charset = kw.get('charset', 'utf-8'),
		autocommit = kw.get('autocommit', True),
		maxsize = kw.get('maxsize', 10),
		minsize = kw.get('minsize', 1),
		loop = loop
		)

@asyncio.coroutine
def  select(sql, args, size=None):
	log(sql, args)
	global __pool
	with (yield from _pool) as conn:
		cur = yield from conn.cursor(aiomysql.DictCursor)
		yield from cur.execute(sql.replace('?', '%s'), args or ())
		if size:
			rs = yield from cur.fetchmany(size)
		else:
			rs = yield from cur.fetchall()

		yield from cur.close()
		logging.info('rows returned : %s' % len(rs))
		return rs

@asyncio.coroutine
def execute(sql, args):
	log(sql)
	with (yield from __pool) as conn:
		try:
			cur = yield from conn.cursor()
			yield from cur.execute(sql.replace('?', '%s'), args)
			affected = cur.rowcount
			yield from cur.close()
		except BaseException as e:	
			raise
		return affected


class Model(dict, metaclass = ModelMetalclass):
	def __init__(self,**kw):
		super(Model, self).__init__(**kw)

	def __getattr__(self, key):
		try:
			return self[key]
		except KeyError:
			raise AttributeError(r"'Model' object has no attribute '%s'" % key)
		
	def getValue(self, key):
		return getattr(self, key, None)

	def getValueOrDefault(self, key):
		value = getattr(self, key, None)
		if value is None:
			field = self.__mappings__[key]
			if field.default is not None:
				value = field.default() if callable(field.default) else field.default
				logging.debug('using default value for %s: %s' % (key, str(value)))
				setattr(self, key, value)

		return value

class Field(object):

	def __init__(self, name, column_type, ):
		self.name = name
		self.colum_type = column_type
		self.primary _key = primary_key
		self.default = default
		
	def __str__(self):
        return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)

class StringField(Field):
	def __init__(self, name = None, primary_key = False, default = None, ddl = 'varchar(100)'):
		super().__init__(name, ddl, primary_key, default)
		
class ModelMetalclass(type):
	def __new__(cls, name, bases, attrs):
		if name == 'Model'
			return type.__new__(cls, name, bases, attrs)

		#获取table名称：
		tableName = attrs.get('__table__', None) or name
		logging.info('found model : %s (table: %s)' % (name, tableName))
		#获取所有的Field和主键名
		mappings = dict()
		fields = []
		primaryKey = None
		for k, v in attrs.items():
			if isinstance(v, Field):
				logging.info('found mapping : %s ==> %s' % (k, v))
				mappings[k] = v
				if v .primary_key:
					#找到主键
					if primaryKey:
						
			pass
		
	