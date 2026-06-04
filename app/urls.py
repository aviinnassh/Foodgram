from django.urls import path
from . import views

urlpatterns=[
    path('shop_login',views.shop_login,name='shop_login'),
    path('validate',views.validate,name="validate"),
    path('logout',views.shp_logout),
    path('',views.home),


    # -----------------------------admin----------------------------
    path('adminHome',views.adminHome),
    path('reports',views.reports),
    path('viewUserAdmin/<pid>',views.viewUserAdmin,name='viewUserAdmin'),
    path('adminDish/<pid>',views.adminDish,name='adminDish'),
    path('removeReport/<pid>',views.removeReport),



    # -----------------------------user-----------------------------


    path('userHome',views.userHome),
    path('explore',views.explore),
    path('image_search/', views.image_search, name='image_search'),
    path('search_dishes/', views.search_dishes, name='search_dishes'),
    path('result', views.result),
    path('profile',views.profile),
    path('dish/<pid>',views.dish,name='dish'),
    path('addRecipe',views.addRecipe),
    path('delete/<pid>',views.delete),
    path('edit/<pid>',views.edit,name='edit'),
    path('like/<pid>/', views.like, name='like'),
    path('addLike/<pid>',views.addLike,name='addLike'),
    path('removeLike/<pid>',views.removeLike),
    path('viewUser/<pid>',views.viewUser,name='viewUser'),
    path('feedbacks/<pid>',views.feedbacks,name='feedbacks'),
    path('follow/<uid>', views.follow_user, name='follow_user'),
    path('unfollow/<uid>', views.unfollow_user, name='unfollow_user'),
    path('save/<pid>',views.save),
    path('unsave/<pid>',views.unsave),
    path('report/<pid>',views.report),
    path('saved',views.saved),
    path('notifications',views.notifications_view),
    path('editProfile',views.editProfile),
    path('recommend/<pid>', views.recommend_view, name='recommend'),

]