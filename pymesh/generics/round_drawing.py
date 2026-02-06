import os
import numpy as np
from typing import Optional
from ..mesh import Nodes, Elements, Nset, Elset, Mesher
from ..etypes import ElementType
from ..utils.extrude import ExtrudeLine


def create_wire(
    D0: float,
    num_div_x: int,
    wire_length0: float,
    mesh: Optional[Mesher] = None,
    num_div_y: Optional[int] = None,
) -> Mesher:
    if mesh is None:
        mesh = Mesher()

    init_label = mesh.get_max_labels()
    init_node_label, init_element_label = init_label.node, init_label.elem

    node_data = [
        [i + 1 + init_node_label, i / num_div_x * D0 / 2.0, 0.0, 0.0]
        for i in range(num_div_x + 1)
    ]
    mesh.add_nodes("global", np.array(node_data))

    elem_data = [
        [i + 1 + init_element_label, node_data[i][0], node_data[i + 1][0]]
        for i in range(len(node_data) - 1)
    ]
    mesh.add_elements("__ptmp", arr=np.array(elem_data), type=ElementType.B31.name)

    if num_div_y is None:
        num_div_y = int(wire_length0 // (D0 / 2 / num_div_x))
    ExtrudeLine(
        mesh=mesh,
        base_elset_name="__ptmp",
        target_elset_name="pwire",
        target_nset_name="global",
    ).extrude_until_position(
        n=num_div_y,
        y=-wire_length0,
    )

    # elements_key = mesh.get_elset_key_from_elset_and_type(
    #     elset="__ptmp", type=ElementType.B31.name
    # )
    # mesh.elements_data.data.pop(elements_key)

    tol = D0 / 2.0 / num_div_x / 5.0

    # 境界条件用
    mesh.set_symmetory(tol=tol, elset_key="pwire")
    mesh.set_gfront(tol=tol, n_each_area=3, n_area=1, axis="y", elset_key="pwire")
    _, element_labels, _, _ = mesh.get_max_or_min_node_and_element_labels(
        tol=tol, axis="y", n_iter=1, ismin=True, elset_key="pwire"
    )
    mesh.add_elset(name="gback", arr=element_labels)

    # 前後位置調整
    y_gmain_max = mesh.get_element_coord_array_with_elset(name="gmain")["y"].max()
    node_coord_array = mesh.get_node_coord_array_with_elements(name="pwire")
    node_coord_array["y"] -= y_gmain_max
    mesh.update_node_coord_with_array(node_coord_array=node_coord_array)

    # 結果処理用に中心付近をグループ化
    elem_coord_arr = mesh.get_element_coord_array("pwire")
    ymax, ymin = elem_coord_arr["y"].max(), elem_coord_arr["y"].min()
    dist = (elem_coord_arr["y"] - ymin) ** 2 + (elem_coord_arr["y"] - ymax) ** 2
    ycenter = elem_coord_arr["y"][np.argmax(dist)]
    gcenter = elem_coord_arr["label"][
        np.abs(elem_coord_arr["y"] - ycenter) <= (ymax - ymin) / (num_div_y * 1.2)
    ].tolist()
    mesh.add_elset("gcenter", gcenter)

    mesh.elements_data.get_parent_with_elset(
        elset_name="pwire", type=ElementType.S4.name
    ).options = dict(elset="pwire", type=ElementType.CAX4R.name)

    return mesh


def create_die(
    D0: float,
    D1: float,
    A0: float,
    R0: float,
    BL0: float,
    mesh: Optional[Mesher] = None,
    num_div: int = 100,
    se: bool = False,
    elset_name: str = "pjig",
    add_refnode: bool = False,
) -> Mesher:
    """
    y方向: ダイス出口側（伸線平行方向）
    x方向: 伸線垂直方向
    p1: ダイス入口側先端
    p2: ダイスリダクションR部とリダクション角度部の交点
    p3: ダイスリダクションR部とベアリング部の交点
    p4: ベアリング部終点
    p5: ダイス出口側先端
    """
    if mesh is None:
        mesh = Mesher()

    tan_a = np.tan(np.deg2rad(A0 / 2.0))
    die_inlet_d = D0 / 2.0 * 1.3

    r_reduction_length = tan_a * R0 * np.sqrt(1 / (1 + tan_a**2))
    r_reduction_d = D1 / 2.0 + (R0 - np.sqrt(R0**2 - r_reduction_length**2))
    a_reduction_length = (die_inlet_d - r_reduction_d) / tan_a
    total_die_length = r_reduction_length + a_reduction_length + BL0 + BL0 * 0.2

    init_label = mesh.get_max_labels()
    init_node_label, init_element_label = init_label.node, init_label.elem

    data = []
    div = total_die_length / num_div

    offset_y = -(die_inlet_d - D0 / 2.0) * 0.7 / tan_a

    for i in range(num_div):
        yi = div * i

        if yi < a_reduction_length:
            xi = die_inlet_d - yi * tan_a

        elif yi < a_reduction_length + r_reduction_length:
            xi = (
                -np.sqrt(R0**2 - (yi - (a_reduction_length + r_reduction_length)) ** 2)
                + R0
                + D1 / 2.0
            )

        elif yi < total_die_length - BL0 * 0.2:
            xi = D1 / 2.0

        else:
            # xi = (yi - (total_die_length - BL0 * 0.2)) / (BL0 * 0.2) * (
            # np.array(data)[:, 1].max() - D1 / 2.0
            # ) + D1 / 2.0
            xi = np.array(data)[:, 1].max()

        # yi = yi - offset_y
        yi = yi + offset_y
        data.append([i + 1 + init_node_label, xi, yi, 0.0])

    mesh.add_nodes("global", arr=data)

    mesh.add_elements(
        "__ptmp",
        type=ElementType.B31.name,
        arr=np.array(
            [
                [i + 1 + init_element_label, data[i][0], data[i + 1][0]]
                for i in range(len(data) - 1)
            ]
        ),
    )

    to_x = max([die_inlet_d * 1.1, D1 / 2.0 + BL0 * 0.2])
    if se:
        num_div_x = 1
    else:
        num_div_x = int((to_x - die_inlet_d) // div)
    ExtrudeLine(
        mesh=mesh,
        base_elset_name="__ptmp",
        target_elset_name=elset_name,
        target_nset_name="global",
    ).extrude_until_position(
        n=num_div_x,
        x=to_x,
    )

    mesh.elements_data.get_parent_with_elset(
        elset_name=elset_name, type=ElementType.S4.name
    ).options = dict(elset=elset_name, type=ElementType.CAX4R.name)

    if add_refnode:
        max_label = mesh.get_max_labels()
        max_node_label = max_label.node
        mesh.add_nodes(
            f"ref{elset_name[1:]}", arr=np.array([[max_node_label + 1, 0.0, 0.0, 0.0]])
        )

    return mesh


def write_input(
    num_div: int,
    D0: float,
    D1: float,
    A0: float,
    R0: float,
    BL0: float,
    BT0: float,
    F0: float,
    inp_filepath: str,
    material_inp_filepath: str,
    material_name: str,
    wire_length0: Optional[float] = None,
    se: bool = False,
    add: bool = False,
    is_explicit: bool = True,
    mass_scale: Optional[float] = 1.0e-6,
):
    m = Mesher()

    if wire_length0 is None or wire_length0 < 0.0:
        contact_length = (D0 - D1) / 2.0 / np.tan(np.radians(A0 / 2.0))
        wire_length0 = contact_length * 2.0

    if wire_length0 is None:
        raise ValueError

    if se:
        num_div_jig = 30
    else:
        num_div_jig = 200
    create_die(
        mesh=m,
        D0=D0,
        D1=D1,
        A0=A0,
        R0=R0,
        BL0=BL0,
        num_div=num_div_jig,
        se=se,
    )

    if se:
        number_of_nodes = m.get_number_of_nodes()
        capacity_of_nodes = 940 - number_of_nodes
        num_div_y_se = int(capacity_of_nodes // num_div) - 1
        num_div_y_auto = int(wire_length0 // (D0 / 2 / num_div))
        num_div_y = min([num_div_y_se, num_div_y_auto])
    else:
        num_div_y = None
    create_wire(
        mesh=m,
        num_div_x=num_div,
        num_div_y=num_div_y,
        D0=D0,
        wire_length0=wire_length0,
    )

    m.dump(inp_filepath=inp_filepath, add=add)

    # init_node_label, _ = m.get_max_labels()
    init_label = m.get_max_labels()
    init_node_label, init_element_label = init_label.node, init_label.elem

    working_directory = os.path.dirname(inp_filepath) + "/"
    os.system(f"cp {material_inp_filepath} {working_directory}")

    with open(inp_filepath, "a") as f:

        text = f"""\
*********************************************************
*********************************************************
*********************************************************
**
*include, input={os.path.basename(material_inp_filepath)}
*parameter
 wire_length0 = {wire_length0}
 D0 = {D0}
 BT0 = {BT0}
 mass_scale_dt = {mass_scale}
 F0 = {F0}
 t = 0.3
 v = wire_length0*2.4 / t
 back_stress0 = BT0/(3.1415*((D0/2.)**2))
*solid section, elset=pwire, material={material_name}
*solid section, elset=pjig, material={material_name}
**
*node, nset=refjig
 {int(init_node_label+1)}, 0., 0., 0.
*rigid body, refnode=refjig, elset=Pjig
*********************************************************
*********************************************************
*********************************************************
**
*surface, type=element, name=Sjig
 Pjig
*surface, type=element, name=Swire
 Pwire
*surface, type=element, name=Smain
 Gmain
*surface, type=element, name=Sback
 Gback
*node, nset=reffront
 {int(init_node_label+2)}, 0., 0., 0.
*equation
 2
 gymax, 2, 1, reffront, 2, -1
*********************************************************
*********************************************************
*********************************************************
**
*surface interaction, name=sint1
*friction
 <F0>
*surface behavior, pressure-overclosure=exponential
 0.0001, 1. 
*surface interaction, name=frict010
*friction
 0.1
*********************************************************
*********************************************************
*********************************************************
**
"""
        if not is_explicit:
            text += """\
*contact pair, interaction=sint1
** Smain, Sjig
 Swire, Sjig
*contact pair, interaction=frict010
 Smain, Smain
*step
 drawing
*dynamic, application=quasi-static
 1.e-2, <t>, 1.e-8, <t>
"""
        else:
            text += """\
*step
 drawing
*dynamic, explicit
 , <t>
*fixed mass scaling, type=below min, dt=<mass_scale_dt>
*contact pair, interaction=sint1
 Smain, Sjig
*contact pair, interaction=frict010
 Smain, Smain
"""
        text += """\
**
*boundary, type=velocity
 reffront, 1, 6, 0.
 refjig, 1, 1, 0.
 refjig, 2, 2, -<v>
 refjig, 3, 6, 0.
*amplitude, definition=smooth step, name=a1
 0.,0.
 0.01, 1.
 1., 1.
*dsload, amplitude=a1, follower=no
 Sback, P, -<back_stress0>
**
*output, history, time interval=0.01
*node output, nset=reffront
 RF, U
*node output, nset=refjig
 RF, U
*output, field, variable=preselect, num=15
*element output, elset=Pwire
 dmicrt
*node output, nset=global
 U, COORD
*end step\
"""
        f.write(text)
