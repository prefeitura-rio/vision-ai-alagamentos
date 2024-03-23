wsgi_app = 'app.server:start(model_address="tcp://127.0.0.1:5555")'
bind = "0.0.0.0:40000"
workers = 5
timeout = 180
