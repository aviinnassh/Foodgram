from django.shortcuts import render,redirect
from django.contrib.auth import authenticate,login,logout
from .models import *
import os
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings   
import math,random
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Follow, Like, Notification
from django.http import JsonResponse
from django.db.models import Q 
from .ml.recommender import get_recommendations
from django.core.paginator import Paginator
from django.core.cache import cache

def get_explore_count(q):
    count = cache.get(f'explore_count_{q}')
    if count is None:
        base_q = (
            Q(cuisine__icontains=q) | 
            Q(name__icontains=q) | 
            Q(category__icontains=q) |
            Q(ingredients__item__icontains=q) |
            Q(user__first_name__icontains=q) |
            Q(user__username__icontains=q)
        )
        count = Dish.objects.filter(base_q).distinct().count()
        cache.set(f'explore_count_{q}', count, 3600)
    return count



import pandas as pd

def get_dish_dataframe():
    dishes = Dish.objects.all()
    data = []

    for dish in dishes:
        ingredients = Ingredients.objects.filter(dish=dish)
        ing_list = " ".join([i.item for i in ingredients])

        data.append({
            'id': dish.id,
            'name': dish.name,
            'cuisine': dish.cuisine,
            'ingredients': ing_list
        })

    return pd.DataFrame(data)

def recommend_view(req, pid):
    if 'user' not in req.session:
        return redirect(shop_login)

    user = User.objects.get(username=req.session['user'])

    current_dish = None
    try:
        pid = int(pid)
        current_dish = Dish.objects.get(pk=pid)
    except (ValueError, Dish.DoesNotExist):
        pass

    # If arriving from sidebar button, preserve the seed to match perfectly; otherwise if direct refresh, regenerate seed
    if req.GET.get('from_sidebar'):
        req.session['kept_seed'] = True
        return redirect(f"/recommend/{pid}")
        
    if req.session.pop('kept_seed', False):
        # We just arrived from sidebar redirect, keep the seed exactly as is!
        pass
    else:
        # User manually reloaded/refreshed the recommend page directly, give them a fresh set of suggested dishes!
        req.session['recs_seed'] = random.randint(1, 10000)
        
    recs_seed = req.session.get('recs_seed', 42)

    # Mirror the exact interleaving and deterministic seed from userHome
    last_searched = req.session.get('last_searched', '')
    searched_dishes = []
    if last_searched:
        base_q = Q(cuisine__icontains=last_searched) | Q(name__icontains=last_searched) | Q(category__icontains=last_searched)
        searched_dishes = list(Dish.objects.filter(base_q, user__username='admin').order_by('-likes')[:16])
        
    liked_based_dishes = []
    if current_dish:
        try:
            recs = get_recommendations(current_dish.id, top_n=32)
            liked_based_dishes = [d for d in recs if d.user.username == 'admin'][:16]
        except Exception:
            pass
            
    new_dataset_dishes = list(Dish.objects.filter(user__username='admin').order_by('-id')[:16])

    combined_recs = []
    existing_ids_recs = set()
    
    for i in range(max(len(searched_dishes), len(liked_based_dishes), len(new_dataset_dishes))):
        if i < len(searched_dishes) and searched_dishes[i].id not in existing_ids_recs:
            combined_recs.append(searched_dishes[i])
            existing_ids_recs.add(searched_dishes[i].id)
        if i < len(liked_based_dishes) and liked_based_dishes[i].id not in existing_ids_recs:
            combined_recs.append(liked_based_dishes[i])
            existing_ids_recs.add(liked_based_dishes[i].id)
        if i < len(new_dataset_dishes) and new_dataset_dishes[i].id not in existing_ids_recs:
            combined_recs.append(new_dataset_dishes[i])
            existing_ids_recs.add(new_dataset_dishes[i].id)
            
    if combined_recs:
        r_gen = random.Random(recs_seed)
        r_gen.shuffle(combined_recs)
        
    if not combined_recs:
        fallback_dishes = list(Dish.objects.filter(user__username='admin').order_by('-likes')[:40])
        if fallback_dishes:
            r_gen = random.Random(recs_seed)
            r_gen.shuffle(fallback_dishes)
        combined_recs = fallback_dishes

    combined_recs = combined_recs[:40]

    for r in combined_recs:
        r.is_ai_recommended = True

    dish_ids = [d.pk for d in combined_recs]
    ingr = Ingredients.objects.filter(dish_id__in=dish_ids)
    cook = Cooking.objects.filter(dish_id__in=dish_ids)
    liked_dishes = set(Like.objects.filter(user=user).values_list('dish_id', flat=True))
    saved_dishes = set(Saved.objects.filter(user=user).values_list('dish_id', flat=True))
    unread_count = Notification.objects.filter(user=user, read=False).count()

    return render(req, 'recommend.html', {
        'recommended': combined_recs,
        'new_dataset': [],
        'current_dish': current_dish or (combined_recs[0] if combined_recs else None),
        'ingr': ingr,
        'cook': cook,
        'liked_dishes': liked_dishes,
        'saved_dishes': saved_dishes,
        'unread_count': unread_count
    })
