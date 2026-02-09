from services.parse.file_parse import FileGroup, FileParse, FileType


def test_new_style_props_and_tags():
    parser = FileParse("go_prop1_v1_idx1.inp")
    assert parser.get_file_type() == FileType.GO
    assert parser.get_index() == "1"
    assert parser.get_version() == "1"
    assert parser.get_props()["prop"] == "1"
    assert parser.get_props()["v"] == "1"
    assert parser.get_props()["idx"] == "1"
    assert parser.get_tags() == []


def test_tags_from_non_prop_tokens():
    parser = FileParse("mesh_tagA_prop2_idx3.msh")
    assert parser.get_file_type() == FileType.MESH
    assert parser.get_props()["prop"] == "2"
    assert parser.get_index() == "3"
    assert parser.get_tags() == ["tagA"]


def test_legacy_version_fallback():
    parser = FileParse("go_idx1_prop1.v2.inp")
    assert parser.get_version() == "2"
    assert parser.get_props()["v"] == "2"
    assert parser.get_index() == "1"


def test_file_group_by_type_and_index():
    candidates = [
        "go_prop1_idx1.inp",
        "go_prop2_idx1.inp",
        "mesh_prop1_idx1.msh",
    ]
    parser = FileParse(candidates[0])
    group = parser.get_file_group(candidates)
    assert isinstance(group, FileGroup)
    assert group.file_type == FileType.GO
    assert group.index == "1"
    assert len(group) == 2
