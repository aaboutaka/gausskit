from setuptools import setup, find_packages

setup(
    name='gausspimom',
    version='0.1.0',
    author='Ali Abou Taka',
    description='Gaussian PIMOM input generator',
    packages=find_packages(),
    install_requires=['prompt_toolkit'],
    entry_points={
        'console_scripts': [
            'gaussjob=gausspimom.cli:main',
        ],
    },
    python_requires='>=3.7',
)


