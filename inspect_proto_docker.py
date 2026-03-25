import os
import tensorflow as tf
from waymo_open_dataset.protos import end_to_end_driving_data_pb2 as e2ed_proto
from waymo_open_dataset.protos import dataset_pb2 as dataset_proto

print("--- E2EDFrame Fields ---")
for field in e2ed_proto.E2EDFrame.DESCRIPTOR.fields:
    print(f"Name: {field.name}, Tag: {field.number}, Type: {field.type}")

print("\n--- Frame Fields ---")
for field in dataset_proto.Frame.DESCRIPTOR.fields:
    if field.name == 'timestamp_micros':
        print(f"Name: {field.name}, Tag: {field.number}, Type: {field.type}")
    if field.name == 'images':
        print(f"Name: {field.name}, Tag: {field.number}, Type: {field.type}")
    if field.name == 'context':
        print(f"Name: {field.name}, Tag: {field.number}, Type: {field.type}")
