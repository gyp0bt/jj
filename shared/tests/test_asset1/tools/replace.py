import glob

for i in glob.glob("go*.inp"):
    with open(i) as f:
        data = f.read()
    data = data.replace("syoumg", "syoumg2")
    data = data.replace("95um", "95")
    data = data.replace("35um", "35")
    data = data.replace("172um", "172")
    with open(i, "w") as f:
        f.write(data)
