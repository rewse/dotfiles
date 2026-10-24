# Kiro CLI の Otty 完了通知と resume

## 目的

Kiro を動かしたまま別のアプリを見ていると、ターンが終わっても気づけない。今は Otty から「kiro-cli / Finished — zsh」という中身のない通知が来るだけで、どの Kiro が何を返したかは分からない。ターンが終わったら、プロジェクト名と返答の冒頭が載った通知を出す。あわせて、Otty が落ちたり Mac を再起動したりしたあとでも、タブを開き直すと同じ会話に同じ起動オプションで戻れるようにする。優先するのは通知のほうである。

## 目標

- ターンが終わるたびに、プロジェクト名と最後の返答の冒頭を載せた macOS 通知を1つだけ出す。
- 承認待ちと質問待ちのバッジと通知を、Kiro 本体の報告のとおりに出す。
- Otty の再起動後に `kiro-cli chat --resume-id <id>` で会話を戻す。起動時の `--trust-all-tools` などのオプションも付け直す。
- 自分で終了した Kiro は復活させない。

## 対象外

- Otty の History、Fork、Usage、Quota。Otty に組み込まれた adapter を持つ agent にしか提供されない。
- Kiro 本体の `chat.enableNotifications`。Otty の中では BEL を鳴らすだけなので、今の設定のままにする。
- Linux。macOS だけで配布する。

## 避けること

- `japanese-guard` に差し戻される英語の下書きを通知すること。差し戻されたターンでは Stop がもう一度発火しないので、下書きを通知すると本当の完了と区別がつかなくなる。
- 1ターンに通知が2つ届くこと。
- Otty が動いていないときや tty に書けないときに、hook が Kiro を止めたりエラーを出したりすること。

## 制約

Kiro と Otty のあいだで今起きていること:

- Kiro 本体は端末に OSC 7501（Program Status）を送る。ターンの始まりに `state=working:app=kiro-cli`、終わりに `state=done:app=kiro-cli`、承認や質問を待つときに `state=blocked:kind=...` を送る。`msg` と `title` は付かない。環境変数 `KIRO_NO_PROGRAM_STATUS` を設定すると送らなくなる。
- Otty は OSC 7501 からタブのバッジと通知を作る。「kiro-cli / Finished — zsh」は、この `done` から作られた通知である。`done` の通知には「Notify on Command Finish」（`privilege-notification-on-finish`）、`blocked` の通知には「Notify When Awaiting Input」が要る。前者は既定でオフだが、今の設定ではオンになっている。
- Otty は、`otty tab badge` で付けたバッジを OSC 7501 のバッジより優先する。今の `otty-state.sh` は `SessionStart`、`UserPromptSubmit`、ツールの前後、`Stop` でバッジを付けるので、Kiro の `blocked` バッジが隠れている。
- hook から `msg` 付きの `done` を送る試作では、Kiro の `done` の前に送っても後に送っても、通知は「Finished」のままだった。記録は受け付けられ、タブのプレビューと Inbox には `msg` が出た。Otty は少し間をおいて記録の状態の変化を見て通知を出すので、同じ記録を使うかぎり Kiro の `done` を内容つきの通知に置き換えられないと考えられる。同じペインからの通知は3秒に1回までで、あふれた分は捨てられる。

hook を書くうえでの制約:

- Kiro の hook は aim サンドボックスの中で動き、制御端末を持たない。`/dev/tty` は開けないが、ペインの tty デバイス（`/dev/ttys007` など）はパスで開いて書ける。試作で OSC 777 の通知が出ることを確かめた。
- 起動したシェルで設定した環境変数は hook まで届く。
- `SessionStart` と `Stop` の stdin には `session_id` と `cwd` が入る。
- Stop hook には返答のテキストが渡らない。`japanese-guard-kiro.py` は `~/.kiro/sessions/<cwd hash>/<session_id>/messages.jsonl` から、最後のツール呼び出しより後ろの `Say` を拾っている。
- Otty は `notification-foreground = "tab-unfocused"` で動いている。開いているタブからの通知は出ない。
- OSC 88 の `arm` は、`cmd` の basename と同じ名前のプロセスがペインのプロセスツリーにいないと登録されない。ペインには `kiro-cli chat ...` のプロセスがいる。
- インストール済みの otty 1.6.2 には `otty resume:arm` がないので、OSC 88 は自分で組み立てて書く。
- Kiro の hook には終了時のトリガーがない。
- `~/.config/otty/config.toml` は Otty が書き換える実ファイルを正とし、変更は `chezmoi add` で取り込む（AGENTS.md）。
- `dot_zshrc.tmpl` には `ka`（`kiro-cli chat --trust-all-tools`）と `kar`（`... --resume`）の alias がある。

## 検討した方式

hook の作り方:

