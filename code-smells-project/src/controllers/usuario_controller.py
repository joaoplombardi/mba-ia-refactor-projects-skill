"""Usuario use cases, including authentication."""
import logging

from src.config.constants import TIPO_USUARIO_PADRAO
from src.controllers.validators import usuario_validator
from src.errors import NotFoundError, UnauthorizedError
from src.models.usuario_model import serialize as serialize_usuario

logger = logging.getLogger(__name__)


class UsuarioController:
    def __init__(self, usuario_model, password_hasher, password_verifier):
        self.usuario_model = usuario_model
        self.hash_password = password_hasher
        self.verify_password = password_verifier

    def listar(self):
        return self.usuario_model.get_all()

    def buscar_por_id(self, usuario_id):
        usuario = self.usuario_model.get_by_id(usuario_id)
        if usuario is None:
            raise NotFoundError("Usuário não encontrado")
        return usuario

    def criar(self, payload):
        dados = usuario_validator.validate_create(payload)
        usuario_id = self.usuario_model.create(
            nome=dados["nome"],
            email=dados["email"],
            senha_hash=self.hash_password(dados["senha"]),
            tipo=TIPO_USUARIO_PADRAO,
        )
        logger.info("Usuário criado: %s", dados["email"])
        return usuario_id

    def login(self, payload):
        credenciais = usuario_validator.validate_login(payload)
        row = self.usuario_model.get_by_email(credenciais["email"])

        if row is None or not self.verify_password(row["senha"], credenciais["senha"]):
            logger.info("Login falhou: %s", credenciais["email"])
            raise UnauthorizedError("Email ou senha inválidos", include_sucesso=True)

        logger.info("Login bem-sucedido: %s", credenciais["email"])
        usuario = serialize_usuario(row)
        # The legacy login payload omitted criado_em.
        usuario.pop("criado_em", None)
        return usuario
