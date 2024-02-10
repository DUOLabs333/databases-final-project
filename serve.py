from routes import users, availabilities, actions

from utils.common import app

app.run(threaded=True,debug=True)
