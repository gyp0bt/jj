// Neo4jスキーマ初期化スクリプト
// jjとjj-dbの共有スキーマ（制約・インデックス）
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

// JJRun: プロジェクト内でjj_idが一意
CREATE CONSTRAINT jjrun_unique IF NOT EXISTS
FOR (n:JJRun) REQUIRE (n.project, n.jj_id) IS UNIQUE;

// JJTag: プロジェクト内でjj_idが一意
CREATE CONSTRAINT jjtag_unique IF NOT EXISTS
FOR (n:JJTag) REQUIRE (n.project, n.jj_id) IS UNIQUE;

// JJDBMaterial: jj-db内部IDが一意
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

// JJRun検索用
CREATE INDEX jjrun_project IF NOT EXISTS FOR (n:JJRun) ON (n.project);
