import datetime


date = datetime.datetime.now() + datetime.timedelta(days=60)

print(date.month)
print(type(date.month))