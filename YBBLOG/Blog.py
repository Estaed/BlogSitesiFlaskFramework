from flask import Flask,render_template,redirect,url_for,session,logging,request,flash
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from wtforms.validators import Email
from functools import wraps


#Kullanıcı Giriş Kontrol Decoretır
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if("logged_in" in session):
            return f(*args, **kwargs)
        else:
            flash("Bu Sayfayı Görüntülemek İçin Lütfen Giriş Yapın","danger")
            return redirect(url_for("login"))
    return decorated_function


#Kullanıcı Kayıt Formu
class RegisterForm(Form):
    name = StringField("İsim Soyisim",validators = [validators.length(min = 3, max = 25),validators.data_required(message = "Bu Alan Doldurulması Zorunludur")])
    username = StringField("Kullanıcı Adı",validators = [validators.length(min = 3, max = 25),validators.data_required(message = "Bu Alan Doldurulması Zorunludur")])
    email = StringField("Email Adresi",validators = [validators.length(min = 10),validators.Email("Lütfen Geçerli Bir Email Giriniz")])
    password = PasswordField("Parola",validators = [
        validators.data_required(message = "Lütfen Bir Parola Belirleyiniz"),
        validators.EqualTo(fieldname = "confirm",message = "Parolanız uyuşmuyor")
    ])
    confirm = PasswordField("Parola Doğrula")

class LoginForm(Form):
    username = StringField("Kullanıcı Adı")
    password = PasswordField("Parola")

app = Flask(__name__)

app.secret_key = "gizlibirsifre"
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "tbblog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)

@app.route("/")
def index():
    articles = []
    return render_template("index.html",articles = articles)

@app.route("/about")
def about():
    return render_template("about.html")

#Makale oluşturma
@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()

    sorgu = "SELECT * FROM articles"

    result = cursor.execute(sorgu)

    if(result > 0):
        articles = cursor.fetchall()
        return render_template("articles.html",articles = articles)
    else:
        return render_template("articles.html")

#kontrol paneli
@app.route("/dashboard")
@login_required
def dashboard():

    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles WHERE author = %s"
    result = cursor.execute(sorgu,(session["username"],))

    if(result > 0):
        articles = cursor.fetchall()
        return render_template("dashboard.html",articles = articles)
    else:
        return render_template("dashboard.html")

#profi editleme ve profil sayfası
@app.route("/profile/<string:id>",methods = ["GET","POST"])
@login_required
def profile(id):
    if(request.method == "GET"):
        cursor = mysql.connection.cursor()
        sorgu = "SELECT * FROM users WHERE username = %s AND id = %s"

        result = cursor.execute(sorgu,(session["username"],id))

        if result == 0:
            flash("Böyle bir kullanıcı yok ya da işleme yetkiniz yok","danger")
            return redirect(url_for("login"))
        else:
            user = cursor.fetchone()
            form = RegisterForm()

            form.name.data = user["name"]
            form.username.data = user["username"]
            form.email.data = user["email"]
            return render_template("profile.html",form = form)
    else:
        #Post Profile Edit 
        form = RegisterForm(request.form)

        newname = form.name.data
        newusername = form.username.data
        newemail = form.email.data
        newpassword = sha256_crypt.encrypt(form.password.data)

        sorgu2 = "UPDATE users SET name = %s,username = %s,email = %s, password = %s WHERE id = %s"
        cursor = mysql.connection.cursor()
        cursor.execute(sorgu2,(newname,newusername,newemail,newpassword,id))

        mysql.connection.commit()

        flash("Profil başarılıyla güncellendi","success")
        return redirect(url_for("index"))

#Register olma
@app.route("/register",methods = ["GET","POST"])
def register():

    form = RegisterForm(request.form)
    if(request.method == "POST" and form.validate()):

        username = form.username.data
        email = form.email.data
        
        cursor = mysql.connection.cursor()

        username_sorgu = "SELECT * FROM users WHERE username = %s"
        username_result = cursor.execute(username_sorgu,(username,))
        
        email_sorgu = "SELECT * FROM users WHERE email = %s"
        email_result = cursor.execute(email_sorgu,(email,))
 
        if username_result > 0:
            flash("Böyle bir kullanıcı zaten mevcut...","danger")
            return redirect(url_for("register"))
        elif email_result > 0:
            flash("Böyle bir email zaten mevcut...", "danger")
            return redirect(url_for("register"))
        else:

            name = form.name.data
            username = form.username.data
            email = form.email.data
            password = sha256_crypt.encrypt(form.password.data)

            sorgu = "INSERT INTO users(name,email,username,password) VALUES(%s,%s,%s,%s)"

            cursor.execute(sorgu,(name,email,username,password))
            mysql.connection.commit()

            cursor.close()

            flash("Başarıyla Kayıt Oldunuz...","success")

            return redirect(url_for("login"))
    else:
        return render_template("register.html",form = form)

