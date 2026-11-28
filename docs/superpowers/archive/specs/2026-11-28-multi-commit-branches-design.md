# 複数コミットの作業をブランチと squash PR で取り込む

## 意図

PR は原則 squash で取り込むと決めたが、デフォルトブランチへ直接 push したコミットはそれを通らない。過去 60 日では dotfiles の 212 コミットのうち PR 経由は 41、ansible-playbooks は 352 のうち 78 で、大半が直接 push だった。1 コミットの修正を直接 push しても履歴は読みにくくならないが、superpowers の計画のようにまとまった作業の細かいコミットが直接 push されると、squash に統一した意味がなくなる。実際に squash 統一の作業自体が、修正コミットを含む 4 コミットのまま dotfiles の main に push された。

## ゴール

- 2 コミット以上になる作業はブランチで進め、PR を squash merge して取り込む。
- 1 コミットで済む変更は、これまでどおりデフォルトブランチへ直接 push してよい。

## 非ゴール

- GitHub の ruleset や branch protection で直接 push を禁止すること。
- push 前に複数コミットを検出する hook。ルールのすり抜けが起きたら別途検討する。
- push 済みの 4 コミット（`8ace90b`〜`d6c736d`）の書き換え。force push が要るので残す。

## 制約

- ルールは `.chezmoitemplates/rules/common-standards.md` の Pull Request Standards に書く。リポジトリの `AGENTS.md` が別のルールを定めていればそちらに従う、という既存の例外がこのルールにもかかる。
- push、PR 作成、マージには引き続きユーザーの確認が要る。

## Approaches

- **A. ruleset で直接 push を禁止する**: GitHub が強制するので確実だが、1 行の修正にもブランチ、PR、CI 待ちが要る。admin を bypass にすると自分は push できてしまうので、例外なしの運用になる。
- **B. ルールでコミット数により分ける（採用）**: 1 コミットの変更は手軽なまま、困っていた複数コミットの作業だけ squash を通る。GitHub は強制しないので、エージェントがルールを守る前提になる。
- **C. B に加え、push 前に hook で複数コミットの push を止める**: 読み落としも防げるが仕組みが増える。B ですり抜けが起きてから足せばよい。

ユーザーは B を選んだ。

## 決めたこと

- Pull Request Standards に次を足す: 2 コミット以上になる作業はブランチ（worktree を含む）で進め、PR を squash merge して取り込む。デフォルトブランチへ直接 push するのは 1 コミットで済む変更だけにする。
- コミット数は作業の開始時に見込みで判断する（実装者の判断）。spec と plan を書く作業は、それだけで spec、plan、実装、archive の複数コミットになるので、spec を書く前からブランチで進める。1 コミットのつもりで始めて 2 コミット目が要るとわかったら、push する前にブランチへ移す。

## 実装者に任せること

- ルールの文面。Rule Authoring Standards に従い、指示を先に書く。
