import os
import django
import pandas as pd
import ast
import urllib.request
from django.core.files.base import ContentFile

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "foodgram.settings")
django.setup()

from app.models import Dish, Ingredients, Cooking
from django.contrib.auth.models import User
from django.db import transaction

def import_recipes_from_csv(csv_path):
    user, created = User.objects.get_or_create(username='admin', defaults={
        'first_name': 'Admin',
        'email': 'admin@foodgram.com'
    })

    print(f"Reading dataset from {csv_path}...")
    try:
        df = pd.read_csv(csv_path)
        
        # Only keep recipes that actually have an image
        df = df.dropna(subset=['image_url'])
        
        # Importing top 50 recipes with images
        df = df.head(50) 
        
        print("Clearing old imported recipes so we don't have duplicates...")
        Dish.objects.filter(user=user).delete()

        ingredients_to_create = []
        cooking_to_create = []
        
        with transaction.atomic():
            for index, row in df.iterrows():
                print(f"Importing recipe: {row.get('name', 'Unknown')}")
                
                total_mins = int(row.get('minutes', 30))
                prep_mins = total_mins // 3
                cook_mins = total_mins - prep_mins
                
                dish = Dish.objects.create(
                    user=user,
                    name=row.get('name', 'Unnamed Recipe'),
                    cuisine='Various', 
                    prep=prep_mins, 
                    cook=cook_mins, 
                    likes=int(row.get('rating_value', 0) * 10) if pd.notna(row.get('rating_value')) else 0
                )
                
                # Download image if available
                image_url = row.get('image_url')
                if pd.notna(image_url) and isinstance(image_url, str) and image_url.startswith('http'):
                    try:
                        req = urllib.request.Request(image_url, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req, timeout=5) as response:
                            dish.img.save(f"recipe_{dish.id}.jpg", ContentFile(response.read()), save=True)
                    except Exception as e:
                        print(f"  - Could not download image: {e}")
                
                ingredients_str = row.get('ingredients', '[]')
                try:
                    ingredients_list = ast.literal_eval(ingredients_str)
                except:
                    ingredients_list = []
                    
                for item in ingredients_list:
                    ingredients_to_create.append(Ingredients(dish=dish, item=item.strip()))
                
                steps_str = row.get('steps', '[]')
                try:
                    steps_list = ast.literal_eval(steps_str)
                    formatted_steps = " ".join([f"{i+1}. {s}" for i, s in enumerate(steps_list)])
                except:
                    formatted_steps = "Follow instructions as needed."
                    
                cooking_to_create.append(Cooking(dish=dish, steps=formatted_steps))
                
                if len(ingredients_to_create) > 5000:
                    Ingredients.objects.bulk_create(ingredients_to_create)
                    ingredients_to_create = []
                if len(cooking_to_create) > 1000:
                    Cooking.objects.bulk_create(cooking_to_create)
                    cooking_to_create = []
                    
            if ingredients_to_create:
                Ingredients.objects.bulk_create(ingredients_to_create)
            if cooking_to_create:
                Cooking.objects.bulk_create(cooking_to_create)
            
        print("✅ Successfully imported enhanced dataset with images!")

    except FileNotFoundError:
        print(f"❌ Error: Could not find {csv_path}.")
    except Exception as e:
        print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    csv_file_name = "recipe_enhanced_v3.csv" 
    import_recipes_from_csv(csv_file_name)
