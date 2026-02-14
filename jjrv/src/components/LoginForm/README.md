# LoginForm

> [← README.md](../../../README.md)
> [← Components一覧](../README.md)

## 概要

ユーザー名とパスワードでログインするフォームコンポーネント

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| onSuccess | `() => void` | - | ログイン成功時のコールバック |

## States

- idle: 初期状態
- loading: ログイン処理中
- error: ログイン失敗

## Events

- onSubmit: フォーム送信時にログインAPIを呼び出し
- onSuccess: ログイン成功時に呼び出し

## 備考

- useAuthフックを使用して認証状態を管理
- エラーメッセージは日本語で表示
