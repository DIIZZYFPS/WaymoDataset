package(default_visibility = ["//visibility:public"])

load("@rules_proto//proto:defs.bzl", "proto_library")

# --- Waymo Protobuf definitions (Self-Contained) ---
proto_library(
    name = "waymo_e2e_proto",
    srcs = [
        "waymo_open_dataset/protos/end_to_end_driving_data.proto",
    ],
)

cc_proto_library(
    name = "waymo_e2e_cc_proto",
    deps = [":waymo_e2e_proto"],
)

# --- C++ Core Engine ---
cc_binary(
    name = "waymo_processor",
    srcs = ["waymo_processor.cc"],
    deps = [
        ":waymo_e2e_cc_proto",
        "@com_google_protobuf//:protobuf",
        "@google_cloud_cpp//:storage",
    ],
    copts = [
        "-std=c++17",
        "-I/usr/local/include",       # redis++ headers (source-compiled)
        "-I/usr/include/opencv4",     # OpenCV4 headers (Ubuntu 22.04 path)
    ],
    linkopts = [
        "-L/usr/local/lib",           # redis++ libs (source-compiled)
        "-lredis++",
        "-lhiredis",
        "-lopencv_core",
        "-lopencv_imgcodecs",
        "-lopencv_stitching",
        "-lopencv_imgproc",
    ],
)
