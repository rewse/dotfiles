# 1Password Options Reference

## Smart Password
- Generates passwords using character patterns based on English phonetic rules
- Balances security, usability, and compatibility
- Entropy: ~67-68 bits
- Recommended for most use cases
- How it works:
  - Selects 4 pseudo-syllables from 10,122 patterns
  - One pattern is entirely uppercase
  - Separates with digits (0-9) and symbols (@#$%^&_*)
  - Uses uniform distribution for true randomness

## Random Password
- Characters: 8 to 100
- Numbers: on/off
- Symbols: on/off
- Fully customizable character composition

## Memorable Password
- Words: 2 to 15
- Separator options:
  - Hyphens (-)
  - Spaces ( )
  - Periods (.)
  - Commas (,)
  - Underscores (_)
  - Numbers
  - Numbers and Symbols
- Capitalize: on/off
  - **IMPORTANT**: Capitalizes ENTIRE words, not just first letter
  - Example: "correct" becomes "CORRECT", not "Correct"
- Full Words: Uses complete dictionary words
- Creates passphrase-style passwords

## PIN Code
- Numbers: 3 to 12
- Numeric-only passwords
- Typically used for device unlock or activation factors

## References

- [A smart\(er\) password generator \| 1Password](https://1password.com/blog/a-smarter-password-generator)
