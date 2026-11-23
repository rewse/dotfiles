# Kiro の自動承認を approve-for-me に任せる

## 目的

`private_dot_kiro/private_settings/private_permissions.yaml.tmpl` は、シェルコマンドを約 630 個の glob で自動承認している。glob は引数を文字列としてしか見ないので、オプションの結合、出力オプション、グロブ、設定ファイルの差し替えといった抜け道が見つかるたびに例外とテストが増えてきた。`dot_agents/hooks/executable_redirect-guard-kiro.py` も、その抜け道を塞ぐために 1000 行を超えた。

個別の自動承認をやめ、ルールで決まらない操作は Kiro の approve-for-me（trust classifier）に判断させる。手で書くルールは、確実に安全な許可と、確実に止めたい操作だけにする。

## ゴール

- user スコープの `permissions.yaml` に `policies: [approve-for-me]` を書き、chezmoi で管理する
- シェルの個別 allow ルールをすべて削除する
- 秘密のパスへの `ask` ルールは残す。ask は allow と evaluate より強いので、preset の許可や分類器の承認より優先される
- フックを、リダイレクト先のチェックと秘密のパスのチェックだけに縮める

## 非ゴール

- 分類器が判断を誤るケースを、ルールやフックで網羅すること
- `--no-interactive` のジョブの権限。ジョブは一時的な `KIRO_HOME` に専用のエージェントを置いて動かすので、この変更の影響を受けない

## 受け入れるリスク

- approve-for-me は workspace 内の書き込みと `read-only-shell` を無条件で許可する。エージェントが workspace にファイルを書いてから、無害に見えるコマンドでそれを実行させる経路は防がない。たとえば `config/mcporter.json` を書いてから `mcporter call`、Makefile を書いてから `make` がこれに当たる。オーナーはこの種類のリスクを受け入れた
- 分類器は確率で判断し、判断の中身は見えない。プロンプトインジェクションで、無害に見えるコマンドに誘導される可能性は残る。秘密のパスとリダイレクトはフックと ask ルールで止める

## 検討した方式

| 方式 | 内容 | 判断 |
|---|---|---|
| glob の許可リストを直し続ける | 抜け道が見つかるたびに exclude とフックを足す | 採らない。抜け道は glob の数だけあり、終わりがない |
| approve-for-me と最小限のルール | 個別の allow を消し、分類器に任せる。ask ルールとフックは残す | 採用 |
| すべて手動承認 | allow を消し、approve-for-me も使わない | 採らない。確認が多すぎて使えない |

## 設計

### permissions.yaml

- `policies: [approve-for-me]` を追加する
- 残すルールは次のとおり
  - shell の `ask`: `$secretPaths`（今の一覧のまま）
  - `fs_read` の `allow`: 今の 6 パターン（`.`、`./**`、`/tmp/**`、`/private/tmp/**` など）
  - `fs_write` の `allow`: 今の 5 パターン（`./**`、`/tmp/**`、`/private/tmp/**`、`~/Desktop/**`、`~/Downloads/**`）。approve-for-me は workspace 外のファイル操作を判断しないので、残さないと毎回確認になる
  - `skill` と `subagent` の `allow`。サブエージェントのツール呼び出しは、親のポリシーでも検査される
  - 業務用 host だけにある `mcp` の `allow`（`builder-mcp/ReadInternalWebsites`）。行き先が社内サイトに限られ、外に出すリスクが低いので、オーナーの判断で残す
- `policies` は host で分けない。業務用 host と、そこで AIM が管理するエージェントにも approve-for-me を効かせる（オーナーの判断）
- 削除するルールは次のとおり
  - shell の allow 6 本（汎用コマンド、出力オプション付きのコマンド、git と rg、agent-browser、mcporter、sysctl）
  - `web_fetch` と `web_search` の無条件 allow。URL やクエリ文字列でデータを外に出せるので、分類器に判断させる
- `$secretPaths` は ask ルールでだけ使う。allow ルールがなくなるので、exclude としての用途はなくなる

### フック

`redirect-guard-kiro.py` に残す機能は次の二つだけにする。

- **リダイレクト先のチェック**: Kiro はリダイレクトを外してからルールと照合する。そのため、`read-only-shell` で許可される `git log > ~/.zshrc` が許可ルールに当たってしまう。`>`、`>>`、`&>`、`>|` の書き込み先が許可された場所（作業ディレクトリ、`/tmp`、`~/Desktop`、`~/Downloads`、デバイスファイル）の外ならブロックする。変数やコマンド置換で書き込み先が静的に決まらない場合と、コマンドを字句解析できない場合もブロックする
- **秘密のパスのチェック**: すべてのコマンドのすべての引数と `<` の入力元について、`~` とグロブを展開し、シンボリックリンクを解決する。そのいずれかが `SECRET_PATTERNS` に当たれば、ブロックせずに `permissionDecision: ask` を返して確認を出す。ask ルールは文字列でしか照合しないので、`git diff --no-index ~/.a?s/c* /dev/null` のようにグロブで書かれたパスを見逃す。確認にするのは、`rg credentials src` や `chmod 600 ~/.ssh/config` のような普通のコマンドも当たるためで、ask ルールと同じ扱いにそろえる（オーナーとの会話ではなく設計時の判断）。Kiro CLI がフックの `permissionDecision: ask` を受け付けることを実装時に確かめ、受け付けない場合は exit 2 のブロックにする。リダイレクト先のチェックは今のまま exit 2 でブロックする

削除するのは、出力オプションの解析（`OUTPUT_OPTIONS` とパーサ種別ごとの処理）、再帰読み取りの判定（`FILE_READERS`、`TREE_READERS` と祖先ディレクトリの判定）、mcporter のチェック、chezmoi のチェック。

ヒアドキュメントの本文、算術展開、コメントの扱いのうち、リダイレクトの誤検知や見逃しを防ぐのに要るものは残す。どこまで残すかは実装者が既存のテストを見て決める。

### 付随する変更

- `tests/test_kiro_permissions.py` と `tests/test_kiro_hooks.py` を、残したルールと機能だけのテストに縮める。消した glob や機能のテストは削除する
- `AGENTS.md` から、mcporter のサーバーを変えたら `mcporter call` の allow も更新する、という指示を削除する
- `.chezmoitemplates/rules/common-standards.md` の Kiro CLI in Scripts にある `permissions.yaml` の説明を、approve-for-me に合わせて書き直す
- `dot_config/mcporter/private_mcporter.json.tmpl` の `"imports": []` は残す。エディタの設定からサーバーが増えないようにするため
- `private_dot_kiro/private_agents/private_main.json.tmpl` の `read-workspace` preset はそのまま残す。AGENTS.md の規則で、`permissions` キーは消せない

## 確認方法

- テンプレートを `chezmoi execute-template` でレンダリングし、YAML として読めること。`policies` に `approve-for-me` があり、shell のルールが ask の 1 本だけであること
- フックに JSON を渡したとき、`git log > ~/.zshrc` が exit 2 になり、`git diff --no-index ~/.a?s/c* /dev/null` と `cat < ~/.ssh/id_ed25519` が `permissionDecision: ask` を返し、`git log > /tmp/x` と `rg foo src` が何も返さず exit 0 になること
- apply 後に新しい Kiro セッションを開き、`/permissions` に approve for me が有効と表示されること。ルールで決まらないコマンドに `Approved for you` が付くこと

## 実装者に任せること

- フックで残すヘルパー関数の範囲と、テストの整理の仕方
- `permissions.yaml` の冒頭コメントの書き方
