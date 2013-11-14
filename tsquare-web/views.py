# Create your views here.

from django.shortcuts import render,render_to_response,redirect
from tsquare.core import TSquareAPI, TSquareAuthException
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from models import *
import urllib
import requests
import os
import pdb

dirname, filename = os.path.split(os.path.abspath(__file__))
GITHUB_BASE_AUTH_URL = 'https://github.com/login/oauth/authorize'
GITHUB_AUTH_EXCHANGE = 'https://github.com/login/oauth/access_token'
GOOGLE_BASE_AUTH_URL = 'https://accounts.google.com/o/oauth2/auth'
GOOGLE_EXCHANGE_REDIRECT_URI = 'http://tsquare-webapp-temp.herokuapp.com/google_login_exchange'
GOOGLE_OAUTH_TOKEN_URL = "https://accounts.google.com/o/oauth2/token"

def tlogin(request):
        if(request.method == 'POST'):
            username = request.POST['username']
            password = request.POST['password']
            try:
                tsapi = TSquareAPI(username, password)
                request.session['tsapi'] = tsapi
                request.session['courses'] = tsapi.get_sites()
                print request.session['courses']
            except TSquareAuthException:
                return render(request,'login.html',{'login_failed':'Invalid username or password.'})
            try:
                user = User.objects.get(username=username)
                user = authenticate(username=username, password=password)
                if user is not None:
                    login(request, user)
                    return redirect('/home/')
                else:
                    return render(request,'login.html')
            except User.DoesNotExist:
                # get username and email from tsapi. leave password blank
                user = User.objects.create_user(username, tsapi.get_user_info().email, password)
                profile = UserProfile(user=user)
                profile.save()
                user = User.objects.get(username=username)
                ua = authenticate(username=username,password=password)
                if ua is not None:
                    login(request,ua)
                    return redirect('/home/')
                else:
                    print 'new user created auth failed...'
        return render(request,'login.html')

def tlogout(request):
	logout(request)
	return redirect('/')

def index(request):
	return render_to_response('index.html')

@login_required
def home(request):
        tsapi = request.session['tsapi']
        user = tsapi.get_user_info()
        return render_to_response('home.html',{'userinfo':user})

@login_required
def profile(request):
	return render_to_response('profile.html')

@login_required
def resources(request):
	return render_to_response('resources.html')

@login_required
def gradebook(request):
	return render_to_response('gradebook.html')

@login_required
def github_login(request):
        profile = UserProfile.objects.get(user_id=request.user.id)
        if len(profile.github_access_token) != 0:
            return redirect('/services?done=already&service=GitHub')
        f = open(dirname+'/github_config.txt','r')
        lines = f.readlines()
        f.close()
        params = {'client_id':lines[0].strip('\n')} # add client id here
        url = GITHUB_BASE_AUTH_URL+"?"+urllib.urlencode(params)
        return redirect(url)

@login_required
def github_login_exchange(request):
        f = open(dirname+'/github_config.txt','r')
        lines = f.readlines()
        f.close()
        params = {
            # add client id and secret here
            'client_id':lines[0].strip('\n'),
            'client_secret':lines[1].strip('\n'),
            'code':request.GET['code']
        }
        access_token = requests.post(GITHUB_AUTH_EXCHANGE,data=params)
        profile = UserProfile.objects.get(user_id=request.user.id)
        profile.github_access_token = access_token.text
        profile.save()
        return redirect('/services?done=new&service=GitHub')

@login_required
def select_github_repos(request):
	profile = UserProfile.objects.get(user_id=request.user.id)
	if len(profile.github_access_token) == 0:
		return redirect('/services')
	return redirect('https://api.github.com/user/repos?'+profile.github_access_token)

# https://developers.google.com/accounts/docs/OAuth2Login
@login_required
def google_login(request):
        profile = UserProfile.objects.get(user_id=request.user.id)
        if len(profile.gdrive_access_token) != 0:
            return redirect('/services?done=already&service=Google Drive')
        f = open(dirname+'/google_config.txt','r')
        lines = f.readlines()
        f.close()
        params = {
            'client_id':lines[0].strip('\n'),
            'response_type':'code',
            'scope':'https://www.googleapis.com/auth/drive',
            'redirect_uri':GOOGLE_EXCHANGE_REDIRECT_URI
        }
        return redirect(GOOGLE_BASE_AUTH_URL+"?"+urllib.urlencode(params))

@login_required
def google_login_exchange(request):
        code = request.GET['code']
        f = open(dirname+'/google_config.txt','r')
        lines = f.readlines()
        f.close()
        params = {
            'client_id':lines[0].strip('\n'),
            'client_secret':lines[1].strip('\n'),
            'code':code,
            'redirect_uri':GOOGLE_EXCHANGE_REDIRECT_URI,
            'grant_type':'authorization_code'
        }
        t = requests.post(GOOGLE_OAUTH_TOKEN_URL,data=params)
        profile = UserProfile.objects.get(user_id=request.user.id)
        profile.gdrive_access_token = t.json()['access_token']
        profile.save()
        return redirect('/services?done=new&service=Google Drive')

@login_required
def gdrive_select(request):
    pass

@login_required
def external_services(request):
    params = {}
    if 'done' in request.GET:
        if request.GET['done'] == 'already':
            params['notice_already'] = 'You have already integrated your account with '+request.GET['service']
        else:
            params['notice_new'] = 'You have successfully integrated your account with '+request.GET['service']+'!'
    return render(request,'external_services.html',params)

@login_required
def profile(request):
	return render(request,'profile.html')

@login_required
def sites(request):
        tsapi = request.session['tsapi']
        sites = tsapi.get_sites()
        return render(request,'sites.html',{'sites':sites})

# example view that gets first site instead of using site_id param
@login_required
def assignments(request):
    tsapi = request.session['tsapi']
    sites = tsapi.get_sites() # get sites from user class?
    #pdb.set_trace()
    site = sites[17]
    assignments = tsapi.get_assignments(site)
    return render(request,'assignments.html',{'assignments':assignments})

@login_required
def course_info(request):
	return render_to_response('course_info.html')

@login_required
def announcements(request):
	return render_to_response('announcements.html')

@login_required
def wiki(request):
	return render_to_response('wiki.html')

@login_required
def help(request):
	return render_to_response('help.html')

@login_required
def assignment_detail(request):
	return render_to_response('assignment_detail.html')
