import io
import picamera
from datetime import datetime
from PIL import Image

# Circular camera loop: https://picamera.readthedocs.io/en/release-1.13/recipes1.html#recording-to-a-circular-stream

'''

PiCameraCircularIO works as a circular buffer, ensuring a continuous
stream with no wasted memory. In detecting motion, we check the frames
recorded within one second of each other. The main while loop waits 1
second before continuing recording.

From picamera docs in regards to stream.seek():
SEEK_SET or 0 - start of stream
SEEK_CUR or 1 - current location in stream
SEEK_END or 2 - end of stream

'''

# Constants
ALPHA = 15 # How much a pixel changes to mark as changed
THRESHOLD = 175 # Number of pixels to change before recording
STREAM_LENGTH = 5 # Length of buffer circle stream (seconds)

# Camera initialization
camera = picamera.PiCamera()

WIDTH, HEIGHT = camera.resolution
FRAMERATE = camera.framerate

stream = picamera.PiCameraCircularIO(camera, seconds=STREAM_LENGTH) # Record STREAM_LENGTH second loop
# Immediately begin recording
camera.start_recording(stream, format='h264')

print("Initializing recording !!! picamera @ " + str(WIDTH) + "x" + str(HEIGHT) + " " + str(FRAMERATE) + " fps")

# file_name -> datetime
# for when motion detected -> write to new file
filename = ""

# recording flag
# for when to know to start new recording
recording = False

# reference image for motion detecting
reference_image = None

def compare_images(buffer_0, buffer_1):
    num_pixels = 0
    # Compare two images
    for x in range(0, WIDTH):
        for y in range(0, HEIGHT):
            # [x,y] = pixel location, [1] is green channel
            difference = abs(buffer_0[x,y][1] - buffer_1[x,y][1])
            if (difference > ALPHA):
                num_pixels += 1
        if (num_pixels >= THRESHOLD): # Time saving in image detection
            break

    return num_pixels

def motion_detected():
    global reference_image, recording, filename

    image_stream = io.BytesIO()
    camera.capture(image_stream, format='jpeg', use_video_port=True)
    image_stream.seek(0)
    
    if reference_image is None:
        reference_image = Image.open(image_stream)
        return False
    else:
        current_image = Image.open(image_stream)
        print("~~comparing images")
        num_pixels = compare_images(reference_image.load(), current_image.load())

        # Swap images
        reference_image = current_image

        # Motion detected
        if (num_pixels >= THRESHOLD and not recording): # begin saving recording
            time = datetime.now()
            # TESTING PURPOSES
            filename = "%02d-%02d-%04d--%02d-%02d-%02d.h264" % (time.day, time.month, time.year, time.hour, time.minute, time.second)
            #filename = "output.h264"
            return True
        elif (num_pixels >= THRESHOLD and recording): # continue saving recording
            return True
        else: # end save of recording
            return False

try:
    while True:
        camera.wait_recording(1)
        print("~")
        if motion_detected():
            recording = True
            print("picamera: Motion detected! @motion_detected()")

            ######

            camera.split_recording(filename)    
            stream.copy_to(filename, seconds=STREAM_LENGTH) # Record to file first 5 seconds before motion
            stream.clear()

            while motion_detected():
                camera.wait_recording(1)
                
            print("picamera: Motion stopped, recording saved @" + filename)
            recording = False
            camera.split_recording(stream)
            
finally:
    camera.stop_recording()
