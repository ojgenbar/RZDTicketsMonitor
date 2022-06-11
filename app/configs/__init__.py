import gzip
import logging.handlers
import os

LOG_FILENAME = 'logs/log.log'
os.makedirs(os.path.dirname(os.path.abspath(LOG_FILENAME)), exist_ok=True)


def namer(name):
    return name + '.gz'


def rotator(source, dest):
    with open(source, 'rb') as sf:
        data = sf.read()
        compressed = gzip.compress(data)
        with open(dest, 'wb') as df:
            df.write(compressed)
    os.remove(source)


rh = logging.handlers.RotatingFileHandler(
    LOG_FILENAME, 'a', encoding='utf8', maxBytes=100 * 2 ** 20, backupCount=10,
)
rh.rotator = rotator
rh.namer = namer
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)-5.5s] [%(name)s] %(message)s',
    handlers=[rh, logging.StreamHandler()],
)

__all__ = []
