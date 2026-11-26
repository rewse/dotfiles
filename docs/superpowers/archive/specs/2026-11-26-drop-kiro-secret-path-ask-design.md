# Kiro の秘密パス確認を廃止する

## 目的と理由

Kiro CLI は、認証情報を置きうる場所（`~/.aws`、`mcporter.json` など）に触れるシェルコマンドで承認を求める。この確認は 2 か所から出る。

- `private_dot_kiro/private_settings/private_permissions.yaml.tmpl` の shell `effect: ask` ルール。コマンド文字列をグロブで照合する。
- `dot_agents/hooks/executable_redirect-guard-kiro.py` の秘密パス検査（`secret_paths()`）。`~`、`$HOME`、ブレース、グロブ、シンボリックリンクを展開してから `SECRET_PATTERNS` と照合し、`permissionDecision: "ask"` を返す。

プロンプトに出るのは「この場所は認証情報を含みうる」という理由だけで、どのコマンドを何のために実行するのかが承認者には分からない。判断材料がないので承認者は毎回 Allow するしかなく、確認が防御として働いていない。chezmoi ソースの `dot_config/mcporter/private_mcporter.json.tmpl` のような誤検知も多い。そこで両方の確認を廃止し、未決のシェルコマンドは approve-for-me の判定に任せる。

## ゴール

- 秘密パスを理由にした承認プロンプトが、yaml ルールからも hook からも出なくなる。
- hook のリダイレクト先検査（許可外への `>` などを exit 2 でブロック）と、引用の危険検査（`quoting_hazard`）はそのまま残す。

## 非ゴール

- 確認プロンプトにコマンドや目的を表示する改善。Kiro 側の UI であり、ここでは扱わない。
- 秘密パスの deny ルール化や、パターンを絞り込んだ再導入。

## 制約と受け入れるリスク

- 認証情報ストアの読み取りは、approve-for-me の分類器が許可すれば無確認で通る。web_fetch や `tvly search` などの持ち出し経路も無確認で使えるため、分類器が見逃した読み取りはそのまま漏えいになりうる。持ち主はこのリスクを受け入れる。`ka`/`kar` の `--trust-all-tools` と同じ扱いになる。
- read ツールでワークスペース外の場所を読む操作は、これまでどおり Kiro の通常プロンプトで確認される（fs_read の allow は `.`、`/tmp`、`~/Desktop`、`~/Downloads` だけ）。

## 検討した方式

1. 誤検知だけ減らす（`*/mcporter*` などを `*.config/mcporter*` に絞る）。承認者に判断材料がないという問題が残るため採らない。
2. hook の秘密パス検査だけ外す。yaml ルールが文字列一致で同じ確認を出し続けるため採らない。
3. 両方外す。持ち主が選んだ方式。

## 変更内容

- `private_permissions.yaml.tmpl`: shell の `ask` ルールとその説明コメントを削除する。fs_read、fs_write、skill、subagent、mcp のルールは残す。
- `executable_redirect-guard-kiro.py`: `SECRET_PATTERNS`、`secret_paths()` と、その検査だけが使う関数・定数（`is_secret`、`reaches_secret`、`input_paths`、`below`、`brace_alternatives`、`HOME_VARIABLE`、`BRACE_LIST`、`MAX_BRACE_WORDS`、`fnmatch` と `glob` の import など）を削除し、`main()` から ask の出力を外す。docstring を、リダイレクトだけを検査する内容に書き直す。リダイレクト検査が使う関数（`command_words`、`ROUGH_WORD` など）は残す。
- `tests/test_kiro_hooks.py` と `tests/test_kiro_permissions.py`: 秘密パスの確認を前提にしたテストを削除し、shell ルールがないことと、秘密パスを含むコマンドに hook が何も返さないことを確かめるテストに置き換える。
- `AGENTS.md`: hook の役割を述べた箇所から秘密パス検査の記述を外す。
- `.chezmoitemplates/rules/common-standards.md` の「Kiro CLI in Scripts」: `permissions.yaml` が「asks before reading credential stores」という記述が事実でなくなるので削る。`KIRO_HOME` を分ける理由は、approve-for-me の判定、MCP サーバー、hook を読み込むことで足りる（Kiro の判断）。
- `main` エージェントのプリセットは `read-workspace` のまま変えない。`tests/test_kiro_agent.py` の `test_default_agent_uses_read_workspace_preset` のコメントは ask ルールを根拠にしているので、根拠を書き直す（Kiro の判断）。
- 実装後にこの Mac で `chezmoi apply` を実行し、`~/.kiro/settings/permissions.yaml`、hook、ルールを配備する。fox、hotel、`7cf34ded5d65` には次回の apply で反映し、この変更では SSH で配備しない（Kiro の判断）。

## 実装者に任せること

- 削除後に未使用になる関数・定数の正確な範囲の見極め。
- テストの置き換え方の細部。
