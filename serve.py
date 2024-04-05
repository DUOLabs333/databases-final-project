from routes import users, availabilities, bookings, tables

from utils.common import app

app.run(threaded=True,debug=True)
