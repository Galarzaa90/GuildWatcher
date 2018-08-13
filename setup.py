import sys

from setuptools import setup

if sys.version_info < (3, 5):
    sys.exit('Sorry, Python < 3.5 is not supported')

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

with open('README.md') as f:
    readme = f.read()

setup(
    name='guildwatcher',
    version='0.1.1',
    author='Allan Galarza',
    author_email="allan.galarza@gmail.com",
    description='A discord webhook to track Tibia guild changes.',
    long_description=readme,
    long_description_content_type="text/markdown",
    url='https://github.com/Galarzaa90/GuildWatcher',
    py_modules=['guildwatcher'],
    install_requires=requirements,
    entry_points='''
        [console_scripts]
        guildwatcher=guildwatcher:scan_guilds
    ''',
    include_package_data=True,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Communications :: Chat',
        'Topic :: Games/Entertainment',
        'Topic :: Games/Entertainment :: Role-Playing'
    ]
)