"""Neo4jスキーマ定義 - jjとjj-dbの共有契約

ノードラベル、リレーションシップタイプ、プロパティキーの定義。
jjとjj-dbはこの定義に基づいてNeo4jとやり取りする。

[READMEへ戻る](../README.md)
"""


class NodeLabel:
    """Neo4jノードラベル定義"""

    # jj由来のノード
    JJ_FILE = "JJFile"
    JJ_MATERIAL = "JJMaterial"
    JJ_RUN = "JJRun"
    JJ_TAG = "JJTag"

    # jj-db由来のノード
    JJDB_MATERIAL = "JJDBMaterial"
    JJDB_TEST = "JJDBTest"


class RelType:
    """Neo4jリレーションシップタイプ定義"""

    # jj内部のリレーション
    NEXT_VERSION = "NEXT_VERSION"
    SAME_INDEX_GROUP = "SAME_INDEX_GROUP"
    INCLUDES = "INCLUDES"
    HAS_OUTPUT = "HAS_OUTPUT"
    DERIVED_FROM = "DERIVED_FROM"
    RESULT_OF = "RESULT_OF"
    CONTAINS = "CONTAINS"
    TAGGED = "TAGGED"
    USES_MATERIAL = "USES_MATERIAL"
    EXECUTED_BY = "EXECUTED_BY"
    GENERATED = "GENERATED"
    DEFINED_IN = "DEFINED_IN"
    ASSIGNED_TO = "ASSIGNED_TO"
    MENTIONED_IN = "MENTIONED_IN"
    HAS_ELSET = "HAS_ELSET"

    # jj-jj-db間のクロスリレーション
    MATCHES = "MATCHES"
    REFERENCES = "REFERENCES"


# jj Relation.label → Neo4j RelType マッピング
LABEL_TO_RELTYPE: dict[str, str] = {
    "next_version": RelType.NEXT_VERSION,
    "same_index_group": RelType.SAME_INDEX_GROUP,
    "includes": RelType.INCLUDES,
    "has_output": RelType.HAS_OUTPUT,
    "derived_from": RelType.DERIVED_FROM,
    "result_of": RelType.RESULT_OF,
    "contains": RelType.CONTAINS,
    "tagged": RelType.TAGGED,
    "uses_material": RelType.USES_MATERIAL,
    "executed_by": RelType.EXECUTED_BY,
    "generated": RelType.GENERATED,
    "defined_in": RelType.DEFINED_IN,
    "assigned_to": RelType.ASSIGNED_TO,
    "mentioned_in": RelType.MENTIONED_IN,
    "has_elset": RelType.HAS_ELSET,
}

# jj Node.type → Neo4j NodeLabel マッピング
TYPE_TO_LABEL: dict[str, str] = {
    "calculation_input": NodeLabel.JJ_FILE,
    "mesh": NodeLabel.JJ_FILE,
    "material": NodeLabel.JJ_FILE,
    "step": NodeLabel.JJ_FILE,
    "result": NodeLabel.JJ_FILE,
    "asset": NodeLabel.JJ_FILE,
    "folder": NodeLabel.JJ_FILE,
    "output": NodeLabel.JJ_FILE,
    "other": NodeLabel.JJ_FILE,
    "directory": NodeLabel.JJ_FILE,
    # 特殊ノードタイプ
    "abaqus_material": NodeLabel.JJ_MATERIAL,
    "abaqus_elset": NodeLabel.JJ_FILE,
    "run": NodeLabel.JJ_RUN,
    "tag": NodeLabel.JJ_TAG,
}


def get_neo4j_label(node_type: str) -> str:
    """jjのNode.typeからNeo4jノードラベルを取得

    マッピングに存在しない場合はJJFileをデフォルトとして返す。
    """
    return TYPE_TO_LABEL.get(node_type, NodeLabel.JJ_FILE)


def get_neo4j_reltype(relation_label: str) -> str:
    """jjのRelation.labelからNeo4jリレーションシップタイプを取得

    マッピングに存在しない場合は大文字化してそのまま返す。
    """
    return LABEL_TO_RELTYPE.get(relation_label, relation_label.upper())
