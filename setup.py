
from distutils.core import setup

setup(
    name="CmsToolsAC3b",
    version="0.1dev",
    author="Heiner Tholen",
    author_email="heiner.tholen@cern.ch",
    packages=["cmstoolsac3b", "cmstoolsac3b_example"],
    license="LICENSE.txt",
    description="Tools to assist and manage an analysis with the CMS experiment.",
    long_description=open('README.rst').read()
)