# Create your views here.
import time   # ✅ add at top

def shop_login(req):
    if 'admin' in req.session:
        return redirect(adminHome)
    if 'user' in req.session:
        return redirect(userHome)

    if req.method == 'POST':

        # ---------------- LOGIN ----------------
        if 'uname' in req.POST and 'passwd' in req.POST:
            uname = req.POST['uname']
            password = req.POST['passwd']

            data = authenticate(username=uname, password=password)

            if data:
                login(req, data)  # This populates request.user
                if data.is_superuser:
                    req.session['admin'] = uname
                    return redirect(adminHome)
                else:
                    req.session['user'] = uname
                    return redirect(userHome)
            else:
                messages.warning(req, 'Invalid username or password.')
                return redirect(shop_login)

        # ---------------- SIGNUP + OTP ----------------
        elif 'name' in req.POST and 'email' in req.POST and 'passwd' in req.POST:
            name = req.POST['name']
            email = req.POST['email']
            password = req.POST['passwd']

            # Check existing user
            if User.objects.filter(email=email).exists():
                messages.error(req, "Email is already in use.")
                return redirect(shop_login)

            # Generate OTP
            otp = OTP(req)

            # Store in session
            req.session['name'] = name
            req.session['email'] = email
            req.session['password'] = password
            req.session['otp'] = otp
            req.session['otp_time'] = time.time()   # ✅ OTP expiry timer

            # Send Email
            send_mail(
                'Foodgram - OTP Verification',
                f"""Hello {name},

Welcome to Foodgram 🍽️

Your OTP for registration is: {otp}

⏳ This OTP is valid for 5 minutes.

If you did not request this, please ignore this email.

Thanks & Regards,  
Foodgram Team
""",
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False
            )

            messages.success(req, "OTP sent to your email.")
            return redirect("validate")

        else:
            return redirect(shop_login)

    return render(req, 'login.html')
    
def shp_logout(req):
    req.session.flush()          #delete session
    logout(req)
    return redirect(shop_login)
    
def OTP(req):
    digits = "0123456789"
    OTP = ""
    for i in range(6) :
        OTP += digits[math.floor(random.random() * 10)]
    return OTP


def validate(req):
    if req.method=='POST':
        uotp=req.POST['uotp']
        name = req.session.get('name')
        email = req.session.get('email')
        password = req.session.get('password')
        otp = req.session.get('otp')
        if uotp==otp:
            data=User.objects.create_user(first_name=name,email=email,password=password,username=email)
            data.save()
            messages.success(req, "OTP verified successfully. You can now log in.")
            return redirect(shop_login)
        else:
            messages.error(req, "Invalid OTP. Please try again.")
            return redirect("validate")
    else:
        return render(req,'validate.html')




# -----------------admin-----------------------------

def adminHome(req):
    if 'admin' in req.session:
        user=User.objects.get(username=req.session['admin'])
        dish_list=Dish.objects.order_by('-id')
        paginator = Paginator(dish_list, 50)
        page_number = req.GET.get('page')
        dish = paginator.get_page(page_number)
        total_dishes_count = paginator.count
        dish_ids = [d.pk for d in dish]
        ingr=Ingredients.objects.filter(dish_id__in=dish_ids)
        cook=Cooking.objects.filter(dish_id__in=dish_ids)
        liked_dishes = set(Like.objects.filter(user=user).values_list('dish_id', flat=True))
        saved_dishes = set(Saved.objects.filter(user=user).values_list('dish_id', flat=True))
        unread_count = Notification.objects.filter(user=user, read=False).count()
        return render(req,'admin/admin_home.html',{'dish':dish,'total_dishes_count':total_dishes_count,'ingr':ingr,'cook':cook,'liked_dishes':liked_dishes,'saved_dishes':saved_dishes,'unread_count':unread_count})
    else:
        return redirect(shop_login)
    
