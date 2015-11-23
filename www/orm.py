
import asyncio, logging
logging.basicConfig(level=logging.DEBUG)
import aiomysql

def log(sql, args=()):
    logging.info('SQL: %s' % sql)

@asyncio.coroutine
def create_pool(loop, **kw):
	logging.info('create database connecting pool ...')
	#全局变量__pool
	global __pool
	#创建数据库连接池
	__pool = yield from aiomysql.create_pool(
		host = kw.get('host', '127.0.0.1'),			#host固定为127.0.0.1
		port = kw.get('port', 3306),				#port固定位3306
		user = kw['user'],							#user取传入的参数key为user的值
		password = kw['password'],					#password取传入的参数key为password的值
		db = kw['db'],								#db取传入的参数key为db的值
		charset = kw.get('charset', 'utf8'),		#编码为utf8
		autocommit = kw.get('autocommit', True),	#自动提交事务设为开启
		maxsize = kw.get('maxsize', 10),			#连接池最多10条连接，默认是10
		minsize = kw.get('minsize', 1),				#连接池最少1条连接，默认是10
		loop = loop									#运行loop为传入的loop
		)

#select函数，负责查询
@asyncio.coroutine
def select(sql, args, size=None):
	log(sql, args)
	global __pool
	#从连接池取一个conn出来，with..as..会在运行完后把conn放回连接池
	with (yield from _pool) as conn:
		#获取一个cursor，通过aiomysql.DictCursor获取到的cursor在返回结果时会返回一个字典格式
		cur = yield from conn.cursor(aiomysql.DictCursor)
		#把sql语句的'?'替换为'%s',并把args的值填充到相应的位置补充成完整的可执行sql语句并执行，mysql中得占位符是'?'，python中得为'%s'
		yield from cur.execute(sql.replace('?', '%s'), args)
		#如果有要求的返回行数，则取要求的行数，如果没有，则全部取出
		if size:
			rs = yield from cur.fetchmany(size)			#取定行
		else:
			rs = yield from cur.fetchall()				#全取

		yield from cur.close()		#关闭cursor
		logging.info('rows returned : %s' % len(rs))
		return rs

#sql语句执行函数
@asyncio.coroutine
def execute(sql, args):
	log(sql)
	log(args)
	#从连接池取一个conn出来，with..as..会在运行完后把conn放回连接池
	with (yield from __pool) as conn:
		try:
			#获取一个cursor
			cur = yield from conn.cursor()
			#执行要执行的sql语句
			yield from cur.execute(sql.replace('?', '%s'), args or ())
			#取出执行结果的条数
			affected = cur.rowcount
			#关闭cursor
			yield from cur.close()
		except BaseException as e:	
			raise
		return affected			#返回执行结果条数

#构造sql语句参数字符串，最后返回的字符串会以','分割多个'?'，如 num==2，则会返回 '?, ?'
def create_args_string(num):
    L = []
    for n in range(num):
        L.append('?')
    return ', '.join(L)

#用于标识model里每个成员变量的类
#name:名字
#column_type:值类型
#primary_key:是否primary_key
#default:默认值
class Field(object):
	#init函数，在对象new之后初始化的时候自动调用，这里初始化一些成员变量
	def __init__(self, name, column_type,  primary_key, default):
		self.name = name
		self.column_type = column_type
		self.primary_key = primary_key
		self.default = default
	#直接打印对象的实现方法
	def __str__(self):
		return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)
#string类型的默认设定
class StringField(Field):
	def __init__(self, name = None, primary_key = False, default = None, ddl = 'varchar(100)'):
		super().__init__(name, ddl, primary_key, default)
#bool类型的默认设定
class BooleanField(Field):
	def __init__(self, name = None, default = False):
		super().__init__(name, 'boolern', False, default)
#integer类型的默认设定
class IntegerField(Field):
    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)
#float类型的默认设定
class FloatField(Field):
    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)
#text类型的默认设定
class TextField(Field):
    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)

#model元类，元类可以创建类对象。可以查看这个http://blog.jobbole.com/21351/，了解元类
class ModelMetalclass(type):
	#new函数
	#cls:
	#name:创建的类名
	#bases:父类的数组，可为空， 如果有值的话，生成的类是继承此数组里的类的
	#attrs:包含属性的字典
	def __new__(cls, name, bases, attrs):
		#如果当前类是Model类
		log(name)
		if name == 'Model':
			return type.__new__(cls, name, bases, attrs)

		#Model的子类会继续往下走
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
						raise RuntimeError('Duplicate primary key for field:%s' % k)
					primaryKey = k
				else:
					fields.append(k)

		if not primaryKey:
			raise RuntimeError('Primary key not found')
		for k in mappings.keys():
			attrs.pop(k)

		escaped_fields = list(map(lambda f : '`%s`' % f, fields))
		attrs['__mappings__'] = mappings  #保存属性和列的映射关系
		attrs['__table__'] = tableName
		attrs['__primary_key__'] = primaryKey #主键属性名
		attrs['__fields__'] = fields # 除主键外的属性名
		# 构造默认的SELECT, INSERT, UPDATE和DELETE语句:
		attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ', '.join(escaped_fields), tableName)
		attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
		attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
		attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
		return type.__new__(cls, name, bases, attrs)

		
class Model(dict, metaclass = ModelMetalclass):
	def __init__(self, **kw):
		super(Model, self).__init__(**kw)

	def __getattr__(self, key):
		try:
			return self[key]
		except KeyError:
			raise AttributeError(r"'Model' object has no attribute '%s'" % key)

	def __setattr__(self, key, value):
		self[key] = value
		
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

	@classmethod
	@asyncio.coroutine
	def find(cls, pk):
		'find object by primary key'
		rs = yield from select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
		if len(rs) == 0:
			return None
		return cls(**rs[0])

	@asyncio.coroutine
	def save(self):
		args = list(map(self.getValueOrDefault, self.__fields__))
		args.append(self.getValueOrDefault(self.__primary_key__))
		# print(args);
		rows  = yield from execute(self.__insert__, args)
		if rows != 1:
			logging.warn('failed to insert record: affected rows :%s' % rows)

	@asyncio.coroutine
	def update(self):
		args = list(map(self.getValue, self.__fields__))
		args.append(self.getValue(self.__primary_key__))
		rows = yield from execute(self.__update__, args)
		if rows != 1:
			logging.warn('failed to update by primary key: affected rows: %s' % rows)

	@asyncio.coroutine
	def remove(self):
		args = [self.getValue(self.__primary_key__)]
		rows = yield from execute(self.__delete__, args)
		if rows != 1:
			logging.warn('failed to remove by primary key: affected rows: %s' % rows)
	