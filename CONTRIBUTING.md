# Contributing to Parody Critics for Jellyfin

Thank you for your interest in contributing! This document provides guidelines and information for contributors.

## 🎭 Philosophy

Parody Critics is designed to bring humor and entertainment to media consumption while maintaining high technical standards. All contributions should align with these principles:

- **Humor over offense**: Parody should be clever and funny, not mean-spirited
- **Technical excellence**: Code should be clean, well-documented, and tested
- **User experience**: Features should enhance, not disrupt, the Jellyfin experience
- **Extensibility**: New characters and features should fit the existing architecture

## 🚀 Getting Started

### Development Setup

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/your-username/parody-critics-jellyfin.git
   cd parody-critics-jellyfin
   ```

2. **Set up Python environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Initialize database:**
   ```bash
   python run_setup.py
   ```

4. **Start development server:**
   ```bash
   python api/main.py
   ```

### Project Structure

```
parody-critics-api/
├── api/                    # FastAPI server
├── database/               # SQLite schema and initialization
├── frontend/               # JavaScript for Jellyfin
├── models/                 # Pydantic data models
├── scripts/                # Utility scripts
└── tests/                  # Test files (to be added)
```

## 🎨 Adding New Critics

### Character Design Guidelines

Each critic should have:
- **Unique personality**: Distinct voice and perspective
- **Consistent theme**: Color scheme and visual identity
- **Comedic value**: Entertaining and memorable reviews
- **Cultural relevance**: Recognizable archetypes or references

### Implementation Steps

1. **Add to database schema** (`database/schema.sql`):
   ```sql
   INSERT INTO characters (id, name, emoji, color, border_color, accent_color, personality, description, active)
   VALUES ('new_critic', 'New Critic', '🎯', '#FF5733', '#FF5733', 'rgba(255, 87, 51, 0.2)', 'archetype', 'Description here', TRUE);
   ```

2. **Update frontend themes** (`frontend/parody-critics-api-client.js`):
   ```javascript
   // Add hover effects for new character
   .parody-critic-card[data-character="new_critic"]:hover {
       box-shadow: 0 4px 12px rgba(255, 87, 51, 0.2);
   }
   ```

3. **Create prompt template** for LLM generation (future)

4. **Add character documentation** to README

## 🔧 API Development

### Adding New Endpoints

1. **Define Pydantic models** in `models/schemas.py`
2. **Implement endpoint** in `api/main.py`
3. **Add database queries** as needed
4. **Update API documentation** in README

### Database Changes

1. **Update schema** in `database/schema.sql`
2. **Create migration script** if needed
3. **Update models** in `models/schemas.py`
4. **Test with existing data**

## 🎨 Frontend Development

### JavaScript Guidelines

- **No dependencies**: Use vanilla JavaScript only
- **Jellyfin compatibility**: Follow Jellyfin's UI patterns
- **Error handling**: Graceful degradation when API unavailable
- **Performance**: Efficient DOM manipulation and caching

### CSS Guidelines

- **Jellyfin theming**: Match existing Jellyfin styles
- **Responsive design**: Work on all screen sizes
- **Accessibility**: Proper contrast and keyboard navigation
- **Browser compatibility**: Modern browsers (ES6+)

## 📝 Code Style

### Python

- **PEP 8**: Follow Python style guidelines
- **Type hints**: Use type annotations throughout
- **Docstrings**: Document all functions and classes
- **Async/await**: Use async code for I/O operations

### JavaScript

- **ES6+**: Modern JavaScript features
- **camelCase**: For variables and functions
- **CONSTANTS**: For configuration values
- **Comments**: Explain complex logic

### SQL

- **Uppercase keywords**: SELECT, FROM, WHERE, etc.
- **Snake_case**: For table and column names
- **Proper indexing**: Add indexes for performance
- **Foreign keys**: Maintain referential integrity

## 🧪 Testing

### Current Status
- Unit tests: **To be implemented**
- Integration tests: **To be implemented**
- API tests: **To be implemented**

### Future Testing Strategy
- **pytest** for Python tests
- **FastAPI TestClient** for API tests
- **JavaScript unit tests** for frontend
- **Database fixtures** for consistent test data

## 📚 Documentation

### Requirements
- **README updates**: For new features
- **API documentation**: Auto-generated from code
- **Character documentation**: For new critics
- **Setup instructions**: Keep current and accurate

### Style Guide
- **Clear headings**: Use meaningful section titles
- **Code examples**: Show real usage
- **Screenshots**: For UI features
- **Links**: Reference related documentation

## 🐛 Bug Reports

### Information to Include
1. **Environment**: OS, Python version, Jellyfin version
2. **Steps to reproduce**: Detailed reproduction steps
3. **Expected vs actual**: What should happen vs what does happen
4. **Logs**: Relevant error messages or logs
5. **Screenshots**: For UI issues

### Bug Report Template
```markdown
**Environment:**
- OS: [e.g., Ubuntu 22.04]
- Python: [e.g., 3.11.2]
- Jellyfin: [e.g., 10.11.6]

**Steps to Reproduce:**
1. Go to '...'
2. Click on '...'
3. See error

**Expected Behavior:**
A clear description of what you expected.

**Actual Behavior:**
A clear description of what actually happened.

**Additional Context:**
Any other context, logs, or screenshots.
```

## 💡 Feature Requests

### Guidelines
- **Use case**: Explain why the feature is needed
- **User benefit**: How it improves the experience
- **Implementation ideas**: Suggest how it might work
- **Alternatives**: Consider other approaches

## 🚀 Pull Request Process

### Before Submitting
1. **Test your changes**: Ensure everything works
2. **Update documentation**: README, API docs, etc.
3. **Follow code style**: Use consistent formatting
4. **Single responsibility**: One feature per PR

### PR Description Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tested locally
- [ ] API tests pass
- [ ] Frontend integration works

## Screenshots (if applicable)
Include screenshots for UI changes

## Checklist
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] No breaking changes (or breaking changes documented)
```

### Review Process
1. **Automatic checks**: Code style and basic tests
2. **Maintainer review**: Code quality and design
3. **Testing**: Manual testing of new features
4. **Documentation**: Ensure docs are updated

## 🌟 Recognition

Contributors will be recognized in:
- **README**: Contributors section
- **CHANGELOG**: Attribution for major features
- **Releases**: Credit in release notes

## 🤝 Code of Conduct

### Our Standards
- **Respectful**: Be kind and professional
- **Inclusive**: Welcome all contributors
- **Constructive**: Provide helpful feedback
- **Focused**: Keep discussions on-topic

### Not Acceptable
- **Harassment**: Any form of harassment
- **Discrimination**: Based on any personal characteristics
- **Offensive content**: Inappropriate language or content
- **Spam**: Off-topic or promotional content

## 📞 Getting Help

### Communication Channels
- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For general questions
- **Documentation**: Check README and wiki first

### Response Times
- **Bug reports**: Within 48 hours
- **Feature requests**: Within 1 week
- **Pull requests**: Within 1 week

---

Thank you for contributing to Parody Critics for Jellyfin! 🎭

*"The spice must flow... and so must the contributions!"* - SAL-9000