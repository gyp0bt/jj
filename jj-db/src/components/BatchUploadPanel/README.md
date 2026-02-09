# BatchUploadPanel

> [← README.md](../../../README.md) /[← Components一覧](../README.md)

## 概要
フォルダ/複数ファイルをまとめて受け取り、`.inp` のみ抽出して material 定義ブロックを抽出するアップロードパネル。

## Props
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| files | `File[]` | `[]` | 入力されたファイル群（フォルダ選択を含む） |
| onFilesChange | `(files: File[]) => void` | - | ファイル選択変更時のコールバック |
| onParse | `(result: ParsedMaterialResult) => void` | - | material 抽出結果の通知 |
| className | `string` | `""` | 追加のCSSクラス |

## 型定義
```ts
export type ParsedMaterial = {
  name: string;
  sourcePath: string;
  block: string;
};

export type ParsedMaterialResult = {
  materials: ParsedMaterial[];
  skippedFiles: string[];
  errors: string[];
};
```

## Variants / States
- **idle**: 未選択
- **parsing**: 解析中
- **done**: 解析完了
- **error**: 解析失敗

## Events
- `onFilesChange`: 入力ファイルが変わったとき
- `onParse`: material 抽出が完了したとき

## 抽出ロジック（仕様）
- 対象: 拡張子 `.inp` のみ
- 前処理: **全て小文字化**し、**空白を削除**して比較
- 判定: `*material` 行を起点にブロックを開始
- 終了条件: 次に「`*` で始まる行」が出現し、かつ **以下の material keywords 以外** の場合にブロック終了
- キーワードは **大文字小文字無視**・**空白無視**で一致判定

### material keywords
- `*elastic`
- `*plastic`
- `*density`
- `*expansion`
- `*damage initiation`
- `*damage evolution`
- `*conductivity`
- `*electrical conductivity`
- `*specific heat`
- `*creep`
- `*hyper elastic`

## 備考
- 解析結果は `BatchEntityEditor` に渡して一括編集に接続する想定
- 解析はクライアント側で完結させる（ロジックは簡潔に）
