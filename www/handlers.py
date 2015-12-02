import re, time, json, logging, hashlib, base64, asyncio

from coroweb import get, post

from models import User, Comment, Blog, next_id

logging.basicConfig(level=logging.DEBUG)

@get('/')
def index(request):
	users = yield from User.findAll()
	logging.info('to index...')
	return {
		'__template__':'test.html',
		'users': users
	}