[READMEへ戻る](../../README.md)

# アダプター層 仕様書

## 1. 概要

本ドメインは、CAEソフト固有のフォーマットや動作を抽象化し、独立した拡張モジュールとして実装する機能を提供します。新しいソフトへの対応を容易にし、コアロジックへの影響を最小化します。

### 目的

- ソフト固有の処理を独立したモジュールとして分離
- 新規ソフトへの対応を容易にする拡張性の確保
- コアロジックの保守性向上

### 責務範囲

- `services/parse/adapters/` : ソフト固有のパーサー
- `services/run/adapters/` : ソフト固有の実行ロジック
- `services/file/adapters/` : ソフト固有のテンプレート

---

## 2. アダプターパターンの概要

### 2.1 基本構造

各アダプターは以下のインターフェースを実装します。

```python
from abc import ABC, abstractmethod
from pathlib import Path
from types import Node, Relation

class CAEAdapter(ABC):
    """CAEソフト固有の処理を抽象化"""

    @abstractmethod
    def get_name(self) -> str:
        """アダプター名を返す（例: 'abaqus', 'fluent', 'dyna'）"""
        pass

    @abstractmethod
    def can_handle(self, file_path: Path) -> bool:
        """このアダプターが対応可能なファイルか判定"""
        pass

    @abstractmethod
    def parse_file(self, file_path: Path) -> Node:
        """ファイルを解析してNodeを生成"""
        pass

    @abstractmethod
    def predict_output_files(self, input_file: Path, command: str) -> list[Path]:
        """実行時に生成されるファイルを予測"""
        pass

    @abstractmethod
    def extract_properties(self, file_path: Path) -> dict[str, str]:
        """ファイルからプロパティを抽出"""
        pass
```

### 2.2 アダプター登録

アダプターは自動検出され、レジストリに登録されます。

```python
class AdapterRegistry:
    """アダプターの管理"""

    def __init__(self):
        self._adapters: list[CAEAdapter] = []

    def register(self, adapter: CAEAdapter):
        """アダプターを登録"""
        self._adapters.append(adapter)

    def get_adapter(self, file_path: Path) -> CAEAdapter | None:
        """ファイルに適したアダプターを取得"""
        for adapter in self._adapters:
            if adapter.can_handle(file_path):
                return adapter
        return None
```

---

## 3. 対応ソフト一覧

### 3.1 Abaqusアダプター

#### 対応拡張子

- `.inp` : 入力ファイル
- `.cdb` : メッシュファイル
- `.odb` : 結果ファイル

#### 生成ファイル予測

入力ファイルが `go_sample_v1_idx1.inp` で、jobが `model` の場合:

```python
predicted_files = [
    "model.odb",
    "model.dat",
    "model.msg",
    "model.sta",
    "model.log",
]
```

#### プロパティ抽出

```python
# go_sample_v1_idx1.inp の内容から抽出
properties = {
    "cpus": "4",
    "memory": "8",
    "solver": "standard",
}
```

### 3.2 Fluentアダプター

#### 対応拡張子

- `.cas.h5` : ケースファイル
- `.dat.h5` : データファイル
- `.jou` : ジャーナルファイル

#### 生成ファイル予測

入力ファイルが `input.cas.h5` の場合:

```python
predicted_files = [
    "output.dat.h5",
    "convergence.out",
    "transcript.log",
]
```

#### プロパティ抽出

```python
# input.cas.h5 の内容から抽出
properties = {
    "solver": "pressure-based",
    "turbulence_model": "k-epsilon",
}
```

### 3.3 LS-DYNAアダプター

#### 対応拡張子

- `.k` : キーワードファイル
- `.key` : キーワードファイル
- `.dat` : データファイル

#### 生成ファイル予測

入力ファイルが `go_sample_v1_idx1.k` の場合:

```python
predicted_files = [
    "d3hsp",
    "messag",
    "binout0000",
]
```

#### プロパティ抽出

```python
# go_sample_v1_idx1.k の内容から抽出
properties = {
    "ncpu": "8",
    "memory": "2gb",
}
```

---

## 4. アダプターの実装例

### 4.1 Abaqusアダプター

