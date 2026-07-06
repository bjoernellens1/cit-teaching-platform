# CIT Teaching Platform - User Guide

Welcome to the CIT Teaching Platform! This guide will help you get started with JupyterHub for your courses.

## Table of Contents

- [Getting Started](#getting-started)
- [First-Time Login](#first-time-login)
- [Course Enrollment](#course-enrollment)
- [Using JupyterHub](#using-jupyterhub)
- [Understanding Compute Profiles](#understanding-compute-profiles)
- [Your Storage Layout](#your-storage-layout)
- [Best Practices](#best-practices)
- [Frequently Asked Questions](#frequently-asked-questions)
- [Getting Help](#getting-help)

---

## Getting Started

The CIT Teaching Platform provides you with access to powerful computing resources through your web browser. No installation required!

### What You Can Do

- Run Python, R, Julia, and other programming languages
- Access GPUs for machine learning workloads
- Collaborate with classmates through shared course folders
- Save your work permanently in your personal storage

### Prerequisites

- University credentials (for SSO login)
- Modern web browser (Chrome, Firefox, Safari, or Edge)
- Course enrollment password (provided by your instructor)

---

## First-Time Login

### Step 1: Navigate to JupyterHub

Visit: **[https://jhub.dshl.unileoben.ac.at](https://jhub.dshl.unileoben.ac.at)**

### Step 2: University SSO Login

1. Click **"Login"** button
2. You'll be redirected to the University authentication system
3. Click **"Login with University SSO"**
4. Enter your university username and password
5. Complete any two-factor authentication if prompted

### Step 3: Course Enrollment (First Time Only)

If this is your first time accessing the platform, you'll be prompted to enroll in a course:

1. **Select Your Course**: Choose from the dropdown menu
2. **Enter Course Password**: Your instructor will provide this password
3. **Confirm**: Click the enrollment button

After enrollment, you'll be automatically redirected back to JupyterHub.

### Step 4: Select a Compute Profile

Depending on your course and user group, you may see different compute profiles:

- **CPU Small**: Standard profile for most coursework
- **GPU Small**: For GPU-accelerated computations (if available to your course)

Select the profile that matches your current needs and click **Start**.

### Step 5: Wait for Server Startup

Your personal server is being created. This typically takes 30-60 seconds on first launch.

---

## Course Enrollment

### Enrolling in Additional Courses

To enroll in another course:

1. Visit: **[https://auth.dshl.unileoben.ac.at](https://auth.dshl.unileoben.ac.at)**
2. Login with your University SSO
3. Navigate to your account settings
4. Follow the enrollment flow
5. Enter the course password provided by your instructor

### Viewing Your Enrollments

To see which courses you're enrolled in:

1. Visit the Authentik portal: **[https://auth.dshl.unileoben.ac.at](https://auth.dshl.unileoben.ac.at)**
2. Login and navigate to your profile
3. View your group memberships under "Groups"
   - Course groups are named: `course-<course-name>`

---

## Using JupyterHub

### The JupyterHub Interface

Once your server starts, you'll see the JupyterLab interface with:

- **File Browser** (left sidebar): Navigate your files and folders
- **Launcher**: Create new notebooks, terminals, and files
- **Menu Bar**: File operations, edit, view, and settings
- **Main Work Area**: Where you'll write code and view outputs

### Creating Your First Notebook

1. Click the **Python 3** icon in the Launcher
   - Or: **File → New → Notebook**
2. Write your code in cells
3. Press **Shift+Enter** to execute a cell
4. Press **B** to create a new cell below
5. Save your work: **File → Save Notebook** (or Ctrl+S)

### Opening a Terminal

Need command-line access?

1. Click **File → New → Terminal**
2. You have full bash shell access within your server

### Stopping Your Server

When you're done working:

1. Click **File → Hub Control Panel**
2. Click **Stop My Server**
3. Your work is automatically saved and will be available next time

> **Important**: Servers auto-stop after 1 hour of inactivity or 8 hours of runtime to conserve resources.

---

## Understanding Compute Profiles

Different profiles provide different resources. Choose based on your workload:

### CPU Small (Default)

**Best for**: Standard coursework, data analysis, small datasets

- **CPU**: 2 cores
- **RAM**: 6 GB
- **Storage**: 10 GB (your personal work directory)
- **GPU**: None
- **Availability**: All students

**Use Cases**:
- Python programming exercises
- Data manipulation with pandas
- Basic plotting and visualization
- Course assignments

### GPU Small

**Best for**: Machine learning training, GPU-accelerated computations

- **CPU**: 16 cores
- **RAM**: 48 GB
- **Storage**: 10 GB (your personal work directory)
- **GPU**: 10 GB VRAM (shared A100, via NVIDIA MPS)
- **Availability**: Course-dependent (ask your instructor)

**Use Cases**:
- Deep learning with PyTorch, TensorFlow
- Computer vision model training
- Neural network experimentation
- GPU-accelerated data processing

### Requesting Access to Higher Profiles

If you need more resources for a specific project:

1. Contact your course instructor
2. Explain your use case and resource requirements
3. Instructors can request profile upgrades from platform admins

---

## Your Storage Layout

Understanding where to save your files is important!

```
/home/jovyan/                 # Your home directory
├── work/                     # 💾 PERSISTENT - Your main workspace
├── temp/                     # ⚡ TEMPORARY - Fast but cleared on restart!
├── shared/                   # 💾 PERSISTENT - Shared (admins only)
└── courses/
    └── <course-name>/        # 💾 PERSISTENT - Your per-course work

/srv/courses/                 # Course-shared directories
└── <course-name>/            # 💾 PERSISTENT - Shared with all course members
    ├── lectures/             # Course materials (read-only for students)
    ├── assignments/          # Assignment templates
    └── datasets/             # Shared datasets
```

### Storage Types Explained

| Directory | Persistent? | Shared? | Purpose |
|-----------|-------------|---------|---------|
| `/home/jovyan/work` | ✅ Yes | ❌ Private | **Your main workspace** - All your personal projects |
| `/home/jovyan/temp` | ❌ No | ❌ Private | **Scratch space** - Fast SSD but cleared on restart |
| `/home/jovyan/courses/<name>` | ✅ Yes | ❌ Private | **Course-specific work** - Organized by course |
| `/srv/courses/<name>` | ✅ Yes | ✅ Shared | **Course materials** - Shared with all enrolled students |

### Best Practices for File Organization

**✅ DO:**
- Save important work in `/home/jovyan/work`
- Organize by project or assignment
- Use `/home/jovyan/temp` for large temporary files
- Access course materials from `/srv/courses/<course-name>`

**❌ DON'T:**
- Don't save important work in `/home/jovyan/temp` (it will be deleted!)
- Don't modify files in `/srv/courses/<course-name>` (read-only for students)
- Don't store sensitive credentials in your files

---

## Best Practices

### Resource Management

**Be a Good Citizen**:
- Stop your server when you're done working
- Use the smallest profile that meets your needs
- Don't leave servers running overnight unnecessarily
- Clean up large files in `/home/jovyan/temp`

### Code Organization

**Keep Your Work Organized**:
```
/home/jovyan/work/
├── course-aml/
│   ├── assignment1/
│   ├── assignment2/
│   └── final-project/
├── course-robotics/
│   └── lab-exercises/
└── personal-projects/
    └── my-research/
```

### Saving Your Work

**Protect Your Work**:
1. **Save frequently**: Use Ctrl+S or File → Save
2. **Backup important files**: Download to your local computer periodically
3. **Use version control**: Consider Git for larger projects
4. **Check file paths**: Ensure you're saving to `/home/jovyan/work`

### Working with Large Datasets

**For Large Files**:
1. Download once to `/home/jovyan/work`
2. Process in `/home/jovyan/temp` for speed
3. Save results back to `/home/jovyan/work`

**Example**:
```python
import shutil

# Copy large dataset to fast temporary storage
shutil.copy('/home/jovyan/work/large_data.csv', '/home/jovyan/temp/')

# Process in temp (fast!)
df = pd.read_csv('/home/jovyan/temp/large_data.csv')
# ... do processing ...

# Save results to persistent storage
results.to_csv('/home/jovyan/work/results.csv')
```

### Using GPUs Effectively

**GPU Best Practices**:
1. Only request GPU profiles when you actually need GPU acceleration
2. Test your code on CPU Small first if possible
3. Stop your server when training is complete
4. Monitor GPU usage: `nvidia-smi` in a terminal

---

## Frequently Asked Questions

### Login & Access

**Q: I forgot my course password. What should I do?**  
A: Contact your course instructor to get the enrollment password again.

**Q: I can't login with my university credentials. What's wrong?**  
A: Ensure you're using your full university username (not email). If problems persist, contact university IT support.

**Q: Why am I being asked to enroll in a course every time I login?**  
A: This shouldn't happen after your first enrollment. Contact platform support if this persists.

### Server & Resources

**Q: My server won't start. What should I do?**  
A: 
1. Wait 2-3 minutes (startup can take time)
2. If it still fails, try stopping and restarting
3. Try a different profile (CPU Small is most reliable)
4. Contact support if the issue persists

**Q: My server is slow. Can I get more resources?**  
A: Contact your instructor to request access to larger profiles. Explain your use case.

**Q: How long can my server run?**  
A: Servers auto-stop after:
- 1 hour of inactivity (no active connections)
- 8 hours of total runtime (even if active)

**Q: Will my work be saved if my server is stopped?**  
A: Yes! Everything in `/home/jovyan/work` is automatically saved. Only `/home/jovyan/temp` is cleared.

### Files & Storage

**Q: Where should I save my files?**  
A: Always save important work in `/home/jovyan/work`. This directory is persistent across server restarts.

**Q: I can't find files I saved earlier. Where are they?**  
A: Check if you saved them in `/home/jovyan/temp` - this directory is cleared on server restart. For the future, use `/home/jovyan/work`.

**Q: How much storage do I have?**  
A: Your persistent home directory has 10 GB. If you need more, contact your instructor.

**Q: Can I share files with classmates?**  
A: Yes! Use the course shared folder at `/srv/courses/<course-name>`. Instructors can place files there for everyone to access.

### Software & Packages

**Q: How do I install Python packages?**  
A: Use `pip install` in a terminal or notebook cell:
```python
!pip install package-name
```

**Q: Will my installed packages persist?**  
A: Yes! Packages installed with `pip install --user` will persist. However, system-level installations may not.

**Q: Can I request pre-installed packages?**  
A: Yes! Contact your instructor or platform admins to request commonly-used packages be added to the default environment.

**Q: Which Python version is available?**  
A: Check by running `python --version` in a terminal. The platform typically runs Python 3.10+.

### Troubleshooting

**Q: My notebook kernel keeps dying. What's wrong?**  
A: This usually means you've run out of memory (RAM). Try:
1. Restart your kernel and run cells one at a time
2. Use a profile with more RAM
3. Optimize your code to use less memory

**Q: I can't access the GPU. How do I check if it's available?**  
A: Run this in a notebook:
```python
import torch
print(torch.cuda.is_available())
print(torch.cuda.get_device_name(0))
```
If False, you may need to select a GPU profile.

**Q: I'm getting "Permission Denied" errors. Why?**  
A: You may be trying to:
- Write to a read-only directory (like course materials)
- Access files outside your home directory
- Modify system files

Stick to `/home/jovyan/work` for your files.

---

## Getting Help

### Course-Specific Questions

Contact your **course instructor** for:
- Course enrollment passwords
- Assignment questions
- Course material access
- Profile/resource requests for coursework

### Technical Issues

Contact **platform support** for:
- Login problems (after verifying university credentials work)
- Server startup failures
- Persistent technical issues
- Feature requests

**Support Email**: [support@dshl.unileoben.ac.at](mailto:support@dshl.unileoben.ac.at)

### Emergency Access Issues

If you cannot access the platform during an exam or critical deadline:

1. **Immediately** contact your instructor
2. Document the error message (screenshot if possible)
3. Note the time and what you were trying to do

---

## Additional Resources

### Learning JupyterLab

- **Official JupyterLab Docs**: [https://jupyterlab.readthedocs.io](https://jupyterlab.readthedocs.io)
- **JupyterLab Tutorial**: [https://jupyter.org/try](https://jupyter.org/try)

### Python Resources

- **Python Official Tutorial**: [https://docs.python.org/3/tutorial/](https://docs.python.org/3/tutorial/)
- **NumPy Tutorial**: [https://numpy.org/doc/stable/user/quickstart.html](https://numpy.org/doc/stable/user/quickstart.html)
- **Pandas Guide**: [https://pandas.pydata.org/docs/user_guide/index.html](https://pandas.pydata.org/docs/user_guide/index.html)

### Machine Learning (for GPU users)

- **PyTorch Tutorials**: [https://pytorch.org/tutorials/](https://pytorch.org/tutorials/)
- **TensorFlow Guides**: [https://www.tensorflow.org/guide](https://www.tensorflow.org/guide)

---

**Last Updated**: February 2026  
**Platform Version**: 1.0  
**Questions?** Contact [support@dshl.unileoben.ac.at](mailto:support@dshl.unileoben.ac.at)
