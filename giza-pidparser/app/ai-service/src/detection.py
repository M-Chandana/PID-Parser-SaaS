 
from pdf2image import convert_from_path
import fitz  # PyMuPDF
from PIL import Image
import numpy as np
import cv2
from ultralytics import YOLO
import os
import pandas as pd
import csv
from skimage import color, io, morphology, filters
from skimage import io
from skimage.filters import threshold_otsu
from skimage.morphology import skeletonize
from skimage.util import invert
from collections import defaultdict
import easyocr
import networkx as nx
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pyvis.network import Network
import os


"""----------------------------------------------------------------------""" 
"""PREPROCESSING"""
"""----------------------------------------------------------------------"""

def pdf_to_images(path):
    pages = convert_from_path(path, dpi=600)
    image = pages[0]
    image.save('pid_parser/input.jpg', 'JPEG')
    return image

def segment_image(image):
    # Segment the image into 100 parts with overlap
    height, width = image.shape[:2]
    segments = []
    seg_height = height // 1
    seg_width = width // 1
    overlap = 0

    for i in range(1):
        for j in range(1):
            start_i = max(0, i * seg_height - overlap)
            start_j = max(0, j * seg_width - overlap)
            segment = image[start_i:min(height, (i + 1) * seg_height + overlap),
                            start_j:min(width, (j + 1) * seg_width + overlap)]
            segments.append(((start_i, start_j), segment))
    return segments