def adminDish(req,pid):
    if 'admin' in req.session:
        # user=User.objects.get(username=req.session['admin'])
        dish=Dish.objects.get(pk=pid)
        ingr=Ingredients.objects.filter(dish=dish)
        cook=Cooking.objects.filter(dish=dish)
        like=Like.objects.filter(dish=dish)
        save=Saved.objects.filter(dish=dish)
        # liked_dishes = [like.dish.pk for like in like if like.user.pk == user.pk]
        # saved_dishes = [save.dish.pk for save in save if save.user.pk == user.pk]
        return render(req,'admin/dish.html',{'data':dish,'ingr':ingr,'cook':cook,'like':like})
    else:
        return redirect(shop_login)

def reports(req):
    if 'admin' in req.session:
        # user=User.objects.get(username=req.session['admin'])
        data=Report.objects.all()[: : -1]
        return render(req,'admin/reports.html',{'data':data})
    else:
        return redirect(shop_login)

    
def viewUserAdmin(req,pid):
    if 'admin' in req.session:
        user1=User.objects.get(username=req.session['admin'])
        user=User.objects.get(pk=pid)
        post=Dish.objects.filter(user=user).count()
        dish_list=Dish.objects.filter(user=user).order_by('-id')
        paginator = Paginator(dish_list, 30)
        page_number = req.GET.get('page')
        dish = paginator.get_page(page_number)
        dish_ids = [d.pk for d in dish]
        ingr=Ingredients.objects.filter(dish_id__in=dish_ids)
        cook=Cooking.objects.filter(dish_id__in=dish_ids)
        liked_dishes = set(Like.objects.filter(user=user1).values_list('dish_id', flat=True))
        saved_dishes = set(Saved.objects.filter(user=user1).values_list('dish_id', flat=True))
        followers = (user.followers.all()).count()
        following = (user.following.all()).count()
        unread_count = Notification.objects.filter(user=user1, read=False).count()
        is_following =  Follow.objects.filter(follower=user1, following=user).exists()
        return render(req,'admin/viewUser.html',{'dish':dish,'ingr':ingr,'cook':cook,'liked_dishes':liked_dishes,'is_following':is_following,'user':user,'user1':user1,'post':post,'followers':followers,'following':following,'saved_dishes':saved_dishes,'unread_count':unread_count})
    else:
        return redirect(shop_login)

def removeReport(req,pid):
    data=Report.objects.get(dish=pid)
    # print(data)
    data.delete()
    return redirect(reports)


# -------------------user----------------------------

def home(req):
    qs = req.GET.urlencode()
    suffix = f"?{qs}" if qs else ""
    if 'admin' in req.session:
        return redirect(f"/adminHome{suffix}")
    if 'user' in req.session:
        return redirect(f"/userHome{suffix}")
    else:
        return redirect(shop_login)


