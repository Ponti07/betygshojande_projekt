from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import mysql.connector
import os
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_jwt_extended import JWTManager, create_access_token, get_jwt_identity, jwt_required
from datetime import timedelta

app = Flask(__name__)
CORS(app)

app.config["JWT_SECRET_KEY"] = "hemlig-nyckel"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=30)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
jwt = JWTManager(app)

UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_image(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

db_config = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "fordonsforum"
}


def get_db_connection():
    return mysql.connector.connect(**db_config)


@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

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
        "access_token": access_token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "name": user["name"]
        }
    }), 200

@app.route("/topics", methods=["GET"])
def get_topics():
    category = request.args.get("category")
    q = request.args.get("q")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    base_sql = """
        SELECT topics.id, topics.title, topics.category, topics.description,
               topics.image_path, topics.created_at, topics.user_id, users.username
        FROM topics
        JOIN users ON topics.user_id = users.id
    """

    conditions = []
    params = []
    if category:
        conditions.append("topics.category = %s")
        params.append(category)
    if q:
        conditions.append("(topics.title LIKE %s OR topics.description LIKE %s)")
        like_pattern = f"%{q}%"
        params.append(like_pattern)
        params.append(like_pattern)

    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    cursor.execute(base_sql + where + " ORDER BY topics.created_at DESC", tuple(params))

    topics = cursor.fetchall()

    cursor.close()
    connection.close()

    return jsonify(topics), 200

@app.route("/topics", methods=["POST"])
@jwt_required()
def create_topic():
    title = request.form.get("title")
    category = request.form.get("category")
    description = request.form.get("description")

    if not title or not category or not description:
        return jsonify({
            "error": "Du måste skicka med title, category och description"
        }), 400

    image = request.files.get("image")
    image_path = None
    if image and image.filename:
        safe_name = secure_filename(image.filename)
        if not safe_name or not allowed_image(safe_name):
            return jsonify({"error": "Otillåten filtyp"}), 400
        ext = safe_name.rsplit(".", 1)[1].lower()
        stored_name = f"{uuid.uuid4().hex}.{ext}"
        image.save(os.path.join(UPLOAD_FOLDER, stored_name))
        image_path = f"uploads/{stored_name}"

    current_user = get_jwt_identity()

    connection = get_db_connection()
    cursor = connection.cursor()

    sql = """
        INSERT INTO topics (title, category, description, image_path, user_id)
        VALUES (%s, %s, %s, %s, %s)
    """
    cursor.execute(sql, (title, category, description, image_path, current_user))
    connection.commit()

    topic_id = cursor.lastrowid

    cursor.close()
    connection.close()

    return jsonify({
        "id": topic_id,
        "title": title,
        "category": category,
        "description": description,
        "image_path": image_path,
        "user_id": current_user
    }), 201

@app.route("/topics/<int:topic_id>", methods=["DELETE"])
@jwt_required()
def delete_topic(topic_id):
    current_user = get_jwt_identity()

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        "SELECT user_id, image_path FROM topics WHERE id = %s",
        (topic_id,)
    )
    topic = cursor.fetchone()

    if not topic:
        cursor.close()
        connection.close()
        return jsonify({"error": "Frågan hittades inte"}), 404

    if str(topic["user_id"]) != str(current_user):
        cursor.close()
        connection.close()
        return jsonify({"error": "Du får bara ta bort dina egna frågor"}), 403

    cursor.execute("DELETE FROM replies WHERE topic_id = %s", (topic_id,))
    cursor.execute("DELETE FROM topics WHERE id = %s", (topic_id,))
    connection.commit()

    cursor.close()
    connection.close()

    if topic["image_path"]:
        try:
            os.remove(os.path.join(app.root_path, "static", topic["image_path"]))
        except OSError:
            pass

    return jsonify({"message": "Frågan togs bort"}), 200


@app.errorhandler(413)
def too_large(_):
    return jsonify({"error": "Bilden är för stor (max 5 MB)"}), 413

