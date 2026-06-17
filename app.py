import json
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import redis

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

class Autor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False, unique=True)
    
    posts = db.relationship('Post', backref='autor', lazy=True)

    def to_dict(self):
        return {"id": self.id, "nome": self.nome}

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    conteudo = db.Column(db.Text, nullable=False)
    
    autor_id = db.Column(db.Integer, db.ForeignKey('autor.id'), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "titulo": self.titulo,
            "conteudo": self.conteudo,
            "autor_id": self.autor_id
        }

with app.app_context():
    db.create_all()
    if not Autor.query.first():
        autor1 = Autor(nome="Carlos Silva")
        autor2 = Autor(nome="Ana Souza")
        db.session.add_all([autor1, autor2])
        db.session.commit()

        post1 = Post(titulo="Começando com Flask", conteudo="Flask é micro, mas poderoso.", autor_id=autor1.id)
        post2 = Post(titulo="Dicas de SQL", conteudo="Aprenda a estruturar seus bancos.", autor_id=autor1.id)
        post3 = Post(titulo="O futuro da IA", conteudo="Como a tecnologia está mudando o mundo.", autor_id=autor2.id)
        db.session.add_all([post1, post2, post3])
        db.session.commit()

@app.route('/autores/<int:autor_id>/posts', methods=['GET'])
def listar_posts_por_autor(autor_id):
    redis_key = f"autor:{autor_id}:posts"

    cache_posts = redis_client.get(redis_key)
    if cache_posts:
        print("[REDIS] Retornando posts direto do Redis...")
        dados_cache = json.loads(cache_posts)
        return jsonify({
            "autor": dados_cache["autor"],
            "posts": dados_cache["posts"]
        })

    print("[SQL] Buscando posts no banco de dados relacional...")
    autor = Autor.query.get(autor_id)
    if not autor:
        return jsonify({"erro": "Autor não encontrado"}), 404

    lista_posts = [post.to_dict() for post in autor.posts]
    
    estrutura_retorno = {
        "autor": autor.nome,
        "posts": lista_posts
    }

    redis_client.set(redis_key, json.dumps(estrutura_retorno), ex=300)
    print("Dados salvos no Redis para as próximas requisições.")

    return jsonify({
        **estrutura_retorno
    })

@app.route('/autores', methods=['GET'])
def listar_todos_autores():
    redis_key = "autores:todos"

    cache_autores = redis_client.get(redis_key)
    if cache_autores:
        print("[REDIS] Retornando lista de autores do Redis...")
        return jsonify({
            "autores": json.loads(cache_autores)
        })

    print("[SQL] Buscando todos os autores no banco...")
    autores = Autor.query.all()
    lista_autores = [autor.to_dict() for autor in autores]

    redis_client.set(redis_key, json.dumps(lista_autores), ex=300)
    
    return jsonify({
        "autores": lista_autores
    })

@app.route('/posts', methods=['POST'])
def criar_post():
    dados = request.get_json()
    
    titulo = dados.get('titulo')
    conteudo = dados.get('conteudo')
    autor_id = dados.get('autor_id')

    if not titulo or not conteudo or not autor_id:
        return jsonify({"erro": "Dados incompletos"}), 400

    if not Autor.query.get(autor_id):
        return jsonify({"erro": "Autor informado não existe"}), 400

    novo_post = Post(titulo=titulo, conteudo=conteudo, autor_id=autor_id)
    db.session.add(novo_post)
    db.session.commit()

    redis_key = f"autor:{autor_id}:posts"
    redis_client.delete(redis_key)
    print(f"[REDIS] Cache limpo para a chave: {redis_key} devido a um novo post.")

    return jsonify({
        "mensagem": "Post criado com sucesso!",
        "post": novo_post.to_dict()
    }), 201

if __name__ == '__main__':
    app.run(debug=True)