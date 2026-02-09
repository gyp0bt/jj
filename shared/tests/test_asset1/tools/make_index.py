import glob

for i in list(glob.glob("./**/*.inp")) + list(glob.glob("./*.inp")):
    if "tmp" in i:
        continue
    if "assets" in i:
        continue
    basename = i.split("\\")[-1][:-4]
    with open(f"notes/inp/{basename}.md", "w") as f:
        f.write("""\
---
---
""")
