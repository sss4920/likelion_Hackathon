from django.db import models

# Create your models here.
class lotteData(models.Model):
    search_lotte = models.TextField()#검색어 필드
    lotteImage = models.ImageField(upload_to='images/', blank=True)# 상품 이미지
    lotteUrl = models.TextField()# 상품 이미지 URL
    lotteName = models.TextField()# 상품 이름
    lottePrice = models.TextField()# 상품 가격