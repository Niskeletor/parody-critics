module.exports = [
  {
    languageOptions: {
      ecmaVersion: 2021,
      globals: {
        window: 'readonly',
        document: 'readonly',
        console: 'readonly',
        fetch: 'readonly',
        WebSocket: 'readonly',
        setTimeout: 'readonly',
        clearTimeout: 'readonly',
        setInterval: 'readonly',
        clearInterval: 'readonly',
        requestAnimationFrame: 'readonly',
        alert: 'readonly',
        confirm: 'readonly',
        module: 'readonly',
        require: 'readonly',
        process: 'readonly',
        __dirname: 'readonly',
        app: 'readonly',
      },
    },
    rules: {
      'no-console': 'warn',
      'no-unused-vars': 'warn',
    },
  },
  {
    ignores: ['node_modules/**', 'venv/**', 'coverage/**'],
  },
];
