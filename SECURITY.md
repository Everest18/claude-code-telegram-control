# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

**DO NOT** open a public GitHub issue for security vulnerabilities.

Instead, email: ariel@example.com

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will respond within 48 hours and work with you to address the issue.

## Security Best Practices

### For Users
1. Never commit `.env` file
2. Use strong bot tokens
3. Set `TELEGRAM_USER_ID` to restrict access
4. Review logs regularly
5. Keep dependencies updated

### For Contributors
1. Never log secrets or tokens
2. Validate all user inputs
3. Use parameterized queries
4. Follow principle of least privilege
5. Review security implications of changes

## Dependency Security

We use:
- `pip` for dependency management
- GitHub Dependabot for automated updates
- Regular security audits

## Known Issues

None currently.

Last updated: 2026-02-12
