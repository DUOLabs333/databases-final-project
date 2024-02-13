from routes import users, availabilities

from utils.common import app

app.run(threaded=True,debug=True)