def process_segment(segment):
    (start_i, start_j), segment = segment
    original_segment = segment.copy()  # Make a copy to work with

    # Invert the image
    inverted_image = invert(segment)

    # Threshold the image using Otsu's method
    thresh = threshold_otsu(inverted_image)
    binary_image = inverted_image > thresh

    # Skeletonize the binary image
    skeleton = skeletonize(binary_image)

    # Convert skeleton to uint8
    skeleton = (skeleton * 255).astype(np.uint8)

    # Define structuring elements for horizontal and vertical line detection
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 20))

    # Detect horizontal and vertical lines using morphological operations
    horizontal_lines = cv2.morphologyEx(skeleton, cv2.MORPH_OPEN, horizontal_kernel)
    vertical_lines = cv2.morphologyEx(skeleton, cv2.MORPH_OPEN, vertical_kernel)

    # Combine horizontal and vertical lines
    combined_lines = cv2.add(horizontal_lines, vertical_lines)

    # Find contours in the combined lines image
    contours, _ = cv2.findContours(combined_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Calculate coordinates of lines relative to original image
    lines_coordinates = []
    for contour in contours:
        x_coords = contour[:, 0, 0] + start_j
        y_coords = contour[:, 0, 1] + start_i
        lines_coordinates.append((x_coords, y_coords))

    return contours

def divide_image(image):
        height, width, _ = image.shape
        segment_size = (height // 2, width // 2)
        segments = []
        for i in range(2):
            for j in range(2):
                start_row = i * segment_size[0]
                start_col = j * segment_size[1]
                end_row = start_row + segment_size[0]
                end_col = start_col + segment_size[1]
                segment = image[start_row:end_row, start_col:end_col]
                segments.append((segment, (start_row, start_col)))

        segment5 = np.concatenate((segments[0][0][:, segment_size[1]//2:], segments[1][0][:, :segment_size[1]//2]), axis=1)
        segment6 = np.concatenate((segments[2][0][:, segment_size[1]//2:], segments[3][0][:, :segment_size[1]//2]), axis=1)
        segment7 = np.concatenate((segments[0][0][segment_size[0]//2:, :], segments[2][0][:segment_size[0]//2, :]), axis=0)
        segment8 = np.concatenate((segments[1][0][segment_size[0]//2:, :], segments[3][0][:segment_size[0]//2, :]), axis=0)
        segment9 = np.concatenate((segment5[segment_size[0]//2:,], segment6[:segment_size[0]//2, :]), axis=0)

        return segments + [(segment5, (0, segment_size[1]//2)), (segment6, (segment_size[0], segment_size[1]//2)),
                        (segment7, (segment_size[0]//2, 0)), (segment8, (segment_size[0]//2, segment_size[1])),
                        (segment9, (segment_size[0]//2, segment_size[1]//2))]

def divide_image25(image_path):
    image = Image.open(r'pid_parser\input.jpg')
    img_width, img_height = image.size

    segment_width = img_width // 5
    segment_height = img_height // 5

    count = 1
    segments = []

    for i in range(5):
        for j in range(5):
                left = i * segment_width
                upper = j * segment_height
                right = (i + 1) * segment_width
                lower = (j + 1) * segment_height

                if i != 0:
                    left -= 100
                if j != 0:
                    upper -= 100
                segment = image.crop((left, upper, right, lower))

                segments.append((segment, (left, upper)))

                count += 1

    return segments

 


 
"""----------------------------------------------------------------------""" 
"""PROCESSING"""
"""----------------------------------------------------------------------"""


script_dir = os.path.dirname(os.path.abspath(__file__))

# Define paths to YOLO models
model1_path = os.path.join(script_dir, '..', 'model', 'yolo_weights', 'model1_best.pt')
model2_path = os.path.join(script_dir, '..', 'model', 'yolo_weights', 'model2_best.pt')  # Update if needed
model3_path = os.path.join(script_dir, '..', 'model', 'yolo_weights', 'model3_best.pt')  # Update if needed

# Load each YOLO model separately
model1 = YOLO(model1_path)
model2 = YOLO(model2_path)
model3 = YOLO(model3_path)
 
 
def run_model_predictions(image):

    def adjust_bbox(bbox, segment_offset):
        x1, y1, x2, y2, score, cls = bbox
        y_offset, x_offset = segment_offset
        return [x1 + x_offset, y1 + y_offset, x2 + x_offset, y2 + y_offset, score, cls]

    def adjust_bbox2(bbox, segment_offset):
        x1, y1, x2, y2, score, cls = bbox
        x_offset, y_offset = segment_offset
        return [x1 + x_offset, y1 + y_offset, x2 + x_offset, y2 + y_offset, score, cls]
    

    def iou(bbox1, bbox2):
        x1_max = max(bbox1[0], bbox2[0])
        y1_max = max(bbox1[1], bbox2[1])
        x2_min = min(bbox1[2], bbox2[2])
        y2_min = min(bbox1[3], bbox2[3])
        inter_area = max(0, x2_min - x1_max) * max(0, y2_min - y1_max)
        bbox1_area = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        bbox2_area = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
        union_area = bbox1_area + bbox2_area - inter_area
        return inter_area / union_area
    
    def is_point_inside_bbox(point, bbox):
        #Check if a point is inside a bounding box.
        x, y = point
        x_min, y_min, x_max, y_max = bbox[:4]
        return x_min <= x <= x_max and y_min <= y <= y_max

    def is_bbox_inside_another_bbox(bbox1, bbox2):
        #Check if bbox1 is entirely inside bbox2.
        x1_min, y1_min, x1_max, y1_max = bbox1[:4]
        return (
            is_point_inside_bbox((x1_min, y1_min), bbox2) and
            is_point_inside_bbox((x1_max, y1_min), bbox2) and
            is_point_inside_bbox((x1_max, y1_max), bbox2) and
            is_point_inside_bbox((x1_min, y1_max), bbox2)
        )

    def remove_bboxes_inside_others(bboxes):
        #Remove bounding boxes that are inside any other bounding box.
        filtered_bboxes = []
        for i, bbox1 in enumerate(bboxes):
            inside_any = False
            for j, bbox2 in enumerate(bboxes):
                if i != j and is_bbox_inside_another_bbox(bbox1, bbox2):
                    inside_any = True
                    break
            if not inside_any:
                filtered_bboxes.append(bbox1)
        return filtered_bboxes
    def merge_overlapping_bboxes(bboxes, iou_threshold=0.1):
        if len(bboxes) == 0:
            return []

        bboxes = sorted(bboxes, key=lambda x: (x[4], (x[2]-x[0])*(x[3]-x[1])), reverse=True)
        merged_bboxes = []

        while bboxes:
            current_bbox = bboxes.pop(0)
            overlapping_bboxes = [current_bbox]
            non_overlapping_bboxes = []

            for bbox in bboxes:
                if iou(bbox, current_bbox) >= iou_threshold:
                    overlapping_bboxes.append(bbox)
                else:
                    non_overlapping_bboxes.append(bbox)

            min_x = min(bbox[0] for bbox in overlapping_bboxes)
            min_y = min(bbox[1] for bbox in overlapping_bboxes)
            max_x = max(bbox[2] for bbox in overlapping_bboxes)
            max_y = max(bbox[3] for bbox in overlapping_bboxes)
            avg_score = np.mean([bbox[4] for bbox in overlapping_bboxes])
            common_cls = overlapping_bboxes[0][5]

            merged_bboxes.append([min_x, min_y, max_x, max_y, avg_score, common_cls])
            bboxes = non_overlapping_bboxes
        filtered_bboxes = remove_bboxes_inside_others(merged_bboxes)

        return filtered_bboxes
    
    def save_model1_image(final_bboxes, image, class_names, output_path):
        for bbox in final_bboxes:
            x1, y1, x2, y2, score, cls = bbox
            class_name = class_names[int(cls)]
            color = (0, 255, 255)  # Default color
            if class_name == 'column':
                color = (255, 0, 0)  # Red
            elif class_name == 'heat exchanger':
                color = (0, 255, 0)  # Green
            elif class_name == 'centrifuges':
                color = (255, 0, 0)  # Red  
            elif class_name == 'instrument':
                color = (255, 255, 0)  # Yellow
            elif class_name == 'inlet':
                color = (255, 0, 255)  # Magenta
            elif class_name == 'outlet':
                color = (255, 165, 0)  # Orange
            elif class_name == 'pit':
                color = (128, 0, 128)  # Purple
            elif class_name == 'tank':
                color = (0, 128, 128)  # Teal
            else:
                color = (128, 128, 128)  # Default color (Gray)

            cv2.rectangle(image, (int(x1), int(y1)), (int(x2), int(y2)), color, 6)
            cv2.putText(image, f"{class_name}", (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 2, color, 2)
        cv2.imwrite(output_path, image)
        return output_path
    
    def save_model2_image(final_bboxes, image, class_names, output_path):
        colors = {
            'component': (255, 0, 0),   # Red
            'cs': (0, 255, 0),          # Green
            'interlock': (0, 0, 255),   # Blue
            'lmi': (255, 255, 0),       # Cyan
            'plc': (255, 0, 255),       # Magenta
            'tag': (0, 255, 255)        # Yellow
        }

        for bbox in final_bboxes:
            x1, y1, x2, y2, score, cls = bbox
            class_name = class_names[int(cls)]
            color = colors[class_name]
            cv2.rectangle(image, (int(x1), int(y1)), (int(x2), int(y2)), color, 6)
            cv2.putText(image, f"{class_name}", (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 2, color, 2)

        cv2.imwrite(output_path, image)
        return output_path
    
    def save_model3_image(final_bboxes, image, class_names, output_path):
        colors = {
            'valve': (0, 0, 255),  # Blue
            'reducer': (0, 255, 0),  # Green
            'uk': (255, 0, 0),  # Red
            'uk2': (0, 255, 255),  # Yellow
            'scada': (255, 255, 0),  # Cyan
            'arrowU': (128, 0, 0),  # Dark Red
            'arrowD': (0, 128, 0),  # Dark Green
            'arrowL': (0, 0, 128),  # Dark Blue
            'arrowR': (128, 128, 0),
            'bug screen':(255, 0, 255),# Dark Yellow
            'connection':(128,0,128)
        }

        for bbox in final_bboxes:
            x1, y1, x2, y2, score, cls = bbox
            class_name = class_names[int(cls)]
            color = colors[class_name]
            if (int(x2)-int(x1))*(int(y2)-int(y1))<=30000:
                cv2.rectangle(image, (int(x1), int(y1)), (int(x2), int(y2)), color, 6)
                cv2.putText(image, f"{class_name}", (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 2, color, 2)

        cv2.imwrite(output_path, image)
        return output_path
    


    segments = divide_image(image)
    segments25 = divide_image25(image)

    all_bboxes1 = []
    for segment, offset in segments:
        results = model1(segment)
        for result in results:
            bboxes = result.boxes.xyxy.cpu().numpy()
            scores = result.boxes.conf.cpu().numpy()
            classes = result.boxes.cls.cpu().numpy()
            for bbox, score, cls in zip(bboxes, scores, classes):
                all_bboxes1.append(adjust_bbox(list(bbox) + [score, cls], offset))

    all_bboxes2 = []
    for segment, offset in segments25:
        results = model2(segment)
        for result in results:
            bboxes = result.boxes.xyxy.cpu().numpy()
            scores = result.boxes.conf.cpu().numpy()
            classes = result.boxes.cls.cpu().numpy()
            for bbox, score, cls in zip(bboxes, scores, classes):
                all_bboxes2.append(adjust_bbox2(list(bbox) + [score, cls], offset))

    all_bboxes3 = []
    for segment, offset in segments25:
        results = model3(segment)
        for result in results:
            bboxes = result.boxes.xyxy.cpu().numpy()
            scores = result.boxes.conf.cpu().numpy()
            classes = result.boxes.cls.cpu().numpy()
            for bbox, score, cls in zip(bboxes, scores, classes):
                all_bboxes3.append(adjust_bbox2(list(bbox) + [score, cls], offset))

    final_bboxes1 = merge_overlapping_bboxes(all_bboxes1)
    final_bboxes2 = merge_overlapping_bboxes(all_bboxes2)
    final_bboxes3 = merge_overlapping_bboxes(all_bboxes3)
    tempList=[]
    for bbox in final_bboxes3:
        x1, y1, x2, y2, score, cls = bbox
        if (int(x2)-int(x1))*(int(y2)-int(y1))<=30000:
            tempList.append(bbox)



    combined_list =  final_bboxes1 + final_bboxes2 + tempList
    final_bboxes3=tempList
    classes_name1 = model1.names
    classes_name2 = model2.names
    classes_name3 = model3.names
    with open(r'app\static\output.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['x1', 'y1', 'x2', 'y2', 'score', 'cls', 'count'])  # header row

        # Write bounding boxes for model 1
        count_dict1 = defaultdict(int)
        for bbox in final_bboxes1:
            x1, y1, x2, y2, score, cls = bbox
            class_name = classes_name1[cls]
            count_dict1[class_name] += 1
            writer.writerow([x1, y1, x2, y2, score, class_name, count_dict1[class_name]])

        # Write bounding boxes for model 2
        count_dict2 = defaultdict(int)
        for bbox in final_bboxes2:
            x1, y1, x2, y2, score, cls = bbox
            class_name = classes_name2[cls]
            count_dict2[class_name] += 1
            writer.writerow([x1, y1, x2, y2, score, class_name, count_dict2[class_name]])

        # Write bounding boxes for model 3
        count_dict3 = defaultdict(int)
        for bbox in tempList:
            x1, y1, x2, y2, score, cls = bbox
            class_name =  classes_name3[cls]
            count_dict3[class_name] += 1
            writer.writerow([x1, y1, x2, y2, score, class_name, count_dict3[class_name]])

    
    model1_image_path = save_model1_image(final_bboxes1, image.copy(), classes_name1, "app/static/model_one.png")
    model2_image_path = save_model2_image(final_bboxes2, image.copy(), classes_name2, "app/static/model_two.png")
    model3_image_path = save_model3_image(final_bboxes3, image.copy(), classes_name3, "app/static/model_three.png")


    return final_bboxes1,final_bboxes2,final_bboxes3,classes_name1,classes_name2,classes_name3

 

def draw_lines(image, lines, color):
    for start, end in lines:
        x1, y1 = start
        x2, y2 = end
        cv2.line(image, (x1, y1), (x2, y2), color, 2)




 
 


def combine_lines(lines, max_gap=200, max_vertical_distance=20): #for horizontal lines
    combined_lines = []

    # Sort lines based on their starting x-coordinate
    lines = sorted(lines, key=lambda x: x[0][0])

    while lines:
        # Start with the first line in the list
        current_line = lines.pop(0)
        (x1, y1), (x2, y2) = current_line
        new_line = current_line

        # Iterate through remaining lines to check if they can be merged with the current line
        for i, ((nx1, ny1), (nx2, ny2)) in enumerate(lines):
            # Check if lines are on the same horizontal level within the max_vertical_distance
            if abs(y1 - ny1) < max_vertical_distance and abs(y2 - ny2) < max_vertical_distance:
                # Check if the lines are close enough horizontally to be considered for merging
                if abs(x2 - nx1) < max_gap:
                    # Merge the lines by extending the current line
                    new_line = ((x1, y1), (nx2, ny2))
                    # Remove the line that has been merged
                    lines.pop(i)
                    break

        # Add the merged or unmerged line to the combined lines list
        combined_lines.append(new_line)

    return combined_lines
def combine_vertical_lines(lines, max_gap=200, max_horizontal_distance=20):
    combined_lines = []

    # Sort lines based on their starting y-coordinate
    lines = sorted(lines, key=lambda x: x[0][1])

    while lines:
        # Start with the first line in the list
        current_line = lines.pop(0)
        (x1, y1), (x2, y2) = current_line
        new_line = current_line

        # Iterate through remaining lines to check if they can be merged with the current line
        for i, ((nx1, ny1), (nx2, ny2)) in enumerate(lines):
            # Check if lines are on the same vertical level within the max_horizontal_distance
            if abs(x1 - nx1) < max_horizontal_distance and abs(x2 - nx2) < max_horizontal_distance:
                # Check if the lines are close enough vertically to be considered for merging
                if abs(y2 - ny1) < max_gap:
                    # Merge the lines by extending the current line
                    new_line = ((x1, y1), (nx2, ny2))
                    # Remove the line that has been merged
                    lines.pop(i)
                    break

        # Add the merged or unmerged line to the combined lines list
        combined_lines.append(new_line)

    return combined_lines

def detect_dashed_lines(image, h_lines,v_lines):
  height, width, channels = image.shape
  white_image = np.full((height, width, channels), 255, dtype=np.uint8)

  df = pd.read_csv('app/static/output.csv')
  v1=list(df.values)

  def draw_lines(image, lines, color):
      for start, end in lines:
          x1, y1 = start
          x2, y2 = end
          cv2.line(image, (x1, y1), (x2, y2), color, 6)

  def draw_rec(image, recs, color):
        for bbox in recs:
          x1, y1, x2, y2, score, cls,count = bbox
          cv2.rectangle(image, (int(x1), int(y1)), (int(x2), int(y2)), color, -1)

  draw_lines(image, h_lines, (255, 255, 255))  # Green lines
  draw_lines(image, v_lines, (255, 255, 255))    # Blue lines
  draw_rec(image, v1, (255, 255, 255))                      # Magenta rectangles

  gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

  # Parameters for Hough Transform
  threshold = 200  # Adjust as needed
  min_line_length = 25  # Adjust as needed
  max_line_gap = 70  # Adjust as needed

  # Initialize an image to draw detected lines
  lines_image = np.copy(image)

  # Load bounding boxes from CSV and filter out unwanted classes

# Load bounding boxes from CSV and filter out unwanted classes
  bboxes = pd.read_csv('app/static/output.csv')
  bbox_df = bboxes[~bboxes['cls'].isin(['arrowL', 'arrowD', 'arrowR', 'arrowU', 'connection', 'scada'])]

  # Function to detect lines using Hough Transform
  def detect_lines_PHT(segment):
      edges = cv2.Canny(segment, 50, 150, apertureSize=7)
      lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold, minLineLength=min_line_length, maxLineGap=max_line_gap)
      return lines

  # Function to merge or remove duplicate lines based on proximity
  def merge_similar_lines(lines, threshold=10):
      unique_lines = []

      def line_is_similar(line1, line2, threshold):
          x1, y1, x2, y2 = line1
          x1_, y1_, x2_, y2_ = line2
          return (abs(x1 - x1_) < threshold and abs(y1 - y1_) < threshold and
                  abs(x2 - x2_) < threshold and abs(y2 - y2_) < threshold)

      for line in lines:
          x1, y1, x2, y2 = line[0]
          is_unique = True

          for unique_line in unique_lines:
              if line_is_similar([x1, y1, x2, y2], unique_line[0], threshold):
                  is_unique = False
                  break

          if is_unique:
              unique_lines.append([[x1, y1, x2, y2]])

      return unique_lines

  # Function to draw lines on an image
  def draw_lines(image, lines, offset_x, offset_y):
      for line in lines:
          x1, y1, x2, y2 = line
          # Filter diagonal lines
          if (x1 == x2 or y1 == y2):  # Keep only horizontal or vertical lines
              cv2.line(image, (x1 + offset_x, y1 + offset_y), (x2 + offset_x, y2 + offset_y), (0, 0, 0), 8)

  # Function to check if a line is inside any bounding box
  def is_line_inside_bbox(x1, y1, x2, y2, bbox_df):
      for _, row in bbox_df.iterrows():
          x_min, y_min, x_max, y_max = row['x1'], row['y1'], row['x2'], row['y2']
          if (x_min <= x1 <= x_max and y_min <= y1 <= y_max and
              x_min <= x2 <= x_max and y_min <= y2 <= y_max):
              return True
      return False
   # Parameters for segmentation
  rows, cols = gray_image.shape
  num_segments = 1
  segment_size = int(np.sqrt(num_segments))
  # Iterate over each segment and apply Hough Transform
  segment_height = rows // segment_size
  segment_width = cols // segment_size

  all_lines = []

  for i in range(segment_size):
      for j in range(segment_size):
          x_start = j * segment_width
          y_start = i * segment_height
          x_end = x_start + segment_width
          y_end = y_start + segment_height

          segment = gray_image[y_start:y_end, x_start:x_end]

          # Detect lines in the segment
          lines = detect_lines_PHT(segment)

          if lines is not None:
              for line in lines:
                  x1, y1, x2, y2 = line[0]
                  # Adjust coordinates to account for segment offset
                  x1, y1, x2, y2 = x1 + x_start, y1 + y_start, x2 + x_start, y2 + y_start

                  # Filter out lines inside any bounding box
                  if not is_line_inside_bbox(x1, y1, x2, y2, bbox_df):
                      # Add valid lines to the global list
                      all_lines.append([[x1, y1, x2, y2]])

  # Remove duplicate or overlapping lines
  all_lines = merge_similar_lines(all_lines, threshold=200)

  # Draw unique lines on the image
  for line in all_lines:
     (lines_image, line, 0, 0)

  #cv2.imwrite("app/static/lines.jpg", lines_image)
  dh_lines,dv_lines=detect_lines(lines_image)
  return dh_lines, dv_lines

def detect_lines(image):
     
    def is_point_inside_bbox(x, y, bbox):
        bx1, by1, bx2, by2 = bbox
        return bx1 <= x <= bx2 and by1 <= y <= by2
    
    def is_line_inside_bbox(start, end, bbox):
        x1, y1 = start
        x2, y2 = end
        return is_point_inside_bbox(x1, y1, bbox) and is_point_inside_bbox(x2, y2, bbox)
     
    grayscale_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    bilateral_filtered_image = cv2.bilateralFilter(grayscale_image, d=9, sigmaColor=75, sigmaSpace=75)
 
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    eroded_image = cv2.erode(bilateral_filtered_image, kernel, iterations=1)
 
    image = cv2.dilate(eroded_image, kernel, iterations=1)
    image = cv2.GaussianBlur(image, (5, 5), 0)

 

    kernel_horizontal = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 1))
    kernel_vertical = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 50))


    closed_horizontal = cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel_horizontal)
    closed_vertical = cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel_vertical)

    _, binary_image_H = cv2.threshold(closed_horizontal, 128, 255, cv2.THRESH_BINARY_INV)
    _, binary_image_V = cv2.threshold(closed_vertical, 128, 255, cv2.THRESH_BINARY_INV)

    kernel_rect = cv2.getStructuringElement(cv2.MORPH_CROSS, (5, 5))
    cleaned_image_H = cv2.morphologyEx(binary_image_H, cv2.MORPH_CLOSE, kernel_rect)
    cleaned_image_V = cv2.morphologyEx(binary_image_V, cv2.MORPH_CLOSE, kernel_rect)

    cleaned_image_H = cv2.bitwise_not(cleaned_image_H)
    cleaned_image_V = cv2.bitwise_not(cleaned_image_V)
     
    segments_H = segment_image(cleaned_image_H)
    segments_V = segment_image(cleaned_image_V)
 
    lines_coordinates_horizontal = []
    lines_coordinates_vertical=[]
     

    horizontal_rectangles=[]
    vertical_rectangles=[]
    for segment in segments_H:
        contours_horizontal = process_segment(segment)
        for contour in contours_horizontal:
            x, y, w, h = cv2.boundingRect(contour)
            horizontal_rectangles.append((segment[0][1] + x, segment[0][0] + y, w, h))


    for segment in segments_V:
        contours_vertical = process_segment(segment)
        for contour in contours_vertical:
            x, y, w, h = cv2.boundingRect(contour)
            vertical_rectangles.append((segment[0][1] + x, segment[0][0] + y, w, h))

     

    horizontal_start_end_points = []
    for (x, y, w, h) in horizontal_rectangles:
        start_point = (x, y)
        end_point = (x + w, y)
        horizontal_start_end_points.append((start_point, end_point))
         


    vertical_start_end_points = []
    for (x, y, w, h) in vertical_rectangles:
        start_point = (x, y)
        end_point = (x, y + h)
        vertical_start_end_points.append((start_point, end_point))
    df = pd.read_csv('app/static/output.csv')

     
    extracted_rows = []

 
    for index, row in df.iterrows():

        extracted_cols = row[:4]

        extracted_rows.append(extracted_cols.tolist())

    all_bboxes = extracted_rows
 
    filtered_horizontal_lines = [
        (start, end) for start, end in horizontal_start_end_points
        if not any(is_line_inside_bbox((start[0],start[1]),(end[0],end[1]), bbox) for bbox in all_bboxes)
    ]

    filtered_vertical_lines = [
        (start,end) for start, end in vertical_start_end_points
        if not any(is_line_inside_bbox((start[0],start[1]),(end[0],end[1]), bbox) for bbox in all_bboxes)
    ]
    min_length=10

    HL= [
        line for line in  filtered_horizontal_lines
        if abs(line[0][0] - line[1][0]) >= min_length
    ]

    
    VL= [
        line for line in filtered_vertical_lines
        if abs(line[0][1] - line[1][1]) >= min_length
    ]
    combined_linesH = combine_lines(HL)
    combined_linesV=combine_vertical_lines(VL)

    return combined_linesH,combined_linesV

def add_scada_connections(bbox_df, scada_df, proximity_threshold=100):
    def bbox_edges(bbox):
        (x1, y1), (x2, y2) = bbox
        return [
            ((x1, y1), (x2, y1)),  # Top edge
            ((x2, y1), (x2, y2)),  # Right edge
            ((x2, y2), (x1, y2)),  # Bottom edge
            ((x1, y2), (x1, y1))   # Left edge
        ]

    def distance_between_points(p1, p2):
        return np.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)

    def closest_tag_to_point(point, tags):
        min_distance = float('inf')
        closest_tag = None
        for tag in tags:
            tag_center = ((tag[0][0] + tag[1][0]) / 2, (tag[0][1] + tag[1][1]) / 2)  # Center of the tag
            dist = distance_between_points(point, tag_center)
            if dist < min_distance:
                min_distance = dist
                closest_tag = tag
        return closest_tag

    # Filter SCADA bounding boxes
    scada_boxes = scada_df[scada_df['cls'] == 'scada']
    scada_connects = []
    seen_connections = set()

    for _, scada_row in scada_boxes.iterrows():
        scada_bbox = ((scada_row['x1'], scada_row['y1']), (scada_row['x2'], scada_row['y2']))
        scada_name = f"scada{scada_row['count']}"

        width = scada_bbox[1][0] - scada_bbox[0][0]
        height = scada_bbox[1][1] - scada_bbox[0][1]

        # Determine if SCADA is vertical or horizontal
        is_vertical = height > width

        # Get the relevant tags close to SCADA's ends (top/bottom for vertical, left/right for horizontal)
        tags_near_scada = [
            ((row['x1'], row['y1']), (row['x2'], row['y2']), f"{row['cls']}{row['count']}")
            for _, row in bbox_df.iterrows()
        ]

        if is_vertical:
            top_point = ((scada_bbox[0][0] + scada_bbox[1][0]) / 2, scada_bbox[0][1])  # Top center
            bottom_point = ((scada_bbox[0][0] + scada_bbox[1][0]) / 2, scada_bbox[1][1])  # Bottom center

            top_tag = closest_tag_to_point(top_point, tags_near_scada)
            bottom_tag = closest_tag_to_point(bottom_point, tags_near_scada)

            if top_tag and bottom_tag:
                connection = tuple(sorted([top_tag[2], bottom_tag[2]]))
                if connection not in seen_connections:
                    seen_connections.add(connection)
                    scada_connects.append(connection)

        else:
            left_point = (scada_bbox[0][0], (scada_bbox[0][1] + scada_bbox[1][1]) / 2)  # Left center
            right_point = (scada_bbox[1][0], (scada_bbox[0][1] + scada_bbox[1][1]) / 2)  # Right center

            left_tag = closest_tag_to_point(left_point, tags_near_scada)
            right_tag = closest_tag_to_point(right_point, tags_near_scada)

            if left_tag and right_tag:
                connection = tuple(sorted([left_tag[2], right_tag[2]]))
                if connection not in seen_connections:
                    seen_connections.add(connection)
                    scada_connects.append(connection)

    return scada_connects
   

def generate_pyvis_graph(edges_df):
    bboxes = pd.read_csv('app/static/output.csv')
    bbox_df = bboxes[~bboxes['cls'].isin(['arrowL', 'arrowD', 'arrowR', 'arrowU', 'connection', 'scada'])]

    # Create a new graph
    G_bboxes = nx.Graph()

    # Function to calculate the center of a bounding box
    def bbox_center(x1, y1, x2, y2):
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    # Add nodes with their center positions
    for i, row in bbox_df.iterrows():
        x1, y1, x2, y2 = row['x1'], row['y1'], row['x2'], row['y2']
        name = f"{row['cls']}{row['count']}"
        center = bbox_center(x1, y1, x2, y2)
        G_bboxes.add_node(name, pos=center, cls=row['cls'])

     
    connections_df = edges_df  # Replace with your actual connections DataFrame

    # Add edges to the graph, ensuring unique and undirected edges
    edges_set = set()
    for _, row in connections_df.iterrows():
        source, target = row['Source'], row['Target']
        if G_bboxes.nodes[source]['cls'] != G_bboxes.nodes[target]['cls']:
            edge = tuple(sorted((source, target)))
            if edge not in edges_set:
                G_bboxes.add_edge(*edge)
                edges_set.add(edge)

    # Filter out edges between nodes of the same type
    edges_to_remove = []
    for edge in G_bboxes.edges():
        src_cls = G_bboxes.nodes[edge[0]]['cls']
        tgt_cls = G_bboxes.nodes[edge[1]]['cls']
        if (src_cls == "inlet" and tgt_cls == "inlet") or (src_cls == "outlet" and tgt_cls == "outlet"):
            edges_to_remove.append(edge)

    G_bboxes.remove_edges_from(edges_to_remove)

    # Function to check if two bounding boxes intersect
    def do_boxes_intersect(box1, box2):
        x1, y1, x2, y2 = box1
        x3, y3, x4, y4 = box2
        return not (x2 < x3 or x4 < x1 or y2 < y3 or y4 < y1)

    # Calculate intersections and add edges
    for i, row1 in bbox_df.iterrows():
        x1, y1, x2, y2 = row1['x1'], row1['y1'], row1['x2'], row1['y2']
        box1 = (x1, y1, x2, y2)
        name1 = f"{row1['cls']}{row1['count']}"
        for j, row2 in bbox_df.iterrows():
            if i >= j:
                continue
            x3, y3, x4, y4 = row2['x1'], row2['y1'], row2['x2'], row2['y2']
            box2 = (x3, y3, x4, y4)
            name2 = f"{row2['cls']}{row2['count']}"
            if do_boxes_intersect(box1, box2):
                if not G_bboxes.has_edge(name1, name2):
                    G_bboxes.add_edge(name1, name2)

    # Function to calculate the distance between two points
    def bbox_edges_distance(box1, box2):
        x1_min, y1_min, x1_max, y1_max = box1
        x2_min, y2_min, x2_max, y2_max = box2
        dx = max(0, max(x1_min - x2_max, x2_min - x1_max))
        dy = max(0, max(y1_min - y2_max, y2_min - y1_max))
        return np.sqrt(dx**2 + dy**2)

    # Add edges based on proximity
    for i, row1 in bbox_df.iterrows():
        x1_min, y1_min, x1_max, y1_max = row1['x1'], row1['y1'], row1['x2'], row1['y2']
        box1 = (x1_min, y1_min, x1_max, y1_max)
        name1 = f"{row1['cls']}{row1['count']}"
        for j, row2 in bbox_df.iterrows():
            if i >= j:
                continue
            x2_min, y2_min, x2_max, y2_max = row2['x1'], row2['y1'], row2['x2'], row2['y2']
            box2 = (x2_min, y2_min, x2_max, y2_max)
            name2 = f"{row2['cls']}{row2['count']}"
            if bbox_edges_distance(box1, box2) < 100:
                if not G_bboxes.has_edge(name1, name2):
                    G_bboxes.add_edge(name1, name2)

    # Create a PyVis network
    net = Network(height="1000px", width='100%')

    # Add nodes to the PyVis network with different colors based on their class
    color_map = {
        'inlet': 'blue',
        'outlet': 'red',
        'valve': 'green',
        'tank': 'orange',
        # Add more colors for other classes as needed
    }

    for node, data in G_bboxes.nodes(data=True):
        cls = data['cls']
        color = color_map.get(cls, 'gray')  # Default color if class is not in the map
        net.add_node(node, title=node, color=color, size=10)

    # Add edges to the PyVis network
    for edge in G_bboxes.edges():
        net.add_edge(edge[0], edge[1])

    # Set options for the PyVis network
    net.set_options('''
    var options = {
        "nodes": {
            "shape": "dot",
            "size": 15,
            "font": {
                "size": 14
            }
        },
        "edges": {
            "smooth": {
                "type": "continuous"
            }
        },
        "physics": {
            "enabled": true
        }
    }
    ''')

    # Save the network to an HTML file
    net.save_graph('app/static/g.html')

def generate_graph(h_lines,v_lines,dashed_edges_df):
    
    print(dashed_edges_df)
    def extend_line(x1, y1, x2, y2, buffer=10):
        line_length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        if line_length == 0:
            return x1, y1, x2, y2
        x1_new = int(x1 - buffer * (x2 - x1) / line_length)
        y1_new = int(y1 - buffer * (y2 - y1) / line_length)
        x2_new = int(x2 + buffer * (x2 - x1) / line_length)
        y2_new = int(y2 + buffer * (y2 - y1) / line_length)
        return x1_new, y1_new, x2_new, y2_new

# Function to check if two lines intersect
    def do_lines_intersect(line1, line2):
        (x1, y1), (x2, y2) = line1
        (x3, y3), (x4, y4) = line2

        def orientation(p, q, r):
            val = (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])
            if val == 0:
                return 0  # collinear
            elif val > 0:
                return 1  # clockwise
            else:
                return 2  # counterclockwise

        o1 = orientation((x1, y1), (x2, y2), (x3, y3))
        o2 = orientation((x1, y1), (x2, y2), (x4, y4))
        o3 = orientation((x3, y3), (x4, y4), (x1, y1))
        o4 = orientation((x3, y3), (x4, y4), (x2, y2))

        # General case
        if o1 != o2 and o3 != o4:
            return True

        # Special cases
        def on_segment(p, q, r):
            if min(p[0], r[0]) <= q[0] <= max(p[0], r[0]) and min(p[1], r[1]) <= q[1] <= max(p[1], r[1]):
                return True
            return False

        # p, q, r are collinear and q lies on pr
        if o1 == 0 and on_segment((x1, y1), (x3, y3), (x2, y2)):
            return True
        if o2 == 0 and on_segment((x1, y1), (x4, y4), (x2, y2)):
            return True
        if o3 == 0 and on_segment((x3, y3), (x1, y1), (x4, y4)):
            return True
        if o4 == 0 and on_segment((x3, y3), (x2, y2), (x4, y4)):
            return True

        return False

    # Function to check if a line intersects with any bounding box
    def is_line_intersecting_bbox(x1, y1, x2, y2, bboxes):
        for _, bbox in bboxes.iterrows():
            if do_lines_intersect(((x1, y1), (x2, y2)), ((bbox['x1'], bbox['y1']), (bbox['x2'], bbox['y2']))):
                return True
        return False
     

     
    extended_linesH = []
    extended_linesV = []
    for line in h_lines:
    #for line in filtered_vertical_lines + filtered_horizontal_lines:
        x1, y1, x2, y2 = line[0][0], line[0][1], line[1][0], line[1][1]
        x1_ext, y1_ext, x2_ext, y2_ext = extend_line(x1, y1, x2, y2, buffer=30)

        #if not is_line_intersecting_bbox(x1_ext, y1_ext, x2_ext, y2_ext, filtered_bboxes):
        extended_linesH.append((x1_ext, y1_ext, x2_ext, y2_ext))
    for line in v_lines:
        x1, y1, x2, y2 = line[0][0], line[0][1], line[1][0], line[1][1]
        x1_ext, y1_ext, x2_ext, y2_ext = extend_line(x1, y1, x2, y2, buffer=30)

        #if not is_line_intersecting_bbox(x1_ext, y1_ext, x2_ext, y2_ext, filtered_bboxes):
        extended_linesV.append((x1_ext, y1_ext, x2_ext, y2_ext))
    
    def create_horizontal_bbox(x1, y1, x2, y2, padding=10):
        return (min(x1, x2) - padding, y1 - 5, max(x1, x2) + padding, y1 + 5)

    # Function to create a bounding box for a vertical line with padding
    def create_vertical_bbox(x1, y1, x2, y2, padding=10):
        return (x1 - 5, min(y1, y2) - padding, x1 + 5, max(y1, y2) + padding)

    # Function to check if two bounding boxes intersect
    def do_bboxes_intersect(bbox1, bbox2):
        return not (bbox1[2] < bbox2[0] or bbox1[0] > bbox2[2] or
                    bbox1[3] < bbox2[1] or bbox1[1] > bbox2[3])

    # Function to merge intersecting horizontal lines
    def merge_horizontal_lines(lines, padding=10):
        merged_lines = []
        while lines:
            line1 = lines.pop(0)
            x1, y1, x2, y2 = line1
            bbox1 = create_horizontal_bbox(x1, y1, x2, y2, padding)
            merged = False

            for i, line2 in enumerate(lines):
                x3, y3, x4, y4 = line2
                bbox2 = create_horizontal_bbox(x3, y3, x4, y4, padding)

                if do_bboxes_intersect(bbox1, bbox2):
                    # Merge lines by taking min and max of x-coordinates
                    new_line = [min(x1, x2, x3, x4), y1, max(x1, x2, x3, x4), y1]
                    lines[i] = new_line
                    merged = True
                    break

            if not merged:
                merged_lines.append(line1)

        return merged_lines

    # Function to merge intersecting vertical lines
    def merge_vertical_lines(lines, padding=10):
        merged_lines = []
        while lines:
            line1 = lines.pop(0)
            x1, y1, x2, y2 = line1
            bbox1 = create_vertical_bbox(x1, y1, x2, y2, padding)
            merged = False

            for i, line2 in enumerate(lines):
                x3, y3, x4, y4 = line2
                bbox2 = create_vertical_bbox(x3, y3, x4, y4, padding)

                if do_bboxes_intersect(bbox1, bbox2):
                    # Merge lines by taking min and max of y-coordinates
                    new_line = [x1, min(y1, y2, y3, y4), x1, max(y1, y2, y3, y4)]
                    lines[i] = new_line
                    merged = True
                    break

            if not merged:
                merged_lines.append(line1)

        return merged_lines
    merged_horizontal_lines = merge_horizontal_lines(extended_linesH, padding=20)
    # Merge vertical lines
    merged_vertical_lines = merge_vertical_lines(extended_linesV, padding=20)

    # Combine the merged lines back
    all_merged_lines = merged_horizontal_lines + merged_vertical_lines
    bboxes = pd.read_csv('app/static/output.csv')
    scada_df = bboxes[bboxes['cls'] == 'scada'] 
    bbox_df = bboxes[~bboxes['cls'].isin(['arrowL', 'arrowD', 'arrowR', 'arrowU', 'connection', 'scada'])]

    # Create a list to hold bounding boxes with their coordinates
    bounding_boxes = []
    for i, row in bbox_df.iterrows():
        x1, y1, x2, y2 = row['x1'], row['y1'], row['x2'], row['y2']
        name = f"{row['cls']}{row['count']}"
        bounding_boxes.append(((x1, y1), (x2, y2), name))

 
    lines = all_merged_lines

    # Create a new graph
    G = nx.Graph()

    intersection_counter = 1
    endpoint_counter = 1
    # Function to check if a point is inside a bounding box
    def point_in_bbox(point, bbox):
        (x1, y1), (x2, y2) = bbox
        px, py = point
        return x1 <= px <= x2 and y1 <= py <= y2

    # Function to get the center of a bounding box
    def bbox_center(bbox):
        (x1, y1), (x2, y2) = bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    # Function to check if two line segments intersect
    def intersect(line1, line2):
        x1, y1, x2, y2 = line1
        x3, y3, x4, y4 = line2
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if denom == 0:
            return False
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
        return 0 <= t <= 1 and 0 <= u <= 1

    def intersection_point(line1, line2):
        x1, y1, x2, y2 = line1
        x3, y3, x4, y4 = line2
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / denom
        py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / denom
        return int(px), int(py)
     
    for line1 in lines:
        x1, y1, x2, y2 = line1
        start_node = (x1, y1)
        end_node = (x2, y2)

        # Add initial nodes and edges with positions
        G.add_node(start_node, pos=start_node, type='line_endpoint')
        G.add_node(end_node, pos=end_node, type='line_endpoint')
        G.add_edge(start_node, end_node)

        for line2 in lines:
            if line1 != line2:
                if intersect(line1, line2):
                    x_int, y_int = intersection_point(line1, line2)
                    intersection_node = (x_int, y_int)

                    # Add intersection node and edges with positions
                    G.add_node(intersection_node, pos=intersection_node, type='intersection')
                    G.add_edge(start_node, intersection_node)
                    G.add_edge(end_node, intersection_node)
                    G.add_edge(intersection_node, (line2[0], line2[1]))
                    G.add_edge(intersection_node, (line2[2], line2[3]))

    scada =add_scada_connections(bbox_df, scada_df)

    # Update nodes to use bounding box centers if inside a bounding box
    def update_node_positions(G, bounding_boxes):
        for node in list(G.nodes()):
            node_pos = G.nodes[node]['pos']  # Get the position of the node
            for bbox in bounding_boxes:
                bbox_coords = bbox[:2]  # Extract the coordinate part of the bbox
                center = bbox_center(bbox_coords)
                name = bbox[2]  # Extract the name (label) part of the bbox
                if point_in_bbox(node_pos, bbox_coords):
                    G.add_node(name, pos=center, type='bbox')
                    for neighbor in list(G.neighbors(node)):
                        G.add_edge(name, neighbor)
                    G.remove_node(node)
                    break

                

    update_node_positions(G, bounding_boxes)
    img = cv2.imread('app/static/input.jpg')
    pos = nx.get_node_attributes(G, 'pos')

    node_labels = {node: node for node in G.nodes()}
    for node in pos:
        x, y = pos[node]
        pos[node] = (x, img.shape[0] - y)

    # Differentiate node colors based on their type
    
    fig, ax = plt.subplots()

# Display the image
    ax.imshow(cv2.flip(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), 0))

    node_colors = []
    for node in G.nodes():
        node_type = G.nodes[node].get('type', 'line_endpoint')
        if node_type == 'bbox':
            node_colors.append('g')  # Green for bbox nodes
        elif node_type == 'intersection':
            node_colors.append('b')  # Blue for intersection nodes
        else:
            node_colors.append('r')  # Red for line endpoint nodes

    nx.draw(G, pos, ax=ax, node_size=50, node_color=node_colors, labels=node_labels, font_size=6, edge_color='gray')

    #plt.gca().invert_yaxis()
    #output_image_file = 'app/static/testing.png'
    #plt.savefig(output_image_file, bbox_inches='tight', pad_inches=0.1)
    #plt.close(fig)
     
    def trace_component_connections(dfs_results):
        component_connections = {}

        def explore_node(component, node):
            if isinstance(node, str):
                # If the node is a string, it's a named component, so we connect it
                if component not in component_connections:
                    component_connections[component] = set()
                component_connections[component].add(node)
            elif node in dfs_results:
                # If the node is a tuple, we need to explore it further
                for next_node in dfs_results[node]:
                    explore_node(component, next_node)

        for component, connections in dfs_results.items():
            for node in connections:
                explore_node(component, node)

        return component_connections

    # Using the provided dfs_results
    df_comp = []
    print("Solid Line Connections")

    for node in G.nodes():
    #print(node)
        if isinstance(node, str):

            dfs_results=nx.dfs_successors(G,node)
            component_connections = trace_component_connections(dfs_results)
            if node in component_connections and component_connections[node]:

                print(node," : ",component_connections[node])
                connections_str = ', '.join(component_connections[node])
                df_comp.append({'Component': node, 'Connected Components': connections_str})
    
    df = pd.DataFrame(df_comp)

    csv_file_path = 'app/static/component_connections.csv'

    # Save the DataFrame to CSV
    df.to_csv(csv_file_path, index=False)

    print(f'DataFrame saved to {csv_file_path}')
    edges = []
    for _, row in df.iterrows():
        source = row['Component']
        targets = row['Connected Components'].split(', ')
        for target in targets:
            if source != target:  # Avoid self-loops
                edges.append((source, target))

     
    edges_df = pd.DataFrame(edges, columns=['Source', 'Target'])

    edges_df = pd.concat([edges_df, dashed_edges_df])

    edges_df['Sorted'] = edges_df.apply(lambda x: tuple(sorted([x['Source'], x['Target']])), axis=1)
 
    edges_df = edges_df.drop_duplicates(subset='Sorted').drop(columns='Sorted')
   
     

    scada_df = pd.DataFrame(scada, columns=['Source', 'Target'])
    print("scada connections")
    for i in scada:
        print(i)

# Append SCADA connections to edges_df
    edges_df = pd.concat([edges_df, scada_df])
    print(edges_df)
     
    G_bboxes = nx.Graph()

    # Function to calculate the center of a bounding box
    def bbox_center(x1, y1, x2, y2):
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    # Add nodes with their center positions
    for i, row in bbox_df.iterrows():
        x1, y1, x2, y2 = row['x1'], row['y1'], row['x2'], row['y2']
        name = f"{row['cls']}{row['count']}"
        center = bbox_center(x1, y1, x2, y2)
        G_bboxes.add_node(name, pos=center, cls=row['cls'])

     
    connections_df = edges_df

    # Add edges to the graph
    edges_set = set()  # Set to track unique edges
    for _, row in connections_df.iterrows():
        source, target = row['Source'], row['Target']
        #if G_bboxes.nodes[source]['cls'] != G_bboxes.nodes[target]['cls']:
            
        edge = tuple(sorted((source, target)))
        if edge not in edges_set:
                G_bboxes.add_edge(*edge)
                edges_set.add(edge)
    
 
    def do_boxes_intersect(box1, box2):
        x1, y1, x2, y2 = box1
        x3, y3, x4, y4 = box2
        return not (x2 < x3 or x4 < x1 or y2 < y3 or y4 < y1)

    # Calculate intersections and add edges
    for i, row1 in bbox_df.iterrows():
        x1, y1, x2, y2 = row1['x1'], row1['y1'], row1['x2'], row1['y2']
        box1 = (x1, y1, x2, y2)
        name1 = f"{row1['cls']}{row1['count']}"
        for j, row2 in bbox_df.iterrows():
            if i >= j:
                continue
            x3, y3, x4, y4 = row2['x1'], row2['y1'], row2['x2'], row2['y2']
            box2 = (x3, y3, x4, y4)
            name2 = f"{row2['cls']}{row2['count']}"
            if do_boxes_intersect(box1, box2):
                if not G_bboxes.has_edge(name1, name2):
                    G_bboxes.add_edge(name1, name2)

    # Function to calculate the distance between two points
     
    edges_to_remove = []
    for edge in G_bboxes.edges():
        src_cls = G_bboxes.nodes[edge[0]]['cls']
        tgt_cls = G_bboxes.nodes[edge[1]]['cls']
        if  (src_cls == "inlet" and  tgt_cls == "inlet") or (src_cls == "outlet" and  tgt_cls == "outlet") or (src_cls == "inlet" and tgt_cls == "outlet")  :
            edges_to_remove.append(edge)
    G_bboxes.remove_edges_from(edges_to_remove)

    # Load the input image
    img = cv2.imread('app/static/input.jpg')

        # Get the positions for all nodes
    pos = nx.get_node_attributes(G_bboxes, 'pos')

        # Get the dimensions of the image
    img_height, img_width = img.shape[:2]

    # Flip the y-coordinates to match the image coordinate system
    pos_flipped = {node: (x, img_height - y) for node, (x, y) in pos.items()}

    # Create a figure and axis using Matplotlib
    fig, ax = plt.subplots(figsize=(8, 6))

    # Display the image
    ax.imshow(cv2.flip(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), 0))

    # Draw the graph on top of the image with flipped y-coordinates
    nx.draw(G_bboxes, pos=pos_flipped, ax=ax, with_labels=True, node_color='lightblue', edge_color='darkblue', node_size=10, font_size=4)

    # Ensure the y-axis is flipped to match the image
    plt.gca().invert_yaxis()
    output_image_file = 'app/static/embedded_graph.png'
    plt.savefig(output_image_file, bbox_inches='tight', pad_inches=0,dpi=600)
    plt.close(fig)
    generate_pyvis_graph(edges_df)




def generate_graph_dashed_lines(h_lines,v_lines):
    def extend_line(x1, y1, x2, y2, buffer=100):
        line_length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        if line_length == 0:
            return x1, y1, x2, y2
        x1_new = int(x1 - buffer * (x2 - x1) / line_length)
        y1_new = int(y1 - buffer * (y2 - y1) / line_length)
        x2_new = int(x2 + buffer * (x2 - x1) / line_length)
        y2_new = int(y2 + buffer * (y2 - y1) / line_length)
        return x1_new, y1_new, x2_new, y2_new

# Function to check if two lines intersect
    def do_lines_intersect(line1, line2):
        (x1, y1), (x2, y2) = line1
        (x3, y3), (x4, y4) = line2

        def orientation(p, q, r):
            val = (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])
            if val == 0:
                return 0  # collinear
            elif val > 0:
                return 1  # clockwise
            else:
                return 2  # counterclockwise

        o1 = orientation((x1, y1), (x2, y2), (x3, y3))
        o2 = orientation((x1, y1), (x2, y2), (x4, y4))
        o3 = orientation((x3, y3), (x4, y4), (x1, y1))
        o4 = orientation((x3, y3), (x4, y4), (x2, y2))

        # General case
        if o1 != o2 and o3 != o4:
            return True

        # Special cases
        def on_segment(p, q, r):
            if min(p[0], r[0]) <= q[0] <= max(p[0], r[0]) and min(p[1], r[1]) <= q[1] <= max(p[1], r[1]):
                return True
            return False

        # p, q, r are collinear and q lies on pr
        if o1 == 0 and on_segment((x1, y1), (x3, y3), (x2, y2)):
            return True
        if o2 == 0 and on_segment((x1, y1), (x4, y4), (x2, y2)):
            return True
        if o3 == 0 and on_segment((x3, y3), (x1, y1), (x4, y4)):
            return True
        if o4 == 0 and on_segment((x3, y3), (x2, y2), (x4, y4)):
            return True

        return False

    # Function to check if a line intersects with any bounding box
    def is_line_intersecting_bbox(x1, y1, x2, y2, bboxes):
        for _, bbox in bboxes.iterrows():
            if do_lines_intersect(((x1, y1), (x2, y2)), ((bbox['x1'], bbox['y1']), (bbox['x2'], bbox['y2']))):
                return True
        return False


     
    extended_linesH = []
    extended_linesV = []
    for line in h_lines:
    #for line in filtered_vertical_lines + filtered_horizontal_lines:
        x1, y1, x2, y2 = line[0][0], line[0][1], line[1][0], line[1][1]
        x1_ext, y1_ext, x2_ext, y2_ext = extend_line(x1, y1, x2, y2, buffer=30)

        #if not is_line_intersecting_bbox(x1_ext, y1_ext, x2_ext, y2_ext, filtered_bboxes):
        extended_linesH.append((x1_ext, y1_ext, x2_ext, y2_ext))
    for line in v_lines:
        x1, y1, x2, y2 = line[0][0], line[0][1], line[1][0], line[1][1]
        x1_ext, y1_ext, x2_ext, y2_ext = extend_line(x1, y1, x2, y2, buffer=30)

        #if not is_line_intersecting_bbox(x1_ext, y1_ext, x2_ext, y2_ext, filtered_bboxes):
        extended_linesV.append((x1_ext, y1_ext, x2_ext, y2_ext))

    def create_horizontal_bbox(x1, y1, x2, y2, padding=10):
        return (min(x1, x2) - padding, y1 - 5, max(x1, x2) + padding, y1 + 5)

# Function to create a bounding box for a vertical line with padding
    def create_vertical_bbox(x1, y1, x2, y2, padding=10):
        return (x1 - 5, min(y1, y2) - padding, x1 + 5, max(y1, y2) + padding)

    # Function to check if two bounding boxes intersect
    def do_bboxes_intersect(bbox1, bbox2):
        return not (bbox1[2] < bbox2[0] or bbox1[0] > bbox2[2] or
                    bbox1[3] < bbox2[1] or bbox1[1] > bbox2[3])

    # Function to merge intersecting horizontal lines
    def merge_horizontal_lines(lines, padding=10):
        merged_lines = []
        while lines:
            line1 = lines.pop(0)
            x1, y1, x2, y2 = line1
            bbox1 = create_horizontal_bbox(x1, y1, x2, y2, padding)
            merged = False

            for i, line2 in enumerate(lines):
                x3, y3, x4, y4 = line2
                bbox2 = create_horizontal_bbox(x3, y3, x4, y4, padding)

                if do_bboxes_intersect(bbox1, bbox2):
                    # Merge lines by taking min and max of x-coordinates
                    new_line = [min(x1, x2, x3, x4), y1, max(x1, x2, x3, x4), y1]
                    lines[i] = new_line
                    merged = True
                    break

            if not merged:
                merged_lines.append(line1)

        return merged_lines

    # Function to merge intersecting vertical lines
    def merge_vertical_lines(lines, padding=10):
        merged_lines = []
        while lines:
            line1 = lines.pop(0)
            x1, y1, x2, y2 = line1
            bbox1 = create_vertical_bbox(x1, y1, x2, y2, padding)
            merged = False

            for i, line2 in enumerate(lines):
                x3, y3, x4, y4 = line2
                bbox2 = create_vertical_bbox(x3, y3, x4, y4, padding)

                if do_bboxes_intersect(bbox1, bbox2):
                    # Merge lines by taking min and max of y-coordinates
                    new_line = [x1, min(y1, y2, y3, y4), x1, max(y1, y2, y3, y4)]
                    lines[i] = new_line
                    merged = True
                    break

            if not merged:
                merged_lines.append(line1)

        return merged_lines
    merged_horizontal_lines = merge_horizontal_lines(extended_linesH, padding=20)
    # Merge vertical lines
    merged_vertical_lines = merge_vertical_lines(extended_linesV, padding=20)

    # Combine the merged lines back
    all_merged_lines = merged_horizontal_lines + merged_vertical_lines
    bboxes = pd.read_csv('app/static/output.csv')
    bbox_df = bboxes[~bboxes['cls'].isin(['arrowL', 'arrowD', 'arrowR', 'arrowU', 'connection', 'scada'])]

    # Create a list to hold bounding boxes with their coordinates
    bounding_boxes = []
    for i, row in bbox_df.iterrows():
        x1, y1, x2, y2 = row['x1'], row['y1'], row['x2'], row['y2']
        name = f"{row['cls']}{row['count']}"
        bounding_boxes.append(((x1, y1), (x2, y2), name))


    lines = all_merged_lines

    # Create a new graph
    G = nx.Graph()

    intersection_counter = 1
    endpoint_counter = 1
    # Function to check if a point is inside a bounding box
    def point_in_bbox(point, bbox):
        (x1, y1), (x2, y2) = bbox
        px, py = point
        return x1 <= px <= x2 and y1 <= py <= y2

    # Function to get the center of a bounding box
    def bbox_center(bbox):
        (x1, y1), (x2, y2) = bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    # Function to check if two line segments intersect
    def intersect(line1, line2):
        x1, y1, x2, y2 = line1
        x3, y3, x4, y4 = line2
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if denom == 0:
            return False
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
        return 0 <= t <= 1 and 0 <= u <= 1

    def intersection_point(line1, line2):
        x1, y1, x2, y2 = line1
        x3, y3, x4, y4 = line2
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / denom
        py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / denom
        return int(px), int(py)

    for line1 in lines:
        x1, y1, x2, y2 = line1
        start_node = (x1, y1)
        end_node = (x2, y2)

        # Add initial nodes and edges with positions
        G.add_node(start_node, pos=start_node, type='line_endpoint')
        G.add_node(end_node, pos=end_node, type='line_endpoint')
        G.add_edge(start_node, end_node)

        for line2 in lines:
            if line1 != line2:
                if intersect(line1, line2):
                    x_int, y_int = intersection_point(line1, line2)
                    intersection_node = (x_int, y_int)

                    # Add intersection node and edges with positions
                    G.add_node(intersection_node, pos=intersection_node, type='intersection')
                    G.add_edge(start_node, intersection_node)
                    G.add_edge(end_node, intersection_node)
                    G.add_edge(intersection_node, (line2[0], line2[1]))
                    G.add_edge(intersection_node, (line2[2], line2[3]))

    # Update nodes to use bounding box centers if inside a bounding box
    def update_node_positions(G, bounding_boxes):
        for node in list(G.nodes()):
            node_pos = G.nodes[node]['pos']  # Get the position of the node
            for bbox in bounding_boxes:
                bbox_coords = bbox[:2]  # Extract the coordinate part of the bbox
                center = bbox_center(bbox_coords)
                name = bbox[2]  # Extract the name (label) part of the bbox
                if point_in_bbox(node_pos, bbox_coords):
                    G.add_node(name, pos=center, type='bbox')
                    for neighbor in list(G.neighbors(node)):
                        G.add_edge(name, neighbor)
                    G.remove_node(node)
                    break

    update_node_positions(G, bounding_boxes)
    img = cv2.imread('app/static/input.jpg')
    pos = nx.get_node_attributes(G, 'pos')

    node_labels = {node: node for node in G.nodes()}
    for node in pos:
        x, y = pos[node]
        pos[node] = (x, img.shape[0] - y)

    # Differentiate node colors based on their type

    fig, ax = plt.subplots()

# Display the image
    ax.imshow(cv2.flip(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), 0))

    node_colors = []
    for node in G.nodes():
        node_type = G.nodes[node].get('type', 'line_endpoint')
        if node_type == 'bbox':
            node_colors.append('g')  # Green for bbox nodes
        elif node_type == 'intersection':
            node_colors.append('b')  # Blue for intersection nodes
        else:
            node_colors.append('r')  # Red for line endpoint nodes

    nx.draw(G, pos, ax=ax, node_size=50, node_color=node_colors, labels=node_labels, font_size=6, edge_color='gray')

     

    def trace_component_connections(dfs_results):
        component_connections = {}

        def explore_node(component, node):
            if isinstance(node, str):
                # If the node is a string, it's a named component, so we connect it
                if component not in component_connections:
                    component_connections[component] = set()
                component_connections[component].add(node)
            elif node in dfs_results:
                # If the node is a tuple, we need to explore it further
                for next_node in dfs_results[node]:
                    explore_node(component, next_node)

        for component, connections in dfs_results.items():
            for node in connections:
                explore_node(component, node)

        return component_connections

    # Using the provided dfs_results
    df_comp = []

    for node in G.nodes():
    #print(node)
        if isinstance(node, str):

            dfs_results=nx.dfs_successors(G,node)
            component_connections = trace_component_connections(dfs_results)
            if node in component_connections and component_connections[node]:

                print(node," : ",component_connections[node])
                connections_str = ', '.join(component_connections[node])
                df_comp.append({'Component': node, 'Connected Components': connections_str})

    df = pd.DataFrame(df_comp)
     
    edges = []
    for _, row in df.iterrows():
        source = row['Component']
        targets = row['Connected Components'].split(', ')
        for target in targets:
            if source != target:  # Avoid self-loops
                edges.append((source, target))


    edges_df = pd.DataFrame(edges, columns=['Source', 'Target'])


    edges_df['Sorted'] = edges_df.apply(lambda x: tuple(sorted([x['Source'], x['Target']])), axis=1)

    edges_df = edges_df.drop_duplicates(subset='Sorted').drop(columns='Sorted')

    print(edges_df)
    return edges_df



"""----------------------------------------------------------------------""" 
"""POST PROCESSING"""
"""----------------------------------------------------------------------""" 
def plot_model3(final_bboxes, image, class_names):
    

    for bbox in final_bboxes:
        x1, y1, x2, y2, score, cls = bbox
        class_name = class_names[int(cls)]
        color = (0, 128, 0, 255)
        if (int(x2)-int(x1))*(int(y2)-int(y1)) <= 30000:
            cv2.rectangle(image, (int(x1), int(y1)), (int(x2), int(y2)), color, 6)
            # cv2.putText(image, f"{class_name}", (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 2, color, 2)
    return image

 


def plot_model2(final_bboxes, image, class_names):
    

    for bbox in final_bboxes:
        x1, y1, x2, y2, score, cls = bbox
        class_name = class_names[int(cls)]
        color =  (128, 0, 0, 255)
        cv2.rectangle(image, (int(x1), int(y1)), (int(x2), int(y2)), color, 6)
        #cv2.putText(image, f"{class_name}", (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 2, color, 2)
    
    return image


def plot_model1(final_bboxes, image, class_names):
    for bbox in final_bboxes:
        x1, y1, x2, y2, score, cls = bbox
        class_name = class_names[int(cls)]
        color =  (0, 0, 255, 255) # Default color
        cv2.rectangle(image, (int(x1), int(y1)), (int(x2), int(y2)), color, 6)
        #cv2.putText(image, f"{class_name}", (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 2, color, 2)
    return image

def plot_lines(filtered_horizontal_lines, filtered_vertical_lines, image):
    for start, end in filtered_horizontal_lines:
        x1, y1 = start
        x2, y2 = end
        cv2.line(image, (x1, y1), (x2, y2),(42, 42, 165, 255), 8)  

    for start, end in filtered_vertical_lines:
        x1, y1 = start
        x2, y2 = end
        cv2.line(image, (x1, y1), (x2, y2), (42, 42, 165, 255), 8)   

    return image