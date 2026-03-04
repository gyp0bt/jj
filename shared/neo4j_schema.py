"""Neo4jスキーマ定義

ノードラベル、リレーションシップタイプ、プロパティキーの定義。

[READMEへ戻る](../README.md)
"""


class NodeLabel:
    """Neo4jノードラベル定義"""

    # jj由来のノード
    JJ_FILE = "JJFile"
    JJ_MATERIAL = "JJMaterial"
    JJ_RUN = "JJRun"
    JJ_TAG = "JJTag"

    # DB由来のノード（将来拡張用）
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

    # MLデータフローリレーション
    TRAINS_WITH = "TRAINS_WITH"
    PRODUCES_MODEL = "PRODUCES_MODEL"
    CONFIGURED_BY = "CONFIGURED_BY"
    EVALUATED_ON = "EVALUATED_ON"
    LOGS_TO = "LOGS_TO"

    # サロゲートモデル/層間リレーション
    EXTRACTED_FROM = "EXTRACTED_FROM"
    SURROGATE_OF = "SURROGATE_OF"
    OPTIMIZES = "OPTIMIZES"
    USES_OBJECTIVE = "USES_OBJECTIVE"

    # クロスリレーション
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
    # MLデータフローリレーション
    "trains_with": RelType.TRAINS_WITH,
    "produces_model": RelType.PRODUCES_MODEL,
    "configured_by": RelType.CONFIGURED_BY,
    "evaluated_on": RelType.EVALUATED_ON,
    "logs_to": RelType.LOGS_TO,
    # サロゲートモデル/層間リレーション
    "extracted_from": RelType.EXTRACTED_FROM,
    "surrogate_of": RelType.SURROGATE_OF,
    "optimizes": RelType.OPTIMIZES,
    "uses_objective": RelType.USES_OBJECTIVE,
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
    "version_diff": NodeLabel.JJ_FILE,
    "run": NodeLabel.JJ_RUN,
    "tag": NodeLabel.JJ_TAG,
    # MLノードタイプ
    "dataset": NodeLabel.JJ_FILE,
    "model_checkpoint": NodeLabel.JJ_FILE,
    "serialized_model": NodeLabel.JJ_FILE,
    "training_script": NodeLabel.JJ_FILE,
    "experiment_config": NodeLabel.JJ_FILE,
    "experiment_metrics": NodeLabel.JJ_FILE,
    # 最適化ノードタイプ
    "optimization_study": NodeLabel.JJ_FILE,
    "optimization_config": NodeLabel.JJ_FILE,
    "trial_history": NodeLabel.JJ_FILE,
}


class PropertyKey:
    """Neo4jプロパティキー定義（メッシュ解析関連）

    Neo4jに格納される際の型変換:
    - dict型 → JSON文字列（Neo4jはネストされたプロパティを扱えないため）
    - list[list] → JSON文字列（同種型リスト以外はJSON化される）
    - list[int|float|str] → Neo4jネイティブリスト
    """

    # メッシュ統計
    MESH_NODE_COUNT = "mesh_node_count"
    MESH_ELEMENT_COUNT = "mesh_element_count"

    # メッシュ品質統計（要素タイプ別）
    # 格納形式: JSON文字列 {"C3D8": {"element_count": N, "quality": {...}}, ...}
    MESH_ELEMENT_QUALITY = "mesh_element_quality"

    # メッシュトポロジーグループ（連結成分）
    # 格納形式: JSON文字列 [["elset_a", "elset_b"], ["elset_c"]]
    MESH_TOPOLOGY_GROUPS = "mesh_topology_groups"

    # メッシュelsetサマリー
    # 格納形式: JSON文字列 {"BODY": {"element_count": N, ...}, ...}
    MESH_ELSET_SUMMARY = "mesh_elset_summary"

    # メッシュ要素タイプ
    # 格納形式: JSON文字列 {"C3D8": N, "C3D4": N, ...}
    MESH_ELEMENT_TYPES = "mesh_element_types"

    # diff関連
    DIFF_SUMMARY = "diff_summary"
    DIFF_DETAILS = "diff_details"
    DIFF_UNIFIED = "diff_unified"


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
