# スキル更新処理の設計

## 目的

`run_install-skills.sh` に定義されたすべての外部スキルを取得元の最新版へ更新し、`skills` CLI が参照する現行 lock に登録する。個別の更新に失敗しても残りを処理し、最後に失敗を通知する。

## 更新方式

`install_skills` と `install_skills_claude_only` は、スキルディレクトリの存在を更新可否の判定に使わない。各呼び出しで `skills add` を実行し、取得元からスキルを再取得すると同時に現行 lock の source、skillPath、hash、更新日時を記録する。

旧 `~/.agents/.skill-lock.json` は現行 lock への全対象登録を確認した後に削除する。`skills` CLI が `XDG_STATE_HOME` に作成する `~/.local/state/skills/.skill-lock.json` を唯一の管理台帳とする。

## エラー処理

各スキル、ppt-master の Python 依存関係、OfficeCLI の存在確認と各スキル更新を最後まで実行する。OfficeCLI が見つからない場合も失敗として扱う。失敗件数を共通カウンターへ記録し、終了時に件数を標準エラーへ表示して非ゼロで終了する。すべて成功した場合だけゼロで終了する。

## 検証

- `bash -n run_install-skills.sh` が成功すること
- スクリプト全体がゼロで終了すること
- `skills` 経由の全対象が現行 lock に取得元付きで登録されること
- 各スキルのローカル内容が取得元の最新版と一致すること
- Claude Code と Kiro CLI のリンクが `~/.agents/skills` を参照すること
- Codex が直接参照する `~/.agents/skills` に実体があること
- OfficeCLI の4スキルが配置されること

## 対象外

旧 lock の移行、取得元リポジトリの固定バージョン化、スキル内容へのローカルパッチ、OfficeCLI 自体の更新は行わない。
