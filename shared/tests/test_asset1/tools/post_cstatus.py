import glob
import json

from pymesh.ext import abq

odb_filepath = "go_idx1.v3.odb"


def main(odb_filepath: str):
    o = abq.load_odb(
        odb_filepath,
        # skip_seriarize=False,
        skip_seriarize=True,
        field_keys=["COORD", "CSTATUS"],
        frames=[0, 13],
        silent=False,
    )
    # print([i for i in o.iter_frames()])

    coord = o.get_frame(0).fields["COORD"]
    cstatus = o.get_frame(-1).fields["CSTATUS"]

    node_labels = cstatus["0"].to_list()
    coord = coord[coord["0"].isin(node_labels)]
    coord = coord.sort_values(by="0").reset_index(drop=True)
    cstatus = cstatus.sort_values(by="0").reset_index(drop=True)

    # df = coord.copy()
    # df["c0"] = cstatus["0"]
    # df["c1"] = cstatus["1"]
    # print(df)
    # df.to_csv("tmp.csv", index=False)

    # print(coord)
    # print(cstatus)
    # cstatus.to_csv("tmp.csv", index=False)

    indices1 = (coord["3"] < 1.0) & (cstatus["1"] < 0.0)
    # print(coord["3"] < 1.0)
    # print(cstatus["1"] < 0.0)
    # print(indices1)

    indices2 = (coord["3"] >= 1.0) & (coord["3"] <= 7.0) & (cstatus["1"] < 0.0)
    indices3 = (coord["3"] >= 7.0) & (cstatus["1"] < 0.0)

    coord1 = coord[indices1]
    coord2 = coord[indices2]
    coord3 = coord[indices3]

    # print(coord1)
    makuuki = {
        "0(center)": (coord1["3"].max() - coord1["3"].min()) * 2.0,
        "1": coord2["3"].max() - coord2["3"].min(),
        "2(edge)": coord3["3"].max() - coord3["3"].min(),
    }

    with open("results/" + odb_filepath[:-4] + "_makuuki-result.json", "w") as f:
        json.dump(makuuki, f, indent=4)


for i in glob.glob("go*.odb"):
    try:
        main(i)
    except Exception as e:
        print(f"Failed to post {i} ({e})")
