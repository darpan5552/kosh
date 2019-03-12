from configparser import ConfigParser
from importlib import import_module as mod
from logging import basicConfig, getLogger
from multiprocessing import Process
from os import environ, getpid, path
from pkgutil import iter_modules
from signal import pause
from sys import argv, exit
from threading import Thread
from time import sleep
from typing import Any, Callable, Dict, List

from elasticsearch_dsl import connections
from flask import Flask

from kosh.api._api import _api
from kosh.elastic.index import index
from kosh.utils import defaultconfig, dotdict, instance, logger


def main() -> None: kosh().main()
if __name__ == '__main__': main()

class kosh():
  '''
  todo: docs
  '''

  def __init__(self) -> None:
    '''
    todo: docs
    '''
    argv.pop(0)
    basicConfig(
      datefmt = '%Y-%m-%d %H:%M:%S',
      format = '%(asctime)s [%(levelname)s] <%(name)s> %(message)s'
    )
    environ['WERKZEUG_RUN_MAIN'] = 'true'
    getLogger('elasticsearch').disabled = True
    getLogger('werkzeug').disabled = True

  def main(self) -> None:
    '''
    todo: docs
    '''
    try:
      instance.config = ConfigParser()
      instance.config.read_dict(defaultconfig())
      logger().info('Started kosh with pid %s', getpid())

      root = '{}/{}'.format(path.dirname(__file__), 'api')
      mods = [i for _, i, _ in iter_modules([root]) if not i[0] is ('_')]
      instance.echoes = [mod('kosh.api.{}'.format(i)).__dict__[i] for i in mods]
      logger().info('Loaded API endpoint modules %s', mods)

      for i in [i for i in argv if i.startswith('--')]:
        try: mod('kosh.param.{}'.format(i[2:])).__dict__[i[2:]](argv)
        except: exit('Invalid parameter {}'.format(i[2:]))

      conf = dotdict(instance.config['data'])
      connections.create_connection(hosts = [conf.host])
      instance.elexes = { i.uid: i for i in index.lookup(conf.root, conf.spec) }
      # for elex in instance.elexes.values(): index.update(elex)

      self.serve()
      self.watch()
      pause()

    except KeyboardInterrupt: print('\N{bomb}')
    except Exception as exception: logger().exception(exception)
    except SystemExit as exception: logger().critical(str(exception))

    finally: logger().info('Stopped kosh with pid %s', getpid())

  def serve(self) -> None:
    '''
    todo: docs
    '''
    conf = dotdict(instance.config['api'])
    wapp = Flask(conf.name)
    wapp.config['PROPAGATE_EXCEPTIONS'] = True

    for elex in instance.elexes.values():
      for echo in instance.echoes: echo(elex).deploy(wapp)

    class process(Process):
      def run(self) -> None:
        logger().info('Deploying web server at %s:%s', conf.host, conf.port)
        wapp.run(host = conf.host, port = conf.port)

    try:
      instance.server.terminate()
      instance.server.join()
    except: pass

    instance.server = process(daemon = True, name = 'server')
    instance.server.start()

  def watch(self) -> None:
    '''
    todo: docs
    '''
    conf = dotdict(instance.config['data'])
    this = self

    class thread(Thread):
      def run(self) -> None:
        logger().info('Starting data sync in %s', conf.root)
        for elex in index.notify(conf.root, conf.spec):
          logger().info('Sync of dict %s triggered', elex.uid)
          index.update(instance.elexes.update({ elex.uid: elex }) or elex)
          this.serve()

    if instance.config.getboolean('data', 'sync'):
      thread(daemon = True, name = 'update').start()
