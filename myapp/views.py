from django.shortcuts import render, redirect, get_object_or_404
import sys
import os,glob
import argparse
import requests
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from .models import itemsaved,wear_mywear
from matplotlib import pyplot as plt
from .models import lotteData ,CartItem # 무신사 데이터 ,장바구니
from .models import CustomUser
from django.contrib.auth import login, authenticate
import cv2
from .forms import  UserForm
from django.http import HttpResponse
from bs4 import BeautifulSoup as bs
from urllib.request import urlopen,urlretrieve
from urllib.parse import quote_plus
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger




#날씨
# Create your views here.

def base(request):
    users = CustomUser.objects.all()
    return render(request, 'myapp/base.html') 

def main(request):
    if not request.user.is_active:
        return redirect('signin')
    else:
        users = CustomUser.objects.all()
        url = 'http://api.openweathermap.org/data/2.5/weather?q={}&units=imperial&appid=1acc16a96aa8764e33997f3c2ac1a09c'
        city = 'busan'
        city_weather = requests.get(url.format(city)).json() #request the API data and convert the JSON to Python data types
        weather = {
            'city' : city,
            'temperature' : round((city_weather['main']['temp'] - 32)/1.8,1),
            'description' : city_weather['weather'][0]['description'],
            'icon' : city_weather['weather'][0]['icon']
        }
        context = {'weather' : weather,
        'users': users}
        
        return render(request, 'myapp/main2.html',context)
    
    


def signin(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username = username, password = password)

        if user is not None:
            login(request, user)
            return redirect('main')
        else:
            return render(request, 'myapp/login.html')
    else:
        return render(request, 'myapp/login.html')

def signup(request):
    if request.method == "POST":
        form = UserForm(request.POST)
        if form.is_valid():
            new_user = CustomUser.objects.create_user(username=form.cleaned_data['username'],
            password = form.cleaned_data['password'],
            name = form.cleaned_data['name'],
            address = form.cleaned_data['address'],
            phone_number = form.cleaned_data['phone_number'],
            gender = form.cleaned_data['gender'])
            login(request, new_user)
            return redirect('main')
    else:
        form = UserForm()
        return render(request, 'myapp/signup.html', {'form': form})


def logout(request):
    auth.logout(request)
    return redirect('main')

def lotte_Data(searchtitle,detail_url,lotte_path,lotte_image_name,M_title,M_price,product_dir):
    lotte = lotteData()
    lotte.search_lotte =searchtitle
    lotte.lotteUrl = detail_url
    image_url = 'images/'+product_dir+lotte_image_name
    lotte.lotteImage = image_url
    lotte.lotteName = M_title
    lotte.lottePrice = M_price
    lotte.save()
    

def crowling(request):
    return render(request, 'myapp/crowling.html' )
        

def add_cart(request, product_pk):
	# 상품을 담기 위해 해당 상품 객체를 product 변수에 할당
    product = lotteData.objects.get(pk=product_pk)

    try:
    	# 장바구니는 user 를 FK 로 참조하기 때문에 save() 를 하기 위해 user 가 누구인지도 알아야 함
        cart = CartItem.objects.get(product__id=product.pk, user__id=request.user.pk)
        if cart:
            if cart.product.lotteName == product.lotteName:
                cart.quantity += 1
                cart.save()
    except CartItem.DoesNotExist:
        user = CustomUser.objects.get(pk=request.user.pk)
        cart = CartItem(
            user=user,
            product=product,
            quantity=1,
        )
        cart.save()
    return redirect('my_cart')
     
def delete_cart_item(request, product_pk):
    
    cart_item = CartItem.objects.filter(product__id=product_pk)
    product = lotteData.objects.get(pk=product_pk)
    cart_item.delete()
    return redirect('my_cart')
    
    

#각 유저의 장바구니
def my_cart(request):
    
    cart_item = CartItem.objects.filter(user__id=request.user.pk)
    # 장바구니에 담긴 상품의 총 합계 가격
    # total_price = 0
    # for loop 를 순회하여 각 상품 * 수량을 total_price 에 담는다
    # for each_total in cart_item:
    #     total_price += each_total.product.price * each_total.quantity
    if cart_item is not None:
        context = {
        	# 없으면 없는대로 빈 conext 를 템플릿 변수에서 사용
            'cart_item': cart_item,
            # 'total_price': total_price,
        }
        return render(request, 'myapp/cart.html', {'cart_item': cart_item,})
    return redirect('my_cart')



def inform(request):
    username = request.user.name
    password = request.user.password
    phone_number = request.user.phone_number
    gender = request.user.gender
    address = request.user.address
    my_inform = {
                 'username':username,
                 'password':password,
                 'phone_number':phone_number,
                 'gender':gender,
                 'address':address,    
                }
    return render(request, 'myapp/inform.html',my_inform)

def introduce(request):
    return render(request, 'myapp/introduce.html')


def mypage(request):
    
    return render(request, 'myapp/mypage.html')

def mypage_drag(request):
    cart_item = CartItem.objects.all().order_by('-id')
    return render(request, 'myapp/mypage_drag.html',{'cart_item': cart_item})

def draganddrop(request):
    cart_item = CartItem.objects.all().order_by('-id')
    return render(request, 'myapp/draganddrop.html',{'cart_item': cart_item})


