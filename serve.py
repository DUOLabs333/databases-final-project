from routes import users, messages, availabilities, actions

from utils.common import app

app.run(threaded=True,debug=True)
