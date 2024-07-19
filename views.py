
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.conf import settings
from .models import *
from django.views.decorators import gzip
from django.http import StreamingHttpResponse
import cv2
import os
import datetime
import threading



HTTP_URL = 'http://mmb.aa1.netvolante.jp:1025/mjpg/video.mjpg?resolution=640x360&compression=50'

class VideoCamera(object):
    def __init__(self, url):
        self.video = cv2.VideoCapture(url)
        self.video.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.video.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer size
        self.video.set(cv2.CAP_PROP_FPS, 30)  # Set frame rate (if supported by the stream)
        (self.grabbed, self.frame) = self.video.read()
        if not self.grabbed:
            raise ValueError(f"Unable to open video source {url}")
        self.lock = threading.Lock()
        threading.Thread(target=self.update, args=()).start()

    def __del__(self):
        if self.video.isOpened():
           self.video.release()

    def get_frame(self):
        with self.lock:
            if not self.grabbed:
                return None
        _, jpeg = cv2.imencode('.jpg', self.frame)
        return jpeg.tobytes()

    def update(self):
        while True:
            try:
                with self.lock:
                   (self.grabbed, self.frame) = self.video.read()
                if not self.grabbed:
                    break
            except Exception as e:
                print (f"Error reading frame: {e}")
                break
        

def gen(camera):
    while True:
        frame = camera.get_frame()
        if frame is not None:
             yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

@gzip.gzip_page
def Home(request):
    try:
        cam = VideoCamera(HTTP_URL)
        return StreamingHttpResponse(gen(cam), content_type="multipart/x-mixed-replace;boundary=frame")
    except Exception as e:
       return render(request, 'index.html', {'error': str(e)})

#to capture video class

def capture_image(request):
    if request.method == 'POST':
        try:
            cam = VideoCamera(HTTP_URL)
            frame = cam.get_frame()
            if frame is None:
                raise ValueError("Could not read frame from the camera.")

            del cam

            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            folder_path = getattr(settings, 'CAPTURE_FOLDER', 'captured_images')

            if not os.path.exists(folder_path):
                os.makedirs(folder_path)

            image_path = os.path.join(folder_path, f'image_{timestamp}.jpg')

            with open(image_path, 'wb') as f:
                f.write(frame)

            return JsonResponse({'message': f'Image captured and saved as {image_path}'})
        except Exception as e:
            return JsonResponse({'message': f'An error occurred: {str(e)}'}, status=500)
    
    return JsonResponse({'message': 'Invalid request'}, status=400)