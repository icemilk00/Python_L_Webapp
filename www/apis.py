
import json, logging, inspect, functools

#简单的几个api错误异常类，用于跑出异常
class APIError(Exception):
	def __init__(self, error, data ='', message=''):
		super(APIError, self).__init__(message)
		self.error = error
		self.data = data
		self.message = message

class APIValueError(APIError):
	"""docstring for APIValueError"""
	def __init__(self, field, message=''):
		super(APIValueError, self).__init__('value:invalid', field, message)

class APIResourceNotFoundError(APIError):
	"""docstring for APIResourceNotFoundError"""
	def __init__(self, arg):
		super(APIResourceNotFoundError, self).__init__('value:notfound', field, message)
		
class APIPermissionError(object):
	"""docstring for APIPermissionError"""
	def __init__(self, arg):
		super(APIPermissionError, self).__init__('permission:forbidden', 'permission', message)
		
		
		
		