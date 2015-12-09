import re, time, json, logging, hashlib, base64, asyncio

from coroweb import get, post
from aiohttp import web

from models import User, Comment, Blog, next_id

from config import configs

from apis import APIValueError, APIResourceNotFoundError,APIError

logging.basicConfig(level=logging.DEBUG)

#email的匹配正则表达式
_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
#密码的匹配正则表达式
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret

def user2cookie(user, max_age):
	# build cookie string by: id-expires-sha1
	#过期时间是当前时间+设置的有效时间
	expires = str(int(time.time() + max_age))
	#构建cookie存储的信息字符串
	s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
	L = [user.id , expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
	#用-隔开，返回
	return '-'.join(L)

@get('/')
def index(request):
	summary = 'Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
	blogs = [
		Blog(id='1', name='Test Blog', summary=summary, created_at=time.time()-120),
		Blog(id='2', name='Something New', summary=summary, created_at=time.time()-3600),
		Blog(id='3', name='Learn Swift', summary=summary, created_at=time.time()-7200)
	]
	return {
		'__template__': 'blogs.html',
		'blogs': blogs
	}

@get('/show_all_users')
def show_all_users():
	users = yield from User.findAll()
	logging.info('to index...')
	# return (404, 'not found')

	return {
		'__template__':'test.html',
		'users': users
	}

@get('/api/users')
def api_get_users(request):
	users = yield from User.findAll(orderBy='created_at desc')
	logging.info('users = %s and type = %s' % (users, type(users)))
	for u in users:
		u.passwd = '******'
	return dict(users=users)

# @get('/api/users')
# def api_get_users(*, page='1'):
# 	page_index = get_page_index(page)
# 	num = yield from User.findNumber('count(id)')
# 	p = Page(num, page_index)
# 	if num == 0:
# 		return dict(page=p, users=())
# 	users = yield from User.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
# 	for u in users:
# 		u.passwd = '******'
# 	return dict(page=p, users=users)

@get('/register')
def register():
	return {
		'__template__': 'register.html'
	}


@post('/api/users')
def api_register_user(*, email, name, passwd):
	#判断name是否存在，且是否只是'\n', '\r',  '\t',  ' '，这种特殊字符
	if not name or not name.strip():
		raise APIValueError('name')
	#判断email是否存在，且是否符合规定的正则表达式
	if not email or not _RE_EMAIL.match(email):
		raise APIValueError('email')
	#判断passwd是否存在，且是否符合规定的正则表达式
	if not passwd or not _RE_SHA1.match(passwd):
		raise APIValueError('passwd')

	#查一下库里是否有相同的email地址，如果有的话提示用户email已经被注册过
	users = yield from User.findAll('email=?', [email])
	if len(users) > 0:
		raise APIError('register:failed', 'email', 'Email is already in use.')

	#生成一个当前要注册用户的唯一uid
	uid = next_id()
	#构建shal_passwd
	sha1_passwd = '%s:%s' % (uid, passwd)
	#创建一个用户（密码是通过sha1加密保存）
	user = User(id = uid, name = name.strip(), email=email, passwd = hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(), image = 'http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())

	#保存这个用户到数据库用户表
	yield from user.save()
	logging.info('save user OK')
	#构建返回信息
	r = web.Response()
	#添加cookie
	r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age = 86400, httponly = True)
	#只把要返回的实例的密码改成'******'，库里的密码依然是正确的，以保证真实的密码不会因返回而暴漏
	user.passwd = '******'
	#返回的是json数据，所以设置content-type为json的
	r.content_type= 'application/json'
	#把对象转换成json格式返回
	r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
	return r
