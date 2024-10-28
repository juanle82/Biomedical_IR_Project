import sys, os
from inspect import isclass
from pkgutil import iter_modules
from importlib import import_module
from Miscellaneous.PluginBase import PluginBase


# Check if the application has been frozen to executable file
if getattr(sys, "frozen", False):
    package_dir = os.path.dirname(sys.executable)
    package_dir = os.path.join(package_dir, "Plugins")
    print(f"Frozen mode: {package_dir}")
else:
    package_dir = os.path.dirname(__file__)
    print(f"No frozen mode: {package_dir}")

# Iterate through the modules in the current package
for (importer, module_name, ispkg) in iter_modules([package_dir]):
    try:
        # import the module and iterate through its attributes
        module = importer.find_module(module_name).load_module(module_name)
        for attribute_name in dir(module):
            attribute = getattr(module, attribute_name)
            if isclass(attribute) and issubclass(attribute, PluginBase):
                # Add the class to this package's variables
                globals()[attribute_name] = attribute
    except Exception as e:
        print(e)
