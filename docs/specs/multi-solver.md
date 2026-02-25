[← README.md](../../README.md)

# マルチソルバー対応仕様書

**日付**: 2026-02-14
**関連マイルストーン**: M1.5（設計・config拡張）、M2（プラグイン実装）

---

## 1. 背景と課題

### 1.1 現行アーキテクチャのAbaqus暗黙前提

現行のjjコアモジュールには、Abaqusのファイル構造を前提とした暗黙の仮定が複数存在する。

| コアモジュール | 暗黙の仮定 | 影響を受けるソルバー |
|---------------|-----------|-------------------|
| `base.py` FileNameParser | `go_`/`mesh_`/`material_`/`step_`接頭辞でタイプ判定 | 全ソルバー（命名規則がAbaqus特有） |
| `base.py` FILE_TYPE_PREFIXES | `.inp`が計算入力の代表拡張子 | LS-DYNA(.k/.key)、OpenFOAM(なし) |
| `config/__init__.py` FileRelationsConfig | `.dat`が結果ファイル扱い | LS-DYNA(.datはインプット) |
| `output_parser.py` ResultRelationParser | 「同一basename = 同一ジョブ」前提 | Flow-3D（出力種類.ジョブ名形式） |
| `directory_parser.py` | ディレクトリは「ファイルの入れ物」 | OpenFOAM/LS-DYNA（ディレクトリ=1計算） |
| `graph/__init__.py` file_to_node | 「1ファイル=1ソース」でNode生成 | フォルダベースソルバー全般 |

### 1.2 ソルバー別ファイル構造の差異

#### Abaqus（現行対応済み）
```
project/
├── go_idx1_v1.inp          # ジョブ名.拡張子（入力）
├── go_idx1_v1.odb          # ジョブ名.拡張子（結果）
├── go_idx1_v1.sta          # ジョブ名.拡張子（ステータス）
├── go_idx1_v1.msg          # ジョブ名.拡張子（メッセージ）
├── go_idx1_v1.dat          # ジョブ名.拡張子（結果データ）← LS-DYNAではインプット
├── material_idx1.inp       # 材料定義（*INCLUDEで参照）
└── mesh_idx1.inp           # メッシュ定義
```
- **命名**: `{prefix}_{props}.{ext}`
- **ソース**: ファイル単位
- **入出力判定**: 拡張子ベース

#### LS-DYNA {#ls-dyna}
```
project/
├── run_case1/              # フォルダ = 1計算ケース
│   ├── case1.k             # インプット（.k / .key / .dat）
│   ├── case1.key           # インプット（別形式）
│   ├── case1.dat           # インプット（Abaqusでは結果！）
│   ├── d3plot              # バイナリ結果（拡張子なし）
│   ├── d3hsp               # 出力ログ
│   ├── glstat              # グローバル統計
│   ├── matsum              # 材料サマリー
│   └── messag              # メッセージログ
```
- **命名**: `{casename}.{k|key|dat}` または固定名ファイル
- **ソース**: **フォルダ単位**（1フォルダ=1計算）
- **入出力判定**: `.dat`がインプットファイル。d3plot等は拡張子なし
- **固有課題**: `.dat`の意味がAbaqusと真逆

#### Flow-3D {#flow-3d}
```
project/
├── simulation_01/
│   ├── prepin.simulation_01    # 入力ファイル（出力種類.ジョブ名形式！）
│   ├── flsgrf.simulation_01   # グラフ出力（出力種類.ジョブ名）
│   ├── flsprt.simulation_01   # 粒子出力
│   ├── prpgrf.simulation_01   # プローブグラフ
│   ├── report.simulation_01   # レポート
│   └── hdtout.simulation_01   # 熱力学出力
```
- **命名**: `{output_type}.{jobname}`（ジョブ名.拡張子の**逆！**）
- **ソース**: **フォルダ単位**
- **入出力判定**: `prepin.*`がインプット、その他が結果
- **固有課題**: 拡張子がジョブ名、ベースネームが出力種類という逆転構造

#### OpenFOAM {#openfoam}
```
project/
├── case_01/
│   ├── system/             # ソルバー設定ディレクトリ
│   │   ├── controlDict
│   │   ├── fvSchemes
│   │   └── fvSolution
│   ├── constant/           # 定数定義ディレクトリ
│   │   ├── polyMesh/       # メッシュ（ディレクトリ）
│   │   └── transportProperties
│   ├── 0/                  # 初期条件ディレクトリ
│   │   ├── U              # 速度場
│   │   ├── p              # 圧力場
│   │   └── T              # 温度場
│   ├── 100/               # タイムステップ結果ディレクトリ
│   ├── 200/
│   └── postProcessing/     # 後処理結果
```
- **命名**: 拡張子なし、ディレクトリ名で意味を持つ
- **ソース**: **ディレクトリ単位**（case = system + constant + 0 + 結果）
- **入出力判定**: `system/`/`constant/`/`0/`が入力、数字ディレクトリが結果
- **固有課題**: 拡張子がない、ディレクトリ構造が計算の意味を持つ

