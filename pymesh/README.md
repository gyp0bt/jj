# pymesh

> abaqus用メッシュ操作ライブラリ
------------------------

## quick-start

### install

`git clone git@shitlab.com/nishioka/pymesh.git`
or gitlab画面右上の"コード"をクリックして、zip形式でダウンロード
-----------------------------------------------------

### sample code(1) 基本機能抜粋

```python
import pymesh

inp_filepath = "./pymesh/assets/sample_mesh.inp"

mesh = pymesh.mesher(inp_filepath)

# xyzのmin/maxに境界条件を設定
mesh.set_symmetory()

# 重複ノード削除
mesh.drop_duplicated_nodes(cutoff=1.e-4)

# 座標スケーリング
mesh.scale_node(scale=(1.e-3, 1.e-3, 1.e-3))

# 最大座標を取得
mesh.get_max_labels()

# Node座標をNDArrayで取得
node_coord_array = mesh.get_node_coord_array()

print(node_coord_array["x"])
print(node_coord_array["label"])

# z座標を+10移動
node_coord_array["z"] += 10.
mesh.update_node_coord_with_array(node_coord_array)

# femapで開けるよう出力
mesh.dump("pymesh_sample.inp", to_femap=True)
```

-----------------------------------------------------

### sample code(2) beamモデル作成

```python
from pymesh import Mesher

def create_beam(L: float, n: int, initial_labels: tuple[int, int] = (1, 1)) -> Mesher:
    mesh = Mesher()
    node_array = [
        [int(initial_labels[0] + i), 0.0, 0.0, L * i / (n - 1)] for i in range(n)
    ]
    mesh.add_nodes(nset="global", arr=node_array)

    element_array = [
        [initial_labels[1] + i, node_array[int(i)][0], node_array[int(i + 1)][0]]
        for i in range(int(len(node_array) - 1))
    ]
    mesh.add_elements(elset="Pwire", arr=element_array, type="B31")

    mesh.add_nset(name="gfix", arr=[node_array[0][0]])
    mesh.add_nset(name="gmove", arr=[node_array[-1][0]])
    return mesh

mesh = create_beam(L=100., n=50, initial_labels=(1,1))
mesh.dump("pymesh_sample_wire.inp", to_femap=True)

```

or

```python
from pymesh.generics.create_beam_model import create_beam
mesh = create_beam(L=100., n=50., initial_labels=(1,1))
```

### sample code(3) shellを元に押出でソリッド作成

```python

from pymesh.utils.extrude import ExtrudeSurface
from pymesh import mesher

mesh_filepath = "pymesh/assets/pymesh_sample_extrude.inp"
n = 7

m = mesher(mesh_filepath)

elements_data = m.elements_data.copy()
for key, value in elements_data.items():

    print(key)

    if any([i in key for i in ["tmp1", "tmp3"]]):
        z = 2.5
    else:
        z = -1.1

    ExtrudeSurface(
        mesh=m,
        elset_name=key,
        target_elset_name=value.name + "_SOLID",
        target_nset_name="global",
    ).extrude_until_position(n=n, z=z)


m.dump("pymesh_sample_extruded.inp", to_femap=True)

```

### sample code(4) 伸線インプット作成

```python

from pymesh.utils.extrude import ExtrudeSurface
from pymesh import mesher

from pymesh.generics.round_drawing import create_wire, create_die

m = Mesher()
m = create_die(m, D1., D1=0.8, A0=32., R0=4., BL0=0.3, num_div=20)
m = create_wire(m, D0=1., num_div_x=10, num_div_y=50, wire_length=5.)
m.dump("pymesh_drawing_sample.inp", to_femap=True)

```

or

```python

from pymesh.utils.extrude import ExtrudeSurface
from pymesh import mesher

from pymesh.generics.round_drawing import write_input

write_input(
    num_div=10,
    D0=1.,
    D1=0.8.
    A0=32.,
    R0=0.1,
    BT0=0.,
    BL0=0.3,
    F0=0.12,
    mass_scale=1.e-5,
    inp_filepath="pymesh_drawing_abq_input.inp",
    material_inp_filepath="./pymesh/assets/drawing/matrial.inp",
    material_name="FECC_FI8_UC06mms_240618",
    wire_length0=None,
    se=True,
    add=False,
)

```
