# CMake macOS compiler configuration module

include_guard(GLOBAL)

option(ENABLE_COMPILER_TRACE "Enable clang time-trace" OFF)
mark_as_advanced(ENABLE_COMPILER_TRACE)

# IDE 인덱싱용 탈출구. 기본 OFF = 기존처럼 Xcode generator 강제.
# CLion/IntelliJ 인덱싱을 위해 Ninja 등 비-Xcode generator로 configure할 때만
# `-DALLOW_NON_XCODE_GENERATOR=ON` 으로 이 가드를 해제한다.
# 실제 서명 .plugin 빌드/릴리스는 반드시 Xcode generator로 해야 한다
# (번들 Info.plist·codesign·hardened runtime이 CMAKE_XCODE_ATTRIBUTE_* 로만 적용되므로).
option(ALLOW_NON_XCODE_GENERATOR "Allow non-Xcode generators for IDE indexing only" OFF)
if(NOT XCODE AND NOT ALLOW_NON_XCODE_GENERATOR)
  message(FATAL_ERROR "Building OBS Studio on macOS requires Xcode generator.")
endif()

include(ccache)
include(compiler_common)

add_compile_options("$<$<NOT:$<COMPILE_LANGUAGE:Swift>>:-fopenmp-simd>")

# Ensure recent enough Xcode and platform SDK
function(check_sdk_requirements)
  set(obs_macos_minimum_sdk 15.0) # Keep in sync with Xcode
  set(obs_macos_minimum_xcode 16.0) # Keep in sync with SDK
  execute_process(
    COMMAND xcrun --sdk macosx --show-sdk-platform-version
    OUTPUT_VARIABLE obs_macos_current_sdk
    RESULT_VARIABLE result
    OUTPUT_STRIP_TRAILING_WHITESPACE
  )
  if(NOT result EQUAL 0)
    message(
      FATAL_ERROR
      "Failed to fetch macOS SDK version. "
      "Ensure that the macOS SDK is installed and that xcode-select points at the Xcode developer directory."
    )
  endif()
  message(DEBUG "macOS SDK version: ${obs_macos_current_sdk}")
  if(obs_macos_current_sdk VERSION_LESS obs_macos_minimum_sdk)
    message(
      FATAL_ERROR
      "Your macOS SDK version (${obs_macos_current_sdk}) is too low. "
      "The macOS ${obs_macos_minimum_sdk} SDK (Xcode ${obs_macos_minimum_xcode}) is required to build OBS."
    )
  endif()
  execute_process(COMMAND xcrun --find xcodebuild OUTPUT_VARIABLE obs_macos_xcodebuild RESULT_VARIABLE result)
  if(NOT result EQUAL 0)
    message(
      FATAL_ERROR
      "Xcode was not found. "
      "Ensure you have installed Xcode and that xcode-select points at the Xcode developer directory."
    )
  endif()
  message(DEBUG "Path to xcodebuild binary: ${obs_macos_xcodebuild}")
  # XCODE_VERSION 은 Xcode generator일 때만 채워진다. 비-Xcode generator(IDE 인덱싱용 Ninja 등)에선
  # 비어 있어 "" < 16.0 으로 오인되므로, 값이 있을 때만 버전을 검사한다.
  if(XCODE_VERSION AND XCODE_VERSION VERSION_LESS obs_macos_minimum_xcode)
    message(
      FATAL_ERROR
      "Your Xcode version (${XCODE_VERSION}) is too low. Xcode ${obs_macos_minimum_xcode} is required to build OBS."
    )
  endif()
endfunction()

check_sdk_requirements()

# Enable dSYM generator for release builds
string(APPEND CMAKE_C_FLAGS_RELEASE " -g")
string(APPEND CMAKE_CXX_FLAGS_RELEASE " -g")
string(APPEND CMAKE_OBJC_FLAGS_RELEASE " -g")
string(APPEND CMAKE_OBJCXX_FLAGS_RELEASE " -g")

# Default ObjC compiler options used by Xcode:
#
# * -Wno-implicit-atomic-properties
# * -Wno-objc-interface-ivars
# * -Warc-repeated-use-of-weak
# * -Wno-arc-maybe-repeated-use-of-weak
# * -Wimplicit-retain-self
# * -Wduplicate-method-match
# * -Wshadow
# * -Wfloat-conversion
# * -Wobjc-literal-conversion
# * -Wno-selector
# * -Wno-strict-selector-match
# * -Wundeclared-selector
# * -Wdeprecated-implementations
# * -Wprotocol
# * -Werror=block-capture-autoreleasing
# * -Wrange-loop-analysis

# Default ObjC++ compiler options used by Xcode:
#
# * -Wno-non-virtual-dtor

add_compile_definitions(
  $<$<NOT:$<COMPILE_LANGUAGE:Swift>>:$<$<CONFIG:DEBUG>:DEBUG>>
  $<$<NOT:$<COMPILE_LANGUAGE:Swift>>:$<$<CONFIG:DEBUG>:_DEBUG>>
  $<$<NOT:$<COMPILE_LANGUAGE:Swift>>:SIMDE_ENABLE_OPENMP>
)

if(ENABLE_COMPILER_TRACE)
  add_compile_options(
    $<$<NOT:$<COMPILE_LANGUAGE:Swift>>:-ftime-trace>
    "$<$<COMPILE_LANGUAGE:Swift>:SHELL:-Xfrontend -debug-time-expression-type-checking>"
    "$<$<COMPILE_LANGUAGE:Swift>:SHELL:-Xfrontend -debug-time-function-bodies>"
  )
  add_link_options(LINKER:-print_statistics)
endif()
