# Configurações centralizadas: variáveis de ambiente + logging estruturado
import os
import structlog
from dotenv import load_dotenv

load_dotenv()

GATEWAY_URL = os.getenv('GATEWAY_URL', 'http://localhost:3001')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./bot.db')

# Configura o structlog com timestamps ISO, nome do logger, nível e formato colorido no console
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt='iso'),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
