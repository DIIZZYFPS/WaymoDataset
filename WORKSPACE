workspace(name = "waymo_dataset_processor")

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

# --- 1. Rules Proto (v6.0.2 - Verified) ---
http_archive(
    name = "rules_proto",
    sha256 = "6fb6767d1bef535310547e03247f7518b03487740c11b6c6adb7952033fe1295",
    strip_prefix = "rules_proto-6.0.2",
    urls = [
        "https://github.com/bazelbuild/rules_proto/releases/download/6.0.2/rules_proto-6.0.2.tar.gz",
    ],
)
load("@rules_proto//proto:repositories.bzl", "rules_proto_dependencies")
rules_proto_dependencies()

load("@rules_proto//proto:setup.bzl", "rules_proto_setup")
rules_proto_setup()

load("@rules_proto//proto:toolchains.bzl", "rules_proto_toolchains")
rules_proto_toolchains()

# --- 2. Protobuf (v21.9 - Verified) ---
http_archive(
    name = "com_google_protobuf",
    sha256 = "0aa7df8289c957a4c54cbe694fbabe99b180e64ca0f8fdb5e2f76dcf56ff2422",
    strip_prefix = "protobuf-21.9",
    urls = ["https://github.com/protocolbuffers/protobuf/archive/v21.9.tar.gz"],
)
load("@com_google_protobuf//:protobuf_deps.bzl", "protobuf_deps")
protobuf_deps()

# --- 3. Google Cloud C++ (v2.20.0 - Upgraded for workspace0-5 support) ---
http_archive(
    name = "google_cloud_cpp",
    sha256 = "0f42208ca782249555aac06455b1669c17dfb31d6d8fa4baad29a90f295666bb",
    strip_prefix = "google-cloud-cpp-2.20.0",
    urls = ["https://github.com/googleapis/google-cloud-cpp/archive/v2.20.0.tar.gz"],
)

# Stage 0: Load initial deps macro
load("@google_cloud_cpp//bazel:google_cloud_cpp_deps.bzl", "google_cloud_cpp_deps")
google_cloud_cpp_deps()

# Stages 0-5: Resolve recursive transitive dependencies (gRPC, Abseil, OpenTelemetry, etc.)
load("@google_cloud_cpp//bazel:workspace0.bzl", "gl_cpp_workspace0")
gl_cpp_workspace0()
load("@google_cloud_cpp//bazel:workspace1.bzl", "gl_cpp_workspace1")
gl_cpp_workspace1()
load("@google_cloud_cpp//bazel:workspace2.bzl", "gl_cpp_workspace2")
gl_cpp_workspace2()
load("@google_cloud_cpp//bazel:workspace3.bzl", "gl_cpp_workspace3")
gl_cpp_workspace3()
load("@google_cloud_cpp//bazel:workspace4.bzl", "gl_cpp_workspace4")
gl_cpp_workspace4()
load("@google_cloud_cpp//bazel:workspace5.bzl", "gl_cpp_workspace5")
gl_cpp_workspace5()
