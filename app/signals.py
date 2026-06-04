from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import *
from django.contrib.auth.models import User

@receiver(post_save, sender=Follow)
def create_follow_notification(sender, instance, created, **kwargs):
    if kwargs.get('raw', False):
        return
    if created:  # Only create notification when a new follow is created
        # Notify the user being followed
        Notification.objects.create(
            user=instance.following,
            sender=instance.follower,
            message="started following you",
        )

@receiver(post_save, sender=Like)
def create_like_notification(sender, instance, created, **kwargs):
    if kwargs.get('raw', False):
        return
    if created:  # Only create notification when a new like is added
        # Notify the user who posted the liked post
        Notification.objects.create(
            user=instance.dish.user,
            sender=instance.user,
            message="liked your post",
        )

@receiver(post_save, sender=Ratings)
def create_rating_notification(sender, instance, created, **kwargs):
    if kwargs.get('raw', False):
        return
    if created:  # Only create notification when a new rating is added
        Notification.objects.create(
            user=instance.dish.user,
            sender=instance.user,
            message="commented on your post",
        )

@receiver(post_save, sender=User)
def create_user_bio(sender, instance, created, **kwargs):
    if kwargs.get('raw', False):
        return
    # Automatically create a Bio when a new User is created
    if created:
        Bio.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_bio(sender, instance, **kwargs):
    if kwargs.get('raw', False):
        return
    # Save the user's bio if it is updated
    if hasattr(instance, 'bio'):
        instance.bio.save()

@receiver(post_save, sender=Dish)
def update_image_index(sender, instance, created, **kwargs):
    if kwargs.get('raw', False):
        return
    # Automatically add to FAISS index when a Dish is created or updated
    try:
        from .ml.image_recommender import add_dish_to_index
        add_dish_to_index(instance)
    except Exception as e:
        print(f"Error in update_image_index signal: {e}")