#login işlemi
@app.route("/login",methods = ["GET","POST"])
def login():
    form = LoginForm(request.form)

    if(request.method == "POST"):
        username = form.username.data
        password_entered = form.password.data

        cursor = mysql.connection.cursor()

        sorgu = "SELECT * FROM users WHERE username = %s"
        result = cursor.execute(sorgu,(username,))

        if(result > 0):
            data = cursor.fetchone()
            real_password = data["password"]
            if(sha256_crypt.verify(password_entered,real_password)):
                flash("Başarıyla Giriş Yaptınız...","success")

                session["logged_in"] = True
                session["username"] = username

                return redirect(url_for("index"))
            else:
                flash("Parolanızı Yanlış Girdiniz...","danger")
                return redirect(url_for("login"))
        else:
            flash("Böyle Bir Kullanıcı Bulunmuyor...","danger")
            return redirect(url_for("login"))

    return render_template("login.html",form = form)

#Detay Satfası
@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles WHERE id = %s"

    result = cursor.execute(sorgu,(id,))

    if(result > 0):
        article = cursor.fetchone()
        return render_template("article.html",article = article)
    else:
        return render_template("article.html")
    
#logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

#Makale Ekleme
@app.route("/addarticle", methods = ["GET","POST"])
def addarticle():

    form = ArticleForm(request.form)
    if(request.method == "POST" and form.validate()):
        title = form.title.data
        content = form.content.data

        cursor = mysql.connection.cursor()

        sorgu = "INSERT INTO articles(title,author,content) VALUES(%s,%s,%s)"

        cursor.execute(sorgu,(title,session["username"],content))
        
        mysql.connection.commit()

        cursor.close()

        flash("Makale Başarılıyla Eklendi","success")

        return redirect(url_for("dashboard"))

    return render_template("addarticle.html",form = form)

#Makale Silme
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles WHERE author = %s AND id = %s"

    result = cursor.execute(sorgu,(session["username"],id))

    if(result > 0):
        sorgu2 = "DELETE FROM articles WHERE id = %s"

        cursor.execute(sorgu2,(id,))
        mysql.connection.commit()

        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir makale yok ya da bu makaleyi silme yetkiniz yok","danger")
        return redirect(url_for("index"))

#Makale Güncelle
@app.route("/edit/<string:id>",methods = ["GET","POST"])
@login_required
def update(id):
    if(request.method == "GET"):
        cursor = mysql.connection.cursor()
        sorgu = "SELECT * FROM articles WHERE id = %s AND author = %s"

        result = cursor.execute(sorgu,(id,session["username"]))

        if result == 0:
            flash("Böyle bir makale yok ya da işleme yetkiniz yok","danger")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone()
            form = ArticleForm()

            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("update.html",form = form)
    else:
        #Post Request
        form = ArticleForm(request.form)
        newTitle = form.title.data
        newContent = form.content.data

        sorgu2 = "UPDATE articles SET title = %s,content = %s WHERE id = %s"
        cursor = mysql.connection.cursor()
        cursor.execute(sorgu2,(newTitle,newContent,id))

        mysql.connection.commit()

        flash("Makale başarılıyla güncellendi","success")
        return redirect(url_for("dashboard"))


#Makale Form 
class ArticleForm(Form):
    title = StringField("Makale Başlığı",validators= [validators.length(min = 5, max = 100)])
    content = TextAreaField("Makale İçeriği",validators=[validators.length(min = 10)])

@app.route("/article/<string:id>")
def detail(id):
    return "Article id: " + id

#Arama URL
@app.route("/search",methods = ["GET","POST"])
def search():
    if(request.method == "GET"):
        return redirect(url_for("index"))

    else:
        keyword = request.form.get("keyword")

        cursor = mysql.connection.cursor()

        sorgu = "SELECT * FROM articles WHERE title LIKE '%" + keyword + "%' "
        result = cursor.execute(sorgu)

        if(result == 0):
            flash("Aranan Kelimeye Uygun Makale Bulunamadı","warning")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()

            return render_template("articles.html",articles = articles)

if __name__ == "__main__":
    app.run(debug=True)
