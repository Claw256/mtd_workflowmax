"""Setup configuration for MTD's WorkflowMax 2 API client package."""

from setuptools import setup, find_packages

# Read version from package __init__.py
with open('src/mtd_workflowmax/__init__.py', 'r') as f:
    for line in f:
        if line.startswith('__version__'):
            version = line.split('=')[1].strip().strip("'").strip('"')
            break

# Read README for long description
with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='mtd-workflowmax',
    version=version,
    description='MTD\'s WorkflowMax 2 API client for fetching LinkedIn profiles',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='MTD',
    author_email='info@mtd.com',
    url='https://github.com/mtd/mtd-workflowmax',
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    python_requires='>=3.11',
    install_requires=[
        'requests>=2.31.0',
        'python-jwt>=4.0.0',
        'python-dotenv>=1.0.0',
        'PyYAML>=6.0.1',
        'tqdm>=4.65.0',
        'urllib3>=2.0.4',
    ],
    extras_require={
        'dev': [
            'mypy>=1.5.1',
            'types-requests>=2.31.0.2',
            'types-PyYAML>=6.0.12.11',
        ],
    },
    entry_points={
        'console_scripts': [
            'mtd-workflowmax-linkedin=mtd_workflowmax.cli:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.11',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
