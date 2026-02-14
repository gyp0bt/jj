[READMEへ戻る](../../README.md)

# status-070: ABQData pickle失敗バグ修正（動的クラスのモジュール登録漏れ）

**日付**: 2026-02-12
**担当**: Claude Code

---

## 概要

ABQDataのキャッシュ保存時に `Can't pickle <class 'services.parse.connectors.abaqus.ReadDensity'>` エラーが発生する問題を修正。

---

## 原因分析

### エラーメッセージ

```
ABQData cache save failed for F:\active\7v\b01\go_idx1.v3.inp: Can't pickle <class 'services.parse.connectors.abaqus.ReadDensity'>: attribute lookup ReadDensity on services.parse.connectors.abaqus failed
```

### 根本原因

`jj/services/parse/connectors/abaqus/__init__.py` の549-555行目で、`type()` による動的クラス生成の戻り値がどこにも代入されていなかった。

**修正前（バグあり）:**
```python
for k in ["SpecificHeat", "Density", "DamageInitiation", "DamageEvolution", "Creep"]:
    type(
        f"Read{k}",
        (MaterialPropertyReadComponent,),
        {},
    )
```

- `type()` はクラスオブジェクトを返すが、戻り値を捨てている
- `ReadComponent.__init_subclass__` により `read_component_list` への登録は成功するため、**INPパース自体は正常に動作**する
- しかし、クラスがモジュールの `globals()` に存在しないため、`pickle` がシリアライズ時にクラスを名前で逆引きできない

### pickleの属性解決プロセス

1. `obj.__class__.__module__` → `services.parse.connectors.abaqus`
2. `obj.__class__.__qualname__` → `ReadDensity`
3. `getattr(sys.modules['services.parse.connectors.abaqus'], 'ReadDensity')` → **AttributeError!**
4. 結果: `PicklingError: Can't pickle ...`

### 影響範囲

以下5つの動的生成クラスすべてが同じ問題を持つ:
- `ReadSpecificHeat`
- `ReadDensity`
- `ReadDamageInitiation`
- `ReadDamageEvolution`
- `ReadCreep`

これらの材料プロパティを含むINPファイルのキャッシュ保存がすべて失敗していた。

---

## 修正内容

**修正後:**
```python
for _k in ["SpecificHeat", "Density", "DamageInitiation", "DamageEvolution", "Creep"]:
    globals()[f"Read{_k}"] = type(
        f"Read{_k}",
        (MaterialPropertyReadComponent,),
        {},
    )
```

`type()` の戻り値を `globals()` に登録することで、`pickle` がモジュール名前空間からクラスを解決可能になった。

---

## 変更ファイル一覧

| ファイル | 変更種別 |
|---|---|
| `services/parse/connectors/abaqus/__init__.py` | 動的クラス生成を `globals()` に登録するよう修正 |
| `docs/status/status-070.md` | 本ステータスファイル |

---

## 副次的な効果

- この修正により、既存のキャッシュファイル（pickle）は問題なく利用可能（クラスが `globals()` に存在するようになるため、デシリアライズも成功する）
- INPパース処理自体には影響なし（`__init_subclass__` による登録は修正前から正常動作）

---

## TODO / 次回引き継ぎ事項

- [ ] 修正後に実際のINPファイル（Density等を含む）でキャッシュの保存・読み込みが成功することを実環境で確認
- [ ] 既存のキャッシュをクリアする必要はない（デシリアライズも修正後は成功する）
- [ ] status-069のTODO引き継ぎ（Phase 3, REST API, ダッシュボード機能拡張など）
