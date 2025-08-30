# Release Guide

Quick reference for creating releases of the Lat Lon Tools QGIS Plugin.

## 🚀 Quick Release (Recommended)

1. **Update CHANGELOG.md**: Add changes to `[Unreleased]` section
2. **Create and push tag**:
   ```bash
   git tag v3.7.5
   git push origin v3.7.5
   ```
3. **Done!** GitHub Actions will automatically:
   - Update `metadata.txt` with version `3.7.5`
   - Update `CHANGELOG.md` with release date
   - Build plugin package (`latlontools-3.7.5.zip`)
   - Create GitHub release with downloadable assets
   - Commit changes back to main branch

## 📋 Manual Release Options

### Via GitHub Actions UI
1. Go to **Actions** → **Manual Release** 
2. Click **"Run workflow"**
3. Enter version: `3.7.5`
4. Choose options:
   - ☑️ Create git tag
   - ☐ Mark as pre-release
5. Click **"Run workflow"**

### Pre-release Example
```bash
git tag v3.8.0-beta1
git push origin v3.8.0-beta1
```

## 📦 What Gets Released

### Package Contents
```
latlontools-3.7.5.zip
└── latlontools/
    ├── All Python modules (*.py)
    ├── metadata.txt (version updated)
    ├── icon.png, LICENSE
    ├── ui/, images/, i18n/, doc/
    ├── Generated documentation (index.html)
    └── README files
```

### Automatic Updates
- ✅ `metadata.txt` version field
- ✅ `CHANGELOG.md` release date  
- ✅ New `[Unreleased]` section added
- ✅ Git commit with updated files

## 🔍 Development Builds

Every push to `main` creates a development artifact:
- **Format**: `latlontools-3.7.5-dev-abc1234.zip`
- **Retention**: 30 days
- **Access**: GitHub Actions → Artifacts

## ✅ Pre-Release Checklist

- [ ] All new features documented in `PLUGIN_ENHANCEMENTS_README.md`
- [ ] `CHANGELOG.md` has `[Unreleased]` section with changes
- [ ] Local testing with `make deploy` successful
- [ ] Plugin Reloader testing completed
- [ ] Version follows semantic versioning (e.g., `3.7.5`)

## 🐛 Hotfix Releases

For urgent fixes:
1. Create hotfix branch: `git checkout -b hotfix/3.7.6`
2. Make minimal changes
3. Update `CHANGELOG.md` with fix details
4. Tag and push: `git tag v3.7.6 && git push origin v3.7.6`
5. Merge back to main

## 📊 Release Workflow Status

Check workflow status at: **Actions** tab in GitHub

### Common Issues
- **Tag already exists**: Delete tag locally and on GitHub first
- **Version format**: Must be `major.minor.patch` (e.g., `3.7.5`)
- **Permissions**: Need write access to repository for releases

## 🔗 Integration with QGIS

1. Download release zip from GitHub Releases
2. Test locally: `make deploy` → Plugin Reloader
3. Submit to [QGIS Plugin Repository](https://plugins.qgis.org/)
4. Version in `metadata.txt` already updated by automation

## 📈 Version Strategy

- **Major** (4.0.0): Breaking changes, major architecture updates
- **Minor** (3.8.0): New features, enhancements
- **Patch** (3.7.6): Bug fixes, small improvements
- **Pre-release** (3.8.0-beta1): Testing versions

---

*For detailed technical information, see [CLAUDE.md - Release Management](CLAUDE.md#release-management)*