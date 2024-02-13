from routes import users, availabilities, bookings

from utils.common import app

app.run(threaded=True,debug=True)
