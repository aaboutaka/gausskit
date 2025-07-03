from setuptools import setup, find_packages

setup(
    name='gausskit',
    version='0.1.0',
    author='Ali Abou Taka',
    description='Toolkit for generating and modifying Gaussian input files',
    packages=find_packages(),
    install_requires=['prompt_toolkit'],
    entry_points={
        'console_scripts': [
            'gausskit=gausskit.cli:main',
        ],
    },
    python_requires='>=3.7',
)



