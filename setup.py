import setuptools
import re


def read_description(path='README.md'):
    with open(path) as f:
        return f.read()


def scrape_version(path='coregent/version.py'):
    with open(path) as f:
        text = f.read()

    m = re.search(r'''__version__ = ['"](.*?)['"]''', text)
    if m:
        print(m, m.groups())
        return m.group(1)


setuptools.setup(
    name='coregent',
    version=scrape_version(),
    author='Daniel Foerster',
    author_email='pydsigner@gmail.com',
    description='Co-regent: a toolkit for building Python games, especially with Kivy',
    long_description=read_description(),
    long_description_content_type='text/markdown',
    license_files=['LICENSE'],
    url='https://github.com/neurite-interactive/coregent',
    packages=['coregent'],
    classifiers=[
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: Apache Software License',
    ],
    python_requires='>=3.7',
)
