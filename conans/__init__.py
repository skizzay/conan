# Allow conans to import ConanFile from here
# to allow refactors
from conans.model.conan_file import ConanFile
from conans.model.options import Options
from conans.model.settings import Settings
from conans.client.build.cmake import CMake
from conans.client.build.meson import Meson
from conans.client.build.gcc import GCC
from conans.client.build.configure_environment import ConfigureEnvironment
from conans.client.build.autotools_environment import AutoToolsBuildEnvironment
from conans.client.build.visual_environment import VisualStudioBuildEnvironment
from conans.client.run_environment import RunEnvironment
from conans.util.files import load

# complex_search: With ORs and not filtering by not restricted settings
COMPLEX_SEARCH_CAPABILITY = "complex_search"
SERVER_CAPABILITIES = [COMPLEX_SEARCH_CAPABILITY, ]


__version__ = '0.29.0-dev'
