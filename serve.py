from routes import users, availabilities, bookings, tables, balance, services

from utils.common import app

app.run(threaded=True,debug=True)
