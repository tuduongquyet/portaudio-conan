from conan import ConanFile, tools
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, rmdir
from conan.tools.system.package_manager import Apt, Yum
import os

class PortaudioConan(ConanFile):
    name = "portaudio"
    topics = ("portaudio", "audio", "recording", "playing")
    description = "PortAudio is a free, cross-platform, open-source, audio I/O library"
    url = "https://github.com/bincrafters/community"
    homepage = "http://www.portaudio.com"
    license = "MIT"    
    
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_alsa": [True, False],
        "with_jack": [True, False]
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_alsa": False,
        "with_jack": False
    }

    exports = ["CMakeLists.txt"]

    def validate(self):
        if self.settings.compiler == "apple-clang" and tools.Version(self.settings.compiler.version) < "11":
            raise ConanInvalidConfiguration("This recipe does not support Apple-Clang versions < 11")

    def configure(self):
        del self.settings.compiler.cppstd
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")
        if self.settings.os != "Linux":
            self.options.rm_safe("with_alsa")
            self.options.rm_safe("with_jack")

    def requirements(self):
        if self.settings.os == "Linux":
            if self.options.with_alsa:
                self.requires("libalsa/1.1.9")

    def system_requirements(self):
        if self.settings.os == "Linux":
                Apt(self).install(["libasound2-dev"]) 
                if self.options.with_jack:
                    Apt(self).install(["libjack-dev"])
                Yum(self).install(["alsa-lib-devel"])
                if self.settings.arch == "x86" and tools.detected_architecture() == "x86_64":
                    Yum(self).install(["glibmm24.i686"])
                    Yum(self).install(["glibc-devel.i686"])
                if self.options.with_jack:
                    Yum(self).install(["jack-audio-connection-kit-devel"])

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["PA_BUILD_STATIC"] = not self.options.shared
        tc.variables["PA_BUILD_SHARED"] = self.options.shared
        tc.variables["PA_USE_JACK"] = self.options.get_safe("with_jack", False)
        if self.options.get_safe("with_alsa", False): # with_alsa=False just makes portaudio use the Linux distro's alsa
            # as a workaround to the fact that conancenter's alsa does not work,
            # at least some of the time (no devices detected by portaudio)
            self.variables["PA_USE_ALSA"] = True
        tc.generate()

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, pattern="LICENSE*", dst="licenses", src=self.source_folder)
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "share"))
        # rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        # rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        # TODO: Add components with > 19.7, because the next release will most likely have major changes for their CMake setup

        if self.settings.os == "Macos":
            self.cpp_info.frameworks.extend(["CoreAudio", "AudioToolbox", "AudioUnit", "CoreServices", "Carbon"])

        if self.settings.os == "Windows" and self.settings.compiler == "gcc" and not self.options.shared:
            self.cpp_info.system_libs.extend(["winmm", "setupapi"])

        if self.settings.os == "Linux" and not self.options.shared:
            self.cpp_info.system_libs.extend(["m", "pthread", "asound"])
            if self.options.with_jack:
                self.cpp_info.system_libs.append("jack")

        if self.settings.os == "Windows":
            if self.options.shared:
                self.cpp_info.libs = ["portaudio_x64"]
            else:
                self.cpp_info.libs = ["portaudio_static_x64"]
        else:
            self.cpp_info.libs = ["portaudio"]