@app.route("/topics/<int:topic_id>/replies", methods=["GET"])
def get_replies(topic_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    sql = """
        SELECT replies.id, replies.parent_reply_id, replies.content,
               replies.created_at, replies.user_id, users.username
        FROM replies
        JOIN users ON replies.user_id = users.id
        WHERE replies.topic_id = %s
        ORDER BY replies.created_at ASC
    """
    cursor.execute(sql, (topic_id,))
    replies = cursor.fetchall()

    cursor.close()
    connection.close()

    return jsonify(replies), 200

@app.route("/topics/<int:topic_id>/replies", methods=["POST"])
@jwt_required()
def create_reply(topic_id):
    data = request.get_json()

    if not data:
        return jsonify({"error": "Du måste skicka med JSON-data"}), 400

    content = data.get("content")
    parent_reply_id = data.get("parent_reply_id")

    if not content or not content.strip():
        return jsonify({"error": "Du måste skicka med content"}), 400

    current_user = get_jwt_identity()

    connection = get_db_connection()
    cursor = connection.cursor()

    sql = """
        INSERT INTO replies (topic_id, parent_reply_id, user_id, content)
        VALUES (%s, %s, %s, %s)
    """
    cursor.execute(sql, (topic_id, parent_reply_id, current_user, content))
    connection.commit()

    reply_id = cursor.lastrowid

    cursor.close()
    connection.close()

    return jsonify({
        "id": reply_id,
        "topic_id": topic_id,
        "parent_reply_id": parent_reply_id,
        "content": content,
        "user_id": current_user
    }), 201

@app.route("/replies/<int:reply_id>", methods=["DELETE"])
@jwt_required()
def delete_reply(reply_id):
    current_user = get_jwt_identity()

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT user_id FROM replies WHERE id = %s", (reply_id,))
    reply = cursor.fetchone()

    if not reply:
        cursor.close()
        connection.close()
        return jsonify({"error": "Svaret hittades inte"}), 404

    if str(reply["user_id"]) != str(current_user):
        cursor.close()
        connection.close()
        return jsonify({"error": "Du får bara ta bort dina egna svar"}), 403

    to_delete = [reply_id]
    frontier = [reply_id]
    while frontier:
        placeholders = ",".join(["%s"] * len(frontier))
        cursor.execute(
            f"SELECT id FROM replies WHERE parent_reply_id IN ({placeholders})",
            tuple(frontier)
        )
        frontier = [r["id"] for r in cursor.fetchall()]
        to_delete.extend(frontier)

    placeholders = ",".join(["%s"] * len(to_delete))
    cursor.execute(
        f"DELETE FROM replies WHERE id IN ({placeholders})",
        tuple(to_delete)
    )
    connection.commit()

    cursor.close()
    connection.close()

    return jsonify({"message": "Svaret togs bort"}), 200

@app.route("/me", methods=["GET"])
@jwt_required()
def get_me():
    current_user = get_jwt_identity()

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, username, name, role FROM users WHERE id = %s",
        (current_user,)
    )
    user = cursor.fetchone()
    cursor.close()
    connection.close()

    if not user:
        return jsonify({"error": "Användare hittades inte"}), 404

    return jsonify(user), 200

@app.route("/me/topics", methods=["GET"])
@jwt_required()
def get_my_topics():
    current_user = get_jwt_identity()

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    sql = """
        SELECT id, title, category, description, image_path, created_at, user_id
        FROM topics
        WHERE user_id = %s
        ORDER BY created_at DESC
    """
    cursor.execute(sql, (current_user,))
    topics = cursor.fetchall()

    cursor.close()
    connection.close()

    return jsonify(topics), 200

@app.route("/me/replies", methods=["GET"])
@jwt_required()
def get_my_replies():
    current_user = get_jwt_identity()

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    sql = """
        SELECT replies.id, replies.topic_id, replies.parent_reply_id,
               replies.content, replies.created_at, replies.user_id,
               topics.title AS topic_title
        FROM replies
        JOIN topics ON replies.topic_id = topics.id
        WHERE replies.user_id = %s
        ORDER BY replies.created_at DESC
    """
    cursor.execute(sql, (current_user,))
    replies = cursor.fetchall()

    cursor.close()
    connection.close()

    return jsonify(replies), 200

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