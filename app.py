from flask import Flask,render_template
from flask_sqlalchemy import SQLAlchemy
from supabase import create_client, Client

db = SQLAlchemy()


app = Flask(__name__)





url = "https://wfpzhgqqtayplxztptbm.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndmcHpoZ3FxdGF5cGx4enRwdGJtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDc5MTA5OTEsImV4cCI6MjA2MzQ4Njk5MX0.lN1rRKRbrOzcSpPCIvEVfpiVvZCHDh-3QIwB6Yz8mqk"
supabase: Client = create_client(url, key)

data = supabase.table("products").select("*").execute()
print(data)



@app.route("/")
def hello_world():
    return render_template('home.html')


class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2))



@app.route("/all-products")
def loads_product_from_db():
    # fetch all rows
    result = supabase.table("products").select("*").execute()
    products = result.data    
    return render_template('products.html', products=products)


@app.route("/serum")
def serum():
    result = (
        supabase
        .table("products")
        .select("*")
        .eq("category", "Serum")
        .execute()
    )
    products = result.data    
    return render_template('serum.html', products=products)


@app.route("/sunscreen")
def sunscreen():
    result = (
        supabase
        .table("products")
        .select("*")
        .eq("category", "Sunscreen")
        .execute()
    )
    products = result.data    
    return render_template('sunscreen.html', products=products)

@app.route("/moisturizer")
def moisturizer():
    result = (
        supabase
        .table("products")
        .select("*")
        .eq("category", "Moisturizer")
        .execute()
    )
    products = result.data
    return render_template('moisturizer.html', products=products)

@app.route("/bundle")
def cleanser():
    result = (
        supabase
        .table("products")
        .select("*")
        .eq("category", "Moisturizer")
        .execute()
    )    
    products = result.data
    return render_template('bundle.html', products=products)


@app.route("/about")
def about():
    return render_template('about.html')

@app.route("/contact")
def contact():
    return render_template('contact.html')


@app.route("/newarrivals")
def newarrivals():
    return render_template('newarrivals.html')


@app.route("/winter")
def winter():
    result = (
        supabase
        .table("products")
        .select("*")
        .eq("season", "Winter")
        .execute()
    )
    products = result.data
    return render_template('winter.html', products=products)

@app.route("/summer")
def summer():
    result = (
        supabase
        .table("products")
        .select("*")
        .eq("season", "Summer")
        .execute()
    )
    products = result.data
    return render_template('summer.html', products=products)

@app.route("/spring")
def spring():
    result = (
        supabase
        .table("products")
        .select("*")
        .eq("season", "Spring")
        .execute()
    )
    products = result.data
    return render_template('spring.html', products=products)


    

if(__name__ == "__main__"):
    app.run(host='0.0.0.0', port=3000,debug=True)

