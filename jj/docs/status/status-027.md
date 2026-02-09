[READMEへ戻る](../../README.md) | [ロードマップ](../roadmap.md)

# Status 027 - Obsidianエクスポート構造改善 + Abaqusコネクタ拡張（.msg解析・テスト追加）

**日付**: 2026-02-06

---

## 概要

3つの構造変更とAbaqusコネクタの拡張を実施した。

### 1. props/inp/ → props/ へのフラット化
frontmatterファイルの配置を `notes/props/inp/{type}/` から `notes/props/{type}/` に変更。
不要な `inp/` 階層を削除し、ディレクトリ構造を簡素化。

### 2. .base.md → .base（YAML filter形式）への変更
`.base.md`（frontmatter + markdown）を `.base`（pure YAML filter）に変更。
`.base` ファイルはObsidian上でフィルター条件に応じてpropertyをテーブル形式で表示する。

### 3. 旧.base.md → {type}_idx{index}-group.md
旧 `.base.md` のNodeGroupメンバー情報は `-group.md` ファイルとして
`notes/props/{type}/` 配下に配置するよう変更。

### 4. Abaqusコネクタ拡張
- `.msg` ファイル解析機能（`parse_msg_file()`）を実装
- GraphServiceへの `.msg` エンリッチメント統合
- `read_inp()` の包括的テスト40件を追加

---

## 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `services/connectors/obsidian.py` | `get_md_path()`: `inp/`階層を削除。`_write_base_files()`: `.base`と`-group.md`の分離出力。`_format_base_filter()`, `_format_group_file()` を新規追加 |
| `services/notes/__init__.py` | `init_tree()`: `props/inp/` → `props/` にディレクトリ構造変更。`base_template()` パス更新 |
| `services/graph/__init__.py` | `parse_msg_file()` 関数追加。`_enrich_msg_status()` メソッド追加 |
| `tests/test_obsidian_connector.py` | パス構造テスト修正 + `TestObsidianBaseAndGroupFiles` クラス追加（4テスト） |
| `tests/test_abaqus_connector.py` | **新規作成**: 40テスト（read_inp, ReadComponent, パラメータ, diff, .msg解析） |

---

## テスト結果

全170テスト通過（既存130 + 新規40）

### 新規テストクラス（test_abaqus_connector.py）
- `TestReadInp`: INP読み込みの基本テスト（9件）
  - ノード・要素・集合・材料・STEP・プロシージャ・境界条件
- `TestReadInpWithInclude`: *INCLUDE処理テスト（1件）
- `TestReadInpWithParameter`: パラメータ置換テスト（2件）
- `TestReadInpFixtures`: テストフィクスチャ使用のテスト（2件）
- `TestReadComponents`: ReadComponent個別テスト（5件）
- `TestMaterialComponents`: 材料物性テスト（2件）
- `TestEvaluateExpressions`: 式評価テスト（4件）
- `TestParseKeylineOptions`: キーワード行パーステスト（2件）
- `TestAbqToDict`: dict変換テスト（2件）
- `TestDiffAbqBlocks`: 差分機能テスト（6件）
- `TestParseMsgFile`: .msg解析テスト（4件）
- `TestDiffIntegration`: diff統合テスト（1件）

### Obsidianコネクタ新規テスト（test_obsidian_connector.py）
- `TestObsidianBaseAndGroupFiles`: base/groupファイル生成テスト（4件）

---

## ディレクトリ構造の変更

### Before
```
notes/
├── props/
│   ├── inp/
│   │   ├── go/        ← goタイプのmd
│   │   ├── mesh/      ← meshタイプのmd
│   │   ├── material/  ← materialタイプのmd
│   │   └── step/      ← stepタイプのmd
│   ├── reports/
│   ├── docs/
│   └── tools/
├── bases/
│   ├── go/
│   │   └── go_idx1.base.md  ← frontmatter + markdown
│   └── ...
└── ...
```

### After
```
notes/
├── props/
│   ├── go/             ← goタイプのmd（inp/階層なし）
│   │   └── go_idx1-group.md  ← メンバー一覧（旧.base.md内容）
│   ├── mesh/
│   ├── material/
│   ├── step/
│   ├── reports/
│   ├── docs/
│   └── tools/
├── bases/
│   ├── go/
│   │   └── go_idx1.base  ← pure YAMLフィルター条件（.base.mdではない）
│   └── ...
└── ...
```

---

## .base ファイルの形式（変更後）

```yaml
views:
- type: table
  name: Table
  filters:
    and:
    - file.folder == "notes/props/go"
    - file.fullname.endsWith(".md")
    - active == true
  order:
  - file.name
  - idx
  - ver
  - success
  - description
  - file.links
  sort:
  - property: idx
    direction: ASC
  - property: ver
    direction: ASC
```

---

## .msg ファイル解析

新しく`parse_msg_file()`関数を実装。Abaqus解析の`.msg`ファイルから
`***ERROR`と`***WARNING`マーカーを抽出する。

```python
# services/graph/__init__.py
result = parse_msg_file(Path("go_idx1.msg"))
# → {"errors": ["CONVERGENCE FAILURE"], "warnings": ["LARGE ROTATION"]}
```

GraphServiceの`_enrich_msg_status()`メソッドで自動的にノードの
propertiesに`msg_errors`/`msg_warnings`として付与される。

---

## 発見した設計課題

- **ReadComponent.__eq__の非対称性**: optionsが空のコンポーネント同士が等価と判定される。
  `all(other.options[k] == self.options.get(k) for k in other.options)` で
  空dictの場合 `all([])` → True となるため、異なるクラスのコンポーネント間で
  誤った等価判定が発生する可能性がある。
  `isinstance` チェックを `__eq__` に追加することで解消可能。

---

## TODO（次回以降の作業）

- [ ] ReadComponent.__eq__のisinstanceチェック追加（設計課題の修正）
- [ ] パーサー層の拡張機能（ファイルグループ、.v1完全対応、パフォーマンス最適化）
- [ ] run(unknown00)のような仮runを介した関連付け
- [ ] config.yamlの拡張（配列スライス、type=iso/aniso定義）
- [ ] ドキュメント連携（index.csv/yaml、Obsidian dailyノート）
- [ ] Windows環境での実機テスト
- [ ] アダプター層基盤の設計（CAEAdapterBase, AdapterRegistry）

---

## 確認事項

- `.base`ファイルの拡張子変更により、Obsidianのプラグイン設定で`.base`を認識させる必要がある可能性あり。ユーザー環境での動作確認が必要。
- `-group.md`ファイルはfrontmatter付きマークダウンのため、Obsidianで通常通り表示可能。
