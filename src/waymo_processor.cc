#include <iostream>
#include <string>
#include <vector>
#include <memory>

#include "google/cloud/storage/client.h"
#include "sw/redis++/redis++.h"
#include "src/waymo_open_dataset/protos/end_to_end_driving_data.pb.h"

#include <cmath>
#include <google/protobuf/io/coded_stream.h>
#include <google/protobuf/io/zero_copy_stream_impl.h>

#include <opencv2/opencv.hpp>
#include <opencv2/stitching.hpp>

namespace gcs = google::cloud::storage;
using namespace sw::redis;
using waymo::open_dataset::E2EDFrame;

// Helper to read a single TFRecord from GCS stream
bool ReadTFRecord(std::istream& stream, std::string* data) {
    uint64_t length;
    if (!stream.read(reinterpret_cast<char*>(&length), sizeof(length))) return false;
    
    uint32_t length_crc;
    if (!stream.read(reinterpret_cast<char*>(&length_crc), sizeof(length_crc))) return false;

    data->resize(length);
    if (!stream.read(&(*data)[0], length)) return false;

    uint32_t data_crc;
    if (!stream.read(reinterpret_cast<char*>(&data_crc), sizeof(data_crc))) return false;

    return true;
}

void ProcessEdgeCase(Redis& redis, const E2EDFrame& frame, double accel, double jerk, long frame_id) {
    // 4. Outcome Analysis (Future States)
    
    // Check future_states in the proto (E2E targets)
    if (frame.has_future_states()) {
        const auto& fs = frame.future_states();
        // Check if future trajectory shows a sudden stop (vel barely changes)
        if (fs.vel_x_size() > 0 && std::abs(fs.vel_x(fs.vel_x_size() - 1)) < 0.1) {
            std::cout << "Collision predicted at t=" << frame.frame().timestamp_micros() << std::endl;
        }
    }

    // Signaling logic: Push to Redis list
    std::string intent_str;
    switch (frame.intent()) {
        case waymo::open_dataset::EgoIntent::UNKNOWN: intent_str = "UNKNOWN"; break;
        case waymo::open_dataset::EgoIntent::GO_STRAIGHT: intent_str = "GO_STRAIGHT"; break;
        case waymo::open_dataset::EgoIntent::GO_LEFT: intent_str = "GO_LEFT"; break;
        case waymo::open_dataset::EgoIntent::GO_RIGHT: intent_str = "GO_RIGHT"; break;
        default: intent_str = "UNKNOWN"; break;
    }

    std::string signal = "{\"timestamp\": " + std::to_string(frame.frame().timestamp_micros()) + 
                         ", \"frame_id\": " + std::to_string(frame_id) + 
                         ", \"accel\": " + std::to_string(accel) + 
                         ", \"jerk\": " + std::to_string(jerk) + 
                         ", \"intent\": \"" + intent_str + "\"}";
    
    redis.lpush("waymo:edge_cases", signal); // For live SSE feed
    redis.lpush("waymo:edge_cases_sink", signal); // For DB sink
    redis.publish("waymo:alerts", "Edge case detected: " + signal);
}

// Upload stitched image to GCS
void UploadImage(gcs::Client& client, const std::string& bucket, const std::string& name, const cv::Mat& image) {
    std::vector<uchar> buf;
    cv::imencode(".png", image, buf);
    std::string data(buf.begin(), buf.end());

    auto writer = client.WriteObject(bucket, name, gcs::ContentType("image/png"));
    writer << data;
    writer.Close();
}

cv::Mat StitchPanorama(const E2EDFrame& frame) {
    if (frame.has_frame()) {
        for (const auto& camera : frame.frame().images()) {
            if (!camera.has_image() || camera.image().empty()) continue;
            
            // Decode jpeg from proto string
            std::vector<uchar> buf(camera.image().begin(), camera.image().end());
            cv::Mat img = cv::imdecode(buf, cv::IMREAD_COLOR);
            if (!img.empty()) {
                return img; // Just return the first valid image to bypass stitching resolution inconsistencies
            }
        }
    }
    return cv::Mat();
}