- A. 今の `otty-state.sh` を sh のまま広げる。JSONL の読み取り、英語の判定、Markdown の除去、日本語を文字数で切る処理を sh で書くことになり、`japanese-guard-kiro.py` と同じ処理を二重に持つ。
- B. Python の hook を新しく作り、`japanese-guard-kiro.py` の `final_answer` と `japanese-guard.py` の `is_english` を読み込んで使い回す。
- C. hook を使わずラッパーだけで済ませる。ラッパーにはターンの終わりが分からないので外した。

利用者は B を選んだ。

通知の出し方:

- 1. hook から別の記録（`id=reply` など）に `done` を3秒以上遅らせて送る。承認待ちの通知は残るが、1ターンに通知が2つ届く。2つ目が本当に出るかも確かめていない。
- 2. Otty の「Notify on Command Finish」をオフにして、Kiro の `done` の通知を止め、内容つきの通知は hook から OSC 777 で出す。承認待ちの通知は残り、1ターンに通知は1つになる。裏で動かしたシェルのコマンドが終わったときの「Command Finished」も出なくなる。失敗したときの通知は別の設定なので残る。
- 3. `KIRO_NO_PROGRAM_STATUS=1` で Kiro の OSC 7501 を止め、状態も通知も hook から送る。通知は1つになるが、hook には承認待ちが分からないので、そのバッジと通知を失う。

利用者は 2 を選び、「Command Finished」がなくなることを受け入れた。

## 決めたこと

### Otty の設定

`~/.config/otty/config.toml` から `privilege-notification-on-finish = true` を外して既定のオフに戻し、`chezmoi add` で取り込む。

### バッジ

`otty-state` の hook をやめ、バッジは Kiro 本体の OSC 7501 に任せる。`private_dot_kiro/hooks/otty-state.json.tmpl` と `executable_otty-state.sh`、そのテスト、`.chezmoiignore` の2行を消し、`.chezmoiremove` に `.kiro/hooks/otty-state.json` と `.kiro/hooks/otty-state.sh` を理由つきで足す。

### ラッパー関数

`dot_zshrc.tmpl` に zsh 関数 `kiro-cli` を置く。サブコマンドが `chat` のとき（引数なしの場合も含める）は、ペインの tty（zsh の `$TTY`）と、引数をシェルの書き方で引用した文字列を環境変数に入れて本体を起動する。本体が終わったら OSC 88 `clear` を `$TTY` に書く。Otty ごと落ちたときはラッパーも一緒に終わるので `clear` は送られず、登録が残る。`chat` 以外のサブコマンドはそのまま本体に渡す。

### hook

Python の hook を1本作り、Kiro の hook 定義の `SessionStart` と `Stop` から呼ぶ。tty の環境変数がないとき、つまりラッパーを通さずに起動したときは何もしない。

`SessionStart` では OSC 88 `arm` を書く。`cmd` は `kiro-cli` にする。`args` は、起動時の引数から `-r`、`--resume`、`--resume-picker`、`--resume-id <id>` を取り除き、`--resume-id <session_id>` を足したもの。`cwd` には stdin の `cwd` を入れる。

`Stop` では OSC 777 の通知を書く。タイトルは `Kiro — <cwd の末尾のディレクトリ名>`、本文は最後の返答から Markdown の記号とコードの囲みを外し、空白をまとめて頭から100字ほどに切ったもの。`is_english` が真のときは通知しない。

シーケンスは1回の `write` でまとめて書く。どの失敗も握りつぶして、終了コード 0 で抜ける。

## 実装する人に任せること

- 環境変数の名前。Kiro 本体が使う名前とぶつからないように、`KIRO_OTTY_TTY` と `KIRO_OTTY_ARGS` のような接頭辞を付けるのを提案する（こちらの判断）。
- hook のファイル名と置き場所、hook 定義のファイル。`japanese-guard` を相対パスで読み込めるように、スクリプトは `dot_agents/hooks/` に置くのを提案する（こちらの判断）。macOS 以外では `.chezmoiignore` で配布から外す。
- OSC 777 のタイトルと本文に入れる前の掃除。区切りの `;` と制御文字はタイトルに入れられない。
- 返答が空のときの本文（固定の文言にするか、通知自体を出さないか）。
- 100字の切り方と、本文の末尾に付ける省略記号。
- テスト。`tests/test_kiro_hooks.py` に追加し、tty の環境変数には一時ファイルのパスを渡して、書き込まれたバイト列を確かめる。

## 実装するときに確かめること

- 「Notify on Command Finish」をオフにしたあと、Kiro の `done` から通知が出なくなり、`blocked` の通知とバッジは出ること。
- Otty が resume するとき、シェルを通して起動するか。通さない場合はラッパー関数が効かないので、復活したセッションでは通知も `clear` も効かなくなる。
- `/load` などでセッションを切り替えたときに `SessionStart` が発火するか。発火しないと、登録が古い会話を指したまま残る。
