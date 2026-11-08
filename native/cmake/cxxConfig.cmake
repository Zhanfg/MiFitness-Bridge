# Minimal standalone NDK libc++ interface expected by recent LSPlant source.
# This is not a replacement for libc++; compiler/toolchain provides runtime.
if(NOT TARGET cxx::cxx)
  add_library(cxx::cxx INTERFACE IMPORTED)
  if(NOT ANDROID_NDK)
    message(FATAL_ERROR "cxxConfig requires the Android NDK toolchain")
  endif()
  get_filename_component(_ndk_prebuilt "${ANDROID_NDK}/toolchains/llvm/prebuilt/linux-x86_64" ABSOLUTE)
  set_target_properties(cxx::cxx PROPERTIES
    INTERFACE_INCLUDE_DIRECTORIES "${_ndk_prebuilt}/sysroot/usr/include/c++/v1"
    INTERFACE_LINK_LIBRARIES "c++_static")
endif()
