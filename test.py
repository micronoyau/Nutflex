import cv2
import numpy as np

img = cv2.imread('lena.jpg',0)
img_float = img/255
img_dct = cv2.dct(img_float)
img_dct[-1,-1] = 0
print(img_dct.shape)
img_final = cv2.idct(img_dct) * 255
cv2.imwrite('test_lena.jpg', img_final)