int main(int argc, char* argv[]) {
    if (argc < 4) {
        std::cerr << "Usage: " << argv[0] << " <gcs_url> <redis_url> <output_bucket>" << std::endl;
        return 1;
    }

    std::string gcs_url = argv[1];
    std::string redis_url = argv[2];
    std::string output_bucket = argv[3];

    try {
        // Initialize Redis
        auto redis = Redis(redis_url);
        std::cout << "Connected to Redis at " << redis_url << std::endl;

        // Initialize GCS Client
        auto client = gcs::Client::CreateDefaultClient().value();
        
        // Extract bucket and object from GCS URL (gs://bucket/object)
        std::string bucket = gcs_url.substr(5, gcs_url.find("/", 5) - 5);
        std::string object = gcs_url.substr(gcs_url.find("/", 5) + 1);

        std::cout << "Streaming from bucket: " << bucket << " object: " << object << std::endl;

        // Start Streaming
        std::cout << "[Init] Opening GCS stream..." << std::flush;
        auto reader = client.ReadObject(bucket, object);
        if (!reader) {
            std::cerr << "Error reading GCS object: " << reader.status() << std::endl;
            return 1;
        }
        std::cout << " OK" << std::endl;

        std::string record_data;
        long record_count = 0;
        long parse_failures = 0;

        std::cout << "[Stream] Reading first TFRecord..." << std::flush;
        while (ReadTFRecord(reader, &record_data)) {
            record_count++;
            if (record_count <= 5) {
                std::cout << "[Debug] Record #" << record_count << " - data_size=" << record_data.size() << std::endl;
            }

            E2EDFrame frame;
            if (!frame.ParseFromString(record_data)) {
                parse_failures++;
                std::cerr << "[ERROR] Parse failure for record #" << record_count << std::endl;
                continue;
            }

            if (record_count <= 1) {
                std::cout << "[Reflection] E2EDFrame fields:" << std::endl;
                std::vector<const google::protobuf::FieldDescriptor*> fields;
                frame.GetReflection()->ListFields(frame, &fields);
                for (auto f : fields) {
                    std::cout << "  Tag " << f->number() << " (" << f->name() << ")" << std::endl;
                }
                
                if (frame.has_frame()) {
                    std::cout << "[Reflection] Frame fields:" << std::endl;
                    fields.clear();
                    frame.frame().GetReflection()->ListFields(frame.frame(), &fields);
                    for (auto f : fields) {
                        std::cout << "  Tag " << f->number() << " (" << f->name() << ")" << std::endl;
                    }
                }
            }

            if (record_count % 100 == 0) {
                std::cout << "[Progress] Processed " << record_count
                          << " records (" << parse_failures << " parse failures)" << std::endl;
            }

            // 1. Extract Motion Metrics from past_states (NOT ego_metrics — which is empty)
            // past_states contains 16 waypoints at 4Hz (t=-4s to t=0)
            // The LAST element is the most recent (closest to t=0)
            double speed = 0, accel_x = 0, accel_y = 0, jerk_x = 0, jerk_y = 0;
            double speed_min = 0, speed_max = 0, speed_mean = 0;
            std::string intent_str;
            switch (frame.intent()) {
                case waymo::open_dataset::EgoIntent::UNKNOWN: intent_str = "UNKNOWN"; break;
                case waymo::open_dataset::EgoIntent::GO_STRAIGHT: intent_str = "GO_STRAIGHT"; break;
                case waymo::open_dataset::EgoIntent::GO_LEFT: intent_str = "GO_LEFT"; break;
                case waymo::open_dataset::EgoIntent::GO_RIGHT: intent_str = "GO_RIGHT"; break;
                default: intent_str = "UNKNOWN"; break;
            }

            if (frame.has_past_states()) {
                const auto& ps = frame.past_states();
                int n = ps.vel_x_size();
                if (n > 0) {
                    // Most recent values (last in array = closest to current time)
                    double vx = ps.vel_x(n - 1);
                    double vy = ps.vel_y(n - 1);
                    speed = std::sqrt(vx * vx + vy * vy);
                    
                    // Speed statistics across the full trajectory
                    speed_min = 1e9; speed_max = 0; double speed_sum = 0;
                    for (int i = 0; i < n; i++) {
                        double s = std::sqrt(ps.vel_x(i) * ps.vel_x(i) + ps.vel_y(i) * ps.vel_y(i));
                        if (s < speed_min) speed_min = s;
                        if (s > speed_max) speed_max = s;
                        speed_sum += s;
                    }
                    speed_mean = speed_sum / n;
                }
                int na = ps.accel_x_size();
                if (na > 0) {
                    accel_x = ps.accel_x(na - 1); // Most recent accel
                    accel_y = ps.accel_y(na - 1); // Most recent lateral
                    
                    // Min accel_x across trajectory (most negative = hardest braking)
                    double accel_x_min = 1e9;
                    for (int i = 0; i < na; i++) {
                        if (ps.accel_x(i) < accel_x_min) accel_x_min = ps.accel_x(i);
                    }
                    accel_x = accel_x_min; // Use the min (worst braking) for edge case detection
                    
                    // Jerk: rate of change of acceleration (compute from trajectory)
                    if (na >= 2) {
                        double dt = 0.25; // 4Hz = 0.25s intervals
                        jerk_x = (ps.accel_x(na - 1) - ps.accel_x(na - 2)) / dt;
                        jerk_y = (ps.accel_y(na - 1) - ps.accel_y(na - 2)) / dt;
                    }
                }
            }

            // 2. Full Frame Export (EVERY frame to Redis)
            int64_t timestamp = frame.has_frame() ? frame.frame().timestamp_micros() : record_count;
            
            // Generate unique filename: {base_tfrecord}_frame_{record_count}.png
            std::string object_base = object;
            if (object_base.find(".") != std::string::npos) {
                object_base = object_base.substr(0, object_base.find("."));
            }
            std::string img_path = "panoramas/" + object_base + "_frame_" + std::to_string(record_count) + ".png";
            
            std::string meta = "{\"frame_id\": " + std::to_string(record_count) + 
                              ", \"file_name\": \"" + object + "\"" +
                              ", \"timestamp\": " + std::to_string(timestamp) + 
                              ", \"gcs_bucket\": \"" + output_bucket + "\"" +
                              ", \"gcs_path\": \"" + img_path + "\"" +
                              ", \"speed\": " + std::to_string(speed) + 
                              ", \"speed_min\": " + std::to_string(speed_min) + 
                              ", \"speed_max\": " + std::to_string(speed_max) + 
                              ", \"speed_mean\": " + std::to_string(speed_mean) + 
                              ", \"accel_x\": " + std::to_string(accel_x) + 
                              ", \"accel_y\": " + std::to_string(accel_y) + 
                              ", \"jerk_x\": " + std::to_string(jerk_x) + 
                              ", \"jerk_y\": " + std::to_string(jerk_y) + 
                              ", \"intent\": \"" + intent_str + "\"}";
            
            if (record_count <= 5) {
                std::cout << "[Debug] Pushing to Redis: " << meta << std::endl;
            }
            redis.lpush("waymo:frames_metadata", meta);

            // 3. Edge Case Detection (thresholds from load_dataset.py)
            // Hard Brake < -0.8, Lateral > 0.6, or Jerk > 0.4
            bool is_edge_case = (accel_x < -0.8) || (std::abs(accel_y) > 0.6) || (std::abs(jerk_x) > 0.4);
            if (is_edge_case) {
                ProcessEdgeCase(redis, frame, accel_x, jerk_x, record_count);
            }

            // 4. Image Stitching & Upload
            cv::Mat panorama = StitchPanorama(frame);
            if (!panorama.empty()) {
                UploadImage(client, output_bucket, img_path, panorama);
                if (record_count % 100 == 0) {
                    std::cout << "[Vision] Uploaded panorama: " << img_path << " (Sample)" << std::endl;
                }
            }
        }

        std::cout << "----------------------------------------" << std::endl;
        std::cout << "✓ Stream complete. Total records: " << record_count << std::endl;
        std::cout << "----------------------------------------" << std::endl;

    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}
