import time
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

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
    print("Buscando posts no banco de dados relacional...")
    
    autor = Autor.query.get(autor_id)
    if not autor:
        return jsonify({"erro": "Autor não encontrado"}), 404

    lista_posts = [post.to_dict() for post in autor.posts]

    return jsonify({
        "fonte": "Banco de Dados SQL",
        "autor": autor.nome,
        "posts": lista_posts
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

    return jsonify({
        "mensagem": "Post criado com sucesso!",
        "post": novo_post.to_dict()
    }), 201


if __name__ == '__main__':
    app.run(debug=True)