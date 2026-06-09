// Neo4jスキーマ初期化スクリプト
// jjとjjrvの共有スキーマ（制約・インデックス）
//
// このファイルはNeo4jコンテナの初回起動時に自動実行される。
// 手動実行: cat neo4j/init/01-schema.cypher | cypher-shell -u neo4j -p password

// === 一意性制約 ===

// JJFile: プロジェクト内でjj_idが一意
CREATE CONSTRAINT jjfile_unique IF NOT EXISTS
FOR (n:JJFile) REQUIRE (n.project, n.jj_id) IS UNIQUE;

// JJMaterial: プロジェクト内でjj_idが一意
CREATE CONSTRAINT jjmaterial_unique IF NOT EXISTS
FOR (n:JJMaterial) REQUIRE (n.project, n.jj_id) IS UNIQUE;

// JJTag: プロジェクト内でjj_idが一意
CREATE CONSTRAINT jjtag_unique IF NOT EXISTS
FOR (n:JJTag) REQUIRE (n.project, n.jj_id) IS UNIQUE;

// JJDBMaterial: jjrv内部IDが一意
CREATE CONSTRAINT jjdbmaterial_unique IF NOT EXISTS
FOR (n:JJDBMaterial) REQUIRE n.jjdb_id IS UNIQUE;

// === インデックス ===

// JJFile検索用
CREATE INDEX jjfile_name IF NOT EXISTS FOR (n:JJFile) ON (n.name);
CREATE INDEX jjfile_type IF NOT EXISTS FOR (n:JJFile) ON (n.type);
CREATE INDEX jjfile_project IF NOT EXISTS FOR (n:JJFile) ON (n.project);

// JJMaterial検索用
CREATE INDEX jjmaterial_name IF NOT EXISTS FOR (n:JJMaterial) ON (n.name);
CREATE INDEX jjmaterial_project IF NOT EXISTS FOR (n:JJMaterial) ON (n.project);

// === メッシュ関連プロパティインデックス ===

// meshタイプのノード統計値検索（mesh_node_count, mesh_element_count）
CREATE INDEX jjfile_mesh_node_count IF NOT EXISTS FOR (n:JJFile) ON (n.mesh_node_count);
CREATE INDEX jjfile_mesh_element_count IF NOT EXISTS FOR (n:JJFile) ON (n.mesh_element_count);

// === 全文検索インデックス ===

// JJFileのname, type, formatで全文検索（大文字小文字非区別、部分一致）
CREATE FULLTEXT INDEX jjfile_fulltext IF NOT EXISTS
FOR (n:JJFile) ON EACH [n.name, n.type, n.format];

// JJMaterialのnameで全文検索
CREATE FULLTEXT INDEX jjmaterial_fulltext IF NOT EXISTS
FOR (n:JJMaterial) ON EACH [n.name];