def userHome(req):
    if 'user' in req.session:
        user=User.objects.get(username=req.session['user'])
        following_users = Follow.objects.filter(follower=user).values_list('following', flat=True)
        
        # Fetch latest posts mixing real users and newly added dataset
        real_dishes = list(Dish.objects.exclude(user__username='admin').select_related('user').order_by('-id')[:200])
        admin_dishes = list(Dish.objects.filter(user__username='admin').select_related('user').order_by('-id')[:200])
        
        # Generate new seed on pull-to-refresh
        if req.headers.get('X-Requested-With') == 'XMLHttpRequest' and not req.GET.get('page'):
            req.session['feed_seed'] = random.randint(1, 10000)
            req.session['recs_seed'] = random.randint(1, 10000)
            
        if 'recs_seed' not in req.session:
            req.session['recs_seed'] = random.randint(1, 10000)
            
        seed = req.session.get('feed_seed', 42)
        random.seed(seed)
        
        # Shuffle admin dishes for variety, but keep real dishes chronological (newest first)
        random.shuffle(admin_dishes)
        
        # Put real user dishes on top, followed by the shuffled admin dishes
        all_dishes = (real_dishes + admin_dishes)[:50]
        
        paginator = Paginator(all_dishes, 50)
        page_number = req.GET.get('page')
        dish_page = paginator.get_page(page_number)
        dish = list(dish_page)
        
        # Optimize: Fetch only what's needed for the current user
        liked_dishes_set = set(
            Like.objects.filter(user=user).values_list('dish_id', flat=True)
        )

        # Get actual AI recommendations based on user's behaviors (last searched and most liking)
        last_searched = req.session.get('last_searched', '')
        
        searched_dishes = []
        if last_searched:
            base_q = Q(cuisine__icontains=last_searched) | Q(name__icontains=last_searched) | Q(category__icontains=last_searched)
            searched_dishes = list(Dish.objects.filter(base_q, user__username='admin').order_by('-likes')[:16])
            
        liked_based_dishes = []
        latest_liked_id = None
        if liked_dishes_set:
            latest_liked_id = list(liked_dishes_set)[-1] if liked_dishes_set else None
            if latest_liked_id:
                try:
                    recs = get_recommendations(latest_liked_id, top_n=32)
                    liked_based_dishes = [d for d in recs if d.user.username == 'admin'][:16]
                except Exception:
                    pass
                    
        # ALSO add newest dataset recipes (admin dishes)
        new_dataset_dishes = list(Dish.objects.filter(user__username='admin').order_by('-id')[:16])

        combined_recs = []
        existing_ids_recs = set()
        
        for i in range(max(len(searched_dishes), len(liked_based_dishes), len(new_dataset_dishes))):
            if i < len(searched_dishes) and searched_dishes[i].id not in existing_ids_recs:
                combined_recs.append(searched_dishes[i])
                existing_ids_recs.add(searched_dishes[i].id)
            if i < len(liked_based_dishes) and liked_based_dishes[i].id not in existing_ids_recs:
                combined_recs.append(liked_based_dishes[i])
                existing_ids_recs.add(liked_based_dishes[i].id)
            if i < len(new_dataset_dishes) and new_dataset_dishes[i].id not in existing_ids_recs:
                combined_recs.append(new_dataset_dishes[i])
                existing_ids_recs.add(new_dataset_dishes[i].id)
                
        recs_seed = req.session.get('recs_seed', 42)
        if combined_recs:
            r_gen = random.Random(recs_seed)
            r_gen.shuffle(combined_recs)
        recommended_dishes = combined_recs[:4]

        if not recommended_dishes:
            # Fallback to top liked dishes if no recommendations available yet
            fallback_dishes = list(Dish.objects.filter(user__username='admin').order_by('-likes')[:20])
            if fallback_dishes:
                r_gen = random.Random(recs_seed)
                r_gen.shuffle(fallback_dishes)
            recommended_dishes = fallback_dishes[:4]
            latest_liked_id = recommended_dishes[0].id if recommended_dishes else 0
        else:
            if not latest_liked_id:
                latest_liked_id = recommended_dishes[0].id

        if len(dish) < 50:
            needed = 50 - len(dish)
            existing_ids = {d.id for d in dish}
            
            pad_dishes = [r for r in combined_recs if r.id not in existing_ids]
            
            if len(pad_dishes) < needed:
                exclude_ids = existing_ids.union({r.id for r in pad_dishes})
                more_fallbacks = list(Dish.objects.exclude(id__in=exclude_ids).order_by('-likes')[:needed - len(pad_dishes)])
                pad_dishes.extend(more_fallbacks)
                
            pad_dishes = pad_dishes[:needed]
            for p in pad_dishes:
                p.is_ai_recommended = True
            dish.extend(pad_dishes)
            
        saved_dishes_set = set(
            Saved.objects.filter(user=user).values_list('dish_id', flat=True)
        )
        
        # Fetch ingredients and cooking steps for dishes being displayed
        dish_ids = [d.pk for d in dish]
        ingr = Ingredients.objects.filter(dish_id__in=dish_ids)
        cook = Cooking.objects.filter(dish_id__in=dish_ids)
        
        unread_count = Notification.objects.filter(user=user, read=False).count()
        
        breakfast_count = get_explore_count('breakfast')
        lunch_count = get_explore_count('lunch')
        dinner_count = get_explore_count('dinner')
        desserts_count = get_explore_count('dessert')
        healthy_count = get_explore_count('healthy')

        return render(req,'home.html',{
            'dish': dish,
            'dish_page': dish_page,
            'ingr': ingr,
            'cook': cook,
            'liked_dishes': liked_dishes_set,
            'saved_dishes': saved_dishes_set,
            'unread_count': unread_count, 
            'recommended_dishes': recommended_dishes,
            'latest_liked_id': latest_liked_id,
            'breakfast_count': breakfast_count,
            'lunch_count': lunch_count,
            'dinner_count': dinner_count,
            'desserts_count': desserts_count,
            'healthy_count': healthy_count,
        })
    else:
        return redirect(shop_login)
