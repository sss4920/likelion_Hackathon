from django.shortcuts import render
import os, re
import numpy as np
import cv2
from PIL import Image
import matplotlib.pyplot as plt

def imagecutter(request): #모든 크롤링 데이터에 대해 적용해야함. 이미지 전처리 함수를 만들엇음
    step = 0
    mouse_is_pressing = False


    def distanceBetweenTwoPoints(point1, point2):
        
        x1,y1 = point1
        x2,y2 = point2
        
        return int(np.sqrt(pow(x1 - x2, 2) + pow(y1 - y2, 2)))


    def mouse_callback(event,x,y,flags,param):
        
        global mouse_is_pressing,points

        if step != 1:
            return

        if event == cv2.EVENT_MOUSEMOVE: 
            if mouse_is_pressing == True: 

                for i,point in enumerate(points):
                    if distanceBetweenTwoPoints((x,y), point) < 15:
                        points[i][0] = x
                        points[i][1] = y
                        break    
            
        elif event == cv2.EVENT_LBUTTONDOWN:
        
            for point in points:
                if distanceBetweenTwoPoints((x,y), point) < 10:
                    mouse_is_pressing = True
                    break

        elif event == cv2.EVENT_LBUTTONUP: 

            mouse_is_pressing = False


    def angle_between(v0, v1):
        
        angle = np.math.atan2(np.linalg.det([v0,v1]),np.dot(v0,v1))

        return np.degrees(angle)


    def sort_points(points):

        points = points.astype(np.float32)

        rect = np.zeros((4, 2), dtype = "float32")
    
        # sort : top left, top right, bottom right, bottom left
        s = points.sum(axis = 1)
        min_index = np.argmin(s)
        rect[0] = points[min_index]
        points = np.delete(points, min_index, axis = 0)

        s = points.sum(axis = 1)
        max_index = np.argmax(s)
        rect[2] = points[max_index]
        points = np.delete(points, max_index, axis = 0)

        v0 = points[0] - rect[0]
        v1 = points[1] - rect[0]

        angle = angle_between(v0, v1)

        if angle < 0:
            rect[1] = points[1]
            rect[3] = points[0]
        else:
            rect[1] = points[0]
            rect[3] = points[1]
    
        return rect


    def transform(img_input, points):

        points = sort_points(points)
        topLeft, topRight, bottomRight, bottomLeft = points
    
        topWidth = distanceBetweenTwoPoints(bottomLeft, bottomRight)
        bottomWidth = distanceBetweenTwoPoints(topLeft, topRight)
        maxWidth = max(int(topWidth), int(bottomWidth))
    
        leftHeight = distanceBetweenTwoPoints(topLeft, bottomLeft)
        rightHeight = distanceBetweenTwoPoints(topRight, bottomRight)
        maxHeight = max(int(leftHeight), int(rightHeight))
    
        # top left, top right, bottom right, bottom left
        dst = np.array([[0, 0],[maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],[0, maxHeight - 1]], dtype = "float32")
    

        H = cv2.getPerspectiveTransform(points, dst)
        img_warped = cv2.warpPerspective(img_input, H, (maxWidth, maxHeight))
    
        return img_warped


    def findMaxArea(contours):
        
        max_contour = None
        max_area = -1


        for contour in contours:
            area = cv2.contourArea(contour)

            x,y,w,h = cv2.boundingRect(contour)

            if area > max_area:
                max_area = area
                max_contour = contour


        return max_area, max_contour


    def process(img_input, debug):

        points = []
        height,width =img_input.shape[:2]

        # Step 1    
        img_mask = np.zeros(img_input.shape[:2],np.uint8)

        bgdModel = np.zeros((1,65),np.float64)
        fgdModel = np.zeros((1,65),np.float64)

        rect = (10,10,width-30,height-30)
        cv2.grabCut(img_input, img_mask, rect, bgdModel,fgdModel,3,cv2.GC_INIT_WITH_RECT)
        img_mask = np.where((img_mask==2)|(img_mask==0), 0, 1).astype('uint8')
        img = img_input*img_mask[:,:,np.newaxis]

        background = img_input - img

        background[np.where((background >= [0,0,0]).all(axis = 2))] = [0,0,0]

        img_grabcut = background + img

        if debug:
            cv2.imshow('grabCut', img_grabcut)


        # Step 2
        img_gray = cv2.cvtColor(img_grabcut, cv2.COLOR_BGR2GRAY)
        img_canny = cv2.Canny(img_gray, 30, 90)

        if debug:
            cv2.imshow('Canny', img_canny)


        # Step 3
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        img_canny = cv2.morphologyEx(img_canny, cv2.MORPH_CLOSE, kernel, 1)

        if debug:
            cv2.imshow('morphology', img_canny)


        # Step 4
        contours, hierarchy = cv2.findContours(img_canny, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        max_area, max_contour = findMaxArea(contours) 
        if max_area < 0:
            return points
        
        if debug:
            img_contour = img_input.copy()
            cv2.drawContours(img_contour, [max_contour], 0, (0, 0, 255), 3)
            cv2.imshow('Contour', img_contour)


        # Step 5
        max_contour = cv2.approxPolyDP(max_contour,0.02*cv2.arcLength(max_contour,True),True)
        hull = cv2.convexHull(max_contour)

        if debug:
            img_convexhull = img_input.copy()
            cv2.drawContours(img_convexhull, [hull], 0, (255,255,0), 5)
            cv2.imshow('convexHull', img_convexhull)


        # Step 6
        size = len(max_contour)

        if size == 4:
            for c in hull:
                points.append(tuple(c[0].tolist()))
                points=np.array(points)
        else:
            rect = cv2.minAreaRect(hull)
            box = cv2.boxPoints(rect)
            points = np.int0(box.tolist())

        found = False
        for p in points:
            if p[0] < 0 or p[0] > width-1 or p[1] < 0 or p[1] > height -1:
                found = True  
                break

        if found:
            points = np.array([[10,10], [width-11, 10], [width-11, height-11], [10, height-11]])

        return points
        

    def channel_cut(image):
        # 3-channel image (no transparency)
        if image.shape[2] == 3:
            b,g,r = cv2.split(image)
            image[:,:,0] = r
            image[:,:,1] = g
            image[:,:,2] = b
        # 4-channel image (with transparency)
        elif image.shape[2] == 4:
            b,g,r,a = cv2.split(image)
            image[:,:,0] = r
            image[:,:,1] = g
            image[:,:,2] = b
        return image 


    image = plt.imread('imageprocess\image2.jpg') #os.walk로 이제 모든 애들 끌고오면 될듯
    pixels = np.array(image) # numpy 배열로 변환하기
    cut = channel_cut(pixels)
    # img = Image.open('sss.jpg')# 이미지 데이터 열기
    # img = img.convert('RGB')
    # pixel_data = swapped.getdata() #픽셀데이터 가져오기
    pixels = np.array(cut) # numpy 배열로 변환하기
    img_input = cv2.cvtColor(pixels, cv2.COLOR_RGB2BGR)
    height, width = img_input.shape[:2]

    points = process(img_input, debug=False)

    size = len(points)

    if size > 0:
        cv2.namedWindow('input')
        cv2.setMouseCallback("input", mouse_callback, 0);  

        step = 1


        while True:

            img_result = img_input.copy()
            for point in points:
                cv2.circle(img_result, tuple(point), 10, (255,0,0), 3 )    
            cv2.imshow('input', img_result)

            key = cv2.waitKey(1)
            if key == 32:
                break


        img_final = transform(img_input, points )


        cv2.imshow('input', img_result)
        cv2.imshow('result', img_final )

    else:
        cv2.imshow('input', img_input)

        cv2.waitKey(0)

        cv2.destroyAllWindows()

def avhash(request):
    search_dir = "media/images/shoes"
    cache_dir = "imageprocess/imagecache/shoes"

    if not os.path.exists(cache_dir):
        os.mkdir(cache_dir)

    def average_hash(fname, size=16):
        fname2 = fname[len(search_dir):]
        #이미지 캐시하기
        print(fname2)
        cache_file = cache_dir + fname2.replace('\\', "_")+".csv"
        print(cache_file)
        if not os.path.exists(cache_file):
            img = Image.open(fname)
            img = img.convert('L').resize((size,size), Image.ANTIALIAS)
            pixels = np.array(img.getdata()).reshape((size,size))
            avg = pixels.mean()
            px = 1 * (pixels > avg)
            np.savetxt(cache_file, px , fmt ="%.0f", delimiter=",")
        else:
            px = np.loadtxt(cache_file, delimiter=",")
            
        return px

    # 해밍거리 구하기
    def hamming_dist(a,b):
        aa = a.reshape(1,-1)
        ab = b.reshape(1,-1)
        dist = (aa != ab).sum()
        return dist
    # 모든 폴더에 처리 적용하기
    def enum_all_files(path):
        for root, dirs, files in os.walk(path):
            for f in files:
                fname = os.path.join(root,f)
                if re.search(r'\.(jpg|jpeg|png)$', fname):
                    yield fname
    # 이미지 찾기                
    def find_image(fname, rate):
        src = average_hash(fname)
        for fname in enum_all_files(search_dir):
            dst = average_hash(fname)
            diff_r = hamming_dist(src, dst) / 256
            print("[check] ",fname)
            if diff_r < rate:
                yield (diff_r, fname)
    # 찾기
    srcfile = search_dir + "/신발(50).jpg" #지금은 search_dir에서 해당파일 찾고잇음 고쳐야됨
    print(srcfile)
    html =""
    sim = list(find_image(srcfile, 0.25))
    sim = sorted(sim, key=lambda x:x[0])
    for r, f in sim:
        print(r,">",f)
        s = '<div style="float:left;"><h3>[ 차이 : ' + str(r) + '-' + \
            os.path.basename(f) + ']</h3>'+\
            '<p><a href="'+f+'"><img src="' + f + '" width=400>'+\
            '</a></p></div>'
        html+= s
    html = """<html><head><meta charset="utf8"></head>
    <body><h3>원래 이미지 </h3><p>
    <img src = '{0}' width=400></p>{1}
    </body></html>""".format(srcfile, html)
    with open("./avhash-search-output.html","w", encoding="utf-8") as f:
        f.write(html)
    print("ok")