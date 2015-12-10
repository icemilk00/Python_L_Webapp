import re, time, json, logging, hashlib, base64, asyncio

from coroweb import get, post
from aiohttp import web

from models import User, Comment, Blog, next_id

from config import configs

from apis import Page, APIValueError, APIResourceNotFoundError,APIError
import markdown2
logging.basicConfig(level=logging.DEBUG)

#email的匹配正则表达式
_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
#密码的匹配正则表达式
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret

def check_admin(request):
	if request.__user__ is None or not request.__user__.admin:
		raise APIPermissionError()

def get_page_index(page_str):
	p = 1
	try:
		p = int(page_str)
	except ValueError as e:
		pass
	if p < 1:
		p = 1
	return p

def text2html(text):
	lines = map(lambda s: '<p>%s</p>' % s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'), filter(lambda s: s.strip() != '', text.split('\n')))
	return ''.join(lines)

def user2cookie(user, max_age):
	# build cookie string by: id-expires-sha1
	#过期时间是当前时间+设置的有效时间
	expires = str(int(time.time() + max_age))
	#构建cookie存储的信息字符串
	s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
	L = [user.id , expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
	#用-隔开，返回
	return '-'.join(L)

@asyncio.coroutine
def cookie2user(cookie_str):
	#cookie_str是空则返回
	if not cookie_str:
		return None
	try:
		#通过'-'分割字符串
		L = cookie_str.split('-')
		#如果不是3个元素的话，与我们当初构造sha1字符串时不符，返回None
		if len(L) != 3:
			return None
		#分别获取到用户id，过期时间和sha1字符串
		uid, expires, sha1 = L
		#如果超时，返回None
		if int(expires) < time.time():
			return None
		#根据用户id查找库，对比有没有该用户
		user = yield from User.find(uid)
		#没有该用户返回None
		if user is None:
			return None
		#根据查到的user的数据构造一个校验sha1字符串
		s = '%s-%s-%s-%s' % (uid, user.passwd, expires, _COOKIE_KEY)
		#比较cookie里的sha1和校验sha1，一样的话，说明当前请求的用户是合法的
		if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
			logging.info('invalid sha1')
			return None
		user.passwd = '******'
		#返回合法的user
		return user
	except Exception as e:
		logging.excepetion(e)
		return None

# @get('/')
# def index(request):
# 	summary = 'Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
# 	blogs = [
# 		Blog(id='1', name='Test Blog', summary=summary, created_at=time.time()-120),
# 		Blog(id='2', name='Something New', summary=summary, created_at=time.time()-3600),
# 		Blog(id='3', name='Learn Swift', summary=summary, created_at=time.time()-7200)
# 	]
# 	return {
# 		'__template__': 'blogs.html',
# 		'blogs': blogs
# 	}

@get('/')
def index(*, page='1'):
	page_index = get_page_index(page)
	num = yield from Blog.findNumber('count(id)')
	page = Page(num)
	if num == 0:
		blogs = []
	else:
		blogs = yield from Blog.findAll(orderBy='created_at desc', limit=(page.offset, page.limit))
	return {
		'__template__': 'blogs.html',
		'page': page,
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

@get('/signin')
def signin():
	return {
		'__template__':'signin.html'
	}

@get('/signout')
def signout(request):
	referer = request.headers.get('Referer')
	r = web.HTTPFound(referer or '/')
	r.set_cookie(COOKIE_NAME, '-deleted-', max_age=0, httponly=True)
	logging.info('user signed out')
	return r

#
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

	admin = False
	if email == 'admin@163.com':
		admin = True

	#创建一个用户（密码是通过sha1加密保存）
	user = User(id = uid, name = name.strip(), email=email, passwd = hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(), image = 'http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest(), admin=admin)

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

@post('/api/authenticate')
def authenticate(*, email, passwd):
	#如果email或passwd为空，都说明有错误
	if not email:
		raise APIValueError('email', 'Invalid email')
	if not passwd:
		raise APIValueError('passwd', 'Invalid  passwd')
	#根据email在库里查找匹配的用户
	users = yield from User.findAll('email=?', [email])
	#没找到用户，返回用户不存在
	if len(users) == 0:
		raise APIValueError('email', 'email not exist')
	#取第一个查到用户，理论上就一个
	user = users[0]
	#按存储密码的方式获取出请求传入的密码字段的sha1值
	sha1 = hashlib.sha1()
	sha1.update(user.id.encode('utf-8'))
	sha1.update(b':')
	sha1.update(passwd.encode('utf-8'))
	#和库里的密码字段的值作比较，一样的话认证成功，不一样的话，认证失败
	if user.passwd != sha1.hexdigest():
		raise APIValueError('passwd', 'Invalid passwd')
	#构建返回信息
	r = web.Response()
	#添加cookie
	r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
	#只把要返回的实例的密码改成'******'，库里的密码依然是正确的，以保证真实的密码不会因返回而暴漏
	user.passwd = '******'
	#返回的是json数据，所以设置content-type为json的
	r.content_type = 'application/json'
	#把对象转换成json格式返回
	r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
	return r

@get('/manage/')
def manage():
	return 'redirect:/manage/comments'

@get('/manage/comments')
def manage_comments(*, page='1'):
	return {
		'__template__': 'manage_comments.html',
		'page_index': get_page_index(page)
	}

@get('/api/comments')
def api_comments(*, page='1'):
	page_index = get_page_index(page)
	num = yield from Comment.findNumber('count(id)')
	p = Page(num, page_index)
	if num == 0:
		return dict(page=p, comments=())
	comments = yield from Comment.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
	return dict(page=p, comments = comments)

@post('/api/blogs/{id}/comments')
def api_create_comment(id, request, *, content):
	user = request.__user__
	if user is None:
		raise APIPermissionError('content')
	if not content or not content.strip():
		raise APIValueError('content')
	blog = yield from Blog.find(id)
	if blog is None:
		raise APIResourceNotFoundError('Blog')
	comment = Comment(blog_id=blog.id, user_id=user.id, user_name=user.name, user_image=user.image, content=content.strip())
	yield from comment.save()
	return comment

@post('/api/comments/{id}/delete')
def api_delete_comments(id, request):
	logging.info(id)
	check_admin(request)
	c = yield from Comment.find(id)
	if c is None:
		raise APIResourceNotFoundError('Comment')
	yield from c.remove()
	return dict(id=id)



@get('/manage/blogs/create')
def manage_create_blog():
	return {
		'__template__':'manage_blog_edit.html',
		'id':'',
		'action':'/api/blogs'
	}

@get('/manage/blogs')
def manage_blogs(*, page='1'):
	return {
		'__template__':'manage_blogs.html',
		'page_index':get_page_index(page)
	}

@get('/manage/users')
def manage_users(*, page='1'):
	return {
		'__template__':'manage_users.html',
		'page_index':get_page_index(page)
	}

@get('/api/blogs')
def api_blogs(*, page='1'):
	page_index = get_page_index(page)
	num = yield from Blog.findNumber('count(id)')
	p = Page(num, page_index)
	if num == 0:
		return dict(page=p, blogs=())
	blogs = yield from Blog.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
	return dict(page=p, blogs=blogs)


@post('/api/blogs')
def api_create_blog(request, *, name, summary, content):
	check_admin(request)
	if not name or not name.strip():
		raise APIValueError('name', 'name cannot be empty')
	if not summary or not summary.strip():
		raise APIValueError('summary', 'summary cannot be empty')
	if not content or not content.strip():
		raise APIValueError('content', 'content cannot be empty')

	blog = Blog(user_id=request.__user__.id, user_name=request.__user__.name,user_image=request.__user__.image, name=name.strip(), summary=summary.strip(), content=content.strip()) 
	yield from blog.save()
	return blog

@get('/blog/{id}')
def get_blog(id):
	blog = yield from Blog.find(id)
	comments = yield from Comment.findAll('blog_id=?',[id], orderBy='created_at desc')
	for c in comments:
		c.html_content = text2html(c.content)
	blog.html_content = markdown2.markdown(blog.content)
	return {
		'__template__':'blog.html',
		'blog':blog,
		'comments':comments
	}

@get('/api/blogs/{id}')
def api_get_blog(*, id):
	blog = yield from Blog.find(id)
	return blog

