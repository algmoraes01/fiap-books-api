from flask import Flask, jsonify, request
from flask_restx import Api, Resource, fields
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
import pandas as pd
from config import Config
import datetime

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

authorizations = {
    "Bearer Auth": {
        "type": "apiKey",
        "in": "header",
        "name": "Authorization",
        "description": "Insira o token JWT no formato: Bearer <seu_token>"
    }
}

api = Api(
    app,
    version="1.0",
    title="Books API",
    description="API pública de consulta de livros - FIAP",
    authorizations=authorizations
)

jwt = JWTManager(app)

ns = api.namespace("api/v1", description="Operações da API")

books_df = pd.read_csv(Config.DATA_PATH)

book_model = api.model("Book", {
    "title": fields.String,
    "price": fields.String,
    "availability": fields.String,
    "rating": fields.String,
    "category": fields.String,
    "image": fields.String
})

user_model = api.model("User", {
    "username": fields.String(required=True),
    "password": fields.String(required=True)
})

metric_model = api.model("Metrics", {
    "total_requests": fields.Integer,
    "last_request_time": fields.String
})

metrics_data = {"total_requests": 0, "last_request_time": None}

@app.before_request
def before_request():
    metrics_data["total_requests"] += 1
    metrics_data["last_request_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@ns.route("/health")
class Health(Resource):
    def get(self):
        return {"status": "API online"}

@ns.route("/books")
class Books(Resource):
    @ns.marshal_with(book_model, as_list=True)
    def get(self):
        return books_df.to_dict(orient="records")

@ns.route("/books/<int:id>")
class BookById(Resource):
    @ns.marshal_with(book_model)
    def get(self, id):
        if 0 <= id < len(books_df):
            return books_df.iloc[id].to_dict()
        api.abort(404, "Livro não encontrado")

@ns.route("/books/search")
@ns.doc(params={
    "title": "Título (ou parte dele) para busca — exemplo: 'Harry'",
    "category": "Categoria (ou parte dela) — exemplo: 'Science Fiction'"
})
class BookSearch(Resource):
    @ns.marshal_with(book_model, as_list=True)
    @ns.response(200, "Livros encontrados com base nos filtros aplicados")
    @ns.response(404, "Nenhum livro encontrado")
    def get(self):
        title = request.args.get("title", "").lower()
        category = request.args.get("category", "").lower()

        result = books_df.copy()

        if title:
            result = result[result["title"].str.lower().str.contains(title, na=False)]
        if category:
            result = result[result["category"].str.lower().str.contains(category, na=False)]

        if result.empty:
            api.abort(404, "Nenhum livro encontrado com os filtros fornecidos.")

        return result.to_dict(orient="records")

@ns.route("/categories")
class Categories(Resource):
    def get(self):
        categories = sorted(books_df["category"].dropna().unique().tolist())
        return jsonify(categories)

@ns.route("/auth/login")
class Login(Resource):
    @ns.expect(user_model)
    def post(self):
        data = request.get_json()
        if data["username"] == "admin" and data["password"] == "123456":
            token = create_access_token(identity=data["username"])
            return {"access_token": token}
        return {"message": "Credenciais inválidas"}, 401

@ns.route("/auth/refresh")
class Refresh(Resource):
    @jwt_required()
    @ns.doc(security="Bearer Auth")
    def post(self):
        current_user = get_jwt_identity()
        new_token = create_access_token(identity=current_user)
        return {"access_token": new_token}

@ns.route("/scraping/trigger")
class ScrapingTrigger(Resource):
    @jwt_required()
    @ns.doc(security="Bearer Auth")
    def post(self):
        user = get_jwt_identity()
        return {"message": f"Scraping iniciado por {user}"}

@ns.route("/ml/predictions")
class MLPredictions(Resource):
    @jwt_required()
    @ns.doc(security="Bearer Auth")
    def post(self):
        data = request.get_json()
        return {"message": "Endpoint de Machine Learning - em desenvolvimento", "input": data}

@ns.route("/stats/overview")
class StatsOverview(Resource):
    def get(self):
        """
        Retorna estatísticas gerais da coleção de livros.
        """
        df = books_df.copy()

        df["price_value"] = (
            df["price"]
            .astype(str)
            .str.replace("Â", "", regex=False)
            .str.replace("£", "", regex=False)
            .str.strip()
        )
        df["price_value"] = pd.to_numeric(df["price_value"], errors="coerce")
        df = df.dropna(subset=["price_value"])

        total_books = len(df)
        avg_price = df["price_value"].mean()
        available = df[df["availability"].str.contains("In stock", na=False)].shape[0]
        unavailable = total_books - available

        return {
            "total_books": total_books,
            "average_price": round(avg_price, 2),
            "available": available,
            "unavailable": unavailable
        }

@ns.route("/stats/categories")
class StatsCategories(Resource):
    def get(self):
        """
        Retorna estatísticas detalhadas por categoria.
        """
        df = books_df.copy()

        df["price_value"] = (
            df["price"]
            .astype(str)
            .str.replace("Â", "", regex=False)
            .str.replace("£", "", regex=False)
            .str.strip()
        )
        df["price_value"] = pd.to_numeric(df["price_value"], errors="coerce")
        df = df.dropna(subset=["price_value"])

        grouped = df.groupby("category").agg(
            total_books=("title", "count"),
            avg_price=("price_value", "mean")
        ).reset_index()

        grouped["avg_price"] = grouped["avg_price"].round(2)
        return grouped.to_dict(orient="records")

@ns.route("/books/top-rated")
class TopRatedBooks(Resource):
    def get(self):
        rating_map = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
        df = books_df.copy()
        df["rating_value"] = df["rating"].map(rating_map)
        top_books = df.sort_values(by="rating_value", ascending=False).head(10)
        return top_books.to_dict(orient="records")

@ns.route("/books/price-range")
@ns.doc(params={
    "min": "Preço mínimo (float) — valor padrão = 0",
    "max": "Preço máximo (float) — valor padrão = 1000"
})
class PriceRange(Resource):
    @ns.response(200, "Lista de livros dentro da faixa de preço")
    def get(self):
        try:
            min_price = float(request.args.get("min", 0))
            max_price = float(request.args.get("max", 1000))
        except ValueError:
            return {"error": "Os parâmetros 'min' e 'max' devem ser numéricos."}, 400

        df = books_df.copy()
        df["price_value"] = (
            df["price"]
            .astype(str)
            .str.replace("Â", "", regex=False)
            .str.replace("£", "", regex=False)
            .str.strip()
        )
        df["price_value"] = pd.to_numeric(df["price_value"], errors="coerce")
        df = df.dropna(subset=["price_value"])

        result = df[
            (df["price_value"] >= min_price) &
            (df["price_value"] <= max_price)
        ]

        return result.to_dict(orient="records")

@ns.route("/ml/features")
class MLFeatures(Resource):
    @ns.response(200, "Dados prontos para uso em modelos de Machine Learning")
    def get(self):
        df = books_df.copy()

        df["price_value"] = (
            df["price"]
            .astype(str)
            .str.replace("Â", "", regex=False)
            .str.replace("£", "", regex=False)
            .str.strip()
        )

        df["price_value"] = pd.to_numeric(df["price_value"], errors="coerce")

        df = df.dropna(subset=["price_value"])

        rating_map = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
        df["rating_num"] = df["rating"].map(rating_map)

        features = df[["price_value", "rating_num", "availability", "category"]]

        return features.to_dict(orient="records")


@ns.route("/stats/categories")
class StatsCategories(Resource):
    def get(self):
        """
        Retorna estatísticas detalhadas por categoria.
        """
        df = books_df.copy()

        df["price_value"] = (
            df["price"]
            .astype(str)
            .str.replace("Â", "", regex=False)
            .str.replace("£", "", regex=False)
            .str.strip()
        )
        df["price_value"] = pd.to_numeric(df["price_value"], errors="coerce")
        df = df.dropna(subset=["price_value"])

        grouped = df.groupby("category").agg(
            total_books=("title", "count"),
            avg_price=("price_value", "mean")
        ).reset_index()

        grouped["avg_price"] = grouped["avg_price"].round(2)
        return grouped.to_dict(orient="records")

@ns.route("/metrics")
class Metrics(Resource):
    @ns.marshal_with(metric_model)
    def get(self):
        return metrics_data

api.add_namespace(ns)

app = app

if __name__ == "__main__":
    # app.run(debug=True)
    app.run(host="0.0.0.0", port=5000, debug=True)
