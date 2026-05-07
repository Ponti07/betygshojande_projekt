from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import JWTManager, create_access_token, get_jwt_identity, jwt_required
from datetime import timedelta

app = Flask(__name__)
CORS(app)

app.config["JWT_SECRET_KEY"] = "hemlig-nyckel"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=30)
jwt = JWTManager(app)

db_config = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "fordonsforum"
}


def get_db_connection():
    return mysql.connector.connect(**db_config)


@app.route("/", methods=["GET"])
def api_docs():
    html = """
    <!DOCTYPE html>
    <html lang="sv">
    <head>
        <meta charset="UTF-8">
        <title>Fordonsforum API</title>
    </head>
    <body>
        <h1>Fordonsforum API</h1>
        <p>Välkommen till mitt REST API för fordonsfrågor.</p>

        <h2>Routes</h2>

        <p><b>POST /users</b> - Skapa användare</p>
        <p><b>POST /login</b> - Logga in och få token</p>

        <p><b>GET /topics</b> - Hämta alla fordonsfrågor</p>
        <p><b>GET /topics/&lt;id&gt;</b> - Hämta en fråga med svar</p>
        <p><b>POST /topics</b> - Skapa fordonsfråga - kräver token</p>

        <p><b>POST /topics/&lt;id&gt;/posts</b> - Svara på fråga - kräver token</p>
        <p><b>DELETE /posts/&lt;id&gt;</b> - Ta bort svar - kräver token</p>
    </body>
    </html>
    """
    return html, 200

@app.route("/users", methods=["POST"])
def create_user():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Du måste skicka med JSON-data"}), 400

    username = data.get("username")
    password = data.get("password")
    name = data.get("name")

    if not username or not password or not name:
        return jsonify({
            "error": "Du måste skicka med username, password och name"
        }), 400

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
    if cursor.fetchone():
        cursor.close()
        connection.close()
        return jsonify({"error": "Användarnamnet finns redan"}), 409

    hashed_password = generate_password_hash(password)

    cursor = connection.cursor()
    sql = """
        INSERT INTO users (username, password, name, role)
        VALUES (%s, %s, %s, %s)
    """
    cursor.execute(sql, (username, hashed_password, name, "user"))
    connection.commit()

    user_id = cursor.lastrowid

    cursor.close()
    connection.close()

    return jsonify({
        "id": user_id,
        "username": username,
        "name": name,
        "role": "user"
    }), 201 

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Du måste skicka med JSON-data"}), 400

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Du måste skicka med username och password"}), 400

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()

    cursor.close()
    connection.close()

    if not user:
        return jsonify({"error": "Fel användarnamn eller lösenord"}), 401

    if not check_password_hash(user["password"], password):
        return jsonify({"error": "Fel användarnamn eller lösenord"}), 401

    access_token = create_access_token(identity=str(user["id"]))

    return jsonify({
        "message": "Login successful",
        "access_token": access_token
    }), 200

@app.route("/topics", methods=["GET"])
def get_topics():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    sql = """
        SELECT topics.id, topics.title, topics.category, topics.description,
               topics.created_at, users.username
        FROM topics
        JOIN users ON topics.user_id = users.id
        ORDER BY topics.created_at DESC
    """
    cursor.execute(sql)
    topics = cursor.fetchall()

    cursor.close()
    connection.close()

    return jsonify(topics), 200

@app.route("/topics", methods=["POST"])
@jwt_required()
def create_topic():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Du måste skicka med JSON-data"}), 400

    title = data.get("title")
    category = data.get("category")
    description = data.get("description")

    if not title or not category or not description:
        return jsonify({
            "error": "Du måste skicka med title, category och description"
        }), 400

    current_user = get_jwt_identity()

    connection = get_db_connection()
    cursor = connection.cursor()

    sql = """
        INSERT INTO topics (title, category, description, user_id)
        VALUES (%s, %s, %s, %s)
    """
    cursor.execute(sql, (title, category, description, current_user))
    connection.commit()

    topic_id = cursor.lastrowid

    cursor.close()
    connection.close()

    return jsonify({
        "id": topic_id,
        "title": title,
        "category": category,
        "description": description,
        "user_id": current_user
    }), 201

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({"error": "Token har gått ut"}), 401


@app.route("/protected", methods=["GET"])
@jwt_required()
def protected():
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200


if __name__ == "__main__":
    app.run(debug=True, port=3001)