# REQUIRED_FIELDS =['name', 'start_time', 'duration']
# data = {'name':'asd', 'start_time':None, 'duration':''}
# error = filter(lambda x: not data.get(x), REQUIRED_FIELDS)
# print error

from datetime import datetime
import datetime as datetimeTypes
# def make_date(date_string):
#     return datetime.strptime(date_string[:10], "%Y-%m-%d").date()
# 
# def make_time(time_string):
#     return datetime.strptime(time_string[:5], "%H:%M").time()
# # 
# # print type(str(make_time('0:03')))
# 
# class One(object):
#     def put(self, **kw):
#         print kw
#         
# class Two(One):
#     def put(self, **kw):
#         if kw.get('a'):
#             print kw.get('a')
#             print self.x, self.y
#             kw.pop('a')
#         return super(Two, self).put(**kw)
# class Three(Two):
#     def __init__(self):
#         self.x = 10
#         self.y = 11
# 
# # 
# #     
# # a = Three()
# # print a.x
# # 
# # a.put(a=1,b=3)
#         
# def time_to_seconds(my_time):
#     if type(my_time) == str:
#         t = my_time.split(":")
#         return (int(t[0])*60) + int(t[1])
#     elif isinstance(my_time, datetimeTypes.time):
#         return (my_time.hour*60) + my_time.minute
#     else:
#         raise TypeError("time needs to be string or datetime.time")
#     
#     
# print time_to_seconds("14:10")
# mt = make_time("14:10")
# print time_to_seconds(mt)
#         
# def minutes_to_timestring(mysec):
#     minutes = mysec % 60
#     hours = mysec / 60
#     minutes = str(minutes) if minutes>10 else '0'+str(minutes)
#     hours = str(hours) if hours>10 else '0'+str(hours)
#     return str(hours)+":"+minutes
#     
#     
# print minutes_to_timestring(time_to_seconds('19:22'))    
#         


# class One(object):
#     @staticmethod
#     def get(x):
#         print x
#         
#     def miau(self):
#         self.x = 12
#         self.get(self.x)
#         
# a = One()
# 
# a.miau()

# import re
# 
# def is_valid_name(name):
#     if name != name.title():
#         return False
#     # source http://stackoverflow.com/questions/3816332/validate-a-name-in-python
#     regex = re.compile(r"^[^\W0-9_]+([ \-'][^\W0-9_]+)*?$", re.U)
#     return regex.match(name) is not None
# 
# name = "Bublbe Bs"
# 
# print is_valid_name(name)
# 
# a = "ag1kZXZ-dWRwb2plY3Q0cjQLEgdQcm9maWxlIhZyb2JlcnQuYXZyYW1AZ21haWwuY29tDAsSCkNvbmZlcmVuY2UY8S4M"
# 
# b = "ag1kZXZ-dWRwb2plY3Q0ckwLEgdQcm9maWxlIhZyb2JlcnQuYXZyYW1AZ21haWwuY29tDAsSCkNvbmZlcmVuY2UY8S4M"#CxIRQ29uZmVyZW5jZVNlc3Npb24Y8y4M"
# 
# print a == b
# 
# for i in range(len(a)):
#     if a[i]!= b[i]:
#         print a[i:]


# f1 = {"field":"asd", "operator":"=", "value":"newval"}
# f2 = {"field":"bsd", "operator":"=", "value":"newval"}
# f3 = {"field":"csd", "operator":"=", "value":"newval"}
# f4 = {"field":"dsd", "operator":"=", "value":"newval"}
# 
# a=[f3,f1,f2,f4]
# 
# 
# 
#     
# for e in a:
#     print e['field']


import re
pattern=re.compile("[^\w']")

s = "doesn't it rain t-o - day?"

print pattern.sub(' ', s)



























