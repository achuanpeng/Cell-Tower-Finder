from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    is_production = os.getenv('FLASK_ENV') == 'production'
    app.run(debug=not is_production)
