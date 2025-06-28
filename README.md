# 🔧 Chrome Troubleshooter

**Advanced Chrome crash diagnosis and auto-remediation tool for Linux systems**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) [![CI](https://github.com/swipswaps/chrome-troubleshooter/workflows/CI/badge.svg)](https://github.com/swipswaps/chrome-troubleshooter/actions) [![Development Status](https://img.shields.io/badge/status-beta-orange.svg)](https://github.com/swipswaps/chrome-troubleshooter)

> **⚠️ BETA STATUS**: This tool is under active development. Core functionality works, but some advanced features are still being implemented. See [Project Status](#-project-status) for details.

## ✨ Features

### 🎯 **Core Functionality**
- **Progressive Launch Fallbacks**: Automatically tries multiple Chrome configurations
- **Comprehensive Diagnostics**: Collects system info, logs, crash dumps, and kernel messages
- **Auto-Remediation**: Fixes common issues (SELinux, Wayland, GPU problems)
- **Structured Logging**: Dual-format logging (JSON Lines + SQLite) with real-time terminal output
- **Flatpak Fallback**: Falls back to Flatpak Chromium when native Chrome fails

### 🔍 **Advanced Diagnostics**
- **System Environment Detection**: Session type, GPU vendor, glibc version
- **Chrome Debug Logs**: Automatic collection from standard locations
- **Crashpad Dump Analysis**: Finds and analyzes recent crash dumps
- **Journal Integration**: Systemd journal analysis for Chrome-related entries
- **dmesg Monitoring**: Kernel message analysis with timestamp deltas
- **Coredump Analysis**: Automatic coredump detection and metadata extraction
- **SELinux Audit**: AVC denial detection and analysis

### 🛠️ **Smart Auto-Remediation**
- **SELinux Fixes**: Automatic chrome_sandbox_t permissive rules
- **Wayland Compatibility**: Forces X11 mode when needed
- **GPU Driver Issues**: Detects and works around VA-API problems
- **Single Instance Protection**: Prevents multiple concurrent runs

### 📊 **Professional Logging**
- **Real-time Terminal Output**: Color-coded messages with timestamps
- **JSON Lines Format**: Streaming-friendly for dashboards and analytics
- **SQLite Database**: Structured storage for complex queries
- **Session Management**: Organized by timestamp with automatic cleanup

## 🚀 Installation

### **Quick Install from GitHub (Recommended)**
```bash
# Install directly from GitHub
pipx install 'chrome-troubleshooter @ git+https://github.com/swipswaps/chrome-troubleshooter.git'

# Or with pip
pip install 'chrome-troubleshooter @ git+https://github.com/swipswaps/chrome-troubleshooter.git'
```

### **From Source (Development)**
```bash
git clone https://github.com/swipswaps/chrome-troubleshooter.git
cd chrome-troubleshooter
pip install -e .
```

### **Development Installation**
```bash
git clone https://github.com/swipswaps/chrome-troubleshooter.git
cd chrome-troubleshooter
pip install -e .[dev]
pre-commit install  # Enable pre-commit hooks
```

## 📋 System Requirements

### **Required Dependencies**
- Python 3.8+
- `flock` (util-linux)
- `journalctl` (systemd)
- `dmesg` (util-linux)
- Chrome/Chromium browser

### **Optional Dependencies**
- `sqlite3` (for database logging)
- `flatpak` (for fallback browser)
- `semanage` (for SELinux fixes)
- `vainfo` (for GPU diagnostics)
- `lspci` (for hardware detection)

### **Check Dependencies**
```bash
chrome-troubleshooter status --check-deps
```

## 🎯 Usage

### **Quick Start**
```bash
# Launch Chrome with troubleshooting
chrome-troubleshooter launch

# Run diagnostics only
chrome-troubleshooter diagnose

# Show system status
chrome-troubleshooter status
```

### **Advanced Usage**

#### **Launch with Custom Settings**
```bash
# Custom timeout and attempts
chrome-troubleshooter launch --timeout 15 --max-attempts 5

# Add extra Chrome flags
chrome-troubleshooter launch --extra-flags --disable-extensions --incognito

# Disable specific features
chrome-troubleshooter launch --no-selinux-fix --no-flatpak-fallback
```

#### **Diagnostics and Analysis**
```bash
# Comprehensive diagnostics
chrome-troubleshooter diagnose --journal-lines 500 --output diagnostics.json

# View recent logs
chrome-troubleshooter logs --latest

# List all sessions
chrome-troubleshooter logs --list

# View specific session
chrome-troubleshooter logs --session 20250628_143022
```

#### **Configuration Management**
```bash
# Show current configuration
chrome-troubleshooter config --show

# Update settings
chrome-troubleshooter config --timeout 20 --max-attempts 6 --enable-colors

# Save custom configuration
chrome-troubleshooter config --config-file ~/.config/ct/custom.json --timeout 30
```

#### **Maintenance**
```bash
# Clean old sessions (older than 7 days)
chrome-troubleshooter clean

# Dry run cleanup
chrome-troubleshooter clean --days 3 --dry-run
```

## 🔧 Configuration

### **Environment Variables**
```bash
# Logging
export CT_COLOR=1                    # Enable colors (default: 1)
export CT_LOG_LEVEL=INFO            # Log level (default: INFO)
export CT_JOURNAL_LINES=200         # Journal lines to collect (default: 200)
export CT_ROTATE_DAYS=7             # Log rotation days (default: 7)

# Chrome Launch
export CT_EXTRA_FLAGS="--disable-extensions"  # Extra Chrome flags
export CT_LAUNCH_TIMEOUT=10         # Launch timeout seconds (default: 10)
export CT_MAX_ATTEMPTS=4            # Maximum attempts (default: 4)

# Features
export CT_SELINUX_FIX=1             # Enable SELinux fixes (default: 1)
export CT_FLATPAK_FALLBACK=1        # Enable Flatpak fallback (default: 1)

# Storage
export CT_BASE_DIR=~/.cache/chrome_troubleshooter  # Base directory
export CT_ENABLE_SQLITE=1           # Enable SQLite logging (default: 1)
export CT_ENABLE_JSON=1             # Enable JSON logging (default: 1)
```

### **Configuration File**
Location: `~/.config/chrome-troubleshooter/config.json`

```json
{
  "enable_colors": true,
  "log_level": "INFO",
  "journal_lines": 200,
  "rotate_days": 7,
  "extra_flags": ["--disable-extensions"],
  "launch_timeout": 10,
  "max_attempts": 4,
  "enable_selinux_fix": true,
  "enable_flatpak_fallback": true,
  "base_dir": "/home/user/.cache/chrome_troubleshooter",
  "enable_sqlite": true,
  "enable_json": true
}
```

## 🔍 Troubleshooting

### **Common Issues**

#### **Chrome Won't Start**
1. Check dependencies: `chrome-troubleshooter status --check-deps`
2. Run diagnostics: `chrome-troubleshooter diagnose`
3. Check recent logs: `chrome-troubleshooter logs --latest`

#### **Permission Errors**
- SELinux issues: Tool automatically adds permissive rules
- File permissions: Ensure Chrome executable is accessible
- Lock file issues: Remove `/tmp/.chrome_troubleshooter.lock`

#### **Missing Dependencies**
```bash
# Fedora/RHEL
sudo dnf install util-linux systemd sqlite flatpak

# Ubuntu/Debian
sudo apt install util-linux systemd-journal sqlite3 flatpak
```

### **Debug Mode**
```bash
# Enable verbose output
chrome-troubleshooter -vv launch

# Save debug diagnostics
chrome-troubleshooter -vv diagnose --output debug.json
```

## 📊 Data Analysis

### **SQLite Queries**
```sql
-- View all log entries
SELECT ts, level, source, content FROM logs ORDER BY ts DESC LIMIT 100;

-- Find error patterns
SELECT source, COUNT(*) as count FROM logs WHERE level = 'ERROR' GROUP BY source;

-- Analyze crash patterns
SELECT content FROM logs WHERE source = 'dmesg' AND content LIKE '%chrome%';
```

### **JSON Lines Processing**
```bash
# Extract errors with jq
cat logs.jsonl | jq 'select(.level == "ERROR")'

# Timeline analysis
cat logs.jsonl | jq -r '[.ts, .source, .content] | @csv'
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make changes and add tests
4. Run tests: `pytest`
5. Format code: `black .`
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📊 Project Status

### **✅ Implemented & Tested**
- ✅ **Core CLI Interface**: Full argparse-based CLI with subcommands
- ✅ **Configuration System**: Environment variables + JSON file support
- ✅ **Structured Logging**: Multi-format output (terminal, JSON, SQLite)
- ✅ **Chrome Launcher**: Progressive fallback strategy
- ✅ **Diagnostics Collection**: System info, logs, crash analysis
- ✅ **Auto-remediation**: SELinux fixes, Wayland compatibility
- ✅ **Package Structure**: Modern Python packaging with pyproject.toml

### **🚧 In Development**
- 🚧 **Enhanced CLI with Typer**: Migrating to Typer + Rich for better UX
- 🚧 **Async Operations**: Non-blocking Chrome launches and log collection
- 🚧 **Advanced Analytics**: Prometheus metrics and D3.js visualizations
- 🚧 **RPM/Flatpak Packaging**: Distribution-specific packages

### **📋 Planned Features**
- 📋 **User Telemetry**: Opt-in usage analytics (GDPR compliant)
- 📋 **Web Dashboard**: Browser-based log analysis interface
- 📋 **Plugin System**: Extensible diagnostic modules
- 📋 **Machine Learning**: Pattern recognition for crash prediction

## 🙏 Acknowledgments

- Based on comprehensive Chrome troubleshooting research
- Inspired by community solutions for Fedora Chrome issues
- Built with modern Python packaging best practices
- Enhanced with ChatGPT audit suggestions for production readiness
