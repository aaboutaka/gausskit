from setuptools import setup, find_packages

setup(
    name='gausskit',
    version='0.1.1',
    author='Ali Abou Taka',
    description='Toolkit for automating Gaussian input preparation, error fixing, and SLURM job submission',
    packages=find_packages(),
    install_requires=[
        'prompt_toolkit>=3.0.0',
        'pyyaml>=6.0'
    ],
    entry_points={
        'console_scripts': [
            'gausskit=gausskit.cli:main',
        ],
    },
    include_package_data=True,
    package_data={
        'gausskit': ['*.yaml'],  # includes gaussian_errors.yaml
    },
    python_requires='>=3.0',
)