def explore(req):
    if 'user' in req.session:
        user=User.objects.get(username=req.session['user'])
        
        q = req.GET.get('q')
        detected = req.GET.get('detected')
        searched_users = []
        if q:
            req.session['last_searched'] = q
            base_q = (
                Q(cuisine__icontains=q) | 
                Q(name__icontains=q) | 
                Q(category__icontains=q) |
                Q(ingredients__item__icontains=q) |
                Q(user__first_name__icontains=q) |
                Q(user__username__icontains=q)
            )
            real_dishes = list(Dish.objects.filter(base_q).exclude(user__username='admin').distinct().order_by('-id'))
            admin_dishes = list(Dish.objects.filter(base_q, user__username='admin').distinct().order_by('-id'))
            dish_list = real_dishes + admin_dishes
            
            searched_users = list(User.objects.filter(Q(first_name__icontains=q) | Q(username__icontains=q)).exclude(id=user.id).distinct()[:20])
            # DO NOT shuffle search results, so relevance and 'Newest First' sorting are preserved properly.
        else:
            real_dishes = list(Dish.objects.exclude(user__username='admin').order_by('-id'))
            admin_dishes = list(Dish.objects.filter(user__username='admin').order_by('-id'))
            
            # Generate new seed on pull-to-refresh
            if req.headers.get('X-Requested-With') == 'XMLHttpRequest' and not req.GET.get('page'):
                req.session['explore_feed_seed'] = random.randint(1, 10000)
                
            seed = req.session.get('explore_feed_seed', 42)
            random.seed(seed)
            
            # Shuffle admin dishes for variety, keep real dishes chronological
            random.shuffle(admin_dishes)
            
            # Put real user dishes on top
            dish_list = real_dishes + admin_dishes
            
        paginator = Paginator(dish_list, 30)
        page_number = req.GET.get('page')
        dish = paginator.get_page(page_number)
            
        dish_ids = [d.pk for d in dish]
        ingr = Ingredients.objects.filter(dish_id__in=dish_ids)
        cook = Cooking.objects.filter(dish_id__in=dish_ids)
        like = [] # Template doesn't use the full like object, only liked_dishes
        liked_dishes = set(Like.objects.filter(user=user).values_list('dish_id', flat=True))
        saved_dishes = set(Saved.objects.filter(user=user).values_list('dish_id', flat=True))
        unread_count = Notification.objects.filter(user=user, read=False).count()
        return render(req,'explore.html',{'dish':dish,'ingr':ingr,'cook':cook,'like':like,'liked_dishes':liked_dishes,'saved_dishes':saved_dishes,'unread_count':unread_count, 'q': q, 'detected': detected, 'searched_users': searched_users})
    else:
        return redirect(shop_login)
    
def result(req):
    return render(req,'result.html')

def search_dishes(req):
    query = req.GET.get('q', '')  # Get the search query from the request
    dishes=[]
    users=[]
    if query:
        req.session['last_searched'] = query
        base_q = (
            Q(name__icontains=query) | 
            Q(cuisine__icontains=query) | 
            Q(category__icontains=query) | 
            Q(ingredients__item__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__username__icontains=query)
        )
        dishes = Dish.objects.filter(base_q).distinct().order_by('-id')[:20]
        users = User.objects.filter(Q(first_name__icontains=query) | Q(username__icontains=query)).distinct()[:10]
        
    dishes_data = []
    for dish in dishes:
        dishes_data.append({
            'id': dish.id,
            'name': dish.name,
            'cuisine': dish.cuisine,
            'img_url': dish.img.url if dish.img else '',
        })

    users_data = []
    for user in users:
        profile_img = ''
        if hasattr(user, 'bio') and user.bio and user.bio.img:
            profile_img = user.bio.img.url
        users_data.append({
            'id': user.id,
            'first_name': user.first_name or user.username,
            'profile_img': profile_img,
        })
    # Return the data as JSON
    return JsonResponse({
        'dishes': dishes_data,
        'users': users_data,
    })


    # Return the HTML fragment with the search results


    
def profile(req):
    if 'user' in req.session:
        user=User.objects.get(username=req.session['user'])
        post=Dish.objects.filter(user=user).count()
        dish_list=Dish.objects.filter(user=user).order_by('-id')
        paginator = Paginator(dish_list, 30)
        page_number = req.GET.get('page')
        dish = paginator.get_page(page_number)
        dish_ids = [d.pk for d in dish]
        ingr = Ingredients.objects.filter(dish_id__in=dish_ids)
        cook = Cooking.objects.filter(dish_id__in=dish_ids)
        liked_dishes = set(Like.objects.filter(user=user).values_list('dish_id', flat=True))
        saved_dishes = set(Saved.objects.filter(user=user).values_list('dish_id', flat=True))
        saved_items = list(Saved.objects.filter(user=user).select_related('dish').order_by('-id')[:50])
        followers = (user.followers.all()).count()
        following = (user.following.all()).count()
        unread_count = Notification.objects.filter(user=user, read=False).count()
        return render(req,'profile.html',{'dish':dish,'ingr':ingr,'cook':cook,'liked_dishes':liked_dishes,'user':user,'post':post,'followers':followers,'following':following,'saved_dishes':saved_dishes,'saved_items':saved_items,'unread_count':unread_count})
    else:
        return redirect(shop_login)
    
