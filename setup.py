from setuptools import find_packages, setup

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

setup(
	name="advanced_compliance",
	version="1.1.5",
	description="Next-generation GRC with Knowledge Graph and AI Intelligence",
	author="Noreli North",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires,
)
