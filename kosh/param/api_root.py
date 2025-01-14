from typing import List

from kosh.param._param import _param
from kosh.utils import concretemethod, instance, logger


class api_root(_param):
  '''
  todo: docs
  '''

  @concretemethod
  def _parse(self, params: List[str]) -> None:
    '''
    todo: docs
    '''
    if not params[0].startswith('/'): raise TypeError()
    instance.config.set('api', 'root', params[0])
    logger().info('Set api root to %s', params[0])