def viewUser(req,pid):
    if 'user' in req.session:
        user1=User.objects.get(username=req.session['user'])
        user=User.objects.get(pk=pid)
        post=Dish.objects.filter(user=user).count()
        dish_list=Dish.objects.filter(user=user).order_by('-id')
        paginator = Paginator(dish_list, 30)
        page_number = req.GET.get('page')
        dish = paginator.get_page(page_number)
        dish_ids = [d.pk for d in dish]
        ingr = Ingredients.objects.filter(dish_id__in=dish_ids)
        cook = Cooking.objects.filter(dish_id__in=dish_ids)
        liked_dishes = set(Like.objects.filter(user=user1).values_list('dish_id', flat=True))
        saved_dishes = set(Saved.objects.filter(user=user1).values_list('dish_id', flat=True))
        followers = (user.followers.all()).count()
        following = (user.following.all()).count()
        unread_count = Notification.objects.filter(user=user1, read=False).count()
        is_following =  Follow.objects.filter(follower=user1, following=user).exists()
        if user1 == user :
            return redirect(profile)
        else:
            return render(req,'viewUser.html',{'dish':dish,'ingr':ingr,'cook':cook,'liked_dishes':liked_dishes,'is_following':is_following,'user':user,'user1':user1,'post':post,'followers':followers,'following':following,'saved_dishes':saved_dishes,'unread_count':unread_count})
    else:
        return redirect(shop_login)
    
def dish(req,pid):
    if 'user' in req.session:
        user=User.objects.get(username=req.session['user'])
        dish=Dish.objects.get(pk=pid)
        ingr=Ingredients.objects.filter(dish=dish)
        cook=Cooking.objects.filter(dish=dish)
        like=Like.objects.filter(dish=dish)
        save=Saved.objects.filter(dish=dish)
        liked_dishes = set(Like.objects.filter(user=user).values_list('dish_id', flat=True))
        saved_dishes = set(Saved.objects.filter(user=user).values_list('dish_id', flat=True))
        unread_count = Notification.objects.filter(user=user, read=False).count()
        return render(req,'dish.html',{'data':dish,'ingr':ingr,'cook':cook,'like':like,'liked_dishes':liked_dishes,'saved_dishes':saved_dishes,'unread_count':unread_count})
    else:
        return redirect(shop_login)
    
def addRecipe(req):
    if 'user' in req.session:
        if req.method=='POST':
            user=User.objects.get(username=req.session['user'])
            name=req.POST['name']
            img=req.FILES['img']
            cuisine=req.POST['cuisine']
            category=req.POST.get('category', 'Various')
            prep=req.POST['prep']
            cook=req.POST['cook']
            data=Dish.objects.create(user=user,name=name,img=img,cuisine=cuisine,category=category,prep=prep,cook=cook,likes=0)
            data.save()
            pk=data.pk
            
            ingredients = req.POST.getlist('ingredients[]')
            for ing in ingredients:
                if ing.strip():
                    Ingredients.objects.create(dish=data, item=ing.strip())
            
            steps = req.POST.getlist('steps[]')
            for step in steps:
                if step.strip():
                    Cooking.objects.create(dish=data, steps=step.strip())
            
            return redirect("dish", pid=pk)
        else:
            unread_count = Notification.objects.filter(user=User.objects.get(username=req.session['user']), read=False).count()
            return render(req,'addRecipe.html',{'unread_count':unread_count})
    else:
        return redirect(shop_login)
    
def delete(req,pid):
    if 'user' in req.session:
        data=Dish.objects.get(pk=pid)
        data.delete()
        return redirect(profile)
    if 'admin' in req.session:
        data=Dish.objects.get(pk=pid)
        data.delete()
        return redirect(reports)
    else:
        return redirect(shop_login)
    