#### CalculiX {#calculix}
```
project/
├── case1.inp               # Abaqusサブセット形式のインプット
├── case1.frd               # 結果ファイル
├── case1.sta               # ステータス（Abaqusと同名！）
├── case1.dat               # 結果データ（Abaqusと同名！）
└── case1.cvg               # 収束情報
```
- **命名**: `{casename}.{ext}`（Abaqusに近い）
- **ソース**: ファイル単位
- **入出力判定**: `.inp`が入力、`.frd`/`.sta`/`.dat`が結果
- **固有課題**: `.dat`がAbaqusと同様に結果ファイル（LS-DYNAとは逆）

#### Fluent {#fluent}
```
project/
├── go_idx1_v1.cas.h5       # ケースファイル（バイナリ、HDF5形式）
├── go_idx1_v1.dat.h5       # 結果データ（バイナリ、HDF5形式）
├── go_idx1_v1.jou          # ジャーナルファイル（バッチ実行用、独自記法）
├── go_idx1_v1.out          # テーブル形式リザルトデータ
├── go_idx1_v1.xy           # テーブル形式リザルトデータ（XYプロット）
├── mesh_idx1.msh           # メッシュファイル
└── reports/
    └── report.csv          # GUI上で出力したレポート
```
- **命名**: `{jobname}.{ext}`（Abaqusと同様のstandard形式）
- **ソース**: ファイル単位
- **入出力判定**: `.cas.h5`が入力（バイナリ）、`.dat.h5`/`.out`/`.xy`が結果
- **固有課題**: `.cas.h5`/`.dat.h5`はHDF5形式でバイナリ、テキストパースは不可。`.jou`は独自記法のスクリプトだがテキスト読取可能。`.out`/`.xy`はテーブル形式テキスト

#### HFSS (Ansys Electronics Desktop) {#hfss}
```
project/
├── design1.aedt             # プロジェクトファイル（バイナリ、部分的にテキスト埋め込み）
├── design1.aedt.batchinfo/  # 計算実行ログディレクトリ
│   ├── log1.txt
│   └── ...
├── design1.aedtresults/     # 結果ディレクトリ
│   ├── result1.asol
│   └── ...
├── output/
│   ├── S-parameters.csv     # GUI上でエクスポートしたCSVデータ
│   └── S-parameters.s2p     # Touchstoneフォーマット（Sパラメータ等）
└── reports/
    └── report.csv           # GUI上でエクスポートしたレポート
```
- **命名**: `{designname}.{ext}`（standard形式）
- **ソース**: ファイル単位（`.aedt`が主インプット）
- **入出力判定**: `.aedt`が入力（バイナリ、部分テキスト埋込）、`.aedtresults/`が結果ディレクトリ、`.csv`/`.s2p`がエクスポートデータ
- **固有課題**: `.aedt`は基本バイナリだが部分的にテキストが読める箇所がある（設計パラメータ等）。結果は`.aedtresults/`ディレクトリに格納。波形データはGUI操作でCSV/Touchstone形式にエクスポートして保存する運用が一般的。`.aedt.batchinfo/`は計算実行ログ

---

## 2. 設計方針

### 2.1 基本原則

1. **コアモジュールはソルバー非依存**: ファイル/フォルダ→Node変換のコアロジックから特定ソルバーの仮定を排除
2. **configで柔軟性を吸収**: 拡張子の意味、命名規則、ソース単位（ファイル/フォルダ）をconfig駆動にする
3. **プラグインで個別対応**: ソルバー固有の深い解析はプラグインコネクタに委譲
4. **既存テストを壊さない**: Abaqus向けの現行動作はデフォルト設定で維持

### 2.2 変更レイヤー

```
レイヤー1: コアconfig拡張（M1.5で実施）
  ├── SolverProfile: ソルバー別のファイル解釈ルールをconfig.yamlで定義
  ├── source-unit: "file" | "directory" の切替
  └── filename-pattern: ジョブ名.拡張子 vs 出力種類.ジョブ名

レイヤー2: コアパーサー修正（M1.5で実施）
  ├── FileRelationsConfig: ソルバー別のinput/result拡張子マッピング
  ├── DirectoryRelationParser: フォルダ=1計算の対応
  └── ResultRelationParser: basename逆転パターンの対応

レイヤー3: プラグイン実装（M2で実施、検証環境確保後）
  ├── services/plugins/lsdyna/
  ├── services/plugins/flow3d/
  ├── services/plugins/openfoam/
  ├── services/plugins/calculix/
  ├── services/plugins/fluent/
  └── services/plugins/hfss/
```

