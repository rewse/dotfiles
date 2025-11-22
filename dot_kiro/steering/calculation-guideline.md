---
inclusion: always
---

# 計算ガイドライン

## 要求レベルについて
この文書における次の各キーワード「しなければならない (MUST)」、「してはならない (MUST NOT)」、「要求されている (REQUIRED)」、「することになる (SHALL)」、「することはない (SHALL NOT)」、「する必要がある (SHOULD)」、「しないほうがよい (SHOULD NOT)」、「推奨される (RECOMMENDED)」、「してもよい (MAY)」、「選択できる (OPTIONAL)」は、RFC 2119 で述べられているように解釈されるべきものです。

## 基本方針

計算を行う際は、適切なツールを使用して正確性を確保しなければなりません (MUST)。

## 数値計算

数値を計算する場合は `python3` を使用しなければなりません (MUST)。

### 理由
- 高精度な浮動小数点演算が可能
- 複雑な数式の計算に対応
- 標準ライブラリで数学関数が利用可能
- シェルの算術演算の制限（整数のみ）を回避

### 使用例

```bash
# 基本的な計算
python3 -c "print(123 + 456)"

# 浮動小数点演算
python3 -c "print(10 / 3)"

# 複雑な計算
python3 -c "import math; print(math.sqrt(2))"

# 複数行の計算
python3 << 'EOF'
result = 0
for i in range(1, 101):
    result += i
print(result)
EOF
```

## 日付計算

日付を計算する場合は `python3` を使用しなければなりません (MUST)。

### 理由
- タイムゾーンを正確に処理
- 夏時間の考慮
- 標準的な日付フォーマットのサポート
- クロスプラットフォーム対応（macOS と Linux で完全に同じコードが動作）
- 数値計算と統一された方法で扱える

### 使用例

```bash
# 現在の日付
python3 -c "from datetime import datetime; print(datetime.now().strftime('%Y-%m-%d'))"

# 特定のフォーマット
python3 -c "from datetime import datetime; print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))"

# 相対的な日付（3日後）
python3 -c "from datetime import datetime, timedelta; print((datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d'))"

# 相対的な日付（1週間前）
python3 -c "from datetime import datetime, timedelta; print((datetime.now() - timedelta(weeks=1)).strftime('%Y-%m-%d'))"

# 特定の日付から計算
python3 -c "from datetime import datetime, timedelta; base = datetime.strptime('2024-01-01', '%Y-%m-%d'); print((base + timedelta(days=30)).strftime('%Y-%m-%d'))"

# 複数行の計算
python3 << 'EOF'
from datetime import datetime, timedelta

# 今日から30日後
today = datetime.now()
future = today + timedelta(days=30)
print(f"30日後: {future.strftime('%Y-%m-%d')}")

# 日付の差分を計算
date1 = datetime.strptime('2024-01-01', '%Y-%m-%d')
date2 = datetime.strptime('2024-12-31', '%Y-%m-%d')
diff = (date2 - date1).days
print(f"日数の差: {diff}日")
EOF
```

## 注意事項

- シェルの算術演算 (`$(( ))`) は整数のみをサポートするため、浮動小数点が必要な場合は使用してはなりません (MUST NOT)
- `bc` コマンドも計算に使用できますが、`python3` の方が可読性が高く推奨されます (RECOMMENDED)
- `date` コマンドは macOS と Linux で構文が異なるため、クロスプラットフォーム対応が必要な場合は `python3` を使用しなければなりません (MUST)
