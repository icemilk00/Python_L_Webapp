import orm, asyncio
from models import User, Blog, Comment

def test(loop):
	yield from orm.create_pool(loop = loop, user = 'root', password='root', db='awsome')

	u = User(name = 'Test', email = 'test@example.com', password = '123', image = 'about:blank')

	yield from u.save()


loop = asyncio.get_event_loop()
loop.run_until_complete(test(loop))
loop.close()