---

## 3. レイヤー1: コアconfig拡張 — SolverProfile

### 3.1 config.yaml への `solver-profiles` セクション追加

```yaml
# .j2/config/config.yaml

# ソルバープロファイル: ソルバー別のファイル解釈ルール
solver-profiles:
  # デフォルト（Abaqus互換）— 明示指定不要
  default:
    source-unit: file          # "file" | "directory"
    filename-pattern: standard  # "standard" (ジョブ名.拡張子) | "reversed" (出力種類.ジョブ名)
    input-extensions: [".inp"]
    result-extensions: [".odb", ".sta", ".msg", ".dat"]

  lsdyna:
    source-unit: directory
    filename-pattern: standard
    input-extensions: [".k", ".key", ".dat"]
    result-extensions: []       # d3plot等は拡張子なし→パスパターンで対応
    result-filenames: ["d3plot", "d3hsp", "glstat", "matsum", "messag"]

  flow3d:
    source-unit: directory
    filename-pattern: reversed  # prepin.jobname → output_type=prepin, jobname=jobname
    input-prefixes: ["prepin"]  # prepin.* がインプットファイル
    result-prefixes: ["flsgrf", "flsprt", "prpgrf", "report", "hdtout"]

  openfoam:
    source-unit: directory
    filename-pattern: none      # ファイル名ベースの解析を行わない
    input-directories: ["system", "constant", "0"]
    result-directory-pattern: "^\\d+$"   # 数字のみのディレクトリ=タイムステップ結果
    post-processing-directory: "postProcessing"

  calculix:
    source-unit: file
    filename-pattern: standard
    input-extensions: [".inp"]
    result-extensions: [".frd", ".sta", ".dat", ".cvg"]

  fluent:
    source-unit: file
    filename-pattern: standard
    input-extensions: [".cas.h5"]
    result-extensions: [".dat.h5", ".out", ".xy"]
    # .jouはジャーナルファイル（バッチ実行スクリプト）、解析対象としてはアセット扱い

  hfss:
    source-unit: file
    filename-pattern: standard
    input-extensions: [".aedt"]
    result-extensions: [".csv", ".s2p"]
    # .aedtresults/ディレクトリは結果格納先だが内部はバイナリ
    # .aedt.batchinfo/ディレクトリは計算実行ログ

# パスパターンでソルバープロファイルを自動選択
solver-detection:
  "**/*.k | **/*.key":    lsdyna
  "**/prepin.*":          flow3d
  "**/system/controlDict": openfoam
  "**/*.cas.h5":          fluent
  "**/*.aedt":            hfss
```

### 3.2 SolverProfileConfig データクラス

```python
@dataclass(frozen=True)
class SolverProfileConfig:
    """ソルバー別のファイル解釈ルール"""
    name: str
    source_unit: str           # "file" | "directory"
    filename_pattern: str      # "standard" | "reversed" | "none"
    input_extensions: list[str]
    result_extensions: list[str]
    result_filenames: list[str]      # 拡張子なしの結果ファイル名
    input_prefixes: list[str]        # Flow-3D: prepin等
    result_prefixes: list[str]       # Flow-3D: flsgrf等
    input_directories: list[str]     # OpenFOAM: system等
    result_directory_pattern: str    # OpenFOAM: 数字ディレクトリ
```

### 3.3 FileRelationsConfig の拡張

現行の `FileRelationsConfig` を拡張し、ソルバープロファイルとの統合を行う。

**変更内容**:
- `file-relations.input-extensions` のデフォルトにソルバープロファイルの `input-extensions` をマージ
- path-type-map でソルバー検出パターンと連携
- 同一拡張子がソルバー間で異なる意味を持つ場合（`.dat`）はpath-type-mapの優先順位で解決

---

## 4. レイヤー2: コアパーサー修正

### 4.1 FileRelationsConfig: `.dat`問題の解決

**現状の問題**: `.dat`は `result-extensions` に含まれているが、LS-DYNAでは入力ファイル。

**解決策**: path-type-map で**パスパターンによるオーバーライド**を可能にする。ソルバー検出で特定されたパス配下では、拡張子の意味を切り替える。

