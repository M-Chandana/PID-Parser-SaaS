from django.shortcuts import redirect, render
from .forms import MyFileForm
from .models import MyFileUpload
from django.contrib import messages
from django.urls import path
import os
import sys
#path=sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../AI-service/src')))
print("Path added to sys.path:", os.path.abspath(os.path.join(os.path.dirname(__file__), '../../AI-service/src')))
path=os.path.abspath(os.path.join(os.path.dirname(__file__), '../../AI-service/src'))
# Import detection module
 
import importlib.util

spec = importlib.util.spec_from_file_location("detection", path+"\detection.py")
detection = importlib.util.module_from_spec(spec)
spec.loader.exec_module(detection)

import cv2
from PIL import Image, ImageDraw, ImageOps
import numpy as np
from datetime import datetime
from django.http import JsonResponse
from PIL import Image

# Create your views here.
def login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        if username == 'admin' and password == 'demodemo':
            return redirect('home')
        else:
            return render(request, 'login.html', {'error': 'Invalid credentials'})
    return render(request, 'login.html')
def home(request):
    mydata=MyFileUpload.objects.all()    
    myform=MyFileForm()
    latest_file_path = mydata.last().my_file.path if mydata else None

    
    if mydata!='':
        context={'form':myform,'mydata':mydata}
        return render(request,'index.html',context)
    else:
        context={'form':myform}
        return render(request,"index.html",context)

def uploadfile(request):
    if request.method=="POST":
        myform=MyFileForm(request.POST,request.FILES)        
        if myform.is_valid():
            MyFileName = request.POST.get('file_name') 
            MyFile = request.FILES.get('file')

            exists=MyFileUpload.objects.filter(my_file=MyFile).exists()

            if exists:
                messages.error(request,'The file %s is already exists...!!!'% MyFile)
            else:
                MyFileUpload.objects.create(file_name=MyFileName,my_file=MyFile).save()
                messages.success(request,"File uploaded successfully.")
        return redirect("home")

def delete_file(request,id):
    mydata=MyFileUpload.objects.get(id=id)    
    mydata.delete()    
    os.remove(mydata.my_file.path)
    messages.success(request,'File deleted successfully.')  
    return redirect('home')

def detect_components(request):
     
    file_path= file_path = request.POST.get('file_path')
    image = detection.pdf_to_images(file_path)
    image_path = "pid_parser/input.jpg"
    
    image = cv2.imread(image_path)
    print(image.shape)
     
    cv2.imwrite("app/static/input.jpg",image)
    height, width, _ = image.shape

# Set last 1000 rows to white
    if height > 500:
        image[-500:] = [255, 255, 255]  # Assuming the image is in RGB format

# Define the size of the rectangle
    rect_size = 1500

# Define the bottom-right corner of the rectangle
    start_x = max(width - rect_size, 0)
    start_y = max(height - rect_size, 0)

# Draw the white rectangle
    image[start_y:start_y + rect_size, start_x:start_x + rect_size] = [255, 255, 255]
    #Running the three models
    df1,df2,df3,cn1,cn2,cn3 = detection.run_model_predictions(image)

    strip_width = 370

    # Define the right edge of the left strip
    end_x_left = min(strip_width, width)

    # Define the starting point of the right strip
    start_x_right = max(width - strip_width-40, 0)

    # Set the leftmost vertical strip to white
    image[:, :end_x_left] = [255, 255, 255]    

    # Set the rightmost vertical strip to white
    image[:, start_x_right:] = [255, 255, 255]  # Assuming the image is in BGR format

    h_lines,v_lines = detection.detect_lines(image)
    dh_lines,dv_lines = detection.detect_dashed_lines(image,h_lines,v_lines)
    dashed_edges_df = detection.generate_graph_dashed_lines(dh_lines,dv_lines)
    #Running the graph generation code 
    detection.generate_graph(h_lines,v_lines,dashed_edges_df)

    #creating a blank png image to draw the bboxes for overlapping and display
    height,width,c = image.shape
    plt_img=np.zeros((height, width, 4), dtype=np.uint8)
    result1=detection.plot_model1(df1,plt_img.copy(),cn1)
    result2=detection.plot_model2(df2,plt_img.copy(),cn2)
    result3=detection.plot_model3(df3,plt_img.copy(),cn3)
    result4=detection.plot_lines(h_lines,v_lines,plt_img.copy())

    #saving them in the static folder 
    cv2.imwrite("app/static/result_one.png",result1)
    cv2.imwrite("app/static/result_two.png",result2)
    cv2.imwrite("app/static/result_three.png",result3)
    cv2.imwrite("app/static/result_four.png",result4)
    
    #detection.add_text_column_to_csv('output.csv', 'app/static/input.jpg', 'app/static/output.csv')
    image_url='app/static/input.jpg'
    image_version = datetime.now().timestamp()

    return render(request, 'detect_components.html', {
        'image_url': image_url,
        'image_version': image_version
    })
 
def about_models(request):
    return render(request, 'about_models.html')

def graph_view(request):
    return render(request, 'g.html') 