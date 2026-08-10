# Contributing

This repository documents autonomous agents built for the DEF CON 34 / AI Village HalCTF competition. While the competition has concluded, contributions are welcome for improvements, bug fixes, and educational enhancements.

## How to Contribute

### Reporting Issues

Found a bug or have a suggestion? Please open an issue with:
- Clear description of the problem or enhancement
- Steps to reproduce (for bugs)
- Expected vs. actual behavior
- Relevant logs or screenshots

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/improvement-name`)
3. Make your changes with clear, descriptive commits
4. Test your changes locally
5. Submit a pull request with a clear description

### Areas for Contribution

- **Documentation**: Clarify writeups, add diagrams, improve explanations
- **Code Quality**: Refactor agents, improve error handling, add type hints
- **Testing**: Add unit tests, improve test harness
- **New Challenges**: Document solutions to unsolved challenges (Pantheon, others)
- **Educational Content**: Tutorials, guides, or explanations of techniques

## Code Style

- **Python**: Follow PEP 8 guidelines
- **Documentation**: Use clear, concise language
- **Commits**: Use conventional commit format (feat:, fix:, docs:, etc.)
- **Docker**: Keep images minimal and well-documented

## Testing

Before submitting:
```bash
# Test agent build
cd agents/[agent-name]
docker build -t test-agent .

# Verify scripts
bash -n scripts/*.sh

# Check Python syntax
python3 -m py_compile agents/*/agent.py
```

## Questions?

Open an issue for discussion or reach out via GitHub.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
