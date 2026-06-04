import random
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
# Create your models here.

class Dish(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE)
    name=models.TextField()
    img=models.FileField(max_length=500)
    cuisine=models.TextField()
    category=models.TextField(default='Various')
    prep=models.IntegerField()
    cook=models.IntegerField()
    likes=models.IntegerField()

    @property
    def fake_author_name(self):
        if self.user.username == 'admin':
            # Use dish ID as seed so the name is consistent for each dish
            random.seed(self.id)
            names = ["Chef John", "Chef Alice", "Foodie Guru", "Gourmet Expert", "Taste Maker", "Kitchen Wizard", "Culinary Master", "Flavor Artist"]
            name = random.choice(names)
            random.seed() # Reset seed
            return name
        return self.user.first_name or self.user.username

class Like(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE)
    dish=models.ForeignKey(Dish, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ('user', 'dish')

class Ratings(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE)
    dish=models.ForeignKey(Dish, on_delete=models.CASCADE)
    ratings=models.TextField()

class Saved(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE)
    dish=models.ForeignKey(Dish, on_delete=models.CASCADE)

class Ingredients(models.Model):
    dish=models.ForeignKey(Dish, on_delete=models.CASCADE)
    item=models.TextField()

class Cooking(models.Model):
    dish=models.ForeignKey(Dish, on_delete=models.CASCADE)
    steps=models.TextField()

class Bio(models.Model):
    user=models.OneToOneField(User,on_delete=models.CASCADE)
    img = models.FileField(upload_to='profile_pics/', default='profile_pics/profile.jpg', max_length=500)
    bio=models.TextField(default="Hi,I'm here")

class Follow(models.Model):
    follower = models.ForeignKey(User, related_name='following', on_delete=models.CASCADE)
    following = models.ForeignKey(User, related_name='followers', on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')  # Ensure that a user can't follow the same user more than once

    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications_received')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications_sent', null=True, blank=True)
    message = models.TextField()
    read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification for {self.user.username}"

class Report(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    dish=models.ForeignKey(Dish, on_delete=models.CASCADE)