def edit(req,pid):
    if 'user' in req.session:
        data=Dish.objects.get(pk=pid)
        if req.method=='POST':
            name=req.POST['name']
            img=req.FILES.get('img')
            cuisine=req.POST['cuisine']
            category=req.POST.get('category', 'Various')
            prep=req.POST['prep']
            cook=req.POST['cook']
            if img:
                Dish.objects.filter(pk=pid).update(name=name,cuisine=cuisine,category=category,prep=prep,cook=cook)
                url=data.img.url
                og_path=url.split('/')[-1]
                if os.path.exists('media/'+og_path):
                    os.remove('media/'+og_path)
                data.img=img
                data.save()
            else:
                Dish.objects.filter(pk=pid).update(name=name,cuisine=cuisine,category=category,prep=prep,cook=cook)
            
            # Clear existing ingredients and steps
            Ingredients.objects.filter(dish=data).delete()
            Cooking.objects.filter(dish=data).delete()
            
            # Add new ones
            ingredients = req.POST.getlist('ingredients[]')
            for ing in ingredients:
                if ing.strip():
                    Ingredients.objects.create(dish=data, item=ing.strip())
            
            steps = req.POST.getlist('steps[]')
            for step in steps:
                if step.strip():
                    Cooking.objects.create(dish=data, steps=step.strip())
                    
            return redirect('dish',pid=pid)
        else:
            ingr_data = Ingredients.objects.filter(dish=data)
            cook_data = Cooking.objects.filter(dish=data)
            unread_count = Notification.objects.filter(user=User.objects.get(username=req.session['user']), read=False).count()
            return render(req,'edit.html',{'data':data, 'ingr_data': ingr_data, 'cook_data': cook_data, 'unread_count':unread_count})
    else:
        return redirect(shop_login)
    
def like(req,pid):
    if 'user' in req.session:
        dish = Dish.objects.get(pk=pid)
        user = User.objects.get(username=req.session['user'])
    # Check if the user has already liked the dish
        existing_like = Like.objects.filter(user=user, dish=dish).first()
    
        if existing_like:
            # Unlike the dish
            existing_like.delete()
            dish.likes -= 1
            dish.save()
            liked = False
        else:
            # Like the dish
            Like.objects.create(user=user, dish=dish)
            dish.likes += 1
            dish.save()
            liked = True

        return JsonResponse({
            'liked': liked,
            'like_count': dish.likes
        })
    else:
        return redirect(shop_login)
    
def addLike(req,pid):
    if 'user' in req.session:
        user=User.objects.get(username=req.session['user'])
        dish=Dish.objects.get(pk=pid)
        dish.likes+=1
        dish.save()
        data=Like.objects.create(dish=dish,user=user)
        data.save()
        # return redirect(home)
        return redirect(req.META.get('HTTP_REFERER'))
    else:
        return redirect(shop_login)

def removeLike(req,pid):
    if 'user' in req.session:
        data=Dish.objects.get(pk=pid)
        user=User.objects.get(username=req.session['user'])
        data.likes-=1
        data.save()
        data=Like.objects.get(dish=pid,user=user)
        data.delete()
        # return redirect(home)
        return redirect(req.META.get('HTTP_REFERER'))
    else:
        return redirect(shop_login)
    
def report(req,pid):
    if 'user' in req.session:
        dish=Dish.objects.get(pk=pid)
        user=User.objects.get(username=req.session['user'])
        data=Report.objects.create(dish=dish,user=user)
        data.save()
        return redirect(req.META.get('HTTP_REFERER'))
    else:
        return redirect(shop_login)

def feedbacks(req,pid):
    if 'user' in req.session:
        user=User.objects.get(username=req.session['user'])
        dish=Dish.objects.get(pk=pid)
        if req.method=='POST':
            rate=req.POST['rating']
            data=Ratings.objects.create(user=user,dish=dish,ratings=rate)
            data.save()
            return redirect('dish',pid=pid)
        else:
            data=Ratings.objects.filter(dish=pid)
            ingr=Ingredients.objects.filter(dish=pid)
            cook=Cooking.objects.filter(dish=pid)
            unread_count = Notification.objects.filter(user=User.objects.get(username=req.session['user']), read=False).count()
            return render(req,'feedback.html',{'data':data,'dish':dish,'ingr':ingr,'cook':cook,'unread_count':unread_count})
    else:
        return redirect(shop_login)
    
def follow_user(req, uid):
    if 'user' in req.session:
        user=User.objects.get(username=req.session['user'])
        user_to_follow = User.objects.get(pk=uid)
        if user != user_to_follow:  # A user cannot follow themselves
            Follow.objects.create(follower=user, following=user_to_follow)
        return redirect('viewUser', pid=uid)
    else:
        return redirect(shop_login)

def unfollow_user(req, uid):
    if 'user' in req.session:
        user=User.objects.get(username=req.session['user'])
        user_to_unfollow = User.objects.get(pk=uid)
        if user != user_to_unfollow:
            Follow.objects.filter(follower=user, following=user_to_unfollow).delete()
        return redirect('viewUser', pid=uid)
    else:
        return redirect(shop_login)

