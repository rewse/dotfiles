---
name: password-policy
description: Recommend appropriate password strength and 1Password settings based on NIST SP 800-63B authentication assurance levels. Use when the user asks about password requirements, password strength recommendations, what type of password to use for different scenarios, or how to configure 1Password for specific use cases.
---

# Password Policy

## Overview

Provide password strength recommendations based on NIST SP 800-63B guidelines and suggest appropriate 1Password settings for different authentication scenarios.

## Workflow

When a user asks about password requirements:

1. **Understand the context**: Ask clarifying questions to determine:
   - What type of account or service is this for?
   - Does it support multi-factor authentication?
   - Is it a high-security or regulated environment?
   - Are there any specific requirements from the service provider?
   - For activation secrets: Is it numeric-only or does it accept alphanumeric input?

2. **Determine AAL level**: Based on the context, identify the appropriate Authentication Assurance Level
   - AAL1: Single-factor authentication
   - AAL2: Multi-factor authentication
   - AAL3: High-security with phishing-resistant authenticator

3. **Consult references**:
   - references/nist-requirements.md for NIST guidelines
   - references/entropy-calculation.md for entropy calculations

4. **Compare options** based on:
   - NIST minimum length requirements
   - Entropy strength (bits)
   - Usability (memorability, typing ease, auto-fill availability)

5. **Recommend 1Password settings**: Use references/1password-options.md to suggest specific configuration

6. **Explain rationale**: Provide entropy comparison, NIST compliance status, and usability considerations

## Common Scenarios

### Single-Factor Authentication (AAL1)
**Use case**: Basic online accounts, low-risk services

**NIST requirement**: Minimum 15 characters

**1Password options comparison**:

1. **Smart Password** (Recommended)
   - Entropy: ~80-100 bits (estimated)
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

**Example**: "For your blog account, I recommend Smart Password (80-100 bits entropy) or a Memorable Password with 5 words (70.5 bits). Both exceed NIST's 15-character minimum and provide strong security."

### Multi-Factor Authentication (AAL2)
**Use case**: Financial services, email, work accounts, accounts with personal information

**NIST requirement**: Minimum 8 characters (when used with another factor)

**1Password options comparison**:

1. **Smart Password** (Recommended)
   - Entropy: ~80-100 bits (estimated)
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

**Example**: "For your bank account with 2FA, I recommend Smart Password (80-100 bits) or a Memorable Password with 4 words (56.4 bits). With MFA enabled, even 4 words provides adequate security while being easier to type on your phone."

### High-Security Authentication (AAL3)
**Use case**: Government systems, high-value financial accounts, enterprise systems

**NIST requirement**: Multi-factor with phishing-resistant authenticator

**1Password options comparison**:

1. **Smart Password** (Recommended)
   - Entropy: ~80-100 bits (estimated)
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

**Example**: "For your enterprise VPN with hardware token, I recommend Smart Password (80-100 bits) or Random Password with 16 characters (104.8 bits). If you need to type it on secure terminals without auto-fill, use a Memorable Password with 6 words (84.6 bits + separators)."

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

**Example**: "For your YubiKey PIN, I recommend a 6-8 digit PIN Code (19.9-26.6 bits) if it's numeric-only. If it accepts letters, use a Memorable Password with 2-3 words (28.2-42.3 bits) for better security while staying easy to memorize."

## References

- [references/nist-requirements.md](references/nist-requirements.md): NIST SP 800-63B authentication requirements
- [references/1password-options.md](references/1password-options.md): 1Password password generator options
- [references/entropy-calculation.md](references/entropy-calculation.md): Password strength calculation methods
