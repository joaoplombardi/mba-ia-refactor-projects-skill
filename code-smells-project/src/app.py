"""Composition root.

The only module that knows how the pieces fit together: it loads config, opens
the database, builds models, injects them into controllers, and registers the
routes and the error handler.
"""
import logging

from flask import Flask
from flask_cors import CORS

from src.config.settings import settings
from src.controllers.pedido_controller import PedidoController
from src.controllers.produto_controller import ProdutoController
from src.controllers.relatorio_controller import HealthController, RelatorioController
from src.controllers.usuario_controller import UsuarioController
from src.middlewares.error_handler import register_error_handlers
from src.models.database import Database
from src.models.pedido_model import PedidoModel
from src.models.produto_model import ProdutoModel
from src.models.schema import init_schema, seed
from src.models.usuario_model import UsuarioModel
from src.services.notifier import LoggingNotifier
from src.services.security import hash_password, verify_password
from src.views.pedido_routes import create_pedido_blueprint
from src.views.produto_routes import create_produto_blueprint
from src.views.relatorio_routes import create_relatorio_blueprint
from src.views.usuario_routes import create_usuario_blueprint

logger = logging.getLogger(__name__)


def configure_logging():
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )


def create_app(database=None, notifier=None):
    configure_logging()
    settings.validate()

    app = Flask(__name__)
    app.config["SECRET_KEY"] = settings.SECRET_KEY
    app.config["DEBUG"] = settings.DEBUG

    # CORS is restricted to configured origins instead of being wide open.
    CORS(app, origins=settings.CORS_ORIGINS)

    db = database or Database(settings.DB_PATH)
    init_schema(db)
    if settings.SEED_ON_BOOT:
        seed(db, hash_password)

    produto_model = ProdutoModel(db)
    usuario_model = UsuarioModel(db)
    pedido_model = PedidoModel(db)

    notifier = notifier or LoggingNotifier()

    produto_controller = ProdutoController(produto_model)
    usuario_controller = UsuarioController(usuario_model, hash_password, verify_password)
    pedido_controller = PedidoController(
        pedido_model, produto_model, usuario_model, notifier
    )
    relatorio_controller = RelatorioController(pedido_model)
    health_controller = HealthController(
        produto_model, usuario_model, pedido_model, settings.VERSION
    )

    app.register_blueprint(create_produto_blueprint(produto_controller))
    app.register_blueprint(create_usuario_blueprint(usuario_controller))
    app.register_blueprint(create_pedido_blueprint(pedido_controller))
    app.register_blueprint(
        create_relatorio_blueprint(relatorio_controller, health_controller, settings.VERSION)
    )

    # Registered last, so it catches everything the routes raise.
    register_error_handlers(app)

    app.extensions["database"] = db
    return app
