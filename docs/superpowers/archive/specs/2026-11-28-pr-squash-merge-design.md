# PR のマージ方式を squash に統一する

## 意図

superpowers で作った feat はタスクごとに細かくコミットされるので、1 コミットにまとめたほうが履歴が読みやすい。また、GitHub の 3 種類のマージ方式のどれを使うか毎回迷い、結果としてリポジトリや状況ごとにばらばらになっている。エージェントはそのばらばらな前例に沿って方式を選ぶので、ばらつきが固定される。原則を 1 つに決め、例外はリポジトリ自身が明文化したものだけにする。

## ゴール

- PR は原則として squash merge で取り込む。例外はリポジトリの AGENTS.md に書かれたものだけにする。
- rewse の自分のリポジトリは、GitHub の設定で squash 以外のボタンを出さない。ルールを読まないツールや手操作でも他の方式を選べないようにする。
- squash でできるコミットの件名が Conventional Commits に従う。

## 非ゴール

- 既存の履歴（ansible-playbooks の merge commit など）の書き換え。
- branch protection や ruleset の導入。
- upstream へ PR を出すための fork（blowfish、obsidian-livesync など）の設定変更。マージは upstream 側で行われる。

## 制約

- ルールは 3 か所に書き、役割を分ける。
  - `.chezmoitemplates/rules/common-standards.md`: マージ方式の原則（全リポジトリ共通、GitHub 以外も含む）。
  - `git/AGENTS.md`（`~/git/AGENTS.md` の生成元）の GitHub Configuration: rewse リポジトリの設定の既定値。この節は fork を対象外としている。
  - `rewse/teslamate` の `AGENTS.md`: teslamate の例外。
- `rewse/teslamate` は public なので、その AGENTS.md は `~/git/AGENTS.md` や common-standards を参照せず、それ単体で読める文にする。
- 設定の既定値を入れるのは、rewse が所有する fork でない、archive されていないリポジトリ 17 個（2026-11-28 時点）: `.github`、`actions`、`ansible-playbooks`、`cloudfront-waf`、`continuum-github`、`dotfiles`、`enecoq-data-fetcher`、`gnucash-import-agent`、`gnucash-quick-expense`、`mac-power-monitor-mqtt`、`outlook-to-icloud-calendar`、`rewse-blog`、`security-findings`、`stock-price-fetcher`、`textlint-config-rewse`、`textlint-rule-ja-space-around-phrase`、`zenn-content`。rewse-blog は fork ではなく、Blowfish テーマを submodule で取り込むので、upstream の更新も通常の PR になり squash で困らない。
- teslamate の upgrade PR は upstream のリリースタグへの `-s ours` マージを含み、`teslamate-fork-upgrade` skill の `inspect_upgrade_state.py` はその履歴で fork の差分を見分ける。squash も rebase もこの履歴を消す。
- GitHub の設定変更は外部への書き込みなので、実行前にユーザーの確認を取る。
- common-standards は `chezmoi apply` で Claude、Codex、Kiro に配る。Codex はディレクトリを glob で読むので include の追加は要らない。`git/AGENTS.md` は `run_after_sync-git-agents-md.sh.tmpl` で `~/git/AGENTS.md` にコピーされる。

## Approaches

- **A. squash のみ、リポジトリ設定でも強制する（採用）**: ボタンが 1 つになるので迷いが消え、エージェントが前例に倣っても squash になる。大きい PR の途中コミットは履歴から消える。
- **B. 基本は squash、コミット単位に意味がある PR だけ rebase**: 例外の判断が毎回要り、迷いとエージェントのぶれが残る。
- **C. ルールだけ書き、設定は変えない**: 変更は最小だが、GitHub の画面には 3 つのボタンが残り、ルールを読まない操作を防げない。

merge commit と rebase の利点（PR 単位の revert、stacked PR での SHA 維持、細かいコミットでの bisect や部分 revert）は、1 人開発で短命な PR が中心の現状では使う場面がない。大きい PR の途中コミットを bisect に使う必要も、ansible-playbooks の merge commit を意図して残す理由もないとユーザーが確認したので A を選んだ。teslamate の upgrade PR だけは merge commit が必要なので、リポジトリの AGENTS.md で上書きする。設定はいつでも戻せる。

## 決めたこと

- common-standards の Commit Message Standards の直後に Pull Request Standards を足し、次を書く:
  - PR は原則として squash merge で取り込む。リポジトリの AGENTS.md に別のルールがあればそれに従う。
  - PR タイトルが squash commit の件名になるので、PR タイトルも Conventional Commits に従う。
- `git/AGENTS.md` の GitHub Configuration に項目を足す: squash merge だけを許可し（`allow_merge_commit=false`、`allow_rebase_merge=false`、`allow_squash_merge=true`）、squash commit の件名を PR タイトル（`squash_merge_commit_title=PR_TITLE`）、本文を空（`squash_merge_commit_message=BLANK`）にする。新しく作るリポジトリにも入れる。既存の 17 リポジトリにもこの設定を入れる。
- squash commit の本文を空にするのは実装者の判断。`COMMIT_MESSAGES` は superpowers の細かいコミットを並べるだけで、`PR_BODY` は Dependabot のリリースノートやコマンド説明をそのまま履歴に入れる。件名末尾の `(#123)` から PR を辿れば詳細は読める。
- `rewse/teslamate` の AGENTS.md に Pull Requests の節を足し、upstream リリースを取り込む upgrade PR は merge commit で、それ以外の PR は squash で取り込むと書く。理由（upgrade skill が `-s ours` マージの履歴に依存すること）も 1 文添える。
- `rewse/teslamate` の設定は merge commit と squash を許可し、rebase を無効にする（実装者の判断）。squash の件名と本文は 17 リポジトリと同じにする。

## 実装者に任せること

- 各ルールの文面。Rule Authoring Standards に従い、指示を先に、理由は範囲を絞るときだけ書く。
- 設定変更のコマンドと、変更後に全リポジトリの値を確かめる方法。
- teslamate の AGENTS.md の変更を PR で入れるか直接 push するか。これまでの teslamate の変更は PR で入れている。
- 既存のメモリ `rewse-branch-cleanup-scope`（新規リポジトリの設定）との重複の扱い。
