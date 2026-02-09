import numpy as np
from pymesh import mesher
from pymesh.misc.smoothing import v2 as sm
from pymesh.misc.smoothing import (
    build_quads_from_labels,
    # area_preserving_laplacian_smoothing_quads,
    # smooth_minimize_area_error_quads,
)

mesh_path = "assets/tmp.inp"
# mesh_path = "assets/tmp3.inp"
m = mesher(mesh_path)
points = m.get_node_coord_matrix()

fixed_mask = np.full(points.shape[0], fill_value=False)
gfix = m.get_node_labels_with_nset("gfix")
indices = np.isin(points[:, 0], gfix)
fixed_mask[indices] = True

node_coord_arr = m.get_node_coord_array()
elem_arr = m.get_element_array()

quads = build_quads_from_labels(
    node_coord_arr=node_coord_arr, elem_arr=elem_arr, elem_has_elem_label=True
)
points_new, stats = sm.optimize_quads_soft_equal_area_with_tangent_boundary(
    points0=points[:, 1:-1],
    quads=quads,
    fixed_mask=fixed_mask,
    cfg=sm.PipelineConfig(
        max_iter=500,
    ),
)
print(stats)

# points_new = area_preserving_laplacian_smoothing_quads(
# points[:, 1:-1], quads, fixed_mask=fixed_mask
# )
# points_new, stats = smooth_minimize_area_error_quads(
# points, quads, fixed_mask=fixed_mask
# )
# print(stats)

node_coord_arr["x"] = points_new[:, 0]
node_coord_arr["y"] = points_new[:, 1]
m.update_node_coord_with_array(node_coord_array=node_coord_arr)
m.dump("assets/tmp2.inp", to_femap=True)
# m.dump("assets/tmp4.inp", to_femap=True)
