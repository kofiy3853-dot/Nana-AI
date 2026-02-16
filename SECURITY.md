# Security Guidelines for Nana AI Assistant

## API Key Security

### IMPORTANT: Never commit API keys to version control!

1. **Environment Variables**: All API keys are stored in `backend/.env` file
2. **Git Ignore**: The `.env` file is excluded from git via `.gitignore`
3. **Example File**: Use `backend/.env.example` as a template

### If You Accidentally Exposed API Keys:

1. **Immediately regenerate** your API keys:
   - Gemini API: https://aistudio.google.com/app/apikey
   - OpenRouter: https://openrouter.ai/keys

2. **Update** your local `.env` file with new keys

3. **Remove** the exposed keys from git history (if committed):
   ```bash
   git filter-branch --force --index-filter \
   "git rm --cached --ignore-unmatch backend/.env" \
   --prune-empty --tag-name-filter cat -- --all
   ```

## Input Validation

The application includes several security measures:

1. **Command Sanitization**: User inputs are sanitized to prevent command injection
2. **File Size Limits**: Maximum 10MB file uploads
3. **File Type Restrictions**: Only allowed file extensions can be processed
4. **Timeout Protection**: Search operations have timeout limits
5. **Request Validation**: API requests are validated for size and format

## Allowed Operations

The system only allows:
- Opening applications from a predefined whitelist
- File operations within user directories
- System commands from a secure whitelist (sleep, shutdown, restart, lock)

## Recommendations

1. **Run in isolated environment**: Use virtual environments for Python
2. **Keep dependencies updated**: Regularly update packages for security patches
3. **Review logs**: Monitor `backend/server.py` logs for suspicious activity
4. **Limit network exposure**: Backend runs on localhost by default
5. **Use HTTPS**: Frontend uses SSL for secure communication

## Reporting Security Issues

If you discover a security vulnerability, please:
1. Do NOT open a public issue
2. Contact the maintainer privately
3. Provide detailed information about the vulnerability
