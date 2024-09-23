from app import app
import os

if __name__ == "__main__":
    app.run(host=os.getenv('host'), port=os.getenv('port'), debug=True)