def save(req,pid):
    if 'user' in req.session:
        user=User.objects.get(username=req.session['user'])
        dish=Dish.objects.get(pk=pid)
        data=Saved.objects.create(dish=dish,user=user)
        data.save()
        return redirect(req.META.get('HTTP_REFERER'))
    else:
        return redirect(shop_login) 
    
def unsave(req,pid):
    if 'user' in req.session:
        user=User.objects.get(username=req.session['user'])
        dish=Dish.objects.get(pk=pid)
        data=Saved.objects.get(dish=dish,user=user)
        data.delete()
        return redirect(req.META.get('HTTP_REFERER'))
    else:
        return redirect(shop_login) 

def saved(req):
    if 'user' in req.session:
        user=User.objects.get(username=req.session['user'])
        data=Saved.objects.filter(user=user)
        saved_dishes = [s.dish.pk for s in data]
        ingr=Ingredients.objects.filter(dish_id__in=saved_dishes)
        cook=Cooking.objects.filter(dish_id__in=saved_dishes)
        liked_dishes = set(Like.objects.filter(user=user).values_list('dish_id', flat=True))
        unread_count = Notification.objects.filter(user=User.objects.get(username=req.session['user']), read=False).count()
        return render(req,'saved.html',{'data':data,'ingr':ingr,'cook':cook,'liked_dishes':liked_dishes,'saved_dishes':saved_dishes,'unread_count':unread_count})
    else:
        return redirect(shop_login)
    


def notifications_view(req):
    if 'user' in req.session:
        user=User.objects.get(username=req.session['user'])
        # Evaluate to list first so template knows which were originally unread
        notifications = list(Notification.objects.filter(user=user).order_by('-id'))
        Notification.objects.filter(user=user, read=False).update(read=True)
        return render(req, 'notifications.html', {'notifications': notifications, 'unread_count': 0})
    else:
        return redirect('shop_login')

def editProfile(req):
    if 'user' in req.session:
        user=User.objects.get(username=req.session['user'])
        if req.method=='POST':
            img=req.FILES.get('img')
            bio=req.POST['bio']
            name=req.POST['name']
            if img:
                User.objects.filter(pk=user.pk).update(first_name=name)
                Bio.objects.filter(user=user).update(bio=bio)
                data=Bio.objects.get(user=user)
                url=data.img.url
                og_path=url.split('/')[-1]
                print(og_path)
                if og_path != 'profile.jpg':
                    os.remove('media/profile_pics/'+og_path)
                data.img=img
                data.save()
            else:
                User.objects.filter(pk=user.pk).update(first_name=name)
                Bio.objects.filter(user=user).update(bio=bio)
            return redirect(profile)
        else:
            return render(req,'editProfile.html',{'user':user})
    else:
        return redirect(shop_login)

def image_search(request):
    import os
    from django.conf import settings
    from .ml.image_recommender import get_similar_recipes_from_image
    from django.contrib.auth.models import User
    
    if request.method == 'POST' and request.FILES.get('food_image'):
        uploaded_file = request.FILES['food_image']
        
        # Save file temporarily
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_ai')
        os.makedirs(temp_dir, exist_ok=True)
        file_path = os.path.join(temp_dir, uploaded_file.name)
        
        with open(file_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
                
        # Analyze image using our new CLIP model and get top 5 dishes
        similar_dishes = get_similar_recipes_from_image(file_path, top_n=5)
        
        # Clean up the temporary file
        try:
            os.remove(file_path)
        except:
            pass
            
        # Get context required for explore.html
        if 'user' in request.session:
            user = User.objects.get(username=request.session['user'])
            dish = list(similar_dishes)
            dish_ids = [d.pk for d in dish]
            ingr = Ingredients.objects.filter(dish_id__in=dish_ids)
            cook = Cooking.objects.filter(dish_id__in=dish_ids)
            like = []
            liked_dishes = set(Like.objects.filter(user=user).values_list('dish_id', flat=True))
            saved_dishes = set(Saved.objects.filter(user=user).values_list('dish_id', flat=True))
            unread_count = Notification.objects.filter(user=user, read=False).count()
            
            return render(request, 'explore.html', {
                'dish': dish,
                'ingr': ingr,
                'cook': cook,
                'like': like,
                'liked_dishes': liked_dishes,
                'saved_dishes': saved_dishes,
                'unread_count': unread_count,
                'q': 'Image Search Results',
                'detected': None,
                'searched_users': []
            })
        else:
            return redirect(shop_login)
        
    return redirect('/')
