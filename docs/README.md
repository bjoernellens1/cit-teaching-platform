# CIT Teaching Platform - Documentation Index

Welcome to the CIT Teaching Platform documentation! This page helps you find the right documentation for your role and needs.

## 📖 Documentation by Role

### 🎓 I'm a Student / User

**Start here**: [User Guide](USER_GUIDE.md)

**What you'll learn**:
- How to login and enroll in courses
- Using JupyterHub and notebooks
- Understanding compute profiles
- File storage and organization
- Best practices for resource usage

**Quick links**:
- [First-time Login](USER_GUIDE.md#first-time-login)
- [Using JupyterHub](USER_GUIDE.md#using-jupyterhub)
- [Storage Layout](USER_GUIDE.md#your-storage-layout)
- [FAQ](USER_GUIDE.md#frequently-asked-questions)

---

### 👨‍🏫 I'm a Course Instructor / Admin

**Start here**: [Admin Guide](ADMIN_GUIDE.md)

**What you'll learn**:
- Managing users and groups
- Creating and managing courses
- Configuring compute profiles
- Monitoring platform health
- Rotating secrets
- Operational procedures

**Quick links**:
- [Course Management](ADMIN_GUIDE.md#course-management)
- [User Management](ADMIN_GUIDE.md#user-management)
- [Resource Management](ADMIN_GUIDE.md#resource-management)
- [Monitoring](ADMIN_GUIDE.md#monitoring-and-maintenance)

---

### 💻 I'm a Developer / Contributor

**Start here**: [Developer Guide](DEVELOPER_GUIDE.md)

**What you'll learn**:
- Platform architecture and design
- Development environment setup
- GitOps workflow with Fleet
- Customizing components
- Testing and deployment
- Contributing guidelines

**Quick links**:
- [Architecture](DEVELOPER_GUIDE.md#architecture)
- [Development Setup](DEVELOPER_GUIDE.md#development-environment-setup)
- [Customization Guide](DEVELOPER_GUIDE.md#customization-guide)
- [Common Tasks](DEVELOPER_GUIDE.md#common-development-tasks)

---

### 🏗️ I'm on the Infrastructure Team

**Start here**: [Infrastructure Guide](INFRASTRUCTURE.md)

**What you'll learn**:
- Infrastructure requirements
- Initial deployment procedures
- Networking and storage architecture
- High availability setup
- Backup and disaster recovery
- Monitoring and capacity planning

**Quick links**:
- [Initial Deployment](INFRASTRUCTURE.md#initial-deployment)
- [Cluster Architecture](INFRASTRUCTURE.md#cluster-architecture)
- [Storage](INFRASTRUCTURE.md#storage)
- [Backup & DR](INFRASTRUCTURE.md#backup-and-disaster-recovery)

---

## 📚 Documentation by Topic

### Getting Help

- **Something's not working**: [Troubleshooting Guide](TROUBLESHOOTING.md)
- **Security questions**: [Security Guide](SECURITY.md)
- **Initial setup**: [SOPS Bootstrap Guide](BOOTSTRAP-SOPS.md)

### By Component

- **Authentik (Identity)**: [bundles/10-authentik/README.md](../bundles/10-authentik/README.md)
- **JupyterHub (Notebooks)**: [bundles/20-jupyterhub/README.md](../bundles/20-jupyterhub/README.md)

### By Task

#### For Users
- [Login for the first time](USER_GUIDE.md#first-time-login)
- [Enroll in a course](USER_GUIDE.md#course-enrollment)
- [Choose a compute profile](USER_GUIDE.md#understanding-compute-profiles)
- [Understand storage](USER_GUIDE.md#your-storage-layout)
- [Install Python packages](USER_GUIDE.md#frequently-asked-questions)

#### For Admins
- [Add a new course](ADMIN_GUIDE.md#creating-a-new-course)
- [Manage user access](ADMIN_GUIDE.md#user-management)
- [Add compute profiles](ADMIN_GUIDE.md#adding-a-new-compute-profile)
- [Rotate secrets](ADMIN_GUIDE.md#rotating-secrets)
- [Monitor platform health](ADMIN_GUIDE.md#health-checks)

#### For Developers
- [Set up development environment](DEVELOPER_GUIDE.md#development-environment-setup)
- [Add a compute profile](DEVELOPER_GUIDE.md#adding-a-new-compute-profile)
- [Customize JupyterHub image](DEVELOPER_GUIDE.md#changing-the-jupyterhub-image)
- [Deploy changes](DEVELOPER_GUIDE.md#gitops-workflow)

#### For Infrastructure
- [Deploy new cluster](INFRASTRUCTURE.md#initial-deployment)
- [Configure networking](INFRASTRUCTURE.md#networking)
- [Set up storage](INFRASTRUCTURE.md#storage)
- [Configure backups](INFRASTRUCTURE.md#backup-and-disaster-recovery)
- [Monitor cluster](INFRASTRUCTURE.md#monitoring-and-observability)

### By Problem

- [Can't login](TROUBLESHOOTING.md#users-cannot-login)
- [Server won't start](TROUBLESHOOTING.md#server-wont-start--stuck-on-spawn)
- [Files missing](TROUBLESHOOTING.md#cant-access-files)
- [Slow performance](TROUBLESHOOTING.md#performance-issues)
- [Network issues](TROUBLESHOOTING.md#network-issues)
- [Secret problems](TROUBLESHOOTING.md#secret-and-configuration-issues)

---

## 📊 Documentation Overview

| Document | Lines | Size | Audience |
|----------|-------|------|----------|
| [User Guide](USER_GUIDE.md) | ~550 | 14 KB | Students, end users |
| [Admin Guide](ADMIN_GUIDE.md) | ~900 | 24 KB | Administrators, instructors |
| [Developer Guide](DEVELOPER_GUIDE.md) | ~1,000 | 30 KB | Developers, contributors |
| [Infrastructure Guide](INFRASTRUCTURE.md) | ~1,000 | 30 KB | Infrastructure team, DevOps |
| [Troubleshooting Guide](TROUBLESHOOTING.md) | ~700 | 18 KB | All roles |
| [Security Guide](SECURITY.md) | ~800 | 21 KB | Security team, admins |
| [SOPS Bootstrap](BOOTSTRAP-SOPS.md) | ~100 | 3 KB | Initial deployment |
| **Total** | **~5,100** | **~140 KB** | |

---

## 🔍 Search Tips

**Looking for specific topics?**

Use your browser's search function (Ctrl+F / Cmd+F) within each document:

- **Authentication**: Check User Guide, Admin Guide, Troubleshooting
- **Storage**: Check User Guide, Admin Guide, Infrastructure Guide
- **Profiles**: Check User Guide, Admin Guide, Developer Guide
- **Courses**: Check Admin Guide
- **Deployment**: Check Infrastructure Guide
- **Security**: Check Security Guide
- **Errors**: Check Troubleshooting Guide

---

## 🆘 Getting Help

| Issue Type | Contact | Documentation |
|------------|---------|---------------|
| 🎓 **Course/Assignment** | Your instructor | [User Guide](USER_GUIDE.md) |
| 🔧 **Technical Issue** | [support@dshl.unileoben.ac.at](mailto:support@dshl.unileoben.ac.at) | [Troubleshooting](TROUBLESHOOTING.md) |
| 🚨 **Platform Outage** | [platform-admins@dshl.unileoben.ac.at](mailto:platform-admins@dshl.unileoben.ac.at) | [Admin Guide](ADMIN_GUIDE.md) |
| 🐛 **Bug Report** | [GitHub Issues](https://github.com/bjoernellens1/cit-teaching-platform/issues) | [Developer Guide](DEVELOPER_GUIDE.md) |
| 🔒 **Security Issue** | [security@dshl.unileoben.ac.at](mailto:security@dshl.unileoben.ac.at) | [Security Guide](SECURITY.md) |

---

## 📝 Documentation Guidelines

### For Contributors

When updating documentation:

1. **Be concise**: Clear and direct language
2. **Be specific**: Include exact commands and paths
3. **Be consistent**: Follow existing structure and style
4. **Be current**: Update version numbers and dates
5. **Cross-reference**: Link to related sections

### Documentation Structure

Each guide follows this structure:
- **Overview**: What this covers and who it's for
- **Table of Contents**: Easy navigation
- **Sections**: Logical grouping of topics
- **Examples**: Real-world code and commands
- **Cross-references**: Links to related docs

---

## 🔄 Recent Updates

**February 2026**:
- ✅ Created comprehensive role-based documentation
- ✅ Added User Guide for students and end users
- ✅ Added Admin Guide for platform management
- ✅ Added Developer Guide for customization
- ✅ Added Infrastructure Guide for deployment
- ✅ Added Troubleshooting Guide
- ✅ Added Security Guide
- ✅ Updated main README with navigation
- ✅ Updated bundle READMEs with references

---

## 📄 License

Internal use only - CIT Teaching Platform  
Maintained by CIT Platform Team

**Last Updated**: February 2026  
**Platform Version**: 1.0