```yaml
# config.yaml
path-type-map:
  # LS-DYNAフォルダ配下では.datをインプットとして扱う
  "**/run_*/*.dat":
    "*.dat": "calculation_input"
```

これにより、デフォルトの `result-extensions` での `.dat` = 結果 という解釈を、特定パスパターン配下でのみオーバーライドできる。**既存のAbaqus動作は一切変更されない**。

### 4.2 ResultRelationParser: Flow-3D逆転ファイル名対応

**現状の問題**: `ResultRelationParser` は「同一basename = 同一ジョブ」前提で `result_of` 関係を構築するが、Flow-3Dでは `prepin.sim01` と `flsgrf.sim01` の basename (`prepin` vs `flsgrf`) が異なる。

**解決策**: 逆転パターン検出時は**ドット右側（拡張子位置）をジョブ名として比較**する。

```python
# output_parser.py 修正案
def _extract_jobname(node: Node, profile: SolverProfileConfig) -> str:
    """ソルバープロファイルに応じてジョブ名を抽出"""
    if profile.filename_pattern == "reversed":
        # Flow-3D: basename = output_type, format = jobname
        return node.format  # .の右側がジョブ名
    else:
        # 標準: basename = jobname
        return node.name
```

### 4.3 DirectoryRelationParser: フォルダ=1計算の対応

**現状の動作**: `DirectoryRelationParser` は命名規則に合致するディレクトリ（`go_idx1_v1/`等）のみを特別扱いし、その他のディレクトリは汎用 `type="directory"` ノードとして扱う。

**変更案**: `source-unit: directory` のソルバープロファイルが適用されるパス配下では、ディレクトリ自体を**計算ケースNode（`type="calculation_case"`）**として認識する。

```python
# directory_parser.py 修正案（概念）
class DirectoryRelationParser(AbstractFileParser):
    def apply(self, graph: ProjectGraph) -> ProjectGraph:
        # ... 既存ロジック ...

        # source-unit: directory のプロファイルが適用されるフォルダを検出
        for dir_path in all_dirs:
            profile = graph.config.detect_solver_profile(dir_path)
            if profile and profile.source_unit == "directory":
                # フォルダを計算ケースNodeとして生成
                case_node = Node(
                    type="calculation_case",
                    name=dir_path.name,
                    format="directory",
                    properties={"solver": profile.name, ...}
                )
                # 配下のファイルをcontainsでリンク
```

### 4.4 graph/__init__.py file_to_node: 逆転ファイル名の解析

**現状**: `FileParse(file_path)` でbasename = ドットの左側、format = 拡張子として解析。

**変更案**: ソルバープロファイルの `filename-pattern: reversed` 時は、basename と format の解釈を逆転させる。

この変更は `FileNameParser` に影響するが、**コンストラクタに `filename_pattern` パラメータを追加するだけ**で対応可能。

---

## 5. レイヤー3: プラグイン実装概要

各ソルバープラグインは `services/plugins/{solver}/` に配置し、`pyproject.toml` のentry_pointsで自動登録する。

### 5.1 LS-DYNA プラグイン

```
services/plugins/lsdyna/
├── __init__.py          # register() 関数
├── keyword_parser.py    # *KEYWORD解析（Abaqusの*KEYWORDと類似だがフォーマット異なる）
└── result_parser.py     # d3plot/glstat等のバイナリ/テキスト結果解析
```

**主な機能**:
- `.k`/`.key`/`.dat` のキーワードカード解析（`*KEYWORD`行以降のカードパーサー）
- `d3plot` バイナリの基本メタデータ抽出（ノード数/要素数）
- `glstat`/`matsum` テキストファイルからのサマリー抽出

### 5.2 Flow-3D プラグイン

```
services/plugins/flow3d/
├── __init__.py          # register() 関数
├── prepin_parser.py     # prepin.* ファイルのパラメータ解析
└── result_parser.py     # flsgrf/flsprt等の結果サマリー抽出
```

**主な機能**:
- `prepin.*` ファイルのシミュレーションパラメータ抽出
- 逆転ファイル名パターンの解決（ジョブ名 = 拡張子）
- 結果ファイルの基本統計サマリー

### 5.3 OpenFOAM プラグイン

```
services/plugins/openfoam/
├── __init__.py          # register() 関数
├── case_parser.py       # ケースディレクトリ構造の検出・解析
├── dict_parser.py       # controlDict/fvSchemes等のOpenFOAM辞書パーサー
└── result_parser.py     # タイムステップディレクトリの解析
```

