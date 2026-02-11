[READMEへ戻る](../../README.md)

# status-059: *SURFACE INTERACTION下の材料サブキーワードパースエラー修正 (2026-02-11)

## 概要

`*SURFACE INTERACTION`下に`*DAMAGE INITIATION`や`*DAMAGE EVOLUTION`などの`MaterialPropertyReadComponent`サブクラスが出現した場合に`RuntimeError("current material がありません")`が発生するバグを修正。

## 問題の詳細

### エラー内容
```
pymesh failed to parse F:\active\7v\b01\step_stress_v1.inp: current materialがありません。
```

### 原因分析

`step_stress_v1.inp`内に以下のような構造が存在:

```
*surface interaction, name=scoh
*cohesive behavior, ...
 ...
*damage initiation, criterion=quads, dependencies=1   ← ここでクラッシュ
 ...
*damage evolution, type=displacement, ...              ← ここでもクラッシュ
 ...
```

- `*DAMAGE INITIATION`と`*DAMAGE EVOLUTION`は動的に生成された`MaterialPropertyReadComponent`のサブクラス（`ReadDamageInitiation`, `ReadDamageEvolution`）にマッチ
- `MaterialPropertyReadComponent.__init__`が`context.current_material is None`の場合に`RuntimeError`を投げていた
- `*SURFACE INTERACTION`下ではこれらは接触特性の一部であり、材料定義(`*MATERIAL`)とは無関係
- Abaqus仕様では`*DAMAGE INITIATION`/`*DAMAGE EVOLUTION`は`*MATERIAL`下にも`*SURFACE INTERACTION`下にも配置可能

### 修正内容

`MaterialPropertyReadComponent.__init__`で`context.current_material is None`の場合、`RuntimeError`を投げる代わりに材料への紐付けをスキップ（`return`）するよう変更。

**修正箇所（2ファイル、同一パターン）**:
- `modules/pymesh/read_inp.py`: L504-510
- `services/parse/connectors/abaqus/__init__.py`: L512-518

```python
# 修正前
if context.current_material is None:
    raise RuntimeError("current material がありません")
context.current_material.data.append(self)

# 修正後
if context.current_material is None:
    # *MATERIAL 外（例: *SURFACE INTERACTION 下）で出現した場合
    # エラーにせず、材料への紐付けをスキップする
    return
context.current_material.data.append(self)
```

### 影響範囲

- `*MATERIAL`下で出現する場合の既存動作に変更なし（`current_material`が存在するため正常に紐付けされる）
- `*SURFACE INTERACTION`下で出現した場合、コンポーネントは生成されるが材料辞書には含まれない（RawBlock相当の扱い）
- パイプライン（`parse_material_blocks()`）はもともと影響なし（独自の正規表現パースを使用）

## テスト変更

`tests/test_abaqus_connector.py`:
- `test_step_stress_friction_error` → `test_step_stress_parses_without_error` にリネーム
- `pytest.raises(RuntimeError)` → 正常パースを検証（materials==0, steps==1）
- `TestReadInpRealErrorCases`のdocstring更新

## テスト結果

- 599 passed, 21 skipped, 1 failed（pymesh未インストールの既存問題のみ）
- 既存テストの破壊なし

## 変更ファイル一覧

| ファイル | 変更内容 |
|---|---|
| `modules/pymesh/read_inp.py` | MaterialPropertyReadComponent: RuntimeError→スキップ |
| `services/parse/connectors/abaqus/__init__.py` | MaterialPropertyReadComponent: RuntimeError→スキップ |
| `tests/test_abaqus_connector.py` | test_step_stress_friction_error→正常パーステストに変更 |
| `docs/status/status-059.md` | 本ステータスファイル |

## TODO / 次のステップ

- [ ] パーサーキャッシュの実装（DRY: read_inp結果の共有キャッシュ）
- [ ] include解決の最大探索深度をconfig.yamlで設定可能にする検討
- [ ] `modules/pymesh/read_inp.py`と`services/parse/connectors/abaqus/__init__.py`のコード重複解消（DRY）
