---
inclusion: manual
---

# Python規約

## ビルドシステム

- Pythonプロジェクトのビルドシステムにはuvを使う必要がある
- `src`レイアウトを使用するプロジェクトで `uv run <command>` でコンソールスクリプトを実行する場合、以下の設定を`pyrpoject.toml`に追加しなければならない

```toml
[project.scripts]
my-command = "my_package.cli:main"

[build-system]
build-backend = "uv_build"

[tool.uv.build-backend]
module-root = "src"
```

### トラブルシューティング

- WEHN `ModuleNotFoundError`が発生する THEN 再度実行してみる

## テスト

テストには `uv run` を使用しなければならない

実行例: `PYTHONPATH=src uv run pytest tests/test_foo.py`
