#!/usr/bin/env python
"""
Package metadata for comm_coordinator.
"""
import os
import re
import sys

from setuptools import setup


def get_version(*file_paths):
    """
    Extract the version string from the file.

    Input:
     - file_paths: relative path fragments to file with
                   version string
    """
    filename = os.path.join(os.path.dirname(__file__), *file_paths)
    version_file = open(filename, encoding="utf8").read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError('Unable to find version string.')


def load_requirements(*requirements_paths):
    """
    Load all requirements from the specified requirements files.

    Requirements will include any constraints from files specified
    with -c in the requirements files.
    Returns a list of requirement strings.
    """
    # UPDATED VIA SEMGREP - if you need to remove/modify this method remove this line and add a comment specifying why.

    requirements = {}
    constraint_files = set()

    # groups "my-package-name<=x.y.z,..." into ("my-package-name", "<=x.y.z,...")
    requirement_line_regex = re.compile(r"([a-zA-Z0-9-_.]+)([<>=][^#\s]+)?")

    def add_version_constraint_or_raise(current_line, current_requirements, add_if_not_present):
        regex_match = requirement_line_regex.match(current_line)
        if regex_match:
            package = regex_match.group(1)
            version_constraints = regex_match.group(2)
            existing_version_constraints = current_requirements.get(package, None)
            # it's fine to add constraints to an unconstrained package, but raise an error if there are already
            # constraints in place
            if existing_version_constraints and existing_version_constraints != version_constraints:
                raise BaseException(f'Multiple constraint definitions found for {package}:'
                                    f' "{existing_version_constraints}" and "{version_constraints}".'
                                    f'Combine constraints into one location with {package}'
                                    f'{existing_version_constraints},{version_constraints}.')
            if add_if_not_present or package in current_requirements:
                current_requirements[package] = version_constraints

    # process .in files and store the path to any constraint files that are pulled in
    for path in requirements_paths:
        with open(path, encoding='utf-8') as reqs:
            for line in reqs:
                if is_requirement(line):
                    add_version_constraint_or_raise(line, requirements, True)
                if line and line.startswith('-c') and not line.startswith('-c http'):
                    constraint_files.add(os.path.dirname(path) + '/' + line.split('#')[0].replace('-c', '').strip())

    # process constraint files and add any new constraints found to existing requirements
    for constraint_file in constraint_files:
        with open(constraint_file, encoding='utf-8') as reader:
            for line in reader:
                if is_requirement(line):
                    add_version_constraint_or_raise(line, requirements, False)

    # process back into list of pkg><=constraints strings
    constrained_requirements = [f'{pkg}{version or ""}' for (pkg, version) in sorted(requirements.items())]
    return constrained_requirements


def is_requirement(line):
    """
    Return True if the requirement line is a package requirement.

    Returns:
        bool: True if the line is not blank, a comment,
        a URL, or an included file
    """
    # UPDATED VIA SEMGREP - if you need to remove/modify this method remove this line and add a comment specifying why

    return line and line.strip() and not line.startswith(('-r', '#', '-e', 'git+', '-c'))


VERSION = get_version('commerce_coordinator', '__init__.py')

if sys.argv[-1] == 'tag':
    print("Tagging the version on github:")
    os.system(f"git tag -a {VERSION} -m 'version {VERSION}'")
    os.system("git push --tags")
    sys.exit()

if sys.argv[-1] == 'ver_check':
    REQ_MAJOR = 3
    REQ_MINOR = 12
    if sys.version_info.major != REQ_MAJOR or (sys.version_info.major == REQ_MAJOR and
                                               sys.version_info.minor != REQ_MINOR):
        print(f"This application only works on Python {REQ_MAJOR}.{REQ_MINOR}. Please check your environment.")
        sys.exit(1)
    else:
        sys.exit(0)

README = open(os.path.join(os.path.dirname(__file__), 'README.rst'), encoding="utf8").read()
CHANGELOG = open(os.path.join(os.path.dirname(__file__), 'CHANGELOG.rst'), encoding="utf8").read()

setup(
    name='commerce-coordinator',
    version=VERSION,
    description="""A controller to manage commerce workflows and services""",
    long_description=README + '\n\n' + CHANGELOG,
    author='edX',
    author_email='oscm@edx.org',
    url='https://github.com/edx/commerce-coordinator',
    packages=[
        'commerce_coordinator',
    ],
    include_package_data=True,
    install_requires=load_requirements('requirements/base.in'),
    python_requires=">=3.12",
    license="AGPL 3.0",
    zip_safe=False,
    keywords='Python edx',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Framework :: Django',
        'Framework :: Django :: 4.2',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.12',
    ],
)
