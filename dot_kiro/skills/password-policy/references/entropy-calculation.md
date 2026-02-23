# Password Entropy Calculation

## Entropy Formula

Entropy (bits) = log₂(possible_combinations)

## Character Set Sizes

- Lowercase letters (a-z): 26
- Uppercase letters (A-Z): 26
- Numbers (0-9): 10
- Symbols (~!@#$%^&*()_+-={}[]|:;"'<>,.?/): ~32

### Combined Sets
- Lowercase + Uppercase: 52
- Lowercase + Numbers: 36
- Lowercase + Uppercase + Numbers: 62
- Lowercase + Uppercase + Numbers + Symbols: ~94

## Random Password Entropy

For random passwords:
- Entropy = length × log₂(character_set_size)

### Examples
- 8 chars, all types (94): 8 × 6.55 = 52.4 bits
- 12 chars, all types (94): 12 × 6.55 = 78.6 bits
- 15 chars, all types (94): 15 × 6.55 = 98.2 bits
- 16 chars, all types (94): 16 × 6.55 = 104.8 bits
- 20 chars, all types (94): 20 × 6.55 = 131.0 bits

## Memorable Password (Passphrase) Entropy

For passphrases using dictionary words:
- Entropy = number_of_words × log₂(dictionary_size)

### Assumptions
- 1Password uses a dictionary of ~18,000 words
- log₂(18000) ≈ 14.1 bits per word

### Examples
- 3 words: 3 × 14.1 = 42.3 bits
- 4 words: 4 × 14.1 = 56.4 bits
- 5 words: 5 × 14.1 = 70.5 bits
- 6 words: 6 × 14.1 = 84.6 bits

### With Separators
Adding numbers or symbols as separators adds minimal entropy (~3-4 bits per separator).

## NIST Entropy Requirements

NIST SP 800-63B doesn't specify exact entropy requirements but focuses on length:
- AAL1 (single-factor): 15+ characters
- AAL2 (multi-factor): 8+ characters
- AAL3 (hardware-based): 8+ characters with phishing-resistant authenticator

## Security Threshold

- **50+ bits**: Adequate for most online accounts (with rate limiting)
- **60+ bits**: Good security for important accounts
- **70+ bits**: Strong security for sensitive accounts
- **80+ bits**: Very strong security for high-value targets
- **100+ bits**: Excellent security, resistant to advanced attacks

## References

- [NIST SP 800-63B](https://pages.nist.gov/800-63-3/sp800-63b.html)
- [Password Strength - Wikipedia](https://en.wikipedia.org/wiki/Password_strength)
