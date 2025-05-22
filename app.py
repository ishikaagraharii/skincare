from flask import Flask,render_template
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

@app.route("/")
def hello_world():
    return render_template('home.html')


@app.route("/all products")
def loads_product_from_db():
    return render_template('products.html')
    #return "This page will show all the products"

if(__name__ == "__main__"):
    app.run(host='0.0.0.0', port=3000,debug=True)

