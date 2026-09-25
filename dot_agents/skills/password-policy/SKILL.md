---
name: password-policy
description: Recommend appropriate password strength and 1Password settings based on NIST SP 800-63B authentication assurance levels. Use when the user asks about password requirements, password strength recommendations, what type of password to use for different scenarios, or how to configure 1Password for specific use cases. Also trigger when the user mentions "how strong should my password be", "what password settings", "1Password configuration", "password generator settings", "secure password", "password for bank", "password for work", "PIN code length", or needs guidance on password security for any account type.
---

# Password Policy

## Overview

Password strength requirements vary based on risk level and authentication factors. A weak password on a high-value account can lead to account compromise, while an overly complex password on a low-risk account creates unnecessary friction. This skill helps you find the right balance by:

- Applying NIST SP 800-63B guidelines (industry-standard authentication requirements)
- Calculating entropy (randomness) to objectively measure password strength
- Considering usability factors (memorability, typing ease, auto-fill availability)
- Recommending appropriate 1Password settings for your specific scenario

### What is Smart Password?

1Password's Smart Password is designed to balance security with usability and compatibility:

**How it works:**
- Selects 4 character patterns from a list of 10,122 pseudo-syllables (character sequences based on English phonetic patterns)
- One pattern is entirely uppercase
- Separates patterns with digits (0-9) and basic symbols (@#$%^&_*)
- Uses uniform distribution (any possible password is equally likely to be generated)

**Entropy:** ~67-68 bits
- Character patterns: log₂(10,122) × 4 ≈ 53.6 bits
- Uppercase position: log₂(4) = 2 bits
- Separators: log₂(16) × 3 ≈ 12 bits

**Design philosophy:** Sacrifices a few bits of entropy compared to pure random passwords to gain significant advantages in convenience, compatibility with website requirements, and accessibility. The patterns look somewhat human-generated but are actually uniformly random.

## Workflow

The recommendation depends on the Authentication Assurance Level (AAL1: single-factor, AAL2: multi-factor, AAL3: multi-factor with a phishing-resistant authenticator), so establish the facts that determine it: the account or service type, whether it supports MFA, whether the environment is regulated, any requirements the provider imposes, and, for activation secrets, whether input is numeric-only. Ask only for what the request leaves open.

Base the comparison on NIST minimum length, entropy in bits, and usability (memorability, typing ease, auto-fill availability), using references/nist-requirements.md and references/entropy-calculation.md. Recommend concrete 1Password settings from references/1password-options.md, and give the entropy comparison, NIST compliance status, and usability trade-off behind the choice.

## Common Scenarios

### Single-Factor Authentication (AAL1)
**Use case**: Basic online accounts, low-risk services

**NIST requirement**: Minimum 15 characters

**1Password options comparison**:

1. **Smart Password** (Recommended)
   - Entropy: ~67-68 bits
   - NIST compliant: Yes
   - Usability: Excellent (auto-fill)
   - Best default choice for most scenarios

2. **Random Password**: 15-20 characters, all types
   - 15 chars: 98.2 bits
   - 20 chars: 131.0 bits
   - NIST compliant: Yes
   - Usability: Good (auto-fill required)
   - Strongest security option

3. **Memorable Password**: 4-5 words
   - 4 words: 56.4 bits
   - 5 words: 70.5 bits
   - NIST compliant: Yes (typically 20-30+ characters)
   - Usability: Excellent (can be memorized)
   - Best for passwords you need to type manually

**Recommendation**: Use Smart Password for convenience, or Memorable Password (5 words) if you need to type it occasionally.


### Multi-Factor Authentication (AAL2)
**Use case**: Financial services, email, work accounts, accounts with personal information

**NIST requirement**: Minimum 8 characters (when used with another factor)

**1Password options comparison**:

1. **Smart Password** (Recommended)
   - Entropy: ~67-68 bits
   - NIST compliant: Yes
   - Usability: Excellent (auto-fill)
   - Best default choice

2. **Random Password**: 12-16 characters, all types
   - 12 chars: 78.6 bits
   - 16 chars: 104.8 bits
   - NIST compliant: Yes
   - Usability: Good (auto-fill required)
   - Stronger than minimum requirement

3. **Memorable Password**: 3-4 words
   - 3 words: 42.3 bits
   - 4 words: 56.4 bits
   - NIST compliant: Yes (typically 15-25+ characters)
   - Usability: Excellent (can be memorized)
   - Adequate with MFA, easier to type

**Recommendation**: Use Smart Password for best balance, or Memorable Password (4 words) if you need to type it on multiple devices.


### High-Security Authentication (AAL3)
**Use case**: Government systems, high-value financial accounts, enterprise systems

**NIST requirement**: Multi-factor with phishing-resistant authenticator

**1Password options comparison**:

1. **Smart Password** (Recommended)
   - Entropy: ~67-68 bits
   - NIST compliant: Yes
   - Usability: Excellent (auto-fill)
   - Best default choice

2. **Random Password**: 16+ characters, all types
   - 16 chars: 104.8 bits
   - 20 chars: 131.0 bits
   - NIST compliant: Yes
   - Usability: Good (auto-fill required)
   - Maximum security option

3. **Memorable Password**: 5-6 words with complex separators
   - 5 words: 70.5 bits (+ ~3-4 bits for separators)
   - 6 words: 84.6 bits (+ ~3-4 bits for separators)
   - NIST compliant: Yes (typically 30-40+ characters)
   - Usability: Good (can be memorized with effort)
   - Strong security with memorability

**Recommendation**: Use Smart Password or Random Password (16+ chars) for maximum security. Use Memorable Password (6 words) only if you must type it frequently without auto-fill.


### Activation Secrets (PINs for multi-factor authenticators)
**Use case**: Unlocking hardware tokens, activating authenticators

**NIST requirement**: Minimum 4 characters, recommended 6 characters

**1Password options comparison**:

1. **PIN Code**: 6-8 numbers (Recommended for numeric-only)
   - 6 digits: 19.9 bits (1,000,000 combinations)
   - 8 digits: 26.6 bits (100,000,000 combinations)
   - NIST compliant: Yes
   - Usability: Excellent (easy to memorize and type on screen)
   - Adequate for activation secrets with rate limiting

2. **Memorable Password**: 2-3 words (Recommended for alphanumeric)
   - 2 words: 28.2 bits
   - 3 words: 42.3 bits
   - NIST compliant: Yes (typically 10-20 characters)
   - Usability: Excellent (easy to memorize and type with keyboard, more secure than PIN)
   - Better security when alphanumeric input is supported

**Recommendation**: 
- If numeric-only: Use 6-8 digit PIN Code
- If alphanumeric supported: Use Memorable Password with 2-3 words for better security and memorability

The physical possession of the hardware token provides the primary security factor.


## References

- [references/nist-requirements.md](references/nist-requirements.md): NIST SP 800-63B authentication requirements
- [references/1password-options.md](references/1password-options.md): 1Password password generator options
- [references/entropy-calculation.md](references/entropy-calculation.md): Password strength calculation methods
