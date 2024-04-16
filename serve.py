from routes import users, availabilities, bookings, tables, balance

from utils.common import app

app.run(threaded=True,debug=True)
