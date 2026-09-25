# Git hook の XDG 移行設計

## 目的

グローバル Git hook を `~/.git-hooks` から XDG 準拠の `~/.config/git/hooks` へ移す。ホスト `7cf34ded5d65` ではシステムの Git Defender hook を使うため、ユーザー Git config に `core.hooksPath` を設定しない。

## 配置

hook のソースを `dot_git-hooks/executable_pre-commit` から `dot_config/git/hooks/executable_pre-commit` へ移す。chezmoi の展開先は `~/.config/git/hooks/pre-commit` になる。

`dot_config/git/config.tmpl` の `[core]` は、ホスト名が `7cf34ded5d65` でない場合だけ次の設定を出力する。

```gitconfig
hooksPath = ~/.config/git/hooks
```

実際のテンプレートでは `~` を使わず、`.chezmoi.homeDir` から絶対パスを生成する。対象ホストでは `hooksPath` 行そのものを出力せず、`/etc/gitconfig` の設定を上書きしない。

## 旧パスの移行

実装時に新しい `~/.config/git/hooks/pre-commit` を chezmoi で反映し、実行可能であることと旧 `~/.git-hooks/pre-commit` から内容が変わっていないことを確認する。確認後、旧 hook を直接削除し、空になった `~/.git-hooks` を `rmdir` で削除する。移行用の chezmoi 管理ファイルは追加しない。

## 変更対象

- Move: `dot_git-hooks/executable_pre-commit` to `dot_config/git/hooks/executable_pre-commit`
- Modify: `dot_config/git/config.tmpl`

hook の処理内容は変更しない。

## エラー処理

- 新 hook が存在しない、実行可能でない、または旧 hook と一致しない場合は旧パスを削除しない。
- 旧ディレクトリにほかのファイルがある場合は `rmdir` が失敗するため、状態を報告してディレクトリを残す。

## 検証

- hook の管理先が `.config/git/hooks/pre-commit` になることを確認する。
- 対象ホストのテンプレート条件では `hooksPath` が出力されないことを確認する。
- 対象外ホストのテンプレート条件では `~/.config/git/hooks` の絶対パスが出力されることを確認する。
- pre-commit hook の内容と実行権限が移動前から変わらないことを確認する。
- 新 hook の確認後、旧 `~/.git-hooks/pre-commit` と空の `~/.git-hooks` が削除されたことを確認する。
