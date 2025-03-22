import base64
from urllib import parse

url = ""
sturl = url.lstrip("thunder://")
enUrl = base64.b64decode(sturl).decode("GB2312")
print(parse.unquote(enUrl).strip("AAZZ"))