**主な機能**:
- `system/controlDict` からソルバータイプ・制御パラメータ抽出
- `constant/transportProperties` からの物性値抽出
- タイムステップディレクトリ（`100/`, `200/`等）の結果メタデータ
- `postProcessing/` の後処理結果統合

### 5.4 CalculiX プラグイン

```
services/plugins/calculix/
├── __init__.py          # register() 関数
├── inp_parser.py        # Abaqusサブセットの.inp解析
└── result_parser.py     # .frd/.cvg結果ファイル解析
```

**主な機能**:
- Abaqus `.inp` サブセットのキーワード解析（CalculiX固有拡張の検出）
- `.frd` 結果ファイルのメタデータ抽出
- `.cvg` 収束情報の解析

### 5.5 Fluent プラグイン

```
services/plugins/fluent/
├── __init__.py          # register() 関数
└── journal_parser.py    # .jouジャーナルファイル解析
```

**主な機能**:
- `.jou` ジャーナルファイルのテキスト解析（バッチ実行パラメータ抽出）
- `.out`/`.xy` テーブル形式結果データのサマリー抽出
- `.cas.h5`/`.dat.h5` はHDF5バイナリのためメタデータ抽出にはh5py依存が必要（将来対応）

### 5.6 HFSS プラグイン

```
services/plugins/hfss/
├── __init__.py          # register() 関数
└── aedt_parser.py       # .aedtファイルの部分テキスト解析
```

**主な機能**:
- `.aedt` ファイルの部分テキスト領域からの設計パラメータ抽出（バイナリ内にテキストブロックが散在）
- `.aedt.batchinfo/` ディレクトリ内の計算実行ログ解析
- `.csv`/`.s2p`（Touchstone）エクスポートデータの認識
- `.aedtresults/` ディレクトリの結果ファイル検出

---

## 6. 実装計画

### M1.5（本マイルストーン）で実施

1. **SolverProfileConfig データクラスの追加** (`config/__init__.py`)
   - `solver-profiles` セクションの読み込み
   - `solver-detection` パターンマッチング
   - デフォルトプロファイル（Abaqus互換）の定義

2. **GraphConfig へのソルバープロファイル統合**
   - `detect_solver_profile(path: str) -> SolverProfileConfig | None`
   - `file_relations` とソルバープロファイルの統合ロジック

3. **default-config.yaml の更新**
   - `solver-profiles` セクションの追加（コメント付き使用例）
   - `solver-detection` セクションの追加

4. **テスト追加**
   - SolverProfileConfig のユニットテスト
   - path-type-map + solver-detection の統合テスト

### M2（検証環境確保後）で実施

1. プラグイン雛形作成（6ソルバー: LS-DYNA, Flow-3D, OpenFOAM, CalculiX, Fluent, HFSS）
2. 各ソルバーのテストアセット作成（`shared/tests/test_asset_{solver}/`）
3. プラグインパッケージの本実装（検証環境確保後に順次）
4. コアパーサーの修正（ResultRelationParser, DirectoryRelationParser）
5. E2Eテスト

---

## 7. 移行時の注意事項

### 7.1 後方互換性

- **デフォルト設定でAbaqus動作を維持**: `solver-profiles` を設定しないプロジェクトは現行と同じ動作
- **既存テスト1,002件は変更なし**: SolverProfileConfigの追加はオプショナルで、既存のGraphConfigロードに影響しない
- **`.dat`問題**: デフォルトのfile-relationsは変更しない。LS-DYNAプロジェクトでのみpath-type-mapでオーバーライド

### 7.2 設計上の懸念

1. **ソルバー自動検出の信頼性**: 拡張子だけでソルバーを判別できないケース（`.inp`はAbaqusとCalculiXで共通）。複数ソルバーが混在するプロジェクトでの競合解決が必要
2. **フォルダベースソルバーのパフォーマンス**: OpenFOAMのタイムステップディレクトリが数千に達する場合のスキャン性能
3. **バイナリファイル対応**: d3plot（LS-DYNA）やflsgrf（Flow-3D）はバイナリで、テキストベースの解析が不可能。メタデータ抽出にはライブラリ依存が必要

---

## 8. 参考資料

- [パーサー仕様書](../../jj/docs/specs/02-parser.md) — FileNameParser, AbstractFileParser
- [設定管理仕様書](../../jj/docs/specs/03-config.md) — GraphConfig, PathTypeMapConfig
- [アダプター仕様書](../../jj/docs/specs/07-adapter.md) — ソフト固有フォーマット対応設計
- [v0.1.0レビュー](../review/review-v0.1.0.md) — Abaqus暗黙前提の指摘
- [CLAUDE.md](../../CLAUDE.md) — プラグイン拡張パターン
