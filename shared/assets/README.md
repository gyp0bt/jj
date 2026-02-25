[READMEへ戻る](../README.md)

# assets

テスト用データや設定ファイルのサンプル置き場です。

## ファイル一覧

- `default-config.yaml`: jjのデフォルト設定ファイル。`jj g init`で`.j2/config/config.yaml`にコピーされます。

## default-config.yaml の設定項目

```yaml
# 語彙マッピング
vocab:
  idx: 条件
  ver: バージョン

# パスパターンによるファイルタイプ指定
path-type-map:
  "**go_* | **go":
    "*.inp": Abaqusインプット
    ...

# パスパターンによるプロパティ指定
path-property-map:
  "**old/*":
    active: false

# 除外パターン（.gitignore相当）
ignore:
  - ".git"
  - ".j2"
  ...

# Obsidianエクスポート設定
obsidian:
  notes-dir: notes/props
  bases-dir: notes/bases
  prefix: "O-"
  default-views: [...]
```
