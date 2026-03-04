from ...mesh import Mesher


def create_beam(L: float, n: int, initial_labels: tuple[int, int] = (1, 1)) -> Mesher:
    mesh = Mesher()
    node_array = [[int(initial_labels[0] + i), 0.0, 0.0, L * i / (n - 1)] for i in range(n)]
    mesh.add_nodes(nset="global", arr=node_array)

    element_array = [
        [initial_labels[1] + i, node_array[int(i)][0], node_array[int(i + 1)][0]]
        for i in range(int(len(node_array) - 1))
    ]
    mesh.add_elements(elset="Pwire", arr=element_array, type="B31")

    mesh.add_nset(name="gfix", arr=[node_array[0][0]])
    mesh.add_nset(name="gmove", arr=[node_array[-1][0]])
    return mesh
