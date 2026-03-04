org_list = ["go_idx1.v3.inp", "go_idx2.v3.inp", "go_idx3.v3.inp"]
t_list = [35, 172]

idx = 4
v = 2
for _i, t in enumerate(t_list):
    for j in org_list:
        filename = f"go_idx{idx}.v{v}.inp"
        with open(j) as f:
            org_data = f.read()
        data = org_data
        data = data.replace("t95.v8", f"t{int(t)!s}.v{v}")
        with open(filename, "w") as f:
            f.write(data)
        idx += 1
