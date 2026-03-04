# pymesh/mesh/mesh.py


from .mesh_base.core import CoreMesher
from .mesh_base.decorater import CountMethodsMeta
from .mesh_base.ops_domain import DomainOpsMixin


class Mesher(DomainOpsMixin, CoreMesher, metaclass=CountMethodsMeta):
    """全部載せMesherクラス"""
