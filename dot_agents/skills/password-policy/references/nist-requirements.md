# NIST SP 800-63B Requirements by Authenticator Type

Source: https://pages.nist.gov/800-63-4/sp800-63b.html

## Authentication Assurance Levels (AAL)

### AAL1 - Basic Confidence
- Single-factor or multi-factor authentication
- Permitted authenticator types:
  - Password (memorized secret)
  - Look-up secret
  - Out-of-band device
  - Single-factor OTP
  - Multi-factor OTP
  - Single-factor cryptographic
  - Multi-factor cryptographic
- Reauthentication: 30 days overall (recommended)
- Phishing resistance: Not required
- Replay resistance: Not required

### AAL2 - High Confidence
- Multi-factor authentication required
- Permitted authenticator types:
  - Multi-factor cryptographic
  - Multi-factor out-of-band
  - Multi-factor OTP
  - Password or biometric plus:
    - Single-factor cryptographic
    - Look-up secret
    - Out-of-band device
    - Single-factor OTP
- Reauthentication: 24 hours overall, 1 hour inactivity (recommended)
- Phishing resistance: Recommended; must be available
- Replay resistance: Required
- Authentication intent: Recommended

### AAL3 - Very High Confidence
- Multi-factor authentication with phishing-resistant authenticator required
- Permitted authenticator types:
  - Multi-factor cryptographic
  - Single-factor cryptographic plus password or biometric
- Reauthentication: 12 hours overall, 15 minutes inactivity (recommended)
- Phishing resistance: Required
- Replay resistance: Required
- Authentication intent: Required
- Key exportability: Prohibited

## Password Requirements

### Single-Factor Password (AAL1)
- Minimum length: 15 characters
- Maximum length: At least 64 characters should be permitted
- Composition rules: SHALL NOT be imposed (no requirements for mixtures of character types)
- Character support:
  - SHOULD accept all printing ASCII characters and space
  - SHOULD accept Unicode characters
- Periodic changes: SHALL NOT be required
- Blocklist: SHALL be compared against known commonly used, expected, or compromised passwords

### Multi-Factor Password (AAL2+)
- Minimum length: 8 characters (when used as part of multi-factor authentication)
- Maximum length: At least 64 characters should be permitted
- Same composition and character support rules as single-factor

### Activation Secrets (for multi-factor authenticators)
- Minimum length: 4 characters
- Recommended length: 6 characters
- MAY be entirely numeric (PIN)
- Retry limit: No more than 10 consecutive failed attempts

## Memorable Password (Passphrase)
- Consists of multiple words
- Effective way to create longer passwords
- Subject to same length requirements as passwords
- No specific word count requirements in NIST guidelines

## General Password Guidance
- Use password managers to generate and store strong passwords
- Avoid password reuse across different services
- Use distinct passwords for each authenticated service
- Longer passwords are generally stronger
- Complexity rules (e.g., requiring symbols) are less effective than length