```python
from pathlib import Path
from types import Node

class AbaqusAdapter(CAEAdapter):

    def get_name(self) -> str:
        return "abaqus"

    def can_handle(self, file_path: Path) -> bool:
        return file_path.suffix in [".inp", ".cdb", ".odb"]

    def parse_file(self, file_path: Path) -> Node:
        # FileParse基底クラスを利用
        from services.parse.file_parse import FileParse
        parser = FileParse(file_path)

        # Abaqus固有のプロパティを追加
        properties = parser.get_props()
        properties.update(self.extract_properties(file_path))

        return Node(
            id=0,  # IDは後で採番
            type="file",
            name=file_path.name,
            format=file_path.suffix.lstrip('.'),
            properties=properties,
        )

    def predict_output_files(self, input_file: Path, command: str) -> list[Path]:
        # コマンドからjob名を抽出
        job_name = self._extract_job_name(command)

        return [
            Path(f"{job_name}.odb"),
            Path(f"{job_name}.dat"),
            Path(f"{job_name}.msg"),
            Path(f"{job_name}.sta"),
            Path(f"{job_name}.log"),
        ]

    def extract_properties(self, file_path: Path) -> dict[str, str]:
        # .inpファイルを解析してプロパティを抽出
        properties = {}

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if "*HEADING" in line.upper():
                    properties["heading"] = line.split(",")[1].strip()
                # 他のキーワードも解析...

        return properties

    def _extract_job_name(self, command: str) -> str:
        # 'abaqus job=model input=...' からjob名を抽出
        for part in command.split():
            if part.startswith("job="):
                return part.split("=")[1]
        return "default"
```

---

## 5. アダプターの配置

### 5.1 ディレクトリ構造

```
services/
├── parse/
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py           # CAEAdapterベースクラス
│   │   ├── registry.py       # AdapterRegistry
│   │   ├── abaqus.py         # AbaqusAdapter
│   │   ├── fluent.py         # FluentAdapter
│   │   └── dyna.py           # DynaAdapter
│   └── file_parse.py
├── run/
│   └── adapters/
│       ├── __init__.py
│       ├── abaqus.py
│       └── fluent.py
└── file/
    └── adapters/
        ├── __init__.py
        └── templates/
            ├── abaqus/
            ├── fluent/
            └── dyna/
```

### 5.2 自動登録

アダプターは `__init__.py` で自動的に登録されます。

```python
# services/parse/adapters/__init__.py
from .registry import AdapterRegistry
from .abaqus import AbaqusAdapter
from .fluent import FluentAdapter
from .dyna import DynaAdapter

registry = AdapterRegistry()
registry.register(AbaqusAdapter())
registry.register(FluentAdapter())
registry.register(DynaAdapter())
```

---

## 6. アダプターの利用

### 6.1 パーサー層での利用

```python
from services.parse.adapters import registry

file_path = Path("go_sample_v1_idx1.inp")
adapter = registry.get_adapter(file_path)

if adapter:
    node = adapter.parse_file(file_path)
    properties = adapter.extract_properties(file_path)
else:
    # 汎用パーサーを利用
    parser = FileParse(file_path)
    node = parser.to_node()
```

### 6.2 runコマンド層での利用

```python
from services.run.adapters import registry

command = "abaqus job=model input=go_sample_v1_idx1.inp cpus=4"
input_file = Path("go_sample_v1_idx1.inp")

adapter = registry.get_adapter(input_file)

if adapter:
    predicted_files = adapter.predict_output_files(input_file, command)
    # 実行後に予測ファイルの存在を確認
```

---

## 7. 実装計画

### Phase 1: アダプター基盤の構築（中期）

- [ ] `CAEAdapter` ベースクラスの定義
- [ ] `AdapterRegistry` の実装
- [ ] アダプター自動検出機構

### Phase 2: 基本アダプターの実装（中期）

- [ ] Abaqusアダプターの実装
- [ ] Fluentアダプターの実装
- [ ] LS-DYNAアダプターの実装

### Phase 3: 高度なアダプター機能（長期）

- [ ] プラグイン方式のアダプター追加
- [ ] アダプターのバージョン管理
- [ ] アダプター間の連携（例: AbaqusからFluentへのデータ転送）

---

## 8. 設計上の注意事項

### 8.1 拡張性

- 新しいソフトへの対応は新しいアダプタークラスを追加するだけ
- コアロジックへの変更は不要

### 8.2 互換性

- アダプターのインターフェース変更は慎重に
- バージョン管理で後方互換性を維持

### 8.3 パフォーマンス

- アダプター選択はファイル拡張子で高速判定
- ファイル解析は遅延実行

---

## 9. テスト方針

### 単体テスト（pytest）

- `tests/services/test_adapters.py` : 各アダプターのテスト
- `tests/services/test_registry.py` : AdapterRegistryのテスト

### テストケース例

- アダプターの自動選択
- ファイル解析の正確性
- 生成ファイル予測の正確性
- プロパティ抽出の正確性
- 未対応ファイルのフォールバック

---

## 10. 他ドメインとの関係

| ドメイン | 依存関係 | 説明 |
|---------|---------|------|
| パーサー層 | ← アダプター層 | ソフト固有の解析ロジックを提供 |
| runコマンド層 | ← アダプター層 | 実行ロジックと生成ファイル予測を提供 |
| fileコマンド層 | ← アダプター層 | テンプレート生成を提供 |
| 設定管理層 | → アダプター層 | ソフト固有設定を取得 |

---

## 11. 参考資料

- [実装詳細](../detail.md)
- [ロードマップ](../roadmap.md)
- [パーサー層仕様書](./02-parser.md)
- [runコマンド層仕様書](./04-run-command